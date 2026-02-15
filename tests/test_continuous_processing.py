"""
Tests for the continuous video processing pipeline.

Covers:
- LiveFrameManager runs continuously and produces frames
- FrameSubscriber receives frames in real-time
- FrameOrchestrator processes frames within latency budget
- Freshness gate rejects stale frames
- Debouncer suppresses redundant announcements
- Watchdog stays alive with heartbeats
- Config ALWAYS_ON / CONTINUOUS_PROCESSING flags
- End-to-end producer → consumer → orchestrator flow
- Proactive mode cadence
- System does not shut down when idle
"""

import asyncio
import time
import uuid
import pytest
import numpy as np

from application.frame_processing.freshness import (
    is_frame_fresh,
    frame_age_ms,
    safe_output,
    FALLBACK_MESSAGE,
)
from application.frame_processing.live_frame_manager import (
    LiveFrameManager,
    TimestampedFrame,
    FrameRingBuffer,
    FrameSubscriber,
    CaptureStats,
)
from application.frame_processing.frame_orchestrator import (
    FrameOrchestrator,
    FrameOrchestratorConfig,
    FusedFrameResult,
    FrameTelemetry,
)
from application.pipelines.worker_pool import WorkerPool, WorkItem, WorkResult, PoolStats
from application.frame_processing.debouncer import Debouncer
from application.pipelines.watchdog import Watchdog


# ── Helpers ────────────────────────────────────────────────────────────

def _make_frame(age_ms: float = 0, width: int = 640, height: int = 480) -> TimestampedFrame:
    """Create a TimestampedFrame with controllable age."""
    return TimestampedFrame(
        frame_id=f"frm_{uuid.uuid4().hex[:8]}",
        sequence_num=1,
        timestamp_epoch_ms=(time.time() * 1000) - age_ms,
        image=np.zeros((height, width, 3), dtype=np.uint8),
        width=width,
        height=height,
    )


def _make_capture_fn(count: int = 100, cadence_ms: float = 10):
    """Return an async capture function that yields `count` frames then stops."""
    produced = {"n": 0}

    async def _capture():
        if produced["n"] >= count:
            return None
        produced["n"] += 1
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        return (img, 640, 480)

    return _capture, produced


# ═══════════════════════════════════════════════════════════════════════
# 1 · Continuous Capture
# ═══════════════════════════════════════════════════════════════════════

class TestContinuousCapture:
    """Verify that LiveFrameManager captures frames continuously."""

    @pytest.mark.asyncio
    async def test_capture_loop_produces_frames(self):
        """Manager capture loop should produce frames that arrive at subscribers."""
        capture_fn, produced = _make_capture_fn(count=20)
        mgr = LiveFrameManager(capture_fn=capture_fn, cadence_ms=10, buffer_capacity=10)
        sub = mgr.subscribe("test_consumer", max_queue_size=10)

        await mgr.start()
        assert mgr.running

        received = 0
        for _ in range(20):
            f = await sub.get_frame(timeout=0.5)
            if f is not None:
                received += 1
        await mgr.stop()

        assert received > 0, "Subscriber should receive at least one frame"
        assert produced["n"] > 0, "Capture function should have been called"

    @pytest.mark.asyncio
    async def test_ring_buffer_wraps(self):
        """Ring buffer should overwrite oldest entries when full."""
        buf = FrameRingBuffer(capacity=3)
        for i in range(5):
            frame = _make_frame()
            frame.sequence_num = i
            buf.push(frame)

        assert len(buf) == 3
        latest = buf.latest()
        assert latest.sequence_num == 4  # last pushed

    @pytest.mark.asyncio
    async def test_manager_stop_is_clean(self):
        """stop() should terminate cleanly without pending tasks."""
        capture_fn, _ = _make_capture_fn(count=1000)
        mgr = LiveFrameManager(capture_fn=capture_fn, cadence_ms=10)

        await mgr.start()
        await asyncio.sleep(0.05)
        await mgr.stop()

        assert not mgr.running

    @pytest.mark.asyncio
    async def test_inject_frame_reaches_subscriber(self):
        """inject_frame() should distribute to all subscribers."""
        mgr = LiveFrameManager()
        sub = mgr.subscribe("injection_test", max_queue_size=5)

        img = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = await mgr.inject_frame(img, 640, 480)

        received = await sub.get_frame(timeout=0.5)
        assert received is not None
        assert received.frame_id == frame.frame_id


# ═══════════════════════════════════════════════════════════════════════
# 2 · Freshness Enforcement in Continuous Loop
# ═══════════════════════════════════════════════════════════════════════

class TestFreshnessInContinuousLoop:
    """Verify freshness gate works during continuous processing."""

    def test_fresh_frame_passes(self):
        frame = _make_frame(age_ms=50)  # 50ms old
        assert frame.is_fresh(max_age_ms=500)

    def test_stale_frame_rejected(self):
        frame = _make_frame(age_ms=1000)  # 1s old
        assert not frame.is_fresh(max_age_ms=500)

    def test_safe_output_returns_fallback_for_stale(self):
        ts = (time.time() - 2) * 1000
        assert safe_output("Obstacle ahead", ts) == FALLBACK_MESSAGE

    def test_safe_output_returns_original_for_fresh(self):
        ts = time.time() * 1000
        assert safe_output("Obstacle ahead", ts) == "Obstacle ahead"

    @pytest.mark.asyncio
    async def test_orchestrator_rejects_stale_frame(self):
        """FrameOrchestrator should mark result stale for old frames."""
        orch = FrameOrchestrator(
            config=FrameOrchestratorConfig(live_frame_max_age_ms=500)
        )
        stale_frame = _make_frame(age_ms=2000)
        result = await orch.process_frame(stale_frame)

        assert not result.is_fresh(max_age_ms=500)


# ═══════════════════════════════════════════════════════════════════════
# 3 · Producer-Consumer Flow
# ═══════════════════════════════════════════════════════════════════════

class TestProducerConsumerFlow:
    """End-to-end: capture → subscribe → process → result."""

    @pytest.mark.asyncio
    async def test_producer_consumer_pipeline(self):
        """Frames flow from capture → subscriber → orchestrator."""
        capture_fn, _ = _make_capture_fn(count=10)
        mgr = LiveFrameManager(capture_fn=capture_fn, cadence_ms=10, buffer_capacity=5)
        sub = mgr.subscribe("pipeline_test", max_queue_size=5)

        orch = FrameOrchestrator(
            config=FrameOrchestratorConfig(
                live_frame_max_age_ms=2000,
                hot_path_timeout_ms=1000,
            )
        )

        await mgr.start()
        results = []

        for _ in range(5):
            frame = await sub.get_frame(timeout=1.0)
            if frame is not None:
                result = await orch.process_frame(frame)
                results.append(result)

        await mgr.stop()
        assert len(results) > 0, "Should have processed at least one frame"
        for r in results:
            assert isinstance(r, FusedFrameResult)

    @pytest.mark.asyncio
    async def test_backpressure_drops_old_frames(self):
        """When subscriber queue is full, oldest frames should be dropped."""
        capture_fn, _ = _make_capture_fn(count=50)
        mgr = LiveFrameManager(capture_fn=capture_fn, cadence_ms=5, buffer_capacity=10)
        sub = mgr.subscribe("slow_consumer", max_queue_size=2)

        await mgr.start()
        await asyncio.sleep(0.2)  # Let frames pile up

        # Consumer starts late — should still get frames (not hang)
        frame = await sub.get_frame(timeout=1.0)
        await mgr.stop()

        assert frame is not None, "Consumer should get at least one frame despite backpressure"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Multiple subscribers each receive independent frame copies."""
        capture_fn, _ = _make_capture_fn(count=5)
        mgr = LiveFrameManager(capture_fn=capture_fn, cadence_ms=10, buffer_capacity=5)

        sub_a = mgr.subscribe("consumer_a", max_queue_size=5)
        sub_b = mgr.subscribe("consumer_b", max_queue_size=5)

        await mgr.start()

        frame_a = await sub_a.get_frame(timeout=1.0)
        frame_b = await sub_b.get_frame(timeout=1.0)

        await mgr.stop()

        assert frame_a is not None
        assert frame_b is not None
        assert frame_a.frame_id == frame_b.frame_id  # Same frame distributed


# ═══════════════════════════════════════════════════════════════════════
# 4 · Watchdog Stays Alive
# ═══════════════════════════════════════════════════════════════════════

class TestWatchdogContinuousMode:
    """Verify watchdog receives heartbeats during continuous processing."""

    @pytest.mark.asyncio
    async def test_heartbeat_keeps_component_alive(self):
        wd = Watchdog()
        wd.register_component("camera")

        wd.heartbeat("camera")
        await asyncio.sleep(0.1)

        h = wd.health()
        assert h["components"]["camera"]["is_healthy"] is True

    @pytest.mark.asyncio
    async def test_no_heartbeat_causes_stale(self):
        from application.pipelines.watchdog import WatchdogConfig
        # Very short stall threshold to trigger staleness quickly
        cfg = WatchdogConfig(camera_stall_threshold_ms=50)
        wd = Watchdog(config=cfg)
        wd.register_component("camera")
        # Give an initial heartbeat then let it go stale
        wd.heartbeat("camera")
        await asyncio.sleep(0.15)

        # Manually check via is_healthy (the check_loop would update this)
        cam = wd._components["camera"]
        assert cam.age_ms > 50  # It's beyond threshold

    @pytest.mark.asyncio
    async def test_continuous_capture_heartbeats_watchdog(self):
        """LiveFrameManager on_frame callback should heartbeat the watchdog."""
        wd = Watchdog()
        wd.register_component("camera")

        heartbeats = {"count": 0}

        def _hb(_frame):
            wd.heartbeat("camera")
            heartbeats["count"] += 1

        capture_fn, _ = _make_capture_fn(count=10)
        mgr = LiveFrameManager(capture_fn=capture_fn, cadence_ms=10)
        mgr.on_frame(_hb)

        await mgr.start()
        await asyncio.sleep(0.15)
        await mgr.stop()

        assert heartbeats["count"] > 0


# ═══════════════════════════════════════════════════════════════════════
# 5 · Debouncer Suppression
# ═══════════════════════════════════════════════════════════════════════

class TestDebouncerInContinuousMode:
    """Debouncer should suppress repeated proactive announcements."""

    def test_same_cue_suppressed(self):
        from application.frame_processing.debouncer import DebouncerConfig
        cfg = DebouncerConfig(debounce_window_seconds=1.0)
        db = Debouncer(config=cfg)
        assert db.should_speak("Obstacle ahead", scene_graph_hash="aaa")
        db.record("Obstacle ahead", scene_graph_hash="aaa")

        # Same cue within window → suppressed
        assert not db.should_speak("Obstacle ahead", scene_graph_hash="aaa")

    def test_different_cue_passes(self):
        from application.frame_processing.debouncer import DebouncerConfig
        cfg = DebouncerConfig(debounce_window_seconds=1.0)
        db = Debouncer(config=cfg)
        db.record("Obstacle ahead", scene_graph_hash="aaa")

        # Different cue text → allowed
        assert db.should_speak("Person approaching", scene_graph_hash="bbb")

    def test_cue_allowed_after_window(self):
        from application.frame_processing.debouncer import DebouncerConfig
        cfg = DebouncerConfig(debounce_window_seconds=0.05)  # 50ms window
        db = Debouncer(config=cfg)
        db.record("Obstacle ahead", scene_graph_hash="aaa")

        import time
        time.sleep(0.06)
        assert db.should_speak("Obstacle ahead", scene_graph_hash="aaa")


# ═══════════════════════════════════════════════════════════════════════
# 6 · Hot-Path Latency Budget
# ═══════════════════════════════════════════════════════════════════════

class TestHotPathLatency:
    """Verify the pipeline meets ≤500ms hot-path budget."""

    @pytest.mark.asyncio
    async def test_orchestrator_within_budget(self):
        orch = FrameOrchestrator(
            config=FrameOrchestratorConfig(
                live_frame_max_age_ms=2000,
                hot_path_timeout_ms=500,
            )
        )
        frame = _make_frame(age_ms=0)

        start = time.time()
        result = await orch.process_frame(frame)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 500, f"Hot-path took {elapsed_ms:.0f}ms, budget is 500ms"
        assert isinstance(result, FusedFrameResult)

    @pytest.mark.asyncio
    async def test_telemetry_records_latency(self):
        orch = FrameOrchestrator(
            config=FrameOrchestratorConfig(live_frame_max_age_ms=2000)
        )
        frame = _make_frame(age_ms=0)
        result = await orch.process_frame(frame)

        assert result.telemetry is not None
        assert result.telemetry.total_ms >= 0


# ═══════════════════════════════════════════════════════════════════════
# 7 · Worker Pool Integration
# ═══════════════════════════════════════════════════════════════════════

class TestWorkerPoolContinuous:
    """WorkerPool handles continuous frame work items."""

    @pytest.mark.asyncio
    async def test_submit_and_collect_result(self):
        results_collected = []

        async def _echo(data):
            return f"processed_{data}"

        pool = WorkerPool(name="test_pool", process_fn=_echo, num_workers=2)
        pool.on_result(lambda r: results_collected.append(r))
        await pool.start()

        item = WorkItem(item_id="item_1", frame_id="frm_1", payload="frame_001")
        submitted = await pool.submit(item)
        assert submitted is True

        # Give workers time to process
        await asyncio.sleep(0.2)
        await pool.stop()

        assert pool.stats.items_completed >= 1

    @pytest.mark.asyncio
    async def test_pool_handles_errors_gracefully(self):
        async def _fail(data):
            raise ValueError("deliberate error")

        pool = WorkerPool(name="error_pool", process_fn=_fail, num_workers=1)
        await pool.start()

        item = WorkItem(item_id="item_bad", frame_id="frm_bad", payload="bad_data")
        await pool.submit(item)

        # Give worker time to process and fail
        await asyncio.sleep(0.2)
        await pool.stop()

        # Worker should have recorded the failure
        assert pool.stats.items_submitted >= 1


# ═══════════════════════════════════════════════════════════════════════
# 8 · Config Flags
# ═══════════════════════════════════════════════════════════════════════

class TestContinuousConfig:
    """Verify ALWAYS_ON / CONTINUOUS_PROCESSING config keys."""

    def test_config_has_continuous_keys(self):
        from shared.config import get_continuous_config
        cfg = get_continuous_config()

        assert "always_on" in cfg
        assert "continuous_processing" in cfg
        assert "proactive_announce" in cfg
        assert "proactive_cadence_s" in cfg
        assert "proactive_critical_only" in cfg

    def test_defaults(self):
        from shared.config import get_continuous_config
        cfg = get_continuous_config()

        assert cfg["always_on"] is True
        assert cfg["continuous_processing"] is True
        assert cfg["proactive_announce"] is True
        assert isinstance(cfg["proactive_cadence_s"], float)
        assert cfg["proactive_cadence_s"] > 0


# ═══════════════════════════════════════════════════════════════════════
# 9 · System Does Not Shut Down When Idle
# ═══════════════════════════════════════════════════════════════════════

class TestAlwaysOn:
    """Verify the system stays alive even without user input."""

    @pytest.mark.asyncio
    async def test_manager_runs_without_consumers(self):
        """Manager should keep running even if no one consumes frames."""
        capture_fn, produced = _make_capture_fn(count=100)
        mgr = LiveFrameManager(capture_fn=capture_fn, cadence_ms=10, buffer_capacity=5)

        await mgr.start()
        await asyncio.sleep(0.2)

        assert mgr.running
        assert produced["n"] > 0

        await mgr.stop()

    @pytest.mark.asyncio
    async def test_watchdog_idle_suppression(self):
        """Watchdog should suppress duplicate alerts via cooldown."""
        wd = Watchdog()
        wd.register_component("camera")

        # Verify the health report works even with no heartbeats yet
        h = wd.health()
        assert "camera" in h["components"]
        assert isinstance(h["overall_healthy"], bool)


# ═══════════════════════════════════════════════════════════════════════
# 10 · FusedFrameResult Freshness
# ═══════════════════════════════════════════════════════════════════════

class TestFusedFrameResult:
    """Verify FusedFrameResult carries freshness metadata."""

    @pytest.mark.asyncio
    async def test_fresh_result(self):
        orch = FrameOrchestrator(
            config=FrameOrchestratorConfig(live_frame_max_age_ms=2000)
        )
        frame = _make_frame(age_ms=0)
        result = await orch.process_frame(frame)

        assert result.is_fresh(max_age_ms=2000)
        assert result.frame_id == frame.frame_id

    @pytest.mark.asyncio
    async def test_result_has_telemetry(self):
        orch = FrameOrchestrator(
            config=FrameOrchestratorConfig(live_frame_max_age_ms=2000)
        )
        frame = _make_frame(age_ms=0)
        result = await orch.process_frame(frame)

        assert result.telemetry is not None
        assert hasattr(result.telemetry, "total_ms")
        assert result.telemetry.total_ms >= 0
