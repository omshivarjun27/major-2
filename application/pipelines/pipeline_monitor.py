"""
Pipeline Monitor
=================

Real-time performance monitoring with alerting.
Tracks latencies across the entire pipeline and fires
alerts when targets are missed.

Exposed via /debug/metrics endpoint for observability.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("pipeline-monitor")


@dataclass
class LatencyTarget:
    """A latency target with SLO tracking."""
    name: str
    target_ms: float
    window_size: int = 100
    _values: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    _violations: int = 0
    _total: int = 0

    def record(self, value_ms: float) -> bool:
        """Record a latency measurement. Returns True if within target."""
        self._values.append(value_ms)
        self._total += 1
        if value_ms > self.target_ms:
            self._violations += 1
            return False
        return True

    @property
    def avg_ms(self) -> float:
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)

    @property
    def p50_ms(self) -> float:
        if not self._values:
            return 0.0
        sorted_vals = sorted(self._values)
        return sorted_vals[len(sorted_vals) // 2]

    @property
    def p95_ms(self) -> float:
        if not self._values:
            return 0.0
        sorted_vals = sorted(self._values)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def p99_ms(self) -> float:
        if not self._values:
            return 0.0
        sorted_vals = sorted(self._values)
        idx = int(len(sorted_vals) * 0.99)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def slo_compliance(self) -> float:
        """Fraction of measurements within target (0.0 - 1.0)."""
        if self._total == 0:
            return 1.0
        return (self._total - self._violations) / self._total

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "target_ms": self.target_ms,
            "avg_ms": round(self.avg_ms, 1),
            "p50_ms": round(self.p50_ms, 1),
            "p95_ms": round(self.p95_ms, 1),
            "p99_ms": round(self.p99_ms, 1),
            "slo_compliance": round(self.slo_compliance, 3),
            "total_measurements": self._total,
            "violations": self._violations,
        }


@dataclass
class EventLoopHealth:
    """Monitors asyncio event loop responsiveness."""
    _check_intervals: Deque[float] = field(
        default_factory=lambda: deque(maxlen=100)
    )
    _max_stall_ms: float = 0.0
    _stall_count: int = 0
    _stall_threshold_ms: float = 50.0  # anything > 50ms is a stall

    def record_check(self, elapsed_ms: float) -> None:
        self._check_intervals.append(elapsed_ms)
        if elapsed_ms > self._stall_threshold_ms:
            self._stall_count += 1
            if elapsed_ms > self._max_stall_ms:
                self._max_stall_ms = elapsed_ms

    @property
    def avg_interval_ms(self) -> float:
        if not self._check_intervals:
            return 0.0
        return sum(self._check_intervals) / len(self._check_intervals)

    def to_dict(self) -> dict:
        return {
            "avg_interval_ms": round(self.avg_interval_ms, 1),
            "max_stall_ms": round(self._max_stall_ms, 1),
            "stall_count": self._stall_count,
            "stall_threshold_ms": self._stall_threshold_ms,
        }


class PipelineMonitor:
    """Central performance monitor for the entire pipeline.

    Tracks six stages:
      1. Frame capture latency
      2. Perception processing latency (detection + depth)
      3. LLM response latency (time to first token + total)
      4. TTS synthesis latency (time to first audio chunk)
      5. End-to-end latency (user speech → audio start)
      6. Event loop health (stall detection)

    Usage::

        monitor = PipelineMonitor()
        await monitor.start()

        # Record measurements throughout the pipeline
        monitor.record("frame_capture", 12.5)
        monitor.record("perception", 85.3)
        monitor.record("llm_first_token", 350.0)
        monitor.record("tts_synthesis", 120.0)
        monitor.record("end_to_end", 680.0)

        # Get dashboard
        print(monitor.dashboard())
    """

    # Default targets based on requirements
    DEFAULT_TARGETS = {
        "frame_capture": 50.0,       # 50ms to grab and convert a frame
        "perception": 200.0,         # 200ms for YOLO + depth + scene graph
        "llm_first_token": 400.0,    # 400ms to first LLM token
        "llm_total": 2000.0,         # 2s max for full LLM response
        "tts_first_chunk": 300.0,    # 300ms from text ready → first audio
        "tts_total": 1000.0,         # 1s max TTS per sentence
        "end_to_end": 800.0,         # 800ms user speech → audio start
        "audio_gap": 300.0,          # 300ms max gap between audio chunks
    }

    def __init__(
        self,
        targets: Optional[Dict[str, float]] = None,
        alert_callback: Optional[Callable] = None,
    ):
        _targets = {**self.DEFAULT_TARGETS, **(targets or {})}
        self._targets: Dict[str, LatencyTarget] = {
            name: LatencyTarget(name=name, target_ms=ms)
            for name, ms in _targets.items()
        }
        self._alert_callback = alert_callback
        self._event_loop_health = EventLoopHealth()
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._start_time = time.monotonic()

        # Counters
        self._total_queries = 0
        self._total_frames = 0
        self._active_queries = 0

    async def start(self) -> None:
        """Start the event loop health monitor."""
        if self._running:
            return
        self._running = True
        self._start_time = time.monotonic()
        self._monitor_task = asyncio.create_task(
            self._event_loop_monitor(), name="event_loop_monitor"
        )
        logger.info("PipelineMonitor started")

    async def stop(self) -> None:
        """Stop the monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("PipelineMonitor stopped")

    def record(self, stage: str, latency_ms: float) -> None:
        """Record a latency measurement for a pipeline stage."""
        target = self._targets.get(stage)
        if target:
            within_target = target.record(latency_ms)
            if not within_target and self._alert_callback:
                try:
                    self._alert_callback(stage, latency_ms, target.target_ms)
                except Exception:
                    pass
        else:
            # Auto-create target with generous default
            self._targets[stage] = LatencyTarget(
                name=stage, target_ms=5000.0
            )
            self._targets[stage].record(latency_ms)

    def record_query_start(self) -> float:
        """Record the start of a user query. Returns start time."""
        self._total_queries += 1
        self._active_queries += 1
        return time.monotonic()

    def record_query_end(self, start_time: float) -> float:
        """Record the end of a query. Returns total latency in ms."""
        self._active_queries = max(0, self._active_queries - 1)
        total_ms = (time.monotonic() - start_time) * 1000
        self.record("end_to_end", total_ms)
        return total_ms

    def record_frame(self) -> None:
        """Record a frame was processed."""
        self._total_frames += 1

    async def _event_loop_monitor(self) -> None:
        """Periodically check event loop responsiveness.

        Schedules a callback and measures how long it takes to execute.
        If the event loop is blocked, the callback will be delayed.
        """
        while self._running:
            start = time.monotonic()
            await asyncio.sleep(0.01)  # Request 10ms sleep
            actual_ms = (time.monotonic() - start) * 1000
            # Subtract the requested 10ms
            stall_ms = max(0, actual_ms - 10.0)
            self._event_loop_health.record_check(actual_ms)

            if stall_ms > 50:
                logger.warning(
                    "Event loop stall detected: %.0fms (target: 10ms)",
                    actual_ms,
                )

    def dashboard(self) -> dict:
        """Return full monitoring dashboard."""
        uptime_s = time.monotonic() - self._start_time
        return {
            "uptime_s": round(uptime_s, 1),
            "total_queries": self._total_queries,
            "total_frames": self._total_frames,
            "active_queries": self._active_queries,
            "stages": {
                name: target.to_dict()
                for name, target in self._targets.items()
            },
            "event_loop": self._event_loop_health.to_dict(),
            "overall_health": self._compute_health(),
        }

    def _compute_health(self) -> str:
        """Compute overall pipeline health."""
        critical_stages = ["end_to_end", "tts_first_chunk", "perception"]
        for stage in critical_stages:
            target = self._targets.get(stage)
            if target and target.slo_compliance < 0.9:
                return "DEGRADED"
        if self._event_loop_health._stall_count > 10:
            return "DEGRADED"
        return "HEALTHY"

    def health(self) -> dict:
        """Compact health check."""
        return {
            "status": self._compute_health(),
            "uptime_s": round(time.monotonic() - self._start_time, 1),
            "queries": self._total_queries,
            "frames": self._total_frames,
            "event_loop_stalls": self._event_loop_health._stall_count,
        }
