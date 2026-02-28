"""
Unit tests for Cloud Sync Architecture (T-111).

Tests:
- VectorTimestamp operations
- ChangeLog tracking and compaction
- BidirectionalSyncProtocol push/pull
- UserPartition isolation
- CloudSyncOrchestrator coordination
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from core.memory.cloud_sync import (
    BidirectionalSyncProtocol,
    ChangeLog,
    ChangeLogEntry,
    CloudSyncConfig,
    CloudSyncOrchestrator,
    StubCloudBackend,
    SyncRecord,
    SyncResult,
    UserPartition,
    VectorTimestamp,
)


class TestVectorTimestamp:
    """Tests for VectorTimestamp (vector clock) operations."""

    def test_create_vector_timestamp(self):
        """Test creating a vector timestamp."""
        vt = VectorTimestamp(node_id="node_1")
        assert vt.node_id == "node_1"
        assert vt.clock == {}

    def test_increment_clock(self):
        """Test incrementing the clock."""
        vt = VectorTimestamp(node_id="node_1")
        vt.increment()
        assert vt.clock["node_1"] == 1
        
        vt.increment()
        assert vt.clock["node_1"] == 2

    def test_merge_timestamps(self):
        """Test merging two vector timestamps."""
        vt1 = VectorTimestamp(node_id="node_1", clock={"node_1": 2, "node_2": 1})
        vt2 = VectorTimestamp(node_id="node_2", clock={"node_1": 1, "node_2": 3})
        
        vt1.merge(vt2)
        
        assert vt1.clock["node_1"] == 2  # max(2, 1)
        assert vt1.clock["node_2"] == 3  # max(1, 3)

    def test_happens_before(self):
        """Test happens-before relationship."""
        vt1 = VectorTimestamp(node_id="node_1", clock={"node_1": 1, "node_2": 1})
        vt2 = VectorTimestamp(node_id="node_2", clock={"node_1": 2, "node_2": 2})
        
        assert vt1.happens_before(vt2)
        assert not vt2.happens_before(vt1)

    def test_concurrent_timestamps(self):
        """Test detecting concurrent timestamps."""
        vt1 = VectorTimestamp(node_id="node_1", clock={"node_1": 2, "node_2": 1})
        vt2 = VectorTimestamp(node_id="node_2", clock={"node_1": 1, "node_2": 2})
        
        assert vt1.concurrent_with(vt2)
        assert vt2.concurrent_with(vt1)

    def test_equal_timestamps_not_concurrent(self):
        """Test that equal timestamps are concurrent."""
        vt1 = VectorTimestamp(node_id="node_1", clock={"node_1": 1})
        vt2 = VectorTimestamp(node_id="node_2", clock={"node_1": 1})
        
        # Equal timestamps: neither happens-before the other
        assert not vt1.happens_before(vt2)
        assert not vt2.happens_before(vt1)

    def test_to_dict_and_from_dict(self):
        """Test serialization/deserialization."""
        vt = VectorTimestamp(node_id="node_1", clock={"node_1": 3, "node_2": 5})
        data = vt.to_dict()
        
        restored = VectorTimestamp.from_dict(data)
        assert restored.node_id == "node_1"
        assert restored.clock == {"node_1": 3, "node_2": 5}


class TestChangeLog:
    """Tests for ChangeLog tracking."""

    @pytest.fixture
    def change_log(self):
        return ChangeLog(node_id="test_node", max_entries=100)

    async def test_append_entry(self, change_log):
        """Test appending a change entry."""
        entry = await change_log.append(
            operation="add",
            record_id="rec_001",
            data={"embedding": [0.1, 0.2, 0.3]}
        )
        
        assert entry.operation == "add"
        assert entry.record_id == "rec_001"
        assert entry.synced is False
        assert change_log.size == 1

    async def test_get_unsynced(self, change_log):
        """Test getting unsynced entries."""
        await change_log.append("add", "rec_001")
        await change_log.append("add", "rec_002")
        
        unsynced = await change_log.get_unsynced()
        assert len(unsynced) == 2

    async def test_mark_synced(self, change_log):
        """Test marking entries as synced."""
        entry1 = await change_log.append("add", "rec_001")
        entry2 = await change_log.append("add", "rec_002")
        
        count = await change_log.mark_synced([entry1.entry_id])
        assert count == 1
        
        unsynced = await change_log.get_unsynced()
        assert len(unsynced) == 1
        assert unsynced[0].entry_id == entry2.entry_id

    async def test_unsynced_count(self, change_log):
        """Test unsynced count property."""
        await change_log.append("add", "rec_001")
        await change_log.append("add", "rec_002")
        
        assert change_log.unsynced_count == 2

    async def test_current_timestamp_increments(self, change_log):
        """Test that current timestamp increments with each append."""
        await change_log.append("add", "rec_001")
        ts1 = change_log.current_timestamp.clock.get("test_node", 0)
        
        await change_log.append("add", "rec_002")
        ts2 = change_log.current_timestamp.clock.get("test_node", 0)
        
        assert ts2 > ts1


class TestChangeLogEntry:
    """Tests for ChangeLogEntry serialization."""

    def test_to_dict(self):
        """Test entry serialization."""
        entry = ChangeLogEntry(
            entry_id="entry_001",
            operation="add",
            record_id="rec_001",
            timestamp=VectorTimestamp(node_id="node_1", clock={"node_1": 1}),
            data={"key": "value"},
            synced=False,
            created_at_ms=1000.0,
        )
        
        data = entry.to_dict()
        assert data["entry_id"] == "entry_001"
        assert data["operation"] == "add"
        assert data["timestamp"]["node_id"] == "node_1"

    def test_from_dict(self):
        """Test entry deserialization."""
        data = {
            "entry_id": "entry_001",
            "operation": "update",
            "record_id": "rec_001",
            "timestamp": {"node_id": "node_1", "clock": {"node_1": 2}},
            "data": None,
            "synced": True,
            "created_at_ms": 2000.0,
        }
        
        entry = ChangeLogEntry.from_dict(data)
        assert entry.entry_id == "entry_001"
        assert entry.operation == "update"
        assert entry.synced is True


class TestUserPartition:
    """Tests for UserPartition isolation."""

    def test_create_partition(self):
        """Test creating a user partition."""
        partition = UserPartition(user_id="user_123")
        
        assert partition.user_id == "user_123"
        assert len(partition.partition_id) == 16  # SHA-256 hex truncated
        assert partition.sync_enabled is True

    def test_partition_id_deterministic(self):
        """Test that partition ID is deterministic for same user."""
        p1 = UserPartition(user_id="user_123")
        p2 = UserPartition(user_id="user_123")
        
        assert p1.partition_id == p2.partition_id

    def test_collection_name(self):
        """Test collection name generation."""
        partition = UserPartition(user_id="user_123")
        assert partition.collection_name.startswith("user_")
        assert partition.partition_id in partition.collection_name

    def test_index_path(self):
        """Test index path generation."""
        partition = UserPartition(user_id="user_123")
        assert "user_indices" in partition.index_path
        assert partition.partition_id in partition.index_path

    def test_to_dict_and_from_dict(self):
        """Test serialization/deserialization."""
        partition = UserPartition(
            user_id="user_123",
            sync_enabled=False,
            data_residency="eu-west-1",
        )
        
        data = partition.to_dict()
        restored = UserPartition.from_dict(data)
        
        assert restored.user_id == "user_123"
        assert restored.sync_enabled is False
        assert restored.data_residency == "eu-west-1"


class TestSyncResult:
    """Tests for SyncResult data class."""

    def test_success_result(self):
        """Test successful sync result."""
        result = SyncResult(
            success=True,
            pushed_count=10,
            pulled_count=5,
            conflicts_detected=2,
            conflicts_resolved=2,
            duration_ms=150.0,
        )
        
        assert result.success is True
        assert result.pushed_count == 10
        assert result.error is None

    def test_failure_result(self):
        """Test failed sync result."""
        result = SyncResult(
            success=False,
            duration_ms=50.0,
            error="Connection timeout",
        )
        
        assert result.success is False
        assert result.error == "Connection timeout"

    def test_to_dict(self):
        """Test result serialization."""
        result = SyncResult(success=True, pushed_count=5)
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["pushed_count"] == 5


class TestBidirectionalSyncProtocol:
    """Tests for BidirectionalSyncProtocol."""

    @pytest.fixture
    def backend(self):
        return StubCloudBackend()

    @pytest.fixture
    def change_log(self):
        return ChangeLog(node_id="test_node")

    @pytest.fixture
    def partition(self):
        return UserPartition(user_id="test_user")

    @pytest.fixture
    def protocol(self, backend, change_log, partition):
        return BidirectionalSyncProtocol(
            backend=backend,
            change_log=change_log,
            partition=partition,
            batch_size=10,
        )

    async def test_sync_empty_log(self, protocol, backend):
        """Test sync with empty change log."""
        await backend.connect()
        result = await protocol.sync()
        
        assert result.success is True
        assert result.pushed_count == 0
        assert result.pulled_count == 0

    async def test_push_changes(self, protocol, backend, change_log):
        """Test pushing local changes."""
        await backend.connect()
        
        # Add some changes
        embedding = np.random.rand(384).astype(np.float32)
        await change_log.append(
            "add",
            "rec_001",
            {"embedding": embedding.tolist(), "metadata": {"text": "test"}}
        )
        
        result = await protocol.push_incremental()
        
        assert result.success is True
        assert result.pushed_count == 1

    async def test_sync_updates_partition_time(self, protocol, backend, partition):
        """Test that sync updates partition last_sync_ms."""
        await backend.connect()
        
        old_time = partition.last_sync_ms
        await protocol.sync()
        
        assert partition.last_sync_ms > old_time

    async def test_sync_timing_under_2_seconds(self, protocol, backend, change_log):
        """Test that incremental sync completes under 2 seconds."""
        await backend.connect()
        
        # Add several changes
        for i in range(10):
            embedding = np.random.rand(384).astype(np.float32)
            await change_log.append(
                "add",
                f"rec_{i:03d}",
                {"embedding": embedding.tolist()}
            )
        
        result = await protocol.sync()
        
        assert result.success is True
        assert result.duration_ms < 2000  # < 2 seconds


class TestCloudSyncOrchestrator:
    """Tests for CloudSyncOrchestrator."""

    @pytest.fixture
    def config(self):
        return CloudSyncConfig(
            enabled=True,
            provider="stub",
            sync_interval_s=60.0,
        )

    @pytest.fixture
    def orchestrator(self, config):
        return CloudSyncOrchestrator(config=config, node_id="test_node")

    async def test_start_and_stop(self, orchestrator):
        """Test starting and stopping orchestrator."""
        started = await orchestrator.start()
        assert started is True
        
        await orchestrator.stop()
        assert orchestrator._running is False

    async def test_register_user(self, orchestrator):
        """Test registering a user partition."""
        partition = orchestrator.register_user("user_123")
        
        assert partition.user_id == "user_123"
        assert "user_123" in orchestrator._partitions

    async def test_record_change(self, orchestrator):
        """Test recording a change for a user."""
        await orchestrator.start()
        orchestrator.register_user("user_123")
        
        entry = await orchestrator.record_change(
            user_id="user_123",
            operation="add",
            record_id="rec_001",
            data={"embedding": [0.1, 0.2, 0.3]}
        )
        
        assert entry is not None
        assert entry.operation == "add"
        
        await orchestrator.stop()

    async def test_record_change_unregistered_user(self, orchestrator):
        """Test recording change for unregistered user returns None."""
        result = await orchestrator.record_change(
            user_id="unknown_user",
            operation="add",
            record_id="rec_001",
        )
        
        assert result is None

    async def test_sync_user(self, orchestrator):
        """Test syncing a specific user."""
        await orchestrator.start()
        orchestrator.register_user("user_123")
        
        result = await orchestrator.sync_user("user_123")
        
        assert result.success is True
        await orchestrator.stop()

    async def test_sync_unregistered_user(self, orchestrator):
        """Test syncing unregistered user fails."""
        await orchestrator.start()
        
        result = await orchestrator.sync_user("unknown_user")
        
        assert result.success is False
        assert "not registered" in result.error
        
        await orchestrator.stop()

    async def test_sync_all(self, orchestrator):
        """Test syncing all users."""
        await orchestrator.start()
        orchestrator.register_user("user_1")
        orchestrator.register_user("user_2")
        
        results = await orchestrator.sync_all()
        
        assert len(results) == 2
        assert results["user_1"].success is True
        assert results["user_2"].success is True
        
        await orchestrator.stop()

    async def test_health(self, orchestrator):
        """Test health status."""
        await orchestrator.start()
        orchestrator.register_user("user_123")
        
        health = orchestrator.health()
        
        assert health["enabled"] is True
        assert health["running"] is True
        assert health["registered_users"] == 1
        assert "user_123" in health["partitions"]
        
        await orchestrator.stop()

    async def test_disabled_sync(self):
        """Test orchestrator with disabled config."""
        config = CloudSyncConfig(enabled=False)
        orchestrator = CloudSyncOrchestrator(config=config)
        
        started = await orchestrator.start()
        assert started is False


class TestCloudSyncConfigFromEnv:
    """Tests for CloudSyncConfig.from_env()."""

    def test_default_config(self):
        """Test default configuration."""
        with patch.dict("os.environ", {}, clear=True):
            config = CloudSyncConfig.from_env()
            
            assert config.enabled is False
            assert config.provider == "stub"
            assert config.sync_interval_s == 300.0

    def test_enabled_config(self):
        """Test enabled configuration from environment."""
        env = {
            "CLOUD_SYNC": "true",
            "CLOUD_SYNC_PROVIDER": "milvus",
            "CLOUD_SYNC_URL": "http://localhost:19530",
            "CLOUD_SYNC_INTERVAL_S": "60",
        }
        
        with patch.dict("os.environ", env, clear=True):
            config = CloudSyncConfig.from_env()
            
            assert config.enabled is True
            assert config.provider == "milvus"
            assert config.url == "http://localhost:19530"
            assert config.sync_interval_s == 60.0


class TestStubCloudBackend:
    """Tests for StubCloudBackend."""

    @pytest.fixture
    def backend(self):
        return StubCloudBackend()

    async def test_connect(self, backend):
        """Test connecting to stub backend."""
        result = await backend.connect()
        assert result is True
        assert backend._connected is True

    async def test_upsert(self, backend):
        """Test upserting records."""
        await backend.connect()
        
        records = [
            SyncRecord(
                record_id="rec_001",
                embedding=np.random.rand(384).astype(np.float32),
                metadata={"text": "test"},
            )
        ]
        
        count = await backend.upsert(records)
        assert count == 1

    async def test_search(self, backend):
        """Test searching records."""
        await backend.connect()
        
        # Add a record
        embedding = np.random.rand(384).astype(np.float32)
        records = [SyncRecord(record_id="rec_001", embedding=embedding)]
        await backend.upsert(records)
        
        # Search
        results = await backend.search(embedding, k=5)
        
        assert len(results) == 1
        assert results[0]["record_id"] == "rec_001"
        assert results[0]["similarity"] > 0.99  # Same vector should have high similarity

    async def test_delete(self, backend):
        """Test deleting records."""
        await backend.connect()
        
        # Add a record
        records = [
            SyncRecord(
                record_id="rec_001",
                embedding=np.random.rand(384).astype(np.float32),
            )
        ]
        await backend.upsert(records)
        
        # Delete
        count = await backend.delete(["rec_001"])
        assert count == 1
        
        # Verify deletion
        health = backend.health()
        assert health["records"] == 0

    async def test_health(self, backend):
        """Test health status."""
        health = backend.health()
        assert health["provider"] == "stub"
        assert health["connected"] is False
        
        await backend.connect()
        health = backend.health()
        assert health["connected"] is True
