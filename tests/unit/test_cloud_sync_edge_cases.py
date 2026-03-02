"""Cloud sync edge-case tests: timeouts, partial failures, retry, and concurrency."""

from __future__ import annotations

import time
from unittest.mock import patch

import numpy as np
import pytest

from core.memory.cloud_sync import (
    ChangeLog,
    CloudSyncAdapter,
    CloudSyncConfig,
    StubCloudBackend,
    SyncRecord,
    VectorTimestamp,
    _create_backend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vec(*v: float) -> np.ndarray:
    return np.array(v, dtype=np.float32)


def _record(rid: str = "r1", dim: int = 4) -> SyncRecord:
    return SyncRecord(
        record_id=rid,
        embedding=np.random.rand(dim).astype(np.float32),
        metadata={"source": "test"},
        timestamp_ms=time.time() * 1000,
    )


# ===========================================================================
# CloudSyncConfig edge cases
# ===========================================================================


class TestCloudSyncConfigEdgeCases:
    """Edge cases for CloudSyncConfig construction and env parsing."""

    def test_default_config_is_disabled(self):
        """Default config should have enabled=False."""
        cfg = CloudSyncConfig()
        assert cfg.enabled is False
        assert cfg.provider == "stub"

    def test_config_from_env_missing_vars(self):
        """from_env with no env vars should return safe defaults."""
        with patch.dict("os.environ", {}, clear=True):
            cfg = CloudSyncConfig.from_env()
        assert cfg.enabled is False
        assert cfg.provider == "stub"

    def test_config_from_env_with_invalid_interval(self):
        """Non-numeric CLOUD_SYNC_INTERVAL_S should raise ValueError."""
        with patch.dict("os.environ", {"CLOUD_SYNC_INTERVAL_S": "not_a_number"}):
            with pytest.raises(ValueError):
                CloudSyncConfig.from_env()

    def test_config_zero_batch_size(self):
        """Zero batch size is allowed at config level (validated elsewhere)."""
        cfg = CloudSyncConfig(batch_size=0)
        assert cfg.batch_size == 0

    def test_config_negative_timeout(self):
        """Negative timeout is stored as-is (no validation at dataclass level)."""
        cfg = CloudSyncConfig(timeout_s=-1.0)
        assert cfg.timeout_s == -1.0


# ===========================================================================
# StubCloudBackend edge cases
# ===========================================================================


class TestStubCloudBackendEdgeCases:
    """Edge cases for the in-memory stub backend."""

    async def test_upsert_empty_list(self):
        """Upserting zero records should succeed with count=0."""
        backend = StubCloudBackend()
        await backend.connect()
        count = await backend.upsert([])
        assert count == 0

    async def test_search_empty_index(self):
        """Searching an empty backend should return empty results."""
        backend = StubCloudBackend()
        await backend.connect()
        results = await backend.search(_vec(1.0, 0.0, 0.0), k=5)
        assert results == []

    async def test_delete_nonexistent_ids(self):
        """Deleting IDs that don't exist should return count=0."""
        backend = StubCloudBackend()
        await backend.connect()
        count = await backend.delete(["nonexistent_1", "nonexistent_2"])
        assert count == 0

    async def test_upsert_duplicate_ids_overwrites(self):
        """Upserting the same record_id twice should overwrite."""
        backend = StubCloudBackend()
        await backend.connect()
        r1 = SyncRecord(record_id="dup", embedding=_vec(1.0, 0.0), metadata={"v": 1})
        r2 = SyncRecord(record_id="dup", embedding=_vec(0.0, 1.0), metadata={"v": 2})
        await backend.upsert([r1])
        await backend.upsert([r2])
        health = backend.health()
        assert health["records"] == 1

    async def test_search_with_zero_norm_query(self):
        """Searching with a zero-vector query should not crash."""
        backend = StubCloudBackend()
        await backend.connect()
        await backend.upsert([SyncRecord(record_id="x", embedding=_vec(1.0, 0.0))])
        results = await backend.search(_vec(0.0, 0.0), k=1)
        assert isinstance(results, list)

    async def test_disconnect_clears_connected_flag(self):
        """After disconnect the health should show connected=False."""
        backend = StubCloudBackend()
        await backend.connect()
        assert backend.health()["connected"] is True
        await backend.disconnect()
        assert backend.health()["connected"] is False


# ===========================================================================
# CloudSyncAdapter edge cases
# ===========================================================================


class TestCloudSyncAdapterEdgeCases:
    """Edge cases for the CloudSyncAdapter orchestrator."""

    async def test_start_when_disabled(self):
        """Starting a disabled adapter should return False immediately."""
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=False))
        result = await adapter.start()
        assert result is False

    async def test_enqueue_triggers_flush_on_batch_full(self):
        """When pending count >= batch_size, flush is triggered."""
        cfg = CloudSyncConfig(enabled=True, provider="stub", batch_size=2)
        adapter = CloudSyncAdapter(cfg)
        await adapter._backend.connect()
        records = [_record(f"r{i}") for i in range(3)]
        await adapter.enqueue(records)
        # After enqueue of 3 with batch_size=2, at least one flush should have occurred
        assert adapter._sync_count >= 2

    async def test_enqueue_below_batch_no_flush(self):
        """Enqueuing fewer than batch_size should not flush."""
        cfg = CloudSyncConfig(enabled=True, provider="stub", batch_size=100)
        adapter = CloudSyncAdapter(cfg)
        await adapter._backend.connect()
        await adapter.enqueue([_record("r1")])
        assert adapter._sync_count == 0
        assert len(adapter._pending) == 1

    async def test_search_cloud_when_disabled(self):
        """Searching cloud when disabled returns empty list."""
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=False))
        results = await adapter.search_cloud(_vec(1.0, 0.0), k=5)
        assert results == []

    async def test_delete_cloud_when_disabled(self):
        """Deleting from cloud when disabled returns 0."""
        adapter = CloudSyncAdapter(CloudSyncConfig(enabled=False))
        count = await adapter.delete_cloud(["id1"])
        assert count == 0

    async def test_stop_flushes_pending(self):
        """Stopping the adapter should flush remaining pending records."""
        cfg = CloudSyncConfig(enabled=True, provider="stub", batch_size=100)
        adapter = CloudSyncAdapter(cfg)
        await adapter._backend.connect()
        await adapter.enqueue([_record("r1"), _record("r2")])
        assert adapter._sync_count == 0
        await adapter.stop()
        assert adapter._sync_count == 2

    async def test_health_reports_pending_count(self):
        """Health dict should report accurate pending count."""
        cfg = CloudSyncConfig(enabled=True, provider="stub", batch_size=100)
        adapter = CloudSyncAdapter(cfg)
        await adapter.enqueue([_record("r1")])
        h = adapter.health()
        assert h["pending"] == 1
        assert h["enabled"] is True

    async def test_double_stop_does_not_raise(self):
        """Calling stop() twice should not raise."""
        cfg = CloudSyncConfig(enabled=True, provider="stub", batch_size=100)
        adapter = CloudSyncAdapter(cfg)
        await adapter._backend.connect()
        await adapter.stop()
        await adapter.stop()  # second call should be safe


# ===========================================================================
# VectorTimestamp edge cases
# ===========================================================================


class TestVectorTimestampEdgeCases:
    """Edge cases for vector clock comparisons."""

    def test_empty_clocks_are_concurrent(self):
        """Two empty clocks should be concurrent (neither happens-before)."""
        a = VectorTimestamp(node_id="a")
        b = VectorTimestamp(node_id="b")
        assert a.concurrent_with(b)

    def test_increment_creates_entry(self):
        """Incrementing should create the node's entry in the clock."""
        ts = VectorTimestamp(node_id="node1")
        ts.increment()
        assert ts.clock["node1"] == 1

    def test_happens_before_after_increment(self):
        """After one increment, ts should happen-before a merged copy."""
        a = VectorTimestamp(node_id="a", clock={"a": 1})
        b = VectorTimestamp(node_id="b", clock={"a": 1, "b": 1})
        assert a.happens_before(b)

    def test_merge_takes_max(self):
        """Merge should take the max of each component."""
        a = VectorTimestamp(node_id="a", clock={"a": 3, "b": 1})
        b = VectorTimestamp(node_id="b", clock={"a": 1, "b": 5})
        a.merge(b)
        assert a.clock["a"] == 3
        assert a.clock["b"] == 5

    def test_to_dict_round_trip(self):
        """Serialization round-trip should preserve data."""
        original = VectorTimestamp(node_id="n1", clock={"n1": 5, "n2": 3})
        restored = VectorTimestamp.from_dict(original.to_dict())
        assert restored.node_id == "n1"
        assert restored.clock == {"n1": 5, "n2": 3}

    def test_concurrent_divergent_clocks(self):
        """Divergent clocks (a>b on one key, b>a on another) are concurrent."""
        a = VectorTimestamp(node_id="a", clock={"a": 2, "b": 1})
        b = VectorTimestamp(node_id="b", clock={"a": 1, "b": 2})
        assert a.concurrent_with(b)
        assert not a.happens_before(b)
        assert not b.happens_before(a)


# ===========================================================================
# ChangeLog edge cases
# ===========================================================================


class TestChangeLogEdgeCases:
    """Edge cases for the ChangeLog write-ahead log."""

    async def test_append_increments_timestamp(self):
        """Each append should increment the local vector clock."""
        cl = ChangeLog(node_id="test_node")
        await cl.append("add", "rec1")
        await cl.append("update", "rec2")
        assert cl.current_timestamp.clock["test_node"] == 2

    async def test_get_unsynced_returns_only_unsynced(self):
        """Only entries not marked synced should appear."""
        cl = ChangeLog(node_id="n1")
        e1 = await cl.append("add", "r1")
        await cl.append("add", "r2")
        await cl.mark_synced([e1.entry_id])
        unsynced = await cl.get_unsynced()
        assert len(unsynced) == 1
        assert unsynced[0].record_id == "r2"

    async def test_mark_synced_nonexistent_ids(self):
        """Marking nonexistent entry IDs should return count=0."""
        cl = ChangeLog(node_id="n1")
        await cl.append("add", "r1")
        count = await cl.mark_synced(["does_not_exist"])
        assert count == 0

    async def test_compact_removes_add_delete_pairs(self):
        """Compacting should eliminate add+delete on the same record."""
        cl = ChangeLog(node_id="n1", max_entries=3)
        await cl.append("add", "r1", {"data": "v1"})
        await cl.append("delete", "r1")
        # Force compact
        await cl.append("add", "r2")
        await cl.append("add", "r3")
        unsynced = await cl.get_unsynced()
        record_ids = [e.record_id for e in unsynced]
        # r1 add+delete should be eliminated
        assert "r1" not in record_ids or len([r for r in record_ids if r == "r1"]) <= 1

    async def test_size_property(self):
        """Size should reflect total entries."""
        cl = ChangeLog(node_id="n1")
        assert cl.size == 0
        await cl.append("add", "r1")
        assert cl.size == 1


# ===========================================================================
# Backend factory edge cases
# ===========================================================================


class TestBackendFactory:
    """Edge cases for _create_backend factory."""

    def test_unknown_provider_returns_stub(self):
        """Unknown provider string should fallback to StubCloudBackend."""
        cfg = CloudSyncConfig(provider="unknown_provider")
        backend = _create_backend(cfg)
        assert isinstance(backend, StubCloudBackend)

    def test_stub_provider_returns_stub(self):
        """Explicit 'stub' provider returns StubCloudBackend."""
        cfg = CloudSyncConfig(provider="stub")
        backend = _create_backend(cfg)
        assert isinstance(backend, StubCloudBackend)
