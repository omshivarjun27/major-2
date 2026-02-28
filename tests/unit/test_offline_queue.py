"""
Unit tests for Cloud Sync Offline Queue (T-116).
"""

import asyncio
import json
from pathlib import Path

import pytest

from core.memory.offline_queue import (
    CompactionResult,
    OfflineQueue,
    QueuedOperation,
    QueueOperationType,
)


class TestQueuedOperation:
    """Tests for QueuedOperation."""

    def test_to_dict(self):
        """Test serialization."""
        op = QueuedOperation(
            operation_id="op_001",
            operation_type=QueueOperationType.ADD,
            record_id="rec_001",
            table_or_index="users",
            data={"name": "Alice"},
        )

        data = op.to_dict()

        assert data["operation_id"] == "op_001"
        assert data["operation_type"] == "add"
        assert data["data"]["name"] == "Alice"

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "operation_id": "op_002",
            "operation_type": "update",
            "record_id": "rec_002",
            "table_or_index": "items",
            "data": {"value": 42},
        }

        op = QueuedOperation.from_dict(data)

        assert op.operation_id == "op_002"
        assert op.operation_type == QueueOperationType.UPDATE


class TestQueueOperationType:
    """Tests for QueueOperationType enum."""

    def test_all_types(self):
        """Test all expected types exist."""
        assert QueueOperationType.ADD.value == "add"
        assert QueueOperationType.UPDATE.value == "update"
        assert QueueOperationType.DELETE.value == "delete"


class TestOfflineQueue:
    """Tests for OfflineQueue."""

    @pytest.fixture
    def queue(self, tmp_path):
        return OfflineQueue(
            queue_path=str(tmp_path / "queue"),
            max_size=10,
            partition_id="test",
        )

    async def test_enqueue(self, queue):
        """Test enqueueing an operation."""
        op = await queue.enqueue(
            operation_type=QueueOperationType.ADD,
            record_id="rec_001",
            table_or_index="users",
            data={"name": "Alice"},
        )

        assert op.operation_id.startswith("op_")
        assert queue.depth == 1

    async def test_dequeue(self, queue):
        """Test dequeueing an operation."""
        await queue.enqueue(
            operation_type=QueueOperationType.ADD,
            record_id="rec_001",
            table_or_index="users",
        )

        op = await queue.dequeue()

        assert op is not None
        assert op.record_id == "rec_001"
        assert queue.depth == 0

    async def test_dequeue_empty(self, queue):
        """Test dequeueing from empty queue."""
        op = await queue.dequeue()
        assert op is None

    async def test_peek(self, queue):
        """Test peeking at operations."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        await queue.enqueue(QueueOperationType.ADD, "rec_002", "t1")

        ops = await queue.peek(1)

        assert len(ops) == 1
        assert ops[0].record_id == "rec_001"
        assert queue.depth == 2  # Not removed

    async def test_get_all(self, queue):
        """Test getting all operations."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        await queue.enqueue(QueueOperationType.ADD, "rec_002", "t1")

        ops = await queue.get_all()

        assert len(ops) == 2

    async def test_remove(self, queue):
        """Test removing specific operations."""
        op1 = await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        op2 = await queue.enqueue(QueueOperationType.ADD, "rec_002", "t1")

        removed = await queue.remove([op1.operation_id])

        assert removed == 1
        assert queue.depth == 1

    async def test_mark_failed(self, queue):
        """Test marking an operation as failed."""
        op = await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")

        updated = await queue.mark_failed(op.operation_id, "Test error")

        assert updated is not None
        assert updated.retry_count == 1
        assert updated.last_error == "Test error"

    async def test_mark_failed_max_retries(self, queue):
        """Test that operation is removed after max retries."""
        op = await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")

        # Fail 3 times (max retries)
        for i in range(3):
            await queue.mark_failed(op.operation_id, f"Error {i}")

        # Should be removed
        assert queue.depth == 0

    async def test_eviction_when_full(self, queue):
        """Test oldest-first eviction when queue is full."""
        # Fill the queue
        for i in range(10):
            await queue.enqueue(QueueOperationType.ADD, f"rec_{i:03d}", "t1")

        # Add one more
        new_op = await queue.enqueue(QueueOperationType.ADD, "rec_new", "t1")

        # Queue should still be at max size
        assert queue.depth == 10

        # First operation should have been evicted
        ops = await queue.get_all()
        record_ids = [op.record_id for op in ops]
        assert "rec_000" not in record_ids
        assert "rec_new" in record_ids

    async def test_compact_multiple_updates(self, queue):
        """Test compacting multiple updates to same record."""
        await queue.enqueue(QueueOperationType.UPDATE, "rec_001", "t1", {"val": 1})
        await queue.enqueue(QueueOperationType.UPDATE, "rec_001", "t1", {"val": 2})
        await queue.enqueue(QueueOperationType.UPDATE, "rec_001", "t1", {"val": 3})

        result = await queue.compact()

        assert result.original_count == 3
        assert result.compacted_count == 1
        assert queue.depth == 1

    async def test_compact_add_then_delete(self, queue):
        """Test compacting add followed by delete."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        await queue.enqueue(QueueOperationType.DELETE, "rec_001", "t1")

        result = await queue.compact()

        # Add + delete should cancel out
        assert result.compacted_count == 0
        assert queue.depth == 0

    async def test_compact_add_then_update(self, queue):
        """Test compacting add followed by update."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1", {"val": 1})
        await queue.enqueue(QueueOperationType.UPDATE, "rec_001", "t1", {"val": 2})

        result = await queue.compact()

        assert result.compacted_count == 1
        ops = await queue.get_all()
        # Should be kept as ADD with latest data
        assert ops[0].operation_type == QueueOperationType.ADD

    async def test_replay(self, queue):
        """Test replaying operations."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        await queue.enqueue(QueueOperationType.ADD, "rec_002", "t1")

        processed = []

        def processor(op):
            processed.append(op.record_id)
            return True

        result = await queue.replay(processor)

        assert result["total_operations"] == 2
        assert result["success_count"] == 2
        assert result["remaining"] == 0
        assert "rec_001" in processed
        assert "rec_002" in processed

    async def test_replay_with_failures(self, queue):
        """Test replay with failing processor."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        await queue.enqueue(QueueOperationType.ADD, "rec_002", "t1")

        def processor(op):
            return op.record_id != "rec_001"  # Fail for rec_001

        result = await queue.replay(processor)

        assert result["success_count"] == 1
        assert result["fail_count"] == 1

    async def test_persistence(self, tmp_path):
        """Test queue persistence across instances."""
        queue_path = str(tmp_path / "persist_queue")

        # Create and populate queue
        queue1 = OfflineQueue(queue_path=queue_path, partition_id="p1")
        await queue1.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        await queue1.enqueue(QueueOperationType.ADD, "rec_002", "t1")

        # Create new instance and verify data loaded
        queue2 = OfflineQueue(queue_path=queue_path, partition_id="p1")

        assert queue2.depth == 2

    def test_is_empty(self, queue):
        """Test is_empty property."""
        assert queue.is_empty is True

    async def test_is_empty_false(self, queue):
        """Test is_empty when not empty."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")
        assert queue.is_empty is False

    def test_health(self, queue):
        """Test health status."""
        health = queue.health()

        assert health["partition_id"] == "test"
        assert health["max_size"] == 10
        assert health["queue_depth"] == 0

    async def test_metrics(self, queue):
        """Test Prometheus metrics."""
        await queue.enqueue(QueueOperationType.ADD, "rec_001", "t1")

        metrics = queue.metrics()

        assert metrics["offline_queue_depth"] == 1.0
        assert metrics["offline_queue_enqueued_total"] == 1.0
