"""
Timing utility for measuring latency in the Voice-Vision Assistant pipeline.
Helps identify bottlenecks in STT, LLM, TTS, and vision processing.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("timing-profiler")

@dataclass
class TimingResult:
    """Stores timing information for a single operation."""
    name: str
    start_time: float
    end_time: float = 0.0

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    def __str__(self):
        return f"{self.name}: {self.duration_ms:.1f}ms"


class PipelineProfiler:
    """
    Profiles the entire voice assistant pipeline to identify latency bottlenecks.

    Usage:
        profiler = PipelineProfiler()

        with profiler.measure("stt_processing"):
            await process_speech()

        with profiler.measure("llm_inference"):
            await generate_response()

        profiler.log_summary()
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.timings: Dict[str, List[TimingResult]] = {}
        self.current_request_id: str = ""
        self._request_start: float = 0.0

    def start_request(self, request_id: Optional[str] = None):
        """Mark the start of a new request."""
        self._request_start = time.perf_counter()
        self.current_request_id = request_id or f"req_{int(time.time() * 1000)}"
        logger.info(f"⏱️ Request started: {self.current_request_id}")

    def end_request(self):
        """Mark the end of a request and log total time."""
        if self._request_start > 0:
            total_ms = (time.perf_counter() - self._request_start) * 1000
            logger.info(f"⏱️ Request completed: {self.current_request_id} - Total: {total_ms:.1f}ms")
            self._request_start = 0.0

    @contextmanager
    def measure(self, operation_name: str):
        """Context manager to measure synchronous operations."""
        if not self.enabled:
            yield
            return

        result = TimingResult(name=operation_name, start_time=time.perf_counter())
        try:
            yield result
        finally:
            result.end_time = time.perf_counter()
            self._record(result)

    @asynccontextmanager
    async def measure_async(self, operation_name: str):
        """Async context manager to measure async operations."""
        if not self.enabled:
            yield
            return

        result = TimingResult(name=operation_name, start_time=time.perf_counter())
        try:
            yield result
        finally:
            result.end_time = time.perf_counter()
            self._record(result)

    def _record(self, result: TimingResult):
        """Record a timing result."""
        if result.name not in self.timings:
            self.timings[result.name] = []
        self.timings[result.name].append(result)

        # Log immediately for real-time feedback
        emoji = self._get_emoji(result.duration_ms)
        logger.info(f"{emoji} {result}")

    def _get_emoji(self, duration_ms: float) -> str:
        """Get emoji based on duration for quick visual feedback."""
        if duration_ms < 100:
            return "🟢"  # Fast
        elif duration_ms < 500:
            return "🟡"  # Moderate
        elif duration_ms < 1000:
            return "🟠"  # Slow
        else:
            return "🔴"  # Very slow

    def get_stats(self, operation_name: str) -> Dict:
        """Get statistics for a specific operation."""
        if operation_name not in self.timings:
            return {}

        durations = [t.duration_ms for t in self.timings[operation_name]]
        return {
            "count": len(durations),
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
        }

    def log_summary(self):
        """Log a summary of all timings."""
        if not self.timings:
            logger.info("No timing data collected")
            return

        logger.info("=" * 50)
        logger.info("⏱️ PIPELINE TIMING SUMMARY")
        logger.info("=" * 50)

        total_avg = 0.0
        for name, results in self.timings.items():
            stats = self.get_stats(name)
            logger.info(f"  {name}:")
            logger.info(f"    Avg: {stats['avg_ms']:.1f}ms | Min: {stats['min_ms']:.1f}ms | Max: {stats['max_ms']:.1f}ms | Count: {stats['count']}")
            total_avg += stats['avg_ms']

        logger.info("-" * 50)
        logger.info(f"  TOTAL AVG: {total_avg:.1f}ms")
        logger.info("=" * 50)

    def reset(self):
        """Reset all timing data."""
        self.timings.clear()


# Global profiler instance
_profiler: Optional[PipelineProfiler] = None

def get_profiler() -> PipelineProfiler:
    """Get the global profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = PipelineProfiler(enabled=True)
    return _profiler


def measure(operation_name: str):
    """Convenience decorator for measuring function execution time."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with get_profiler().measure_async(operation_name):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with get_profiler().measure(operation_name):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator


# Quick timing functions for inline use
def time_start() -> float:
    """Start a timer and return the start time."""
    return time.perf_counter()

def time_end(start: float, label: str) -> float:
    """End a timer and log the duration. Returns duration in ms."""
    duration_ms = (time.perf_counter() - start) * 1000
    emoji = "🟢" if duration_ms < 100 else "🟡" if duration_ms < 500 else "🟠" if duration_ms < 1000 else "🔴"
    logger.info(f"{emoji} {label}: {duration_ms:.1f}ms")
    return duration_ms
