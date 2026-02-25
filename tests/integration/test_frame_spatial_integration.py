"""Integration tests for FrameOrchestrator + SpatialProcessor wiring (T-031).

Validates that ``create_frame_bindings`` and ``create_wired_orchestrator``
correctly bridge ``core.vision.spatial`` into ``application.frame_processing``.
"""

from __future__ import annotations

import asyncio
import time

from application.frame_processing.frame_orchestrator import (
    FrameOrchestratorConfig,
    FusedFrameResult,
)

# ── Fixtures ────────────────────────────────────────────────────────────────
from application.frame_processing.live_frame_manager import TimestampedFrame
from application.frame_processing.spatial_binding import (
    create_frame_bindings,
    create_wired_orchestrator,
)


def _make_fresh_frame(width: int = 640, height: int = 480) -> TimestampedFrame:
    """Create a fresh ``TimestampedFrame`` with a synthetic PIL image."""
    from PIL import Image

    image = Image.new("RGB", (width, height), color=(128, 128, 128))
    return TimestampedFrame(
        frame_id="frm_test_001",
        sequence_num=1,
        timestamp_epoch_ms=time.time() * 1000,
        image=image,
        width=width,
        height=height,
        source="test",
    )


def _make_stale_frame() -> TimestampedFrame:
    """Create a ``TimestampedFrame`` that is well past the freshness budget."""
    from PIL import Image

    image = Image.new("RGB", (640, 480), color=(64, 64, 64))
    return TimestampedFrame(
        frame_id="frm_stale_001",
        sequence_num=0,
        timestamp_epoch_ms=(time.time() - 10) * 1000,  # 10 seconds old
        image=image,
        width=640,
        height=480,
        source="test",
    )


# ============================================================================
# Tests
# ============================================================================


class TestFrameSpatialIntegration:
    """End-to-end integration tests: frame → orchestrator → spatial → result."""

    async def test_wired_orchestrator_detects_objects(self):
        """Process a frame through the full pipeline; expect detections."""
        orchestrator = create_wired_orchestrator()
        bindings = orchestrator._default_bindings

        frame = _make_fresh_frame()
        result = await orchestrator.process_frame(
            frame,
            detector=bindings["detector"],
            depth_estimator=bindings["depth_estimator"],
            segmenter=bindings["segmenter"],
        )

        assert isinstance(result, FusedFrameResult)
        assert result.frame_id == "frm_test_001"
        # MockObjectDetector returns at least 1 detection
        assert len(result.detections) >= 1

    async def test_wired_orchestrator_produces_depth(self):
        """Verify depth_map is populated with a valid DepthMap."""
        orchestrator = create_wired_orchestrator()
        bindings = orchestrator._default_bindings

        frame = _make_fresh_frame()
        result = await orchestrator.process_frame(
            frame,
            detector=bindings["detector"],
            depth_estimator=bindings["depth_estimator"],
        )

        assert result.depth_map is not None
        # DepthMap should have a depth_array attribute
        assert hasattr(result.depth_map, "depth_array")

    async def test_wired_orchestrator_builds_scene_graph(self):
        """Verify scene_graph is populated when scene builder is provided."""
        orchestrator = create_wired_orchestrator()
        bindings = orchestrator._default_bindings

        frame = _make_fresh_frame()
        result = await orchestrator.process_frame(
            frame,
            detector=bindings["detector"],
            depth_estimator=bindings["depth_estimator"],
        )

        # Scene graph should be built when detections exist
        assert result.scene_graph is not None
        assert hasattr(result.scene_graph, "obstacles")
        assert hasattr(result.scene_graph, "frame_id")
        assert result.scene_graph.frame_id == "frm_test_001"

    async def test_wired_orchestrator_records_telemetry(self):
        """Verify telemetry has latencies for detection and depth modules."""
        orchestrator = create_wired_orchestrator()
        bindings = orchestrator._default_bindings

        frame = _make_fresh_frame()
        result = await orchestrator.process_frame(
            frame,
            detector=bindings["detector"],
            depth_estimator=bindings["depth_estimator"],
        )

        assert result.telemetry is not None
        assert "detection" in result.telemetry.latencies_per_module
        assert "depth" in result.telemetry.latencies_per_module
        assert result.telemetry.latencies_per_module["detection"] >= 0
        assert result.telemetry.latencies_per_module["depth"] >= 0
        # At least detection should succeed
        assert "detection" in result.telemetry.modules_succeeded

    async def test_stale_frame_rejected(self):
        """Pass a very old TimestampedFrame; verify freshness gate triggers."""
        orchestrator = create_wired_orchestrator()
        bindings = orchestrator._default_bindings

        frame = _make_stale_frame()
        result = await orchestrator.process_frame(
            frame,
            detector=bindings["detector"],
            depth_estimator=bindings["depth_estimator"],
        )

        # Stale frame should be rejected — no detections processed
        assert len(result.detections) == 0
        assert result.depth_map is None
        # Freshness gate failure should be recorded
        assert "freshness_gate" in result.telemetry.modules_failed

    async def test_create_frame_bindings_returns_callables(self):
        """Verify returned dict has correct keys and values are async callables."""
        bindings = create_frame_bindings()

        assert "detector" in bindings
        assert "depth_estimator" in bindings
        assert "segmenter" in bindings

        # All values should be async callables
        assert asyncio.iscoroutinefunction(bindings["detector"])
        assert asyncio.iscoroutinefunction(bindings["depth_estimator"])
        assert asyncio.iscoroutinefunction(bindings["segmenter"])

    async def test_pipeline_timeout_returns_partial(self):
        """Set very low timeout; verify partial results returned without crash."""
        cfg = FrameOrchestratorConfig(
            pipeline_timeout_ms=1,  # 1ms — will almost certainly time out
            enable_depth=True,
            enable_segmentation=False,
        )
        orchestrator = create_wired_orchestrator(config=cfg)
        bindings = orchestrator._default_bindings

        frame = _make_fresh_frame()
        # Should NOT raise — never-raise guarantee
        result = await orchestrator.process_frame(
            frame,
            detector=bindings["detector"],
            depth_estimator=bindings["depth_estimator"],
        )

        assert isinstance(result, FusedFrameResult)
        assert result.frame_id == "frm_test_001"
        # Either partial results or empty — both valid under timeout
        assert result.telemetry is not None

    async def test_fused_result_freshness(self):
        """Verify FusedFrameResult.is_fresh() works correctly."""
        orchestrator = create_wired_orchestrator()
        bindings = orchestrator._default_bindings

        frame = _make_fresh_frame()
        result = await orchestrator.process_frame(
            frame,
            detector=bindings["detector"],
            depth_estimator=bindings["depth_estimator"],
        )

        # Result from a fresh frame should still be fresh
        assert result.is_fresh(max_age_ms=5000)

        # Artificially old timestamp should not be fresh
        result.frame_timestamp_ms = (time.time() - 60) * 1000
        assert not result.is_fresh(max_age_ms=500)
