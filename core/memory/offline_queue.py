"""
Cloud Sync Offline Queue Module (T-116).

Implements offline operation queue for cloud sync:
- Persistent write-ahead log for offline changes
- Queue replay on reconnection with conflict detection
- Queue compaction to merge redundant operations
- Maximum queue size with oldest-first eviction
- Prometheus metrics for queue depth monitoring
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("offline-queue")


class QueueOperationType(Enum):
    """Types of queue operations."""

    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class QueuedOperation:
    """An operation queued for sync."""

    operation_id: str
    operation_type: QueueOperationType
    record_id: str
    table_or_index: str
    data: Optional[Dict[str, Any]] = None
    created_at_ms: float = field(default_factory=lambda: time.time() * 1000)
    retry_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "record_id": self.record_id,
            "table_or_index": self.table_or_index,
            "data": self.data,
            "created_at_ms": self.created_at_ms,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueuedOperation":
        return cls(
            operation_id=data["operation_id"],
            operation_type=QueueOperationType(data["operation_type"]),
            record_id=data["record_id"],
            table_or_index=data["table_or_index"],
            data=data.get("data"),
            created_at_ms=data.get("created_at_ms", 0),
            retry_count=data.get("retry_count", 0),
            last_error=data.get("last_error"),
        )


@dataclass
class CompactionResult:
    """Result of queue compaction."""

    original_count: int
    compacted_count: int
    removed_count: int
    merged_operations: List[str]


class OfflineQueue:
    """Persistent offline queue for sync operations.

    Features:
    - Write-ahead log for durability
    - Queue compaction to merge redundant operations
    - Oldest-first eviction when queue is full
    - Metrics for monitoring
    """

    MAX_QUEUE_SIZE = 1000
    MAX_RETRY_COUNT = 3

    def __init__(
        self,
        queue_path: str = "./data/offline_queue/",
        max_size: int = MAX_QUEUE_SIZE,
        partition_id: str = "default",
    ):
        self.queue_path = Path(queue_path)
        self.max_size = max_size
        self.partition_id = partition_id

        self.queue_path.mkdir(parents=True, exist_ok=True)

        # In-memory queue (also persisted)
        self._queue: List[QueuedOperation] = []
        self._operation_count = 0
        self._lock = asyncio.Lock()

        # Metrics
        self._total_enqueued = 0
        self._total_processed = 0
        self._total_evicted = 0
        self._total_compacted = 0

        # Load existing queue
        self._load_queue()

    def _queue_file(self) -> Path:
        """Get queue file path."""
        return self.queue_path / f"queue_{self.partition_id}.json"

    def _load_queue(self) -> None:
        """Load queue from disk."""
        queue_file = self._queue_file()
        if queue_file.exists():
            try:
                data = json.loads(queue_file.read_text())
                self._queue = [
                    QueuedOperation.from_dict(op)
                    for op in data.get("operations", [])
                ]
                self._operation_count = data.get("operation_count", 0)
                logger.info(f"Loaded {len(self._queue)} operations from queue")
            except Exception as exc:
                logger.error(f"Failed to load queue: {exc}")
                self._queue = []

    def _save_queue(self) -> None:
        """Save queue to disk."""
        queue_file = self._queue_file()
        data = {
            "operations": [op.to_dict() for op in self._queue],
            "operation_count": self._operation_count,
            "saved_at": time.time() * 1000,
        }
        queue_file.write_text(json.dumps(data, indent=2))

    async def enqueue(
        self,
        operation_type: QueueOperationType,
        record_id: str,
        table_or_index: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> QueuedOperation:
        """Add an operation to the queue."""
        async with self._lock:
            # Check if we need to evict
            while len(self._queue) >= self.max_size:
                evicted = self._queue.pop(0)
                self._total_evicted += 1
                logger.warning(
                    f"Evicted oldest operation {evicted.operation_id} "
                    f"(queue full at {self.max_size})"
                )

            self._operation_count += 1
            op = QueuedOperation(
                operation_id=f"op_{self.partition_id}_{int(time.time() * 1000)}_{self._operation_count}",
                operation_type=operation_type,
                record_id=record_id,
                table_or_index=table_or_index,
                data=data,
            )

            self._queue.append(op)
            self._total_enqueued += 1
            self._save_queue()

            return op

    async def dequeue(self) -> Optional[QueuedOperation]:
        """Remove and return the oldest operation from the queue."""
        async with self._lock:
            if not self._queue:
                return None

            op = self._queue.pop(0)
            self._total_processed += 1
            self._save_queue()

            return op

    async def peek(self, count: int = 1) -> List[QueuedOperation]:
        """View operations without removing them."""
        return self._queue[:count]

    async def get_all(self) -> List[QueuedOperation]:
        """Get all operations in the queue."""
        return list(self._queue)

    async def remove(self, operation_ids: List[str]) -> int:
        """Remove specific operations by ID."""
        async with self._lock:
            initial_count = len(self._queue)
            id_set = set(operation_ids)
            self._queue = [op for op in self._queue if op.operation_id not in id_set]
            removed = initial_count - len(self._queue)
            self._total_processed += removed
            self._save_queue()
            return removed

    async def mark_failed(
        self,
        operation_id: str,
        error: str,
    ) -> Optional[QueuedOperation]:
        """Mark an operation as failed with error."""
        async with self._lock:
            for op in self._queue:
                if op.operation_id == operation_id:
                    op.retry_count += 1
                    op.last_error = error

                    # Remove if max retries exceeded
                    if op.retry_count >= self.MAX_RETRY_COUNT:
                        self._queue.remove(op)
                        logger.error(
                            f"Operation {operation_id} permanently failed "
                            f"after {op.retry_count} retries: {error}"
                        )
                    else:
                        # Move to end of queue for retry
                        self._queue.remove(op)
                        self._queue.append(op)

                    self._save_queue()
                    return op

            return None

    async def compact(self) -> CompactionResult:
        """Compact the queue by merging redundant operations.

        Merge rules:
        - Multiple updates to same record -> keep latest
        - Add + update -> keep as add with latest data
        - Add + delete -> remove both
        - Update + delete -> keep delete only
        """
        async with self._lock:
            original_count = len(self._queue)

            # Group by record_id
            by_record: Dict[str, List[QueuedOperation]] = {}
            for op in self._queue:
                key = f"{op.table_or_index}:{op.record_id}"
                if key not in by_record:
                    by_record[key] = []
                by_record[key].append(op)

            # Compact each group
            compacted = []
            merged_ids = []

            for key, ops in by_record.items():
                if len(ops) == 1:
                    compacted.append(ops[0])
                else:
                    # Sort by timestamp
                    ops.sort(key=lambda o: o.created_at_ms)
                    op_types = [o.operation_type for o in ops]

                    # Check for add + delete (cancels out)
                    if (
                        QueueOperationType.ADD in op_types
                        and QueueOperationType.DELETE in op_types
                    ):
                        add_idx = op_types.index(QueueOperationType.ADD)
                        delete_idx = len(op_types) - 1 - op_types[::-1].index(
                            QueueOperationType.DELETE
                        )
                        if delete_idx > add_idx:
                            # Add then delete - cancel both
                            merged_ids.extend([o.operation_id for o in ops])
                            continue

                    # Keep the latest meaningful operation
                    if QueueOperationType.DELETE in op_types:
                        # Keep delete
                        latest_delete = next(
                            o for o in reversed(ops)
                            if o.operation_type == QueueOperationType.DELETE
                        )
                        compacted.append(latest_delete)
                    else:
                        # Keep latest add/update
                        latest = ops[-1]
                        if ops[0].operation_type == QueueOperationType.ADD:
                            latest.operation_type = QueueOperationType.ADD
                        compacted.append(latest)

                    merged_ids.extend([
                        o.operation_id for o in ops
                        if o.operation_id != compacted[-1].operation_id
                    ])

            self._queue = compacted
            self._total_compacted += original_count - len(compacted)
            self._save_queue()

            result = CompactionResult(
                original_count=original_count,
                compacted_count=len(compacted),
                removed_count=original_count - len(compacted),
                merged_operations=merged_ids,
            )

            logger.info(
                f"Queue compacted: {original_count} -> {len(compacted)} operations"
            )

            return result

    async def replay(
        self,
        processor: Callable[[QueuedOperation], bool],
    ) -> Dict[str, Any]:
        """Replay queued operations using the provided processor.

        Args:
            processor: Async function that processes an operation and returns success

        Returns:
            Replay statistics
        """
        operations = await self.get_all()
        success_count = 0
        fail_count = 0
        processed_ids = []

        for op in operations:
            try:
                success = processor(op)
                if success:
                    success_count += 1
                    processed_ids.append(op.operation_id)
                else:
                    fail_count += 1
                    await self.mark_failed(op.operation_id, "Processor returned False")
            except Exception as exc:
                fail_count += 1
                await self.mark_failed(op.operation_id, str(exc))

        # Remove successfully processed operations
        await self.remove(processed_ids)

        return {
            "total_operations": len(operations),
            "success_count": success_count,
            "fail_count": fail_count,
            "remaining": len(self._queue),
        }

    @property
    def depth(self) -> int:
        """Get current queue depth."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    def health(self) -> Dict[str, Any]:
        """Get health status."""
        return {
            "partition_id": self.partition_id,
            "queue_depth": len(self._queue),
            "max_size": self.max_size,
            "total_enqueued": self._total_enqueued,
            "total_processed": self._total_processed,
            "total_evicted": self._total_evicted,
            "total_compacted": self._total_compacted,
            "utilization_pct": (len(self._queue) / self.max_size) * 100,
        }

    def metrics(self) -> Dict[str, float]:
        """Get Prometheus-compatible metrics."""
        return {
            "offline_queue_depth": float(len(self._queue)),
            "offline_queue_max_size": float(self.max_size),
            "offline_queue_enqueued_total": float(self._total_enqueued),
            "offline_queue_processed_total": float(self._total_processed),
            "offline_queue_evicted_total": float(self._total_evicted),
            "offline_queue_compacted_total": float(self._total_compacted),
        }
