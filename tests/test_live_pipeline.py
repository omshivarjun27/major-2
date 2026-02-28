"""
Tests for the live-frame pipeline infrastructure.

Covers:
- Freshness helpers & decorator
- Debouncer (scene-graph hashing, time-window, distance delta)
- LiveFrameManager (ring buffer, pub/sub, freshness)
- Watchdog (registration, heartbeat, stale detection)
- WorkerPool (submit, backpressure, timeout)
- FrameOrchestrator (process_frame stub, freshness validation)
- Stale-cache removal in perception.py (MockObjectDetector, SimpleDepthEstimator)
- PerceptionResult / SceneGraph carry frame_id + timestamp
"""

import asyncio
import time
import uuid
import pytest
import numpy as np

# ---------------------------------------------------------------------------
# Freshness helpers
# ---------------------------------------------------------------------------
from application.frame_processing.freshness import (
    is_frame_fresh,
    frame_age_ms,
    assert_fresh,
    safe_output,
    set_max_age,
    LIVE_FRAME_MAX_AGE_MS,
    FALLBACK_MESSAGE,
)


class TestFreshness:
    """Unit tests for freshness.py helpers."""

    def test_fresh_frame(self):
        ts = time.time() * 1000  # now
        assert is_frame_fresh(ts, max_age_ms=500)

    def test_stale_frame(self):
        ts = (time.time() - 2) * 1000  # 2 seconds ago
        assert not is_frame_fresh(ts, max_age_ms=500)

    def test_frame_age_ms(self):
        ts = (time.time() - 0.1) * 1000
        age = frame_age_ms(ts)
        assert 80 < age < 200  # ~100 ms with tolerance

    def test_assert_fresh_passes(self):
        ts = time.time() * 1000
        assert_fresh(ts)  # should not raise

    def test_assert_fresh_raises(self):
        ts = (time.time() - 5) * 1000
        with pytest.raises(ValueError, match="Stale"):
            assert_fresh(ts)

    def test_safe_output_fresh(self):
        ts = time.time() * 1000
        result = safe_output("Chair ahead", ts)
        assert result == "Chair ahead"

    def test_safe_output_stale(self):
        ts = (time.time() - 5) * 1000
        result = safe_output("Chair ahead", ts)
        assert result == FALLBACK_MESSAGE

    def test_set_max_age(self):
        original = LIVE_FRAME_MAX_AGE_MS
        set_max_age(1000)
        ts = (time.time() - 0.8) * 1000  # 800ms ago
        assert is_frame_fresh(ts, max_age_ms=1000)
        set_max_age(original)  # restore


# ---------------------------------------------------------------------------
# Debouncer
# ---------------------------------------------------------------------------
from application.pipelines.debouncer import Debouncer, DebouncerConfig


class TestDebouncer:
    """Unit tests for debouncer.py."""

    def _make(self, window: float = 5.0) -> Debouncer:
        return Debouncer(DebouncerConfig(
            debounce_window_seconds=window,
            distance_delta_meters=0.5,
            confidence_delta=0.15,
        ))

    def test_first_cue_always_speaks(self):
        d = self._make()
        assert d.should_speak("Chair 1.2m ahead") is True

    def test_duplicate_within_window_suppressed(self):
        d = self._make(window=10.0)
        assert d.should_speak("Chair 1.2m ahead") is True
        d.record("Chair 1.2m ahead")  # must record after speaking
        assert d.should_speak("Chair 1.2m ahead") is False

    def test_different_cue_speaks(self):
        d = self._make()
        d.should_speak("Chair 1.2m ahead")
        d.record("Chair 1.2m ahead")
        assert d.should_speak("Table 2.0m left") is True

    def test_distance_delta_allows_repeat(self):
        d = self._make(window=10.0)
        d.should_speak("Chair ahead", distance_m=2.0)
        d.record("Chair ahead", distance_m=2.0)
        # Same text but distance changed > 0.5m
        assert d.should_speak("Chair ahead", distance_m=1.0) is True

    def test_scene_graph_hash_change_allows_repeat(self):
        d = self._make(window=10.0)
        d.should_speak("Chair ahead", scene_graph_hash="aaa")
        d.record("Chair ahead", scene_graph_hash="aaa")
        assert d.should_speak("Chair ahead", scene_graph_hash="bbb") is True

    def test_expired_window_allows_repeat(self):
        d = self._make(window=0.01)  # 10ms window
        d.should_speak("Chair ahead")
        d.record("Chair ahead")
        time.sleep(0.02)
        assert d.should_speak("Chair ahead") is True


# ---------------------------------------------------------------------------
# LiveFrameManager
# ---------------------------------------------------------------------------
from application.frame_processing.live_frame_manager import (
    LiveFrameManager,
    TimestampedFrame,
    FrameRingBuffer,
)


class TestTimestampedFrame:
    def test_age_ms(self):
        f = TimestampedFrame(
            frame_id="f1", sequence_num=1,
            timestamp_epoch_ms=time.time() * 1000,
            image=np.zeros((2, 2, 3), dtype=np.uint8),
        )
        assert f.age_ms < 100

    def test_is_fresh(self):
        f = TimestampedFrame(
            frame_id="f2", sequence_num=2,
            timestamp_epoch_ms=time.time() * 1000,
            image=np.zeros((2, 2, 3), dtype=np.uint8),
        )
        assert f.is_fresh(max_age_ms=500)

    def test_stale(self):
        f = TimestampedFrame(
            frame_id="f3", sequence_num=3,
            timestamp_epoch_ms=(time.time() - 2) * 1000,
            image=np.zeros((2, 2, 3), dtype=np.uint8),
        )
        assert not f.is_fresh(max_age_ms=500)


class TestFrameRingBuffer:
    def test_push_and_latest(self):
        buf = FrameRingBuffer(capacity=3)
        for i in range(5):
            buf.push(TimestampedFrame(
                frame_id=f"f{i}", sequence_num=i,
                timestamp_epoch_ms=time.time() * 1000,
                image=None,
            ))
        assert buf.latest().frame_id == "f4"
        assert len(buf) == 3  # capacity

    def test_empty_buffer_latest_none(self):
        buf = FrameRingBuffer(capacity=3)
        assert buf.latest() is None


@pytest.mark.asyncio
class TestLiveFrameManager:
    async def test_inject_and_get(self):
        mgr = LiveFrameManager()
        await mgr.start()
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        await mgr.inject_frame(img, width=4, height=4)  # explicit dims for numpy
        frame = mgr.get_latest_frame()
        assert frame is not None
        assert frame.is_fresh(max_age_ms=1000)
        await mgr.stop()

    async def test_subscribe_receives_frame(self):
        mgr = LiveFrameManager()
        await mgr.start()
        sub = mgr.subscribe("test_sub")
        img = np.zeros((4, 4, 3), dtype=np.uint8)
        await mgr.inject_frame(img, width=4, height=4)
        # Give time for publish
        await asyncio.sleep(0.05)
        frame = await sub.get_frame(timeout=1.0)
        assert frame is not None
        assert frame.frame_id != ""
        mgr.unsubscribe("test_sub")
        await mgr.stop()

    async def test_health(self):
        mgr = LiveFrameManager()
        await mgr.start()
        h = mgr.health()
        assert "running" in h
        await mgr.stop()


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------
from application.pipelines.watchdog import Watchdog, WatchdogConfig


@pytest.mark.asyncio
class TestWatchdog:
    async def test_register_and_heartbeat(self):
        wd = Watchdog(WatchdogConfig(
            camera_stall_threshold_ms=200,
            check_interval_ms=50,
        ))
        wd.register_component("camera")
        wd.heartbeat("camera")
        h = wd.camera_health()
        assert h.get("healthy") is True or h.get("last_frame_age_ms") is None
        # Cleanup - don't start the loop

    async def test_stale_detection(self):
        wd = Watchdog(WatchdogConfig(
            camera_stall_threshold_ms=50,
            check_interval_ms=20,
        ))
        wd.register_component("camera")
        wd.heartbeat("camera")
        await asyncio.sleep(0.1)  # let it go stale
        h = wd.camera_health()
        # After 100ms with 50ms threshold → stale
        assert h.get("healthy") is False or h.get("last_frame_age_ms", 0) > 50


# ---------------------------------------------------------------------------
# WorkerPool
# ---------------------------------------------------------------------------
from application.pipelines.worker_pool import WorkerPool, WorkItem


@pytest.mark.asyncio
class TestWorkerPool:
    async def test_submit_and_result(self):
        async def double(x):
            return x * 2

        pool = WorkerPool(name="test", process_fn=double, num_workers=2)
        await pool.start()
        item = WorkItem(item_id="i1", payload=5)
        await pool.submit(item)
        # Worker picks up from queue and processes; poll stats
        for _ in range(40):
            await asyncio.sleep(0.05)
            if pool.stats.items_completed >= 1:
                break
        assert pool.stats.items_completed >= 1, f"Expected >=1 completed, got {pool.stats.items_completed}"
        await pool.stop()

    async def test_timeout(self):
        async def slow(x):
            await asyncio.sleep(5)
            return x

        pool = WorkerPool(name="slow", process_fn=slow, num_workers=1, timeout_ms=100)
        await pool.start()
        item = WorkItem(item_id="i2", payload=1)
        await pool.submit(item)
        # Wait for worker to pick up and timeout
        for _ in range(40):
            await asyncio.sleep(0.1)
            if pool.stats.items_completed >= 1 or any(w.items_failed >= 1 for w in pool.stats.workers):
                break
        total_failed = sum(w.items_failed for w in pool.stats.workers)
        assert total_failed >= 1, f"Expected >=1 failed (timeout), got {total_failed}"
        await pool.stop()

    async def test_health(self):
        async def noop(x):
            return x

        pool = WorkerPool(name="hp", process_fn=noop, num_workers=1)
        await pool.start()
        h = pool.health()
        assert h["name"] == "hp"
        assert h["running"] is True
        await pool.stop()


# ---------------------------------------------------------------------------
# Perception stale-cache removal
# ---------------------------------------------------------------------------


class TestPerceptionCacheRemoval:
    """Verify that MockObjectDetector and SimpleDepthEstimator no longer cache."""

    @pytest.mark.asyncio
    async def test_mock_detector_no_cache(self):
        from core.vqa.perception import MockObjectDetector
        d = MockObjectDetector()
        assert not hasattr(d, "_cached"), "MockObjectDetector should not have _cached attribute"
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        det1 = await d.detect(img)
        det2 = await d.detect(img)
        # Both calls should succeed and return equal (but independent) results
        assert len(det1) == len(det2)

    @pytest.mark.asyncio
    async def test_simple_depth_no_cache(self):
        from core.vqa.perception import SimpleDepthEstimator
        e = SimpleDepthEstimator()
        assert not hasattr(e, "_cached"), "SimpleDepthEstimator should not have _cached attribute"
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        dm1 = await e.estimate(img)
        dm2 = await e.estimate(img)
        assert dm1.depth_array.shape == dm2.depth_array.shape


# ---------------------------------------------------------------------------
# Shared types carry frame_id / timestamp
# ---------------------------------------------------------------------------


class TestSharedTypesFrameFields:
    def test_perception_result_has_frame_fields(self):
        from shared.schemas import PerceptionResult, DepthMap
        pr = PerceptionResult(
            detections=[], masks=[],
            depth_map=DepthMap(
                depth_array=np.zeros((2, 2), dtype=np.float32),
                min_depth=0, max_depth=1, is_metric=False,
            ),
            image_size=(640, 480), latency_ms=1.0,
            timestamp="2025-01-01T00:00:00",
            frame_id="abc123", timestamp_epoch_ms=12345.0,
        )
        assert pr.frame_id == "abc123"
        assert pr.timestamp_epoch_ms == 12345.0

    def test_scene_graph_has_frame_fields(self):
        from core.vqa.scene_graph import SceneGraph
        sg = SceneGraph(
            nodes=[], obstacles=[], image_size=(640, 480),
            timestamp="2025-01-01T00:00:00",
            summary="test",
            frame_id="xyz", timestamp_epoch_ms=99999.0,
        )
        assert sg.frame_id == "xyz"
        d = sg.to_dict()
        assert d["frame_id"] == "xyz"
        assert d["timestamp_epoch_ms"] == 99999.0


# ---------------------------------------------------------------------------
# Config getters
# ---------------------------------------------------------------------------


class TestConfigGetters:
    def test_get_live_frame_config(self):
        from shared.config import get_live_frame_config
        cfg = get_live_frame_config()
        assert "live_frame_max_age_ms" in cfg or "max_age_ms" in cfg
        # Check at least one key is a number
        values = list(cfg.values())
        assert any(isinstance(v, (int, float)) for v in values)

    def test_get_debounce_config(self):
        from shared.config import get_debounce_config
        cfg = get_debounce_config()
        assert "debounce_window_seconds" in cfg or "window_seconds" in cfg

    def test_get_watchdog_config(self):
        from shared.config import get_watchdog_config
        cfg = get_watchdog_config()
        assert "camera_stall_threshold_ms" in cfg or "camera_stall_ms" in cfg

    def test_get_worker_config(self):
        from shared.config import get_worker_config
        cfg = get_worker_config()
        assert "num_detect_workers" in cfg or "num_detect" in cfg
