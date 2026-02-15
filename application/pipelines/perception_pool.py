"""
Perception Worker Pool
======================

Offloads ALL CPU-intensive perception work to a dedicated thread pool,
keeping the asyncio event loop free for audio I/O, WebRTC, and TTS.

This fixes the #2 root cause: synchronous ONNX inference, PIL ops,
embedding generation, and FAISS search all running on the event loop.

Architecture::

    asyncio event loop (audio, WebRTC, TTS)
         │
         ├── submit_detection(image) ──→ ThreadPoolExecutor ──→ result
         ├── submit_depth(image)     ──→ ThreadPoolExecutor ──→ result  
         ├── submit_embedding(text)  ──→ ThreadPoolExecutor ──→ result
         └── submit_ocr(image)       ──→ ThreadPoolExecutor ──→ result
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("perception-pool")


@dataclass
class WorkerTelemetry:
    """Per-worker-type telemetry."""
    name: str
    total_calls: int = 0
    total_ms: float = 0.0
    failures: int = 0
    last_ms: float = 0.0
    active: int = 0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / max(1, self.total_calls)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_calls": self.total_calls,
            "avg_ms": round(self.avg_ms, 1),
            "last_ms": round(self.last_ms, 1),
            "failures": self.failures,
            "active": self.active,
        }


class PerceptionWorkerPool:
    """Thread-pool executor for CPU-bound perception tasks.

    All heavy operations (ONNX inference, FAISS search, embedding,
    PIL operations) are dispatched to threads, returning Futures
    that can be awaited from async code without blocking.

    Usage::

        pool = PerceptionWorkerPool(max_workers=4)
        pool.register("detection", yolo_detect_fn)
        pool.register("depth", midas_depth_fn)
        pool.register("embedding", sentence_embed_fn)

        # From async code:
        detections = await pool.submit("detection", image)
        depth_map = await pool.submit("depth", image)
        embedding = await pool.submit("embedding", text)
    """

    def __init__(
        self,
        max_workers: int = 4,
        thread_name_prefix: str = "perception",
    ):
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
        )
        self._workers: Dict[str, Callable] = {}
        self._telemetry: Dict[str, WorkerTelemetry] = {}
        self._max_workers = max_workers
        self._shutdown = False

    def register(self, name: str, fn: Callable) -> None:
        """Register a synchronous function for thread-pool execution.

        fn must be thread-safe and must not access asyncio primitives.
        """
        self._workers[name] = fn
        self._telemetry[name] = WorkerTelemetry(name=name)
        logger.info("Registered perception worker: %s", name)

    async def submit(
        self,
        name: str,
        *args: Any,
        timeout_ms: float = 500.0,
        **kwargs: Any,
    ) -> Any:
        """Submit a task to the thread pool and await the result.

        Raises:
            KeyError: if worker name not registered
            asyncio.TimeoutError: if execution exceeds timeout_ms
            RuntimeError: if pool is shut down
        """
        if self._shutdown:
            raise RuntimeError("PerceptionWorkerPool is shut down")

        fn = self._workers.get(name)
        if fn is None:
            raise KeyError(f"No worker registered for '{name}'")

        telemetry = self._telemetry[name]
        telemetry.active += 1
        telemetry.total_calls += 1

        loop = asyncio.get_running_loop()
        start = time.monotonic()

        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(self._executor, lambda: fn(*args, **kwargs)),
                timeout=timeout_ms / 1000.0,
            )
            elapsed = (time.monotonic() - start) * 1000
            telemetry.total_ms += elapsed
            telemetry.last_ms = elapsed
            return result

        except asyncio.TimeoutError:
            telemetry.failures += 1
            elapsed = (time.monotonic() - start) * 1000
            logger.warning("Worker '%s' timed out after %.0fms", name, elapsed)
            raise

        except Exception as exc:
            telemetry.failures += 1
            logger.error("Worker '%s' failed: %s", name, exc)
            raise

        finally:
            telemetry.active -= 1

    async def submit_parallel(
        self,
        tasks: Dict[str, tuple],
        timeout_ms: float = 500.0,
    ) -> Dict[str, Any]:
        """Submit multiple tasks in parallel and collect results.

        Args:
            tasks: Dict of {worker_name: (arg1, arg2, ...)}
            timeout_ms: Global timeout for all tasks

        Returns:
            Dict of {worker_name: result_or_None}
        """
        if not tasks:
            return {}

        async def _run(name: str, args: tuple) -> tuple:
            try:
                result = await self.submit(name, *args, timeout_ms=timeout_ms)
                return (name, result, None)
            except Exception as exc:
                return (name, None, exc)

        jobs = [_run(name, args) for name, args in tasks.items()]

        try:
            completed = await asyncio.wait_for(
                asyncio.gather(*jobs, return_exceptions=False),
                timeout=timeout_ms / 1000.0 + 0.5,  # slight buffer
            )
        except asyncio.TimeoutError:
            logger.warning("submit_parallel global timeout (%.0fms)", timeout_ms)
            return {name: None for name in tasks}

        results = {}
        for name, result, error in completed:
            if error:
                logger.debug("Parallel worker '%s' failed: %s", name, error)
                results[name] = None
            else:
                results[name] = result
        return results

    def shutdown(self) -> None:
        """Shutdown the thread pool."""
        self._shutdown = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        logger.info("PerceptionWorkerPool shut down")

    def health(self) -> dict:
        return {
            "max_workers": self._max_workers,
            "shutdown": self._shutdown,
            "workers": {n: t.to_dict() for n, t in self._telemetry.items()},
        }


# ============================================================================
# Convenience: pre-configured pool factory
# ============================================================================

def create_perception_pool(
    detector_fn: Optional[Callable] = None,
    depth_fn: Optional[Callable] = None,
    embedding_fn: Optional[Callable] = None,
    ocr_fn: Optional[Callable] = None,
    faiss_search_fn: Optional[Callable] = None,
    edge_density_fn: Optional[Callable] = None,
    max_workers: int = 4,
) -> PerceptionWorkerPool:
    """Create a pre-configured perception pool.

    All registered functions MUST be thread-safe synchronous callables.
    """
    pool = PerceptionWorkerPool(max_workers=max_workers)

    if detector_fn:
        pool.register("detection", detector_fn)
    if depth_fn:
        pool.register("depth", depth_fn)
    if embedding_fn:
        pool.register("embedding", embedding_fn)
    if ocr_fn:
        pool.register("ocr", ocr_fn)
    if faiss_search_fn:
        pool.register("faiss_search", faiss_search_fn)
    if edge_density_fn:
        pool.register("edge_density", edge_density_fn)

    return pool
