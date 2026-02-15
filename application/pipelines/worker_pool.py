"""
Worker Pool
===========
Generic async worker pool with backpressure, configurable concurrency,
and per-worker telemetry.

Workers process items from a shared input queue and push results to
an output queue. Backpressure is handled by dropping oldest items
when the input queue exceeds capacity.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("worker-pool")


# ============================================================================
# Telemetry
# ============================================================================

@dataclass
class WorkerStats:
    """Per-worker telemetry."""
    worker_id: str
    items_processed: int = 0
    items_failed: int = 0
    total_processing_ms: float = 0.0
    last_processing_ms: float = 0.0
    busy: bool = False

    @property
    def avg_processing_ms(self) -> float:
        if self.items_processed == 0:
            return 0.0
        return self.total_processing_ms / self.items_processed

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
            "avg_processing_ms": round(self.avg_processing_ms, 1),
            "last_processing_ms": round(self.last_processing_ms, 1),
            "busy": self.busy,
        }


@dataclass
class PoolStats:
    """Aggregate pool telemetry."""
    pool_name: str
    num_workers: int
    items_submitted: int = 0
    items_completed: int = 0
    items_dropped: int = 0
    workers: List[WorkerStats] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pool_name": self.pool_name,
            "num_workers": self.num_workers,
            "items_submitted": self.items_submitted,
            "items_completed": self.items_completed,
            "items_dropped": self.items_dropped,
            "workers": [w.to_dict() for w in self.workers],
        }


# ============================================================================
# Work Item
# ============================================================================

@dataclass
class WorkItem:
    """An item submitted to a worker pool."""
    item_id: str
    payload: Any
    submitted_at: float = field(default_factory=time.time)
    frame_id: Optional[str] = None  # Link to source frame
    priority: int = 0  # Lower = higher priority

    @property
    def age_ms(self) -> float:
        return (time.time() - self.submitted_at) * 1000


@dataclass
class WorkResult:
    """Result produced by a worker."""
    item_id: str
    frame_id: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    processing_ms: float = 0.0
    worker_id: str = ""

    @property
    def success(self) -> bool:
        return self.error is None


# ============================================================================
# Worker Pool
# ============================================================================

class WorkerPool:
    """Async worker pool with backpressure.

    Parameters
    ----------
    name : str
        Human-readable pool name.
    process_fn : callable
        Async function: ``async def process(payload) -> result``.
    num_workers : int
        Number of concurrent workers (default 2).
    max_queue_size : int
        Max items in input queue; oldest dropped when exceeded.
    timeout_ms : float
        Per-item processing timeout.
    """

    def __init__(
        self,
        name: str,
        process_fn: Callable,
        num_workers: int = 2,
        max_queue_size: int = 10,
        timeout_ms: float = 500.0,
    ):
        self.name = name
        self._process_fn = process_fn
        self._num_workers = max(1, num_workers)
        self._max_queue_size = max(1, max_queue_size)
        self._timeout_s = timeout_ms / 1000.0
        self._input_queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._result_callbacks: List[Callable] = []
        self._workers: List[asyncio.Task] = []
        self._running = False
        self.stats = PoolStats(pool_name=name, num_workers=self._num_workers)

    # -- Lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        """Start worker tasks."""
        if self._running:
            return
        self._running = True
        self.stats.workers.clear()
        for i in range(self._num_workers):
            wid = f"{self.name}_w{i}"
            ws = WorkerStats(worker_id=wid)
            self.stats.workers.append(ws)
            task = asyncio.create_task(self._worker_loop(wid, ws))
            self._workers.append(task)
        logger.info("WorkerPool '%s' started (%d workers, queue=%d)",
                     self.name, self._num_workers, self._max_queue_size)

    async def stop(self) -> None:
        """Stop all workers gracefully."""
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("WorkerPool '%s' stopped. Stats: %s", self.name, self.stats.to_dict())

    @property
    def running(self) -> bool:
        return self._running

    # -- Submit & results ---------------------------------------------------

    async def submit(self, item: WorkItem) -> bool:
        """Submit a work item. Returns False if dropped due to backpressure."""
        self.stats.items_submitted += 1
        if self._input_queue.full():
            # Backpressure: drop oldest
            try:
                self._input_queue.get_nowait()
                self.stats.items_dropped += 1
                logger.debug("Pool '%s': dropped oldest item (backpressure)", self.name)
            except asyncio.QueueEmpty:
                pass
        try:
            self._input_queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            self.stats.items_dropped += 1
            return False

    def on_result(self, callback: Callable) -> None:
        """Register a callback for completed results."""
        self._result_callbacks.append(callback)

    # -- Worker loop --------------------------------------------------------

    async def _worker_loop(self, worker_id: str, ws: WorkerStats) -> None:
        """Individual worker coroutine."""
        logger.debug("Worker %s started", worker_id)
        while self._running:
            try:
                item: WorkItem = await asyncio.wait_for(
                    self._input_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            ws.busy = True
            start = time.time()
            result = WorkResult(item_id=item.item_id, frame_id=item.frame_id, worker_id=worker_id)

            try:
                output = await asyncio.wait_for(
                    self._process_fn(item.payload),
                    timeout=self._timeout_s,
                )
                result.result = output
                ws.items_processed += 1
                self.stats.items_completed += 1
            except asyncio.TimeoutError:
                result.error = f"timeout ({self._timeout_s * 1000:.0f}ms)"
                ws.items_failed += 1
                logger.warning("Worker %s: item %s timed out", worker_id, item.item_id)
            except Exception as exc:
                result.error = str(exc)
                ws.items_failed += 1
                logger.error("Worker %s: item %s failed: %s", worker_id, item.item_id, exc)
            finally:
                elapsed = (time.time() - start) * 1000
                result.processing_ms = elapsed
                ws.last_processing_ms = elapsed
                ws.total_processing_ms += elapsed
                ws.busy = False

            # Notify result callbacks
            for cb in self._result_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(result)
                    else:
                        cb(result)
                except Exception as exc:
                    logger.warning("Result callback error in pool '%s': %s", self.name, exc)

    # -- Health -------------------------------------------------------------

    def health(self) -> dict:
        return {
            "name": self.name,
            "running": self._running,
            "queue_size": self._input_queue.qsize(),
            "max_queue_size": self._max_queue_size,
            "stats": self.stats.to_dict(),
        }


# ============================================================================
# Convenience: create pre-configured pools for perception workers
# ============================================================================

def create_detection_pool(process_fn: Callable, num_workers: int = 2) -> WorkerPool:
    return WorkerPool("detection", process_fn, num_workers=num_workers, timeout_ms=300)

def create_depth_pool(process_fn: Callable, num_workers: int = 1) -> WorkerPool:
    return WorkerPool("depth", process_fn, num_workers=num_workers, timeout_ms=300)

def create_segmentation_pool(process_fn: Callable, num_workers: int = 1) -> WorkerPool:
    return WorkerPool("segmentation", process_fn, num_workers=num_workers, timeout_ms=300)

def create_ocr_pool(process_fn: Callable, num_workers: int = 1) -> WorkerPool:
    return WorkerPool("ocr", process_fn, num_workers=num_workers, timeout_ms=500)

def create_qr_pool(process_fn: Callable, num_workers: int = 1) -> WorkerPool:
    return WorkerPool("qr", process_fn, num_workers=num_workers, timeout_ms=300)

def create_embedding_pool(process_fn: Callable, num_workers: int = 1) -> WorkerPool:
    return WorkerPool("embedding", process_fn, num_workers=num_workers, max_queue_size=20, timeout_ms=1000)
