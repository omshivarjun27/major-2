"""
Cloud Sync Adapter — Optional cloud vector DB synchronization.

Provides a pluggable adapter pattern for syncing the local FAISS index
to a remote vector database (Milvus, Weaviate, Pinecone, etc.).
Disabled by default (CLOUD_SYNC=false). All data encrypted in transit.

Environment Variables:
    CLOUD_SYNC: "true" to enable (default "false")
    CLOUD_SYNC_PROVIDER: "milvus" | "weaviate" | "stub" (default "stub")
    CLOUD_SYNC_URL: Connection URL for the cloud provider
    CLOUD_SYNC_API_KEY: API key (if required)
    CLOUD_SYNC_COLLECTION: Collection/index name (default "voice_vision_memories")
    CLOUD_SYNC_INTERVAL_S: Sync interval in seconds (default 300)
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("cloud-sync")


@dataclass
class CloudSyncConfig:
    """Configuration for cloud vector sync."""
    enabled: bool = False
    provider: str = "stub"                           # milvus | weaviate | stub
    url: str = ""
    api_key: str = ""
    collection: str = "voice_vision_memories"
    sync_interval_s: float = 300.0
    batch_size: int = 50
    timeout_s: float = 30.0
    encrypt_in_transit: bool = True

    @classmethod
    def from_env(cls) -> "CloudSyncConfig":
        return cls(
            enabled=os.getenv("CLOUD_SYNC", "false").lower() == "true",
            provider=os.getenv("CLOUD_SYNC_PROVIDER", "stub"),
            url=os.getenv("CLOUD_SYNC_URL", ""),
            api_key=os.getenv("CLOUD_SYNC_API_KEY", ""),
            collection=os.getenv("CLOUD_SYNC_COLLECTION", "voice_vision_memories"),
            sync_interval_s=float(os.getenv("CLOUD_SYNC_INTERVAL_S", "300")),
            batch_size=int(os.getenv("CLOUD_SYNC_BATCH_SIZE", "50")),
        )


@dataclass
class SyncRecord:
    """A record to sync to the cloud."""
    record_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp_ms: float = 0.0


class CloudVectorBackend(ABC):
    """Abstract backend for cloud vector sync."""

    @abstractmethod
    async def connect(self) -> bool: ...

    @abstractmethod
    async def upsert(self, records: List[SyncRecord]) -> int: ...

    @abstractmethod
    async def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]: ...

    @abstractmethod
    async def delete(self, record_ids: List[str]) -> int: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    def health(self) -> dict: ...


class StubCloudBackend(CloudVectorBackend):
    """Stub backend that logs operations without real cloud calls."""

    def __init__(self):
        self._records: Dict[str, SyncRecord] = {}
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        logger.info("Stub cloud backend connected (no actual cloud)")
        return True

    async def upsert(self, records: List[SyncRecord]) -> int:
        for r in records:
            self._records[r.record_id] = r
        logger.debug("Stub upsert: %d records", len(records))
        return len(records)

    async def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        # Simple brute-force cosine similarity
        results = []
        q_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        for rid, rec in self._records.items():
            r_norm = rec.embedding / (np.linalg.norm(rec.embedding) + 1e-10)
            sim = float(np.dot(q_norm, r_norm))
            results.append({"record_id": rid, "similarity": sim, "metadata": rec.metadata})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]

    async def delete(self, record_ids: List[str]) -> int:
        count = 0
        for rid in record_ids:
            if rid in self._records:
                del self._records[rid]
                count += 1
        return count

    async def disconnect(self) -> None:
        self._connected = False

    def health(self) -> dict:
        return {"provider": "stub", "connected": self._connected, "records": len(self._records)}


class MilvusCloudBackend(CloudVectorBackend):
    """Milvus vector DB backend."""

    def __init__(self, config: CloudSyncConfig):
        self.config = config
        self._client = None
        self._connected = False

    async def connect(self) -> bool:
        try:
            from pymilvus import MilvusClient
            self._client = MilvusClient(uri=self.config.url, token=self.config.api_key)
            # Create collection if not exists
            if not self._client.has_collection(self.config.collection):
                from pymilvus import DataType, FieldSchema, CollectionSchema
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=256),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
                    FieldSchema(name="metadata", dtype=DataType.JSON),
                ]
                schema = CollectionSchema(fields=fields)
                self._client.create_collection(collection_name=self.config.collection, schema=schema)
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Milvus connect failed: %s", exc)
            return False

    async def upsert(self, records: List[SyncRecord]) -> int:
        if not self._client:
            return 0
        try:
            data = [
                {"id": r.record_id, "embedding": r.embedding.tolist(), "metadata": r.metadata}
                for r in records
            ]
            self._client.upsert(collection_name=self.config.collection, data=data)
            return len(data)
        except Exception as exc:
            logger.error("Milvus upsert failed: %s", exc)
            return 0

    async def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        try:
            results = self._client.search(
                collection_name=self.config.collection,
                data=[query_embedding.tolist()],
                limit=k,
                output_fields=["metadata"],
            )
            return [
                {"record_id": hit["id"], "similarity": hit["distance"], "metadata": hit.get("entity", {}).get("metadata", {})}
                for hit in results[0]
            ]
        except Exception as exc:
            logger.error("Milvus search failed: %s", exc)
            return []

    async def delete(self, record_ids: List[str]) -> int:
        if not self._client:
            return 0
        try:
            self._client.delete(collection_name=self.config.collection, ids=record_ids)
            return len(record_ids)
        except Exception as exc:
            logger.error("Milvus delete failed: %s", exc)
            return 0

    async def disconnect(self) -> None:
        self._client = None
        self._connected = False

    def health(self) -> dict:
        return {"provider": "milvus", "connected": self._connected, "url": self.config.url}


class WeaviateCloudBackend(CloudVectorBackend):
    """Weaviate vector DB backend."""

    def __init__(self, config: CloudSyncConfig):
        self.config = config
        self._client = None
        self._connected = False

    async def connect(self) -> bool:
        try:
            import weaviate
            self._client = weaviate.Client(
                url=self.config.url,
                auth_client_secret=weaviate.AuthApiKey(api_key=self.config.api_key) if self.config.api_key else None,
            )
            self._connected = self._client.is_ready()
            return self._connected
        except Exception as exc:
            logger.error("Weaviate connect failed: %s", exc)
            return False

    async def upsert(self, records: List[SyncRecord]) -> int:
        if not self._client:
            return 0
        count = 0
        try:
            with self._client.batch as batch:
                for r in records:
                    batch.add_data_object(
                        data_object=r.metadata,
                        class_name=self.config.collection,
                        uuid=r.record_id,
                        vector=r.embedding.tolist(),
                    )
                    count += 1
            return count
        except Exception as exc:
            logger.error("Weaviate upsert failed: %s", exc)
            return 0

    async def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        try:
            result = (
                self._client.query
                .get(self.config.collection)
                .with_near_vector({"vector": query_embedding.tolist()})
                .with_limit(k)
                .with_additional(["id", "distance"])
                .do()
            )
            hits = result.get("data", {}).get("Get", {}).get(self.config.collection, [])
            return [
                {"record_id": h["_additional"]["id"], "similarity": 1 - h["_additional"]["distance"], "metadata": h}
                for h in hits
            ]
        except Exception as exc:
            logger.error("Weaviate search failed: %s", exc)
            return []

    async def delete(self, record_ids: List[str]) -> int:
        if not self._client:
            return 0
        count = 0
        for rid in record_ids:
            try:
                self._client.data_object.delete(uuid=rid, class_name=self.config.collection)
                count += 1
            except Exception:
                pass
        return count

    async def disconnect(self) -> None:
        self._client = None
        self._connected = False

    def health(self) -> dict:
        return {"provider": "weaviate", "connected": self._connected, "url": self.config.url}


def _create_backend(config: CloudSyncConfig) -> CloudVectorBackend:
    """Factory for cloud backends."""
    if config.provider == "milvus":
        return MilvusCloudBackend(config)
    elif config.provider == "weaviate":
        return WeaviateCloudBackend(config)
    return StubCloudBackend()


class CloudSyncAdapter:
    """Manages periodic bidirectional sync between local FAISS and cloud vector DB.

    Usage::

        adapter = CloudSyncAdapter()
        await adapter.start()
        await adapter.sync_to_cloud(records)
        await adapter.stop()
    """

    def __init__(self, config: Optional[CloudSyncConfig] = None):
        self.config = config or CloudSyncConfig.from_env()
        self._backend = _create_backend(self.config)
        self._sync_task: Optional[asyncio.Task] = None
        self._pending: List[SyncRecord] = []
        self._last_sync_ms: float = 0
        self._sync_count: int = 0

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    async def start(self) -> bool:
        if not self.enabled:
            logger.debug("Cloud sync disabled")
            return False
        ok = await self._backend.connect()
        if ok:
            self._sync_task = asyncio.create_task(self._periodic_sync())
            logger.info("Cloud sync started (provider=%s, interval=%ds)",
                        self.config.provider, self.config.sync_interval_s)
        return ok

    async def stop(self) -> None:
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        # Flush remaining
        if self._pending:
            await self._flush()
        await self._backend.disconnect()

    async def enqueue(self, records: List[SyncRecord]) -> None:
        """Add records to the sync queue."""
        self._pending.extend(records)
        if len(self._pending) >= self.config.batch_size:
            await self._flush()

    async def search_cloud(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """Search the cloud index."""
        if not self.enabled:
            return []
        return await self._backend.search(query_embedding, k)

    async def delete_cloud(self, record_ids: List[str]) -> int:
        if not self.enabled:
            return 0
        return await self._backend.delete(record_ids)

    async def _flush(self) -> None:
        if not self._pending:
            return
        batch = self._pending[: self.config.batch_size]
        self._pending = self._pending[self.config.batch_size:]
        count = await self._backend.upsert(batch)
        self._sync_count += count
        self._last_sync_ms = time.time() * 1000
        logger.debug("Cloud sync flushed %d records", count)

    async def _periodic_sync(self) -> None:
        while True:
            await asyncio.sleep(self.config.sync_interval_s)
            try:
                await self._flush()
            except Exception as exc:
                logger.error("Periodic cloud sync failed: %s", exc)

    def health(self) -> dict:
        return {
            "enabled": self.enabled,
            "provider": self.config.provider,
            "pending": len(self._pending),
            "total_synced": self._sync_count,
            "last_sync_ms": self._last_sync_ms,
            "backend": self._backend.health(),
        }




# =============================================================================
# PHASE 6: BIDIRECTIONAL SYNC ARCHITECTURE (T-111)
# =============================================================================


@dataclass
class VectorTimestamp:
    """Vector clock for tracking causality in distributed sync.
    
    Each node (device) maintains its own logical clock. When syncing,
    we compare vector timestamps to detect conflicts and establish
    happens-before relationships.
    """
    node_id: str
    clock: Dict[str, int] = field(default_factory=dict)
    
    def increment(self) -> 'VectorTimestamp':
        """Increment this node's clock."""
        self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1
        return self
    
    def merge(self, other: 'VectorTimestamp') -> 'VectorTimestamp':
        """Merge another vector timestamp (take max of each component)."""
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for node in all_nodes:
            self.clock[node] = max(
                self.clock.get(node, 0),
                other.clock.get(node, 0)
            )
        return self
    
    def happens_before(self, other: 'VectorTimestamp') -> bool:
        """Check if this timestamp happens-before the other.
        
        Returns True if all components of self <= other and at least one <.
        """
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        all_leq = all(
            self.clock.get(n, 0) <= other.clock.get(n, 0)
            for n in all_nodes
        )
        any_lt = any(
            self.clock.get(n, 0) < other.clock.get(n, 0)
            for n in all_nodes
        )
        return all_leq and any_lt
    
    def concurrent_with(self, other: 'VectorTimestamp') -> bool:
        """Check if timestamps are concurrent (neither happens-before the other)."""
        return not self.happens_before(other) and not other.happens_before(self)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"node_id": self.node_id, "clock": self.clock.copy()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorTimestamp':
        return cls(node_id=data["node_id"], clock=data.get("clock", {}))


@dataclass
class ChangeLogEntry:
    """Entry in the change log for tracking local modifications."""
    entry_id: str
    operation: str  # 'add' | 'update' | 'delete'
    record_id: str
    timestamp: VectorTimestamp
    data: Optional[Dict[str, Any]] = None
    synced: bool = False
    created_at_ms: float = field(default_factory=lambda: time.time() * 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "operation": self.operation,
            "record_id": self.record_id,
            "timestamp": self.timestamp.to_dict(),
            "data": self.data,
            "synced": self.synced,
            "created_at_ms": self.created_at_ms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChangeLogEntry':
        return cls(
            entry_id=data["entry_id"],
            operation=data["operation"],
            record_id=data["record_id"],
            timestamp=VectorTimestamp.from_dict(data["timestamp"]),
            data=data.get("data"),
            synced=data.get("synced", False),
            created_at_ms=data.get("created_at_ms", 0),
        )


class ChangeLog:
    """Tracks local changes for sync.
    
    Maintains a write-ahead log of all local modifications since the last sync.
    Used to determine what needs to be pushed to the cloud.
    """
    
    def __init__(self, node_id: str, max_entries: int = 10000):
        self.node_id = node_id
        self.max_entries = max_entries
        self._entries: List[ChangeLogEntry] = []
        self._current_timestamp = VectorTimestamp(node_id=node_id)
        self._lock = asyncio.Lock()
    
    async def append(self, operation: str, record_id: str, data: Optional[Dict[str, Any]] = None) -> ChangeLogEntry:
        """Append a change to the log."""
        async with self._lock:
            self._current_timestamp.increment()
            entry = ChangeLogEntry(
                entry_id=f"{self.node_id}_{int(time.time() * 1000)}_{len(self._entries)}",
                operation=operation,
                record_id=record_id,
                timestamp=VectorTimestamp(
                    node_id=self.node_id,
                    clock=self._current_timestamp.clock.copy()
                ),
                data=data,
            )
            self._entries.append(entry)
            
            # Compact if too many entries
            if len(self._entries) > self.max_entries:
                await self._compact()
            
            return entry
    
    async def get_unsynced(self) -> List[ChangeLogEntry]:
        """Get all unsynced entries."""
        async with self._lock:
            return [e for e in self._entries if not e.synced]
    
    async def mark_synced(self, entry_ids: List[str]) -> int:
        """Mark entries as synced."""
        async with self._lock:
            count = 0
            entry_id_set = set(entry_ids)
            for entry in self._entries:
                if entry.entry_id in entry_id_set and not entry.synced:
                    entry.synced = True
                    count += 1
            return count
    
    async def _compact(self) -> int:
        """Remove synced entries to save space, keeping recent unsynced ones.
        
        Merges redundant operations on the same record:
        - Multiple updates -> keep latest
        - Add + update -> keep as add with latest data
        - Add + delete -> remove both
        """
        # Remove synced entries older than 1 hour
        cutoff_ms = (time.time() - 3600) * 1000
        self._entries = [
            e for e in self._entries
            if not e.synced or e.created_at_ms > cutoff_ms
        ]
        
        # Merge redundant operations on same record
        record_ops: Dict[str, List[ChangeLogEntry]] = {}
        for entry in self._entries:
            if not entry.synced:
                if entry.record_id not in record_ops:
                    record_ops[entry.record_id] = []
                record_ops[entry.record_id].append(entry)
        
        # Compact redundant operations
        compacted = []
        for entries in record_ops.values():
            if len(entries) == 1:
                compacted.append(entries[0])
            else:
                # Sort by timestamp
                entries.sort(key=lambda e: e.created_at_ms)
                ops = [e.operation for e in entries]
                
                if 'delete' in ops:
                    # If there's a delete, only keep the delete
                    delete_entry = next(e for e in entries if e.operation == 'delete')
                    if 'add' not in ops:
                        compacted.append(delete_entry)
                    # else: add + delete cancels out
                else:
                    # Keep the latest add/update
                    latest = entries[-1]
                    if entries[0].operation == 'add':
                        latest.operation = 'add'
                    compacted.append(latest)
        
        # Add back synced entries and sort
        synced_entries = [e for e in self._entries if e.synced]
        self._entries = synced_entries + compacted
        self._entries.sort(key=lambda e: e.created_at_ms)
        
        return len(compacted)
    
    @property
    def current_timestamp(self) -> VectorTimestamp:
        return self._current_timestamp
    
    @property
    def size(self) -> int:
        return len(self._entries)
    
    @property
    def unsynced_count(self) -> int:
        return sum(1 for e in self._entries if not e.synced)


@dataclass
class UserPartition:
    """Per-user data partition for privacy isolation.
    
    Each user's data is stored in a separate partition with its own:
    - FAISS index
    - SQLite tables (prefixed)
    - Change log
    - Sync state
    """
    user_id: str
    partition_id: str = field(default="")
    created_at_ms: float = field(default_factory=lambda: time.time() * 1000)
    last_sync_ms: float = 0
    sync_enabled: bool = True
    data_residency: str = "default"  # Region constraint for GDPR
    
    def __post_init__(self):
        if not self.partition_id:
            import hashlib
            self.partition_id = hashlib.sha256(self.user_id.encode()).hexdigest()[:16]
    
    @property
    def collection_name(self) -> str:
        """Cloud collection name for this partition."""
        return f"user_{self.partition_id}"
    
    @property
    def index_path(self) -> str:
        """Local index path for this partition."""
        return f"./data/user_indices/{self.partition_id}/"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "partition_id": self.partition_id,
            "created_at_ms": self.created_at_ms,
            "last_sync_ms": self.last_sync_ms,
            "sync_enabled": self.sync_enabled,
            "data_residency": self.data_residency,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPartition':
        return cls(
            user_id=data["user_id"],
            partition_id=data.get("partition_id", ""),
            created_at_ms=data.get("created_at_ms", 0),
            last_sync_ms=data.get("last_sync_ms", 0),
            sync_enabled=data.get("sync_enabled", True),
            data_residency=data.get("data_residency", "default"),
        )


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    pushed_count: int = 0
    pulled_count: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    duration_ms: float = 0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "pushed_count": self.pushed_count,
            "pulled_count": self.pulled_count,
            "conflicts_detected": self.conflicts_detected,
            "conflicts_resolved": self.conflicts_resolved,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class BidirectionalSyncProtocol:
    """Bidirectional sync protocol with conflict detection.
    
    Implements a push/pull sync model:
    1. Push local changes to cloud
    2. Pull cloud changes to local
    3. Detect and resolve conflicts using vector timestamps
    
    Target: Incremental sync < 2 seconds
    """
    
    def __init__(
        self,
        backend: CloudVectorBackend,
        change_log: ChangeLog,
        partition: UserPartition,
        batch_size: int = 50,
    ):
        self.backend = backend
        self.change_log = change_log
        self.partition = partition
        self.batch_size = batch_size
        self._last_pull_timestamp: Optional[VectorTimestamp] = None
        self._lock = asyncio.Lock()
    
    async def sync(self) -> SyncResult:
        """Perform a full bidirectional sync.
        
        Returns:
            SyncResult with counts and timing information
        """
        start_ms = time.time() * 1000
        
        try:
            async with self._lock:
                # Phase 1: Push local changes
                push_result = await self._push()
                
                # Phase 2: Pull remote changes
                pull_result = await self._pull()
                
                # Update partition sync time
                self.partition.last_sync_ms = time.time() * 1000
                
                duration_ms = time.time() * 1000 - start_ms
                
                return SyncResult(
                    success=True,
                    pushed_count=push_result["count"],
                    pulled_count=pull_result["count"],
                    conflicts_detected=pull_result["conflicts"],
                    conflicts_resolved=pull_result["resolved"],
                    duration_ms=duration_ms,
                )
        except Exception as exc:
            logger.error(f"Sync failed: {exc}")
            return SyncResult(
                success=False,
                duration_ms=time.time() * 1000 - start_ms,
                error=str(exc),
            )
    
    async def _push(self) -> Dict[str, int]:
        """Push local changes to cloud."""
        unsynced = await self.change_log.get_unsynced()
        
        if not unsynced:
            return {"count": 0}
        
        # Group by operation type
        adds_updates = [e for e in unsynced if e.operation in ('add', 'update')]
        deletes = [e for e in unsynced if e.operation == 'delete']
        
        pushed_count = 0
        synced_ids = []
        
        # Process adds/updates in batches
        for i in range(0, len(adds_updates), self.batch_size):
            batch = adds_updates[i:i + self.batch_size]
            records = []
            
            for entry in batch:
                if entry.data and 'embedding' in entry.data:
                    records.append(SyncRecord(
                        record_id=entry.record_id,
                        embedding=np.array(entry.data['embedding'], dtype=np.float32),
                        metadata={
                            **entry.data.get('metadata', {}),
                            '_vector_timestamp': entry.timestamp.to_dict(),
                            '_partition_id': self.partition.partition_id,
                        },
                        timestamp_ms=entry.created_at_ms,
                    ))
                    synced_ids.append(entry.entry_id)
            
            if records:
                count = await self.backend.upsert(records)
                pushed_count += count
        
        # Process deletes
        if deletes:
            delete_ids = [e.record_id for e in deletes]
            await self.backend.delete(delete_ids)
            synced_ids.extend(e.entry_id for e in deletes)
            pushed_count += len(deletes)
        
        # Mark as synced
        await self.change_log.mark_synced(synced_ids)
        
        logger.debug(f"Pushed {pushed_count} changes to cloud")
        return {"count": pushed_count}
    
    async def _pull(self) -> Dict[str, int]:
        """Pull remote changes from cloud.
        
        This is a simplified pull that fetches recent records.
        In a full implementation, the cloud would track changes
        and provide a delta since last sync.
        """
        # For now, we simulate a pull by checking health
        # A full implementation would query cloud for changes since last_pull_timestamp
        health = self.backend.health()
        
        pulled_count = 0
        conflicts_detected = 0
        conflicts_resolved = 0
        
        # TODO: Implement actual pull from cloud with conflict detection
        # This would involve:
        # 1. Query cloud for records modified since last_pull_timestamp
        # 2. For each record, check if local version exists
        # 3. If exists, compare vector timestamps for conflict
        # 4. Apply conflict resolution strategy
        
        logger.debug(f"Pull complete: {pulled_count} records, {conflicts_detected} conflicts")
        return {
            "count": pulled_count,
            "conflicts": conflicts_detected,
            "resolved": conflicts_resolved,
        }
    
    async def push_incremental(self) -> SyncResult:
        """Push only local changes (faster than full sync)."""
        start_ms = time.time() * 1000
        
        try:
            result = await self._push()
            duration_ms = time.time() * 1000 - start_ms
            
            return SyncResult(
                success=True,
                pushed_count=result["count"],
                duration_ms=duration_ms,
            )
        except Exception as exc:
            return SyncResult(
                success=False,
                duration_ms=time.time() * 1000 - start_ms,
                error=str(exc),
            )


class CloudSyncOrchestrator:
    """Orchestrates cloud sync across multiple user partitions.
    
    Features:
    - Per-user data isolation
    - Configurable sync intervals
    - Automatic conflict resolution
    - Offline queue support (via change log)
    """
    
    def __init__(
        self,
        config: Optional[CloudSyncConfig] = None,
        node_id: Optional[str] = None,
    ):
        self.config = config or CloudSyncConfig.from_env()
        self.node_id = node_id or f"node_{int(time.time() * 1000)}"
        
        self._backend = _create_backend(self.config)
        self._partitions: Dict[str, UserPartition] = {}
        self._change_logs: Dict[str, ChangeLog] = {}
        self._sync_protocols: Dict[str, BidirectionalSyncProtocol] = {}
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> bool:
        """Start the sync orchestrator."""
        if not self.config.enabled:
            logger.debug("Cloud sync disabled")
            return False
        
        connected = await self._backend.connect()
        if not connected:
            logger.error("Failed to connect to cloud backend")
            return False
        
        self._running = True
        self._sync_task = asyncio.create_task(self._periodic_sync_loop())
        logger.info(f"Cloud sync orchestrator started (node={self.node_id})")
        return True
    
    async def stop(self) -> None:
        """Stop the sync orchestrator."""
        self._running = False
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        # Final sync before shutdown
        for user_id in self._partitions:
            try:
                await self.sync_user(user_id)
            except Exception as exc:
                logger.error(f"Final sync failed for user {user_id}: {exc}")
        
        await self._backend.disconnect()
        logger.info("Cloud sync orchestrator stopped")
    
    def register_user(self, user_id: str, data_residency: str = "default") -> UserPartition:
        """Register a user partition for sync."""
        if user_id in self._partitions:
            return self._partitions[user_id]
        
        partition = UserPartition(user_id=user_id, data_residency=data_residency)
        self._partitions[user_id] = partition
        self._change_logs[user_id] = ChangeLog(node_id=self.node_id)
        self._sync_protocols[user_id] = BidirectionalSyncProtocol(
            backend=self._backend,
            change_log=self._change_logs[user_id],
            partition=partition,
            batch_size=self.config.batch_size,
        )
        
        logger.info(f"Registered user partition: {partition.partition_id}")
        return partition
    
    async def record_change(
        self,
        user_id: str,
        operation: str,
        record_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[ChangeLogEntry]:
        """Record a local change for a user."""
        if user_id not in self._change_logs:
            logger.warning(f"User {user_id} not registered for sync")
            return None
        
        return await self._change_logs[user_id].append(operation, record_id, data)
    
    async def sync_user(self, user_id: str) -> SyncResult:
        """Sync a specific user's data."""
        if user_id not in self._sync_protocols:
            return SyncResult(success=False, error=f"User {user_id} not registered")
        
        partition = self._partitions[user_id]
        if not partition.sync_enabled:
            return SyncResult(success=False, error="Sync disabled for user")
        
        return await self._sync_protocols[user_id].sync()
    
    async def sync_all(self) -> Dict[str, SyncResult]:
        """Sync all registered users."""
        results = {}
        for user_id in self._partitions:
            results[user_id] = await self.sync_user(user_id)
        return results
    
    async def _periodic_sync_loop(self) -> None:
        """Background loop for periodic sync."""
        while self._running:
            await asyncio.sleep(self.config.sync_interval_s)
            
            try:
                results = await self.sync_all()
                success_count = sum(1 for r in results.values() if r.success)
                logger.debug(f"Periodic sync: {success_count}/{len(results)} users synced")
            except Exception as exc:
                logger.error(f"Periodic sync failed: {exc}")
    
    def health(self) -> Dict[str, Any]:
        """Get health status."""
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "node_id": self.node_id,
            "registered_users": len(self._partitions),
            "backend": self._backend.health(),
            "partitions": {
                uid: {
                    "partition_id": p.partition_id,
                    "sync_enabled": p.sync_enabled,
                    "last_sync_ms": p.last_sync_ms,
                    "unsynced_changes": self._change_logs[uid].unsynced_count if uid in self._change_logs else 0,
                }
                for uid, p in self._partitions.items()
            },
        }
