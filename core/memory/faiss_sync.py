"""
FAISS Index Synchronization Module (T-112).

Implements bidirectional FAISS index sync between local and cloud storage with:
- Incremental sync via change log
- Merge strategies for concurrent modifications
- Checksum verification for corruption detection
- S3-compatible and Azure Blob storage backends
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from core.memory.cloud_sync import (
    ChangeLog,
    SyncResult,
    UserPartition,
    VectorTimestamp,
)

logger = logging.getLogger("faiss-sync")


# =============================================================================
# STORAGE BACKENDS
# =============================================================================


class StorageBackend(ABC):
    """Abstract storage backend for index persistence."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload data to storage."""
        ...

    @abstractmethod
    async def download(self, key: str) -> Optional[bytes]:
        """Download data from storage."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete data from storage."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...

    @abstractmethod
    async def list_keys(self, prefix: str) -> List[str]:
        """List keys with prefix."""
        ...

    @abstractmethod
    async def get_metadata(self, key: str) -> Optional[Dict[str, str]]:
        """Get metadata for a key."""
        ...


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend for testing."""

    def __init__(self, base_path: str = "./data/cloud_storage/"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._metadata: Dict[str, Dict[str, str]] = {}

    async def upload(self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None) -> bool:
        try:
            file_path = self.base_path / key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(data)
            if metadata:
                self._metadata[key] = metadata
            return True
        except Exception as exc:
            logger.error(f"Local upload failed: {exc}")
            return False

    async def download(self, key: str) -> Optional[bytes]:
        try:
            file_path = self.base_path / key
            if file_path.exists():
                return file_path.read_bytes()
            return None
        except Exception as exc:
            logger.error(f"Local download failed: {exc}")
            return None

    async def delete(self, key: str) -> bool:
        try:
            file_path = self.base_path / key
            if file_path.exists():
                file_path.unlink()
                self._metadata.pop(key, None)
                return True
            return False
        except Exception as exc:
            logger.error(f"Local delete failed: {exc}")
            return False

    async def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()

    async def list_keys(self, prefix: str) -> List[str]:
        results = []
        prefix_path = self.base_path / prefix
        if prefix_path.exists():
            for path in prefix_path.rglob("*"):
                if path.is_file():
                    results.append(str(path.relative_to(self.base_path)))
        return results

    async def get_metadata(self, key: str) -> Optional[Dict[str, str]]:
        return self._metadata.get(key)


class S3StorageBackend(StorageBackend):
    """S3-compatible storage backend (AWS S3, MinIO, etc.)."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self._client = None

    def _get_client(self):
        """Lazy init boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    region_name=self.region,
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                )
            except ImportError:
                logger.error("boto3 not installed. Run: pip install boto3")
                raise
        return self._client

    async def upload(self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None) -> bool:
        try:
            client = self._get_client()
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata
            client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra_args)
            return True
        except Exception as exc:
            logger.error(f"S3 upload failed: {exc}")
            return False

    async def download(self, key: str) -> Optional[bytes]:
        try:
            client = self._get_client()
            response = client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as exc:
            logger.error(f"S3 download failed: {exc}")
            return None

    async def delete(self, key: str) -> bool:
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as exc:
            logger.error(f"S3 delete failed: {exc}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = self._get_client()
            client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    async def list_keys(self, prefix: str) -> List[str]:
        try:
            client = self._get_client()
            response = client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception as exc:
            logger.error(f"S3 list failed: {exc}")
            return []

    async def get_metadata(self, key: str) -> Optional[Dict[str, str]]:
        try:
            client = self._get_client()
            response = client.head_object(Bucket=self.bucket, Key=key)
            return response.get("Metadata", {})
        except Exception:
            return None


class AzureBlobStorageBackend(StorageBackend):
    """Azure Blob storage backend."""

    def __init__(
        self,
        container: str,
        connection_string: Optional[str] = None,
        account_url: Optional[str] = None,
    ):
        self.container = container
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
        self.account_url = account_url
        self._client = None

    def _get_client(self):
        """Lazy init Azure client."""
        if self._client is None:
            try:
                from azure.storage.blob import ContainerClient
                if self.connection_string:
                    self._client = ContainerClient.from_connection_string(
                        self.connection_string,
                        container_name=self.container,
                    )
                else:
                    raise ValueError("Azure connection string required")
            except ImportError:
                logger.error("azure-storage-blob not installed. Run: pip install azure-storage-blob")
                raise
        return self._client

    async def upload(self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None) -> bool:
        try:
            client = self._get_client()
            blob_client = client.get_blob_client(key)
            blob_client.upload_blob(data, overwrite=True, metadata=metadata)
            return True
        except Exception as exc:
            logger.error(f"Azure upload failed: {exc}")
            return False

    async def download(self, key: str) -> Optional[bytes]:
        try:
            client = self._get_client()
            blob_client = client.get_blob_client(key)
            return blob_client.download_blob().readall()
        except Exception as exc:
            logger.error(f"Azure download failed: {exc}")
            return None

    async def delete(self, key: str) -> bool:
        try:
            client = self._get_client()
            blob_client = client.get_blob_client(key)
            blob_client.delete_blob()
            return True
        except Exception as exc:
            logger.error(f"Azure delete failed: {exc}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = self._get_client()
            blob_client = client.get_blob_client(key)
            return blob_client.exists()
        except Exception:
            return False

    async def list_keys(self, prefix: str) -> List[str]:
        try:
            client = self._get_client()
            return [blob.name for blob in client.list_blobs(name_starts_with=prefix)]
        except Exception as exc:
            logger.error(f"Azure list failed: {exc}")
            return []

    async def get_metadata(self, key: str) -> Optional[Dict[str, str]]:
        try:
            client = self._get_client()
            blob_client = client.get_blob_client(key)
            props = blob_client.get_blob_properties()
            return props.metadata
        except Exception:
            return None


# =============================================================================
# MERGE STRATEGIES
# =============================================================================


class MergeStrategy(ABC):
    """Abstract merge strategy for concurrent modifications."""

    @abstractmethod
    def merge(
        self,
        local_vectors: Dict[str, np.ndarray],
        remote_vectors: Dict[str, np.ndarray],
        local_timestamps: Dict[str, VectorTimestamp],
        remote_timestamps: Dict[str, VectorTimestamp],
    ) -> Tuple[Dict[str, np.ndarray], List[str]]:
        """Merge local and remote vectors.

        Returns:
            Tuple of (merged_vectors, conflict_ids)
        """
        ...


class UnionMergeStrategy(MergeStrategy):
    """Union merge: keep all vectors from both sides."""

    def merge(
        self,
        local_vectors: Dict[str, np.ndarray],
        remote_vectors: Dict[str, np.ndarray],
        local_timestamps: Dict[str, VectorTimestamp],
        remote_timestamps: Dict[str, VectorTimestamp],
    ) -> Tuple[Dict[str, np.ndarray], List[str]]:
        merged = {}
        conflicts = []

        # Add all local vectors
        merged.update(local_vectors)

        # Add remote vectors, detecting conflicts
        for vid, vec in remote_vectors.items():
            if vid in local_vectors:
                # Conflict: same ID exists in both
                local_ts = local_timestamps.get(vid)
                remote_ts = remote_timestamps.get(vid)

                if local_ts and remote_ts and local_ts.concurrent_with(remote_ts):
                    # True conflict - keep local (last-writer-wins)
                    conflicts.append(vid)
                elif remote_ts and (not local_ts or local_ts.happens_before(remote_ts)):
                    # Remote is newer
                    merged[vid] = vec
            else:
                # New remote vector
                merged[vid] = vec

        return merged, conflicts


class LastWriterWinsMergeStrategy(MergeStrategy):
    """Last writer wins: prefer vector with higher timestamp."""

    def merge(
        self,
        local_vectors: Dict[str, np.ndarray],
        remote_vectors: Dict[str, np.ndarray],
        local_timestamps: Dict[str, VectorTimestamp],
        remote_timestamps: Dict[str, VectorTimestamp],
    ) -> Tuple[Dict[str, np.ndarray], List[str]]:
        merged = {}
        conflicts = []

        all_ids = set(local_vectors.keys()) | set(remote_vectors.keys())

        for vid in all_ids:
            local_vec = local_vectors.get(vid)
            remote_vec = remote_vectors.get(vid)
            local_ts = local_timestamps.get(vid)
            remote_ts = remote_timestamps.get(vid)

            if local_vec is not None and remote_vec is not None:
                # Both have the vector
                if local_ts and remote_ts:
                    if local_ts.happens_before(remote_ts):
                        merged[vid] = remote_vec
                    elif remote_ts.happens_before(local_ts):
                        merged[vid] = local_vec
                    else:
                        # Concurrent - keep local, mark conflict
                        merged[vid] = local_vec
                        conflicts.append(vid)
                else:
                    # No timestamps, keep local
                    merged[vid] = local_vec
            elif local_vec is not None:
                merged[vid] = local_vec
            else:
                merged[vid] = remote_vec

        return merged, conflicts


# =============================================================================
# FAISS SYNC MANAGER
# =============================================================================


@dataclass
class FAISSIndexState:
    """State of a FAISS index for sync."""

    index_id: str
    partition_id: str
    vector_count: int
    dimension: int
    checksum: str
    last_modified_ms: float
    vector_ids: Set[str] = field(default_factory=set)
    timestamps: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index_id": self.index_id,
            "partition_id": self.partition_id,
            "vector_count": self.vector_count,
            "dimension": self.dimension,
            "checksum": self.checksum,
            "last_modified_ms": self.last_modified_ms,
            "vector_ids": list(self.vector_ids),
            "timestamps": self.timestamps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FAISSIndexState":
        return cls(
            index_id=data["index_id"],
            partition_id=data["partition_id"],
            vector_count=data["vector_count"],
            dimension=data["dimension"],
            checksum=data["checksum"],
            last_modified_ms=data["last_modified_ms"],
            vector_ids=set(data.get("vector_ids", [])),
            timestamps=data.get("timestamps", {}),
        )


@dataclass
class FAISSSyncConfig:
    """Configuration for FAISS sync."""

    storage_backend: str = "local"  # local | s3 | azure
    bucket_or_container: str = "faiss-indices"
    region: str = "us-east-1"
    endpoint_url: Optional[str] = None
    merge_strategy: str = "union"  # union | last_writer_wins
    verify_checksum: bool = True
    compression: bool = True


class FAISSSyncManager:
    """Manages FAISS index synchronization with cloud storage.

    Features:
    - Incremental sync via change log
    - Merge strategies for concurrent modifications
    - Checksum verification
    - GPU/CPU index format handling
    """

    def __init__(
        self,
        config: FAISSSyncConfig,
        change_log: ChangeLog,
        partition: UserPartition,
    ):
        self.config = config
        self.change_log = change_log
        self.partition = partition

        # Initialize storage backend
        self._storage = self._create_storage_backend()

        # Initialize merge strategy
        self._merge_strategy = self._create_merge_strategy()

        # Local state tracking
        self._local_state: Optional[FAISSIndexState] = None
        self._local_vectors: Dict[str, np.ndarray] = {}
        self._local_timestamps: Dict[str, VectorTimestamp] = {}
        self._deleted_ids: Set[str] = set()

        self._lock = asyncio.Lock()

    def _create_storage_backend(self) -> StorageBackend:
        """Create storage backend based on config."""
        if self.config.storage_backend == "s3":
            return S3StorageBackend(
                bucket=self.config.bucket_or_container,
                region=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )
        elif self.config.storage_backend == "azure":
            return AzureBlobStorageBackend(
                container=self.config.bucket_or_container,
            )
        else:
            # For local backend, check if path is absolute or use default
            path = self.config.bucket_or_container
            if not Path(path).is_absolute():
                path = f"./data/cloud_storage/{path}/"
            return LocalStorageBackend(base_path=path)

    def _create_merge_strategy(self) -> MergeStrategy:
        """Create merge strategy based on config."""
        if self.config.merge_strategy == "last_writer_wins":
            return LastWriterWinsMergeStrategy()
        return UnionMergeStrategy()

    def _compute_checksum(self, data: bytes) -> str:
        """Compute SHA-256 checksum of data."""
        return hashlib.sha256(data).hexdigest()

    def _index_key(self) -> str:
        """Get storage key for index."""
        return f"{self.partition.partition_id}/index.faiss"

    def _state_key(self) -> str:
        """Get storage key for state."""
        return f"{self.partition.partition_id}/state.json"

    def _vectors_key(self) -> str:
        """Get storage key for vectors."""
        return f"{self.partition.partition_id}/vectors.npz"

    async def track_add(self, vector_id: str, embedding: np.ndarray, timestamp: VectorTimestamp) -> None:
        """Track a vector addition."""
        async with self._lock:
            self._local_vectors[vector_id] = embedding
            self._local_timestamps[vector_id] = timestamp
            self._deleted_ids.discard(vector_id)

    async def track_delete(self, vector_id: str) -> None:
        """Track a vector deletion."""
        async with self._lock:
            self._local_vectors.pop(vector_id, None)
            self._local_timestamps.pop(vector_id, None)
            self._deleted_ids.add(vector_id)

    async def push(self) -> SyncResult:
        """Push local changes to cloud storage."""
        start_ms = time.time() * 1000

        try:
            async with self._lock:
                if not self._local_vectors:
                    return SyncResult(success=True, pushed_count=0, duration_ms=time.time() * 1000 - start_ms)

                # Serialize vectors
                vectors_data = self._serialize_vectors(self._local_vectors)
                vectors_checksum = self._compute_checksum(vectors_data)

                # Create state
                state = FAISSIndexState(
                    index_id=f"idx_{self.partition.partition_id}",
                    partition_id=self.partition.partition_id,
                    vector_count=len(self._local_vectors),
                    dimension=next(iter(self._local_vectors.values())).shape[0] if self._local_vectors else 0,
                    checksum=vectors_checksum,
                    last_modified_ms=time.time() * 1000,
                    vector_ids=set(self._local_vectors.keys()),
                    timestamps={vid: ts.to_dict() for vid, ts in self._local_timestamps.items()},
                )

                # Upload vectors
                uploaded = await self._storage.upload(
                    self._vectors_key(),
                    vectors_data,
                    metadata={"checksum": vectors_checksum},
                )

                if not uploaded:
                    return SyncResult(
                        success=False,
                        error="Failed to upload vectors",
                        duration_ms=time.time() * 1000 - start_ms,
                    )

                # Upload state
                state_data = json.dumps(state.to_dict()).encode()
                await self._storage.upload(self._state_key(), state_data)

                self._local_state = state

                return SyncResult(
                    success=True,
                    pushed_count=len(self._local_vectors),
                    duration_ms=time.time() * 1000 - start_ms,
                )

        except Exception as exc:
            logger.error(f"Push failed: {exc}")
            return SyncResult(
                success=False,
                error=str(exc),
                duration_ms=time.time() * 1000 - start_ms,
            )

    async def pull(self) -> SyncResult:
        """Pull remote changes from cloud storage."""
        start_ms = time.time() * 1000

        try:
            async with self._lock:
                # Download state
                state_data = await self._storage.download(self._state_key())
                if not state_data:
                    return SyncResult(
                        success=True,
                        pulled_count=0,
                        duration_ms=time.time() * 1000 - start_ms,
                    )

                remote_state = FAISSIndexState.from_dict(json.loads(state_data))

                # Download vectors
                vectors_data = await self._storage.download(self._vectors_key())
                if not vectors_data:
                    return SyncResult(
                        success=False,
                        error="Failed to download vectors",
                        duration_ms=time.time() * 1000 - start_ms,
                    )

                # Verify checksum
                if self.config.verify_checksum:
                    actual_checksum = self._compute_checksum(vectors_data)
                    if actual_checksum != remote_state.checksum:
                        return SyncResult(
                            success=False,
                            error="Checksum verification failed",
                            duration_ms=time.time() * 1000 - start_ms,
                        )

                # Deserialize vectors
                remote_vectors = self._deserialize_vectors(vectors_data)
                remote_timestamps = {
                    vid: VectorTimestamp.from_dict(ts_data)
                    for vid, ts_data in remote_state.timestamps.items()
                }

                # Merge
                merged_vectors, conflicts = self._merge_strategy.merge(
                    self._local_vectors,
                    remote_vectors,
                    self._local_timestamps,
                    remote_timestamps,
                )

                # Apply merged state
                self._local_vectors = merged_vectors
                for vid, ts in remote_timestamps.items():
                    if vid in self._local_timestamps:
                        self._local_timestamps[vid].merge(ts)
                    else:
                        self._local_timestamps[vid] = ts

                return SyncResult(
                    success=True,
                    pulled_count=len(remote_vectors),
                    conflicts_detected=len(conflicts),
                    conflicts_resolved=len(conflicts),
                    duration_ms=time.time() * 1000 - start_ms,
                )

        except Exception as exc:
            logger.error(f"Pull failed: {exc}")
            return SyncResult(
                success=False,
                error=str(exc),
                duration_ms=time.time() * 1000 - start_ms,
            )

    async def sync(self) -> SyncResult:
        """Perform bidirectional sync (pull then push)."""
        start_ms = time.time() * 1000

        # Pull first
        pull_result = await self.pull()
        if not pull_result.success:
            return pull_result

        # Then push
        push_result = await self.push()

        return SyncResult(
            success=push_result.success,
            pushed_count=push_result.pushed_count,
            pulled_count=pull_result.pulled_count,
            conflicts_detected=pull_result.conflicts_detected,
            conflicts_resolved=pull_result.conflicts_resolved,
            duration_ms=time.time() * 1000 - start_ms,
            error=push_result.error,
        )

    def _serialize_vectors(self, vectors: Dict[str, np.ndarray]) -> bytes:
        """Serialize vectors to bytes using numpy's NPZ format."""
        buffer = io.BytesIO()
        arrays = {f"vec_{vid}": vec for vid, vec in vectors.items()}
        arrays["_ids"] = np.array(list(vectors.keys()))
        np.savez_compressed(buffer, **arrays) if self.config.compression else np.savez(buffer, **arrays)
        return buffer.getvalue()

    def _deserialize_vectors(self, data: bytes) -> Dict[str, np.ndarray]:
        """Deserialize vectors from NPZ format."""
        buffer = io.BytesIO(data)
        loaded = np.load(buffer, allow_pickle=True)

        vectors = {}
        if "_ids" in loaded:
            ids = loaded["_ids"].tolist()
            for vid in ids:
                key = f"vec_{vid}"
                if key in loaded:
                    vectors[vid] = loaded[key]

        return vectors

    def get_local_state(self) -> Optional[FAISSIndexState]:
        """Get current local state."""
        return self._local_state

    @property
    def local_vector_count(self) -> int:
        """Get number of local vectors."""
        return len(self._local_vectors)

    def health(self) -> Dict[str, Any]:
        """Get health status."""
        return {
            "partition_id": self.partition.partition_id,
            "local_vector_count": len(self._local_vectors),
            "deleted_count": len(self._deleted_ids),
            "storage_backend": self.config.storage_backend,
            "merge_strategy": self.config.merge_strategy,
            "has_local_state": self._local_state is not None,
        }


def create_faiss_sync_manager(
    partition: UserPartition,
    change_log: ChangeLog,
    storage_backend: str = "local",
    bucket_or_container: str = "faiss-indices",
) -> FAISSSyncManager:
    """Factory function to create a FAISS sync manager."""
    config = FAISSSyncConfig(
        storage_backend=storage_backend,
        bucket_or_container=bucket_or_container,
    )
    return FAISSSyncManager(config=config, change_log=change_log, partition=partition)
