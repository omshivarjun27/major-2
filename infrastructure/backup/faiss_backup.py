"""FAISS index backup and restore procedures.

Implements automated backup with compression, retention policies,
and validation. Supports local filesystem and S3-compatible storage.

Task: T-098 - FAISS Backup/Restore
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Storage Backend Protocol
# ─────────────────────────────────────────────────────────────────────────────

class StorageBackend(Protocol):
    """Protocol for backup storage backends."""
    
    def upload(self, local_path: Path, remote_key: str) -> bool:
        """Upload a file to remote storage."""
        ...
    
    def download(self, remote_key: str, local_path: Path) -> bool:
        """Download a file from remote storage."""
        ...
    
    def list_backups(self, prefix: str) -> List[str]:
        """List backup files with prefix."""
        ...
    
    def delete(self, remote_key: str) -> bool:
        """Delete a file from remote storage."""
        ...
    
    def exists(self, remote_key: str) -> bool:
        """Check if a file exists."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Local Filesystem Backend
# ─────────────────────────────────────────────────────────────────────────────

class LocalStorageBackend:
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: Path):
        """Initialize local storage backend.
        
        Args:
            base_path: Base directory for storing backups
        """
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
    
    def upload(self, local_path: Path, remote_key: str) -> bool:
        """Copy file to backup location."""
        try:
            dest = self._base_path / remote_key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest)
            logger.debug("Uploaded %s to %s", local_path, dest)
            return True
        except Exception as e:
            logger.error("Failed to upload %s: %s", local_path, e)
            return False
    
    def download(self, remote_key: str, local_path: Path) -> bool:
        """Copy file from backup location."""
        try:
            src = self._base_path / remote_key
            if not src.exists():
                logger.error("Backup file not found: %s", src)
                return False
            local_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, local_path)
            logger.debug("Downloaded %s to %s", src, local_path)
            return True
        except Exception as e:
            logger.error("Failed to download %s: %s", remote_key, e)
            return False
    
    def list_backups(self, prefix: str) -> List[str]:
        """List backup files with prefix."""
        try:
            pattern = f"{prefix}*"
            return sorted([
                str(p.relative_to(self._base_path))
                for p in self._base_path.glob(pattern)
                if p.is_file()
            ])
        except Exception as e:
            logger.error("Failed to list backups: %s", e)
            return []
    
    def delete(self, remote_key: str) -> bool:
        """Delete backup file."""
        try:
            path = self._base_path / remote_key
            if path.exists():
                path.unlink()
                logger.debug("Deleted %s", path)
            return True
        except Exception as e:
            logger.error("Failed to delete %s: %s", remote_key, e)
            return False
    
    def exists(self, remote_key: str) -> bool:
        """Check if backup exists."""
        return (self._base_path / remote_key).exists()


# ─────────────────────────────────────────────────────────────────────────────
# S3-Compatible Backend
# ─────────────────────────────────────────────────────────────────────────────

class S3StorageBackend:
    """S3-compatible storage backend (AWS S3, MinIO, etc.)."""
    
    def __init__(
        self,
        bucket: str,
        prefix: str = "backups/faiss/",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        """Initialize S3 storage backend.
        
        Args:
            bucket: S3 bucket name
            prefix: Key prefix for all backups
            endpoint_url: Custom endpoint for S3-compatible services
            aws_access_key_id: AWS access key (or from env)
            aws_secret_access_key: AWS secret key (or from env)
            region_name: AWS region
        """
        self._bucket = bucket
        self._prefix = prefix
        self._endpoint_url = endpoint_url
        self._client = None
        
        # Store credentials for lazy initialization
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._region_name = region_name
    
    def _get_client(self):
        """Lazily initialize S3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self._endpoint_url,
                    aws_access_key_id=self._aws_access_key_id,
                    aws_secret_access_key=self._aws_secret_access_key,
                    region_name=self._region_name,
                )
            except ImportError:
                raise RuntimeError("boto3 not installed. Run: pip install boto3")
        return self._client
    
    def upload(self, local_path: Path, remote_key: str) -> bool:
        """Upload file to S3."""
        try:
            client = self._get_client()
            key = f"{self._prefix}{remote_key}"
            client.upload_file(str(local_path), self._bucket, key)
            logger.debug("Uploaded %s to s3://%s/%s", local_path, self._bucket, key)
            return True
        except Exception as e:
            logger.error("S3 upload failed: %s", e)
            return False
    
    def download(self, remote_key: str, local_path: Path) -> bool:
        """Download file from S3."""
        try:
            client = self._get_client()
            key = f"{self._prefix}{remote_key}"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(self._bucket, key, str(local_path))
            logger.debug("Downloaded s3://%s/%s to %s", self._bucket, key, local_path)
            return True
        except Exception as e:
            logger.error("S3 download failed: %s", e)
            return False
    
    def list_backups(self, prefix: str) -> List[str]:
        """List backups in S3."""
        try:
            client = self._get_client()
            full_prefix = f"{self._prefix}{prefix}"
            response = client.list_objects_v2(Bucket=self._bucket, Prefix=full_prefix)
            
            keys = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                # Remove the base prefix to get relative key
                relative_key = key[len(self._prefix):] if key.startswith(self._prefix) else key
                keys.append(relative_key)
            
            return sorted(keys)
        except Exception as e:
            logger.error("S3 list failed: %s", e)
            return []
    
    def delete(self, remote_key: str) -> bool:
        """Delete file from S3."""
        try:
            client = self._get_client()
            key = f"{self._prefix}{remote_key}"
            client.delete_object(Bucket=self._bucket, Key=key)
            logger.debug("Deleted s3://%s/%s", self._bucket, key)
            return True
        except Exception as e:
            logger.error("S3 delete failed: %s", e)
            return False
    
    def exists(self, remote_key: str) -> bool:
        """Check if file exists in S3."""
        try:
            client = self._get_client()
            key = f"{self._prefix}{remote_key}"
            client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False


# ─────────────────────────────────────────────────────────────────────────────
# Backup Metadata
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BackupMetadata:
    """Metadata for a FAISS index backup."""
    
    backup_id: str
    index_name: str
    created_at: str  # ISO 8601
    vector_count: int
    dimension: int
    original_size_bytes: int
    compressed_size_bytes: int
    checksum_sha256: str
    compression: str = "gzip"
    faiss_version: str = "unknown"
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "backup_id": self.backup_id,
            "index_name": self.index_name,
            "created_at": self.created_at,
            "vector_count": self.vector_count,
            "dimension": self.dimension,
            "original_size_bytes": self.original_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "compression": self.compression,
            "faiss_version": self.faiss_version,
            "extra": self.extra,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupMetadata":
        """Create from dictionary."""
        return cls(
            backup_id=data["backup_id"],
            index_name=data["index_name"],
            created_at=data["created_at"],
            vector_count=data["vector_count"],
            dimension=data["dimension"],
            original_size_bytes=data["original_size_bytes"],
            compressed_size_bytes=data["compressed_size_bytes"],
            checksum_sha256=data["checksum_sha256"],
            compression=data.get("compression", "gzip"),
            faiss_version=data.get("faiss_version", "unknown"),
            extra=data.get("extra", {}),
        )


# ─────────────────────────────────────────────────────────────────────────────
# FAISS Backup Manager
# ─────────────────────────────────────────────────────────────────────────────

class FAISSBackupManager:
    """Manages FAISS index backup and restore operations.
    
    Features:
    - Gzip compression
    - SHA-256 checksum validation
    - Configurable retention (default 30 days)
    - Support for local and S3 storage backends
    - Incremental backup support via checksum comparison
    """
    
    def __init__(
        self,
        storage: StorageBackend,
        retention_days: int = 30,
    ):
        """Initialize backup manager.
        
        Args:
            storage: Storage backend for backups
            retention_days: Number of days to retain backups
        """
        self._storage = storage
        self._retention_days = retention_days
    
    def backup(
        self,
        index_path: Path,
        index_name: str = "default",
        vector_count: int = 0,
        dimension: int = 0,
        incremental: bool = True,
    ) -> Optional[BackupMetadata]:
        """Create a backup of a FAISS index.
        
        Args:
            index_path: Path to the FAISS index file
            index_name: Name identifier for the index
            vector_count: Number of vectors in the index
            dimension: Vector dimension
            incremental: Skip backup if unchanged (based on checksum)
            
        Returns:
            BackupMetadata if successful, None otherwise
        """
        if not index_path.exists():
            logger.error("Index file not found: %s", index_path)
            return None
        
        try:
            # Calculate checksum of original file
            checksum = self._calculate_checksum(index_path)
            original_size = index_path.stat().st_size
            
            # Check for incremental backup
            if incremental:
                latest = self._get_latest_backup(index_name)
                if latest and latest.checksum_sha256 == checksum:
                    logger.info("Index unchanged, skipping backup: %s", index_name)
                    return latest
            
            # Generate backup ID
            timestamp = datetime.now(timezone.utc)
            backup_id = f"{index_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # Compress the index
            with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as tmp:
                compressed_path = Path(tmp.name)
            
            self._compress_file(index_path, compressed_path)
            compressed_size = compressed_path.stat().st_size
            
            # Upload compressed backup
            backup_key = f"{index_name}/{backup_id}.index.gz"
            if not self._storage.upload(compressed_path, backup_key):
                logger.error("Failed to upload backup: %s", backup_key)
                compressed_path.unlink()
                return None
            
            # Clean up temp file
            compressed_path.unlink()
            
            # Get FAISS version if available
            faiss_version = "unknown"
            try:
                import faiss
                faiss_version = faiss.__version__
            except ImportError:
                pass
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                index_name=index_name,
                created_at=timestamp.isoformat(),
                vector_count=vector_count,
                dimension=dimension,
                original_size_bytes=original_size,
                compressed_size_bytes=compressed_size,
                checksum_sha256=checksum,
                faiss_version=faiss_version,
            )
            
            # Upload metadata
            metadata_key = f"{index_name}/{backup_id}.metadata.json"
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(metadata.to_dict(), f, indent=2)
                metadata_path = Path(f.name)
            
            self._storage.upload(metadata_path, metadata_key)
            metadata_path.unlink()
            
            logger.info(
                "Backup created: %s (%d bytes -> %d bytes, %.1f%% compression)",
                backup_id,
                original_size,
                compressed_size,
                (1 - compressed_size / original_size) * 100 if original_size > 0 else 0,
            )
            
            # Emit Prometheus metric
            try:
                from infrastructure.monitoring import get_metrics
                get_metrics().set_queue_size(f"faiss_backup_{index_name}_size", compressed_size)
            except Exception:
                pass
            
            return metadata
            
        except Exception as e:
            logger.error("Backup failed: %s", e, exc_info=True)
            return None
    
    def restore(
        self,
        backup_id: str,
        index_name: str,
        restore_path: Path,
        verify: bool = True,
    ) -> bool:
        """Restore a FAISS index from backup.
        
        Args:
            backup_id: Backup ID to restore
            index_name: Index name
            restore_path: Path to restore the index to
            verify: Verify checksum after restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Download metadata
            metadata_key = f"{index_name}/{backup_id}.metadata.json"
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                metadata_path = Path(f.name)
            
            if not self._storage.download(metadata_key, metadata_path):
                logger.error("Failed to download backup metadata: %s", metadata_key)
                return False
            
            with open(metadata_path) as f:
                metadata = BackupMetadata.from_dict(json.load(f))
            metadata_path.unlink()
            
            # Download compressed backup
            backup_key = f"{index_name}/{backup_id}.index.gz"
            with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f:
                compressed_path = Path(f.name)
            
            if not self._storage.download(backup_key, compressed_path):
                logger.error("Failed to download backup: %s", backup_key)
                compressed_path.unlink()
                return False
            
            # Decompress
            restore_path.parent.mkdir(parents=True, exist_ok=True)
            self._decompress_file(compressed_path, restore_path)
            compressed_path.unlink()
            
            # Verify checksum
            if verify:
                restored_checksum = self._calculate_checksum(restore_path)
                if restored_checksum != metadata.checksum_sha256:
                    logger.error(
                        "Checksum mismatch! Expected %s, got %s",
                        metadata.checksum_sha256,
                        restored_checksum,
                    )
                    restore_path.unlink()
                    return False
            
            logger.info("Restored backup %s to %s", backup_id, restore_path)
            return True
            
        except Exception as e:
            logger.error("Restore failed: %s", e, exc_info=True)
            return False
    
    def list_backups(self, index_name: str) -> List[BackupMetadata]:
        """List all backups for an index.
        
        Args:
            index_name: Index name
            
        Returns:
            List of backup metadata, sorted by creation time (newest first)
        """
        try:
            prefix = f"{index_name}/"
            keys = self._storage.list_backups(prefix)
            
            metadata_list = []
            for key in keys:
                if key.endswith(".metadata.json"):
                    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
                        metadata_path = Path(f.name)
                    
                    if self._storage.download(key, metadata_path):
                        with open(metadata_path) as f:
                            metadata = BackupMetadata.from_dict(json.load(f))
                            metadata_list.append(metadata)
                        metadata_path.unlink()
            
            # Sort by creation time (newest first)
            metadata_list.sort(key=lambda m: m.created_at, reverse=True)
            return metadata_list
            
        except Exception as e:
            logger.error("Failed to list backups: %s", e)
            return []
    
    def cleanup_old_backups(self, index_name: str) -> int:
        """Delete backups older than retention period.
        
        Args:
            index_name: Index name
            
        Returns:
            Number of backups deleted
        """
        try:
            backups = self.list_backups(index_name)
            cutoff = datetime.now(timezone.utc).timestamp() - (self._retention_days * 86400)
            
            deleted = 0
            for backup in backups:
                created = datetime.fromisoformat(backup.created_at.replace("Z", "+00:00"))
                if created.timestamp() < cutoff:
                    # Delete backup and metadata
                    backup_key = f"{index_name}/{backup.backup_id}.index.gz"
                    metadata_key = f"{index_name}/{backup.backup_id}.metadata.json"
                    
                    self._storage.delete(backup_key)
                    self._storage.delete(metadata_key)
                    deleted += 1
                    logger.info("Deleted old backup: %s", backup.backup_id)
            
            return deleted
            
        except Exception as e:
            logger.error("Cleanup failed: %s", e)
            return 0
    
    def verify_backup(self, backup_id: str, index_name: str) -> bool:
        """Verify a backup by downloading and checking integrity.
        
        Args:
            backup_id: Backup ID to verify
            index_name: Index name
            
        Returns:
            True if backup is valid
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                restore_path = Path(tmpdir) / "test_restore.index"
                if not self.restore(backup_id, index_name, restore_path, verify=True):
                    return False
                
                # Optionally try to load with FAISS
                try:
                    import faiss
                    index = faiss.read_index(str(restore_path))
                    logger.info(
                        "Backup %s verified: %d vectors",
                        backup_id,
                        index.ntotal,
                    )
                except ImportError:
                    logger.debug("FAISS not available for index validation")
                except Exception as e:
                    logger.error("FAISS index validation failed: %s", e)
                    return False
                
                return True
                
        except Exception as e:
            logger.error("Backup verification failed: %s", e)
            return False
    
    def _get_latest_backup(self, index_name: str) -> Optional[BackupMetadata]:
        """Get the most recent backup for an index."""
        backups = self.list_backups(index_name)
        return backups[0] if backups else None
    
    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _compress_file(self, src: Path, dst: Path) -> None:
        """Compress a file with gzip."""
        with open(src, "rb") as f_in:
            with gzip.open(dst, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _decompress_file(self, src: Path, dst: Path) -> None:
        """Decompress a gzip file."""
        with gzip.open(src, "rb") as f_in:
            with open(dst, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)


# ─────────────────────────────────────────────────────────────────────────────
# Factory Function
# ─────────────────────────────────────────────────────────────────────────────

def create_faiss_backup_manager(
    backend: str = "local",
    local_path: Optional[str] = None,
    s3_bucket: Optional[str] = None,
    s3_endpoint: Optional[str] = None,
    retention_days: int = 30,
) -> FAISSBackupManager:
    """Create a FAISS backup manager with specified backend.
    
    Args:
        backend: Storage backend type ("local" or "s3")
        local_path: Path for local storage backend
        s3_bucket: S3 bucket name
        s3_endpoint: S3 endpoint URL (for MinIO, etc.)
        retention_days: Backup retention period
        
    Returns:
        Configured FAISSBackupManager
    """
    if backend == "local":
        path = Path(local_path or os.environ.get("FAISS_BACKUP_PATH", "data/backups/faiss"))
        storage = LocalStorageBackend(path)
    elif backend == "s3":
        bucket = s3_bucket or os.environ.get("FAISS_BACKUP_S3_BUCKET", "voice-vision-backups")
        storage = S3StorageBackend(
            bucket=bucket,
            endpoint_url=s3_endpoint or os.environ.get("S3_ENDPOINT_URL"),
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")
    
    return FAISSBackupManager(storage=storage, retention_days=retention_days)
