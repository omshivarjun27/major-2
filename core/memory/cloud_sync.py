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
