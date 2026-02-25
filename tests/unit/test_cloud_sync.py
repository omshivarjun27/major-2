"""Unit tests for cloud sync adapter and stub backend."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import cast

import numpy as np
import pytest
import pytest_asyncio

from core.memory.cloud_sync import CloudSyncAdapter, CloudSyncConfig, StubCloudBackend, SyncRecord

DEFAULT_TIMESTAMP = datetime(2026, 2, 25, 12, 0, 0, tzinfo=timezone.utc)


def _vector(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float32)


def _make_record(
    record_id: str,
    vector: np.ndarray,
    *,
    metadata: Mapping[str, object] | None = None,
    timestamp: datetime | None = None,
) -> SyncRecord:
    ts = timestamp or DEFAULT_TIMESTAMP
    record_metadata: dict[str, object] = {
        "source": "unit-test",
        "timestamp": ts.isoformat(),
    }
    if metadata:
        record_metadata.update(dict(metadata))
    return SyncRecord(
        record_id=record_id,
        embedding=vector,
        metadata=record_metadata,
        timestamp_ms=ts.timestamp() * 1000,
    )


def _health_status(target: object) -> Mapping[str, object]:
    health_fn = cast(Callable[[], Mapping[str, object]], getattr(target, "health"))
    return health_fn()


def _backend_record_count(adapter: CloudSyncAdapter) -> int:
    health = _health_status(adapter)
    backend_health = cast(Mapping[str, object], health["backend"])
    return int(cast(int, backend_health["records"]))


async def _flush_adapter(adapter: CloudSyncAdapter) -> None:
    if adapter.enabled:
        flush = cast(Callable[[], Awaitable[None]], getattr(adapter, "_flush"))
        await flush()


@pytest_asyncio.fixture
async def stub_backend() -> AsyncGenerator[StubCloudBackend, None]:
    backend = StubCloudBackend()
    _ = await backend.connect()
    yield backend
    await backend.disconnect()


@pytest.fixture
def sync_adapter() -> CloudSyncAdapter:
    config = CloudSyncConfig(
        enabled=True,
        provider="stub",
        batch_size=10,
        sync_interval_s=1.0,
    )
    return CloudSyncAdapter(config)


async def test_stub_connect_and_health(stub_backend: StubCloudBackend) -> None:
    health = _health_status(stub_backend)

    assert health["connected"] is True
    assert health["provider"] == "stub"


async def test_stub_upsert_stores_records(stub_backend: StubCloudBackend) -> None:
    records = [
        _make_record("rec_1", _vector(1.0, 0.0, 0.0), metadata={"index": 1}),
        _make_record("rec_2", _vector(0.0, 1.0, 0.0), metadata={"index": 2}),
        _make_record("rec_3", _vector(0.0, 0.0, 1.0), metadata={"index": 3}),
    ]

    count = await stub_backend.upsert(records)
    health = _health_status(stub_backend)

    assert count == 3
    assert health["records"] == 3


async def test_stub_search_cosine_similarity(stub_backend: StubCloudBackend) -> None:
    query = _vector(1.0, 0.0, 0.0)
    close_vec = _vector(0.9, 0.1, 0.0)
    far_vec = _vector(0.0, 1.0, 0.0)

    _ = await stub_backend.upsert(
        [
            _make_record("close", close_vec, metadata={"label": "close"}),
            _make_record("far", far_vec, metadata={"label": "far"}),
        ]
    )

    results = await stub_backend.search(query, k=2)

    assert len(results) == 2
    assert results[0]["record_id"] == "close"
    assert results[0]["similarity"] > results[1]["similarity"]


async def test_stub_delete_removes_record(stub_backend: StubCloudBackend) -> None:
    record = _make_record("delete_me", _vector(0.2, 0.1, 0.0), metadata={"tag": "delete"})

    _ = await stub_backend.upsert([record])
    deleted = await stub_backend.delete(["delete_me"])
    health = _health_status(stub_backend)
    results = await stub_backend.search(record.embedding, k=1)

    assert deleted == 1
    assert health["records"] == 0
    assert results == []


async def test_adapter_enqueue_and_flush(sync_adapter: CloudSyncAdapter) -> None:
    records = [
        _make_record(
            f"rec_{idx}",
            _vector(float(idx), float(idx + 1), float(idx + 2)),
            metadata={"index": idx},
        )
        for idx in range(5)
    ]

    await sync_adapter.enqueue(records)
    await _flush_adapter(sync_adapter)

    assert _backend_record_count(sync_adapter) == 5


async def test_adapter_disabled_skips_flush() -> None:
    adapter = CloudSyncAdapter(CloudSyncConfig(enabled=False, provider="stub", batch_size=10))
    records = [
        _make_record("rec_a", _vector(0.1, 0.2, 0.3), metadata={"index": 1}),
        _make_record("rec_b", _vector(0.4, 0.5, 0.6), metadata={"index": 2}),
    ]

    await adapter.enqueue(records)
    await _flush_adapter(adapter)

    assert _backend_record_count(adapter) == 0


async def test_adapter_periodic_flush(sync_adapter: CloudSyncAdapter) -> None:
    sync_adapter.config.sync_interval_s = 0.1
    records = [
        _make_record("rec_1", _vector(0.3, 0.1, 0.0), metadata={"index": 1}),
        _make_record("rec_2", _vector(0.0, 0.3, 0.1), metadata={"index": 2}),
    ]

    started = await sync_adapter.start()
    assert started is True
    try:
        await sync_adapter.enqueue(records)
        await asyncio.sleep(0.3)

        assert _backend_record_count(sync_adapter) == len(records)
    finally:
        await sync_adapter.stop()


async def test_adapter_health_reports_queue_size(sync_adapter: CloudSyncAdapter) -> None:
    records = [
        _make_record("rec_1", _vector(0.7, 0.1, 0.0), metadata={"index": 1}),
        _make_record("rec_2", _vector(0.1, 0.7, 0.0), metadata={"index": 2}),
        _make_record("rec_3", _vector(0.0, 0.1, 0.7), metadata={"index": 3}),
    ]

    await sync_adapter.enqueue(records)
    health = _health_status(sync_adapter)
    queue_size = int(cast(int, health["pending"]))

    assert queue_size == 3
    assert _backend_record_count(sync_adapter) == 0
