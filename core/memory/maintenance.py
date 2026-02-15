"""
Memory Engine - Maintenance Module
====================================

Scheduled maintenance tasks for memory system.
- Retention enforcement (delete expired memories)
- Index compaction
- Backup
- Key rotation (if encryption enabled)
"""

import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_memory_config, MemoryConfig
from .indexer import FAISSIndexer

logger = logging.getLogger("memory-maintenance")


class MemoryMaintenance:
    """Scheduled maintenance for memory system.
    
    Run periodically (e.g., daily) to:
    - Delete expired memories
    - Compact FAISS index
    - Back up index and metadata
    
    Usage:
        maintenance = MemoryMaintenance(indexer=indexer)
        report = await maintenance.run()
    """
    
    def __init__(
        self,
        indexer: FAISSIndexer,
        config: Optional[MemoryConfig] = None,
    ):
        self._indexer = indexer
        self._config = config or get_memory_config()
        
        # Maintenance history
        self._last_run: Optional[str] = None
        self._run_count = 0
    
    async def run(self) -> Dict[str, Any]:
        """Run all maintenance tasks.
        
        Returns:
            Report with task results
        """
        start_time = time.time()
        report = {
            "started_at": datetime.utcnow().isoformat() + "Z",
            "tasks": {},
        }
        
        # Task 1: Enforce retention
        try:
            deleted = await self.enforce_retention()
            report["tasks"]["retention"] = {
                "success": True,
                "deleted_count": deleted,
            }
        except Exception as e:
            logger.error(f"Retention enforcement failed: {e}")
            report["tasks"]["retention"] = {
                "success": False,
                "error": str(e),
            }
        
        # Task 2: Compact index (if many deletions)
        deleted_count = report["tasks"].get("retention", {}).get("deleted_count", 0)
        if deleted_count > 10 or len(self._indexer._deleted_indices) > 50:
            try:
                await self.compact_index()
                report["tasks"]["compaction"] = {
                    "success": True,
                    "new_size": self._indexer.size,
                }
            except Exception as e:
                logger.error(f"Index compaction failed: {e}")
                report["tasks"]["compaction"] = {
                    "success": False,
                    "error": str(e),
                }
        else:
            report["tasks"]["compaction"] = {"skipped": True}
        
        # Task 3: Save index
        try:
            self._indexer.save()
            report["tasks"]["save"] = {"success": True}
        except Exception as e:
            logger.error(f"Index save failed: {e}")
            report["tasks"]["save"] = {
                "success": False,
                "error": str(e),
            }
        
        # Task 4: Backup (if configured)
        backup_path = self._config.ensure_index_dir().parent / "memory_backup"
        try:
            await self.backup(backup_path)
            report["tasks"]["backup"] = {
                "success": True,
                "path": str(backup_path),
            }
        except Exception as e:
            logger.warning(f"Backup failed: {e}")
            report["tasks"]["backup"] = {
                "success": False,
                "error": str(e),
            }
        
        # Finalize report
        elapsed_ms = (time.time() - start_time) * 1000
        report["completed_at"] = datetime.utcnow().isoformat() + "Z"
        report["duration_ms"] = round(elapsed_ms, 2)
        
        self._last_run = report["completed_at"]
        self._run_count += 1
        
        logger.info(f"Maintenance completed in {elapsed_ms:.1f}ms")
        
        return report
    
    async def enforce_retention(self) -> int:
        """Delete memories that have passed their expiry date.
        
        Returns:
            Number of deleted memories
        """
        now = datetime.utcnow()
        to_delete = []
        
        for idx, meta in list(self._indexer._metadata.items()):
            if not meta.expiry:
                continue
            
            try:
                expiry = datetime.fromisoformat(meta.expiry.replace("Z", "+00:00"))
                expiry = expiry.replace(tzinfo=None)
                
                if expiry <= now:
                    to_delete.append(meta.id)
            except (ValueError, AttributeError):
                continue
        
        # Delete expired memories
        deleted = 0
        for memory_id in to_delete:
            if self._indexer.delete(memory_id):
                deleted += 1
                logger.debug(f"Deleted expired memory: {memory_id}")
        
        if deleted > 0:
            logger.info(f"Retention enforcement: deleted {deleted} expired memories")
        
        return deleted
    
    async def compact_index(self):
        """Rebuild FAISS index to reclaim space."""
        logger.info("Starting index compaction...")
        self._indexer.compact()
        logger.info("Index compaction completed")
    
    async def backup(self, backup_path: Path) -> bool:
        """Create backup of index and metadata.
        
        Args:
            backup_path: Destination path for backup
            
        Returns:
            True if successful
        """
        source_path = self._config.ensure_index_dir()
        
        # Ensure backup directory exists
        backup_path = Path(backup_path)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Copy index files
        for file_name in ["index.faiss", "metadata.json"]:
            src = source_path / file_name
            dst = backup_path / file_name
            
            if src.exists():
                shutil.copy2(src, dst)
        
        # Write backup metadata
        backup_meta = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source_path": str(source_path),
            "index_size": self._indexer.size,
        }
        
        with open(backup_path / "backup_info.json", "w") as f:
            json.dump(backup_meta, f, indent=2)
        
        logger.info(f"Backup created at {backup_path}")
        return True
    
    async def restore(self, backup_path: Path) -> bool:
        """Restore index from backup.
        
        Args:
            backup_path: Source path of backup
            
        Returns:
            True if successful
        """
        backup_path = Path(backup_path)
        target_path = self._config.ensure_index_dir()
        
        if not (backup_path / "index.faiss").exists():
            raise ValueError(f"No backup found at {backup_path}")
        
        # Clear current index
        self._indexer.clear()
        
        # Copy backup files
        for file_name in ["index.faiss", "metadata.json"]:
            src = backup_path / file_name
            dst = target_path / file_name
            
            if src.exists():
                shutil.copy2(src, dst)
        
        # Reload index
        self._indexer._load()
        
        logger.info(f"Index restored from {backup_path}")
        return True
    
    async def rotate_encryption_key(
        self,
        old_key: bytes,
        new_key: bytes,
    ) -> bool:
        """Rotate encryption key (placeholder).
        
        In production, this would re-encrypt all stored data.
        """
        if not self._config.encryption_enabled:
            logger.warning("Encryption not enabled, key rotation skipped")
            return False
        
        # Placeholder for encryption key rotation
        # Would require:
        # 1. Decrypt all data with old key
        # 2. Re-encrypt with new key
        # 3. Update stored key reference
        
        logger.info("Key rotation completed (placeholder)")
        return True
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status of the memory system."""
        now = datetime.utcnow()
        
        # Calculate index age distribution
        age_buckets = {"<1h": 0, "1-24h": 0, "1-7d": 0, ">7d": 0}
        expired_count = 0
        
        for idx, meta in self._indexer._metadata.items():
            try:
                ts = datetime.fromisoformat(meta.timestamp.replace("Z", "+00:00"))
                ts = ts.replace(tzinfo=None)
                age_hours = (now - ts).total_seconds() / 3600
                
                if age_hours < 1:
                    age_buckets["<1h"] += 1
                elif age_hours < 24:
                    age_buckets["1-24h"] += 1
                elif age_hours < 168:
                    age_buckets["1-7d"] += 1
                else:
                    age_buckets[">7d"] += 1
                
                # Check expiry
                if meta.expiry:
                    expiry = datetime.fromisoformat(meta.expiry.replace("Z", "+00:00"))
                    if expiry.replace(tzinfo=None) <= now:
                        expired_count += 1
            except (ValueError, AttributeError):
                continue
        
        return {
            "status": "healthy",
            "index_size": self._indexer.size,
            "total_vectors": self._indexer.total_vectors,
            "deleted_pending": len(self._indexer._deleted_indices),
            "expired_pending": expired_count,
            "age_distribution": age_buckets,
            "last_maintenance": self._last_run,
            "maintenance_run_count": self._run_count,
            "config": {
                "enabled": self._config.enabled,
                "retention_days": self._config.retention_days,
                "max_vectors": self._config.max_vectors,
            },
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get maintenance statistics."""
        return {
            "last_run": self._last_run,
            "run_count": self._run_count,
            "index_size": self._indexer.size,
        }
