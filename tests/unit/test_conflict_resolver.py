"""
Unit tests for Cloud Sync Conflict Resolution (T-114).
"""


import numpy as np
import pytest

from core.memory.cloud_sync import VectorTimestamp
from core.memory.conflict_resolver import (
    ConflictRecord,
    ConflictResolutionManager,
    ConflictType,
    LastWriterWinsResolver,
    MergeResolver,
    ResolutionStrategy,
)


class TestConflictRecord:
    """Tests for ConflictRecord."""

    def test_to_dict(self):
        """Test serialization."""
        record = ConflictRecord(
            conflict_id="conflict_001",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="rec_001",
            table_or_index="users",
            local_value={"name": "Alice"},
            remote_value={"name": "Bob"},
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 1}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n2": 1}),
        )

        data = record.to_dict()

        assert data["conflict_id"] == "conflict_001"
        assert data["conflict_type"] == "concurrent_edit"
        assert data["local_value"] == {"name": "Alice"}

    def test_numpy_serialization(self):
        """Test numpy array serialization."""
        record = ConflictRecord(
            conflict_id="conflict_002",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="vec_001",
            table_or_index="vectors",
            local_value=np.array([1.0, 2.0]),
            remote_value=np.array([3.0, 4.0]),
            local_timestamp=VectorTimestamp(node_id="n1"),
            remote_timestamp=VectorTimestamp(node_id="n2"),
        )

        data = record.to_dict()

        assert data["local_value"] == [1.0, 2.0]
        assert data["remote_value"] == [3.0, 4.0]


class TestLastWriterWinsResolver:
    """Tests for LastWriterWinsResolver."""

    @pytest.fixture
    def resolver(self):
        return LastWriterWinsResolver()

    async def test_remote_newer_wins(self, resolver):
        """Test that remote wins when newer."""
        conflict = ConflictRecord(
            conflict_id="c1",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="r1",
            table_or_index="t1",
            local_value="old",
            remote_value="new",
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 1}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n1": 2}),
        )

        value, strategy = await resolver.resolve(conflict)

        assert value == "new"
        assert strategy == ResolutionStrategy.LAST_WRITER_WINS

    async def test_local_newer_wins(self, resolver):
        """Test that local wins when newer."""
        conflict = ConflictRecord(
            conflict_id="c1",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="r1",
            table_or_index="t1",
            local_value="new",
            remote_value="old",
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 2}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n1": 1}),
        )

        value, strategy = await resolver.resolve(conflict)

        assert value == "new"

    async def test_concurrent_defaults_to_local(self, resolver):
        """Test that concurrent timestamps default to local."""
        conflict = ConflictRecord(
            conflict_id="c1",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="r1",
            table_or_index="t1",
            local_value="local",
            remote_value="remote",
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 2, "n2": 1}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n1": 1, "n2": 2}),
        )

        value, strategy = await resolver.resolve(conflict)

        assert value == "local"
        assert strategy == ResolutionStrategy.LOCAL_WINS


class TestMergeResolver:
    """Tests for MergeResolver."""

    @pytest.fixture
    def resolver(self):
        return MergeResolver()

    async def test_merge_dicts(self, resolver):
        """Test merging dictionaries."""
        conflict = ConflictRecord(
            conflict_id="c1",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="r1",
            table_or_index="t1",
            local_value={"a": 1, "b": 2},
            remote_value={"b": 3, "c": 4},
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 2}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n1": 1}),
        )

        value, strategy = await resolver.resolve(conflict)

        assert strategy == ResolutionStrategy.MERGE
        assert value["a"] == 1  # Only in local
        assert value["c"] == 4  # Only in remote
        assert value["b"] == 2  # Local wins (newer timestamp)

    async def test_non_dict_falls_back_to_lww(self, resolver):
        """Test that non-dicts fall back to LWW."""
        conflict = ConflictRecord(
            conflict_id="c1",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="r1",
            table_or_index="t1",
            local_value="local",
            remote_value="remote",
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 1}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n1": 2}),
        )

        value, strategy = await resolver.resolve(conflict)

        assert value == "remote"  # Remote is newer


class TestConflictResolutionManager:
    """Tests for ConflictResolutionManager."""

    @pytest.fixture
    def manager(self):
        return ConflictResolutionManager()

    async def test_detect_conflict(self, manager):
        """Test conflict detection."""
        conflict = await manager.detect_conflict(
            record_id="rec_001",
            table_or_index="users",
            local_value={"name": "Alice"},
            remote_value={"name": "Bob"},
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 1, "n2": 1}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n1": 1, "n2": 2}),
        )

        assert conflict is not None
        assert conflict.conflict_type == ConflictType.CONCURRENT_EDIT

    async def test_no_conflict_for_equal_values(self, manager):
        """Test no conflict when values are equal."""
        conflict = await manager.detect_conflict(
            record_id="rec_001",
            table_or_index="users",
            local_value={"name": "Same"},
            remote_value={"name": "Same"},
            local_timestamp=VectorTimestamp(node_id="n1"),
            remote_timestamp=VectorTimestamp(node_id="n2"),
        )

        assert conflict is None

    async def test_resolve_conflict(self, manager):
        """Test resolving a conflict."""
        conflict = ConflictRecord(
            conflict_id="c1",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="r1",
            table_or_index="t1",
            local_value="local",
            remote_value="remote",
            local_timestamp=VectorTimestamp(node_id="n1", clock={"n1": 1}),
            remote_timestamp=VectorTimestamp(node_id="n2", clock={"n1": 2}),
        )

        resolved = await manager.resolve_conflict(conflict)

        assert resolved.resolved_value == "remote"
        assert resolved.resolution_strategy is not None
        assert resolved.resolved_at_ms > 0

    async def test_resolve_all(self, manager):
        """Test resolving multiple conflicts."""
        conflicts = [
            ConflictRecord(
                conflict_id=f"c{i}",
                conflict_type=ConflictType.CONCURRENT_EDIT,
                record_id=f"r{i}",
                table_or_index="t1",
                local_value=f"local{i}",
                remote_value=f"remote{i}",
                local_timestamp=VectorTimestamp(node_id="n1"),
                remote_timestamp=VectorTimestamp(node_id="n2"),
            )
            for i in range(3)
        ]

        result = await manager.resolve_all(conflicts)

        assert result.conflicts_resolved == 3
        assert result.conflicts_pending == 0

    async def test_audit_log(self, manager):
        """Test audit log is maintained."""
        conflict = ConflictRecord(
            conflict_id="c1",
            conflict_type=ConflictType.CONCURRENT_EDIT,
            record_id="r1",
            table_or_index="t1",
            local_value="local",
            remote_value="remote",
            local_timestamp=VectorTimestamp(node_id="n1"),
            remote_timestamp=VectorTimestamp(node_id="n2"),
        )

        await manager.resolve_conflict(conflict)

        log = manager.get_audit_log()
        assert len(log) == 1
        assert log[0]["conflict_id"] == "c1"

    async def test_network_partition_recovery(self, manager):
        """Test handling network partition recovery."""
        local_changes = [
            {"record_id": "r1", "table": "t1", "value": "local_v1"},
            {"record_id": "r2", "table": "t1", "value": "local_v2"},
        ]
        remote_changes = [
            {"record_id": "r1", "table": "t1", "value": "remote_v1"},  # Conflict
            {"record_id": "r3", "table": "t1", "value": "remote_v3"},  # No conflict
        ]

        conflicts = await manager.handle_network_partition_recovery(
            local_changes=local_changes,
            remote_changes=remote_changes,
            local_timestamp=VectorTimestamp(node_id="n1"),
            remote_timestamp=VectorTimestamp(node_id="n2"),
        )

        # Only r1 has a conflict (both modified)
        assert len(conflicts) == 1
        assert conflicts[0].record_id == "r1"

    def test_health(self, manager):
        """Test health status."""
        health = manager.health()

        assert "total_conflicts" in health
        assert "default_strategy" in health
