"""Integration tests for SpatialProcessor.process_frame() end-to-end pipeline.

T-016: Validates detection → segmentation → depth → fusion → navigation output.
"""

import time
from typing import Any, List

import numpy as np
import pytest
from PIL import Image

from core.vision.spatial import (
    BaseDetector,
    SimpleDepthEstimator,
    SpatialProcessor,
    create_spatial_processor,
)
from shared.schemas import (
    BoundingBox,
    DepthMap,
    Detection,
    Direction,
    NavigationOutput,
    Priority,
)

# ---------------------------------------------------------------------------
# Test-local mock detectors
# ---------------------------------------------------------------------------


class _EmptyDetector(BaseDetector):
    """Returns zero detections (blank scene)."""

    async def detect(self, image: Any) -> List[Detection]:
        return []

    def is_ready(self) -> bool:
        return True


class _MultiDetector(BaseDetector):
    """Returns a configurable list of detections."""

    def __init__(self, detections: List[Detection]):
        self._detections = detections

    async def detect(self, image: Any) -> List[Detection]:
        return self._detections

    def is_ready(self) -> bool:
        return True


class _FixedDepthEstimator(SimpleDepthEstimator):
    """Returns a uniform depth map at a fixed value (full image resolution)."""

    def __init__(self, depth_value: float):
        super().__init__()
        self._fixed = depth_value

    async def estimate_depth(self, image: Any) -> DepthMap:
        width, height = image.size
        arr = np.full((height, width), self._fixed, dtype=np.float32)
        return DepthMap(depth_array=arr, min_depth=self._fixed, max_depth=self._fixed, is_metric=False)

def _make_image(w: int = 640, h: int = 480) -> Image.Image:
    return Image.new("RGB", (w, h), color=(100, 100, 100))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSpatialPipeline:
    """End-to-end integration tests for SpatialProcessor."""

    async def test_process_frame_returns_navigation_output(self):
        """Default mock components produce a valid NavigationOutput."""
        processor = SpatialProcessor()
        nav = await processor.process_frame(_make_image())

        assert isinstance(nav, NavigationOutput)
        assert isinstance(nav.short_cue, str) and len(nav.short_cue) > 0
        assert isinstance(nav.verbose_description, str) and len(nav.verbose_description) > 0
        assert isinstance(nav.telemetry, list)
        assert isinstance(nav.has_critical, bool)

    async def test_process_frame_empty_scene(self):
        """Empty detection list yields 'Path clear.' with no critical flag."""
        processor = SpatialProcessor(detector=_EmptyDetector())
        nav = await processor.process_frame(_make_image())

        assert nav.short_cue == "Path clear."
        assert nav.has_critical is False
        assert nav.telemetry == []

    async def test_obstacle_priority_sorting(self):
        """Obstacles are sorted CRITICAL before FAR_HAZARD."""
        # Detection near bottom-center → close, detection near top-right → far
        close_det = Detection(id="obj_close", class_name="chair", confidence=0.9, bbox=BoundingBox(290, 400, 350, 460))
        far_det = Detection(id="obj_far", class_name="table", confidence=0.8, bbox=BoundingBox(500, 20, 560, 80))

        # Full-resolution depth array (480x640): bottom half shallow, top half deep
        depth_arr = np.zeros((480, 640), dtype=np.float32)
        depth_arr[:240, :] = 4.0   # top half → far
        depth_arr[240:, :] = 0.6   # bottom half → close

        class _GradientDepth(SimpleDepthEstimator):
            async def estimate_depth(self, image: Any) -> DepthMap:
                return DepthMap(depth_array=depth_arr, min_depth=0.6, max_depth=4.0, is_metric=False)

        processor = SpatialProcessor(
            detector=_MultiDetector([close_det, far_det]),
            depth_estimator=_GradientDepth(),
        )
        nav = await processor.process_frame(_make_image())

        assert len(nav.telemetry) == 2
        assert nav.telemetry[0]["priority"] == Priority.CRITICAL.value
        # Second obstacle should have a less urgent priority
        assert nav.telemetry[1]["priority"] in (Priority.FAR_HAZARD.value, Priority.NEAR_HAZARD.value, Priority.SAFE.value)

    async def test_has_critical_flag_consistency(self):
        """has_critical True when obstacle < 1m, False when > 5m."""
        center_det = Detection(id="obj_1", class_name="person", confidence=0.9, bbox=BoundingBox(290, 200, 350, 280))

        # Critical case: depth 0.5m
        processor_critical = SpatialProcessor(
            detector=_MultiDetector([center_det]),
            depth_estimator=_FixedDepthEstimator(0.5),
        )
        nav_crit = await processor_critical.process_frame(_make_image())
        assert nav_crit.has_critical is True

        # Safe case: depth 6.0m
        processor_safe = SpatialProcessor(
            detector=_MultiDetector([center_det]),
            depth_estimator=_FixedDepthEstimator(6.0),
        )
        nav_safe = await processor_safe.process_frame(_make_image())
        assert nav_safe.has_critical is False

    async def test_direction_assignment_accuracy(self):
        """Bbox at known x positions maps to correct Direction values."""
        # FAR_LEFT: center_x ~32
        det_left = Detection(id="obj_l", class_name="pole", confidence=0.8, bbox=BoundingBox(12, 200, 52, 260))
        # CENTER: center_x ~320
        det_center = Detection(id="obj_c", class_name="chair", confidence=0.8, bbox=BoundingBox(300, 200, 340, 260))
        # FAR_RIGHT: center_x ~608
        det_right = Detection(id="obj_r", class_name="bin", confidence=0.8, bbox=BoundingBox(588, 200, 628, 260))

        processor = SpatialProcessor(
            detector=_MultiDetector([det_left, det_center, det_right]),
            depth_estimator=_FixedDepthEstimator(3.0),
        )
        nav = await processor.process_frame(_make_image())

        directions = {t["id"]: t["direction"] for t in nav.telemetry}
        assert directions["obj_l"] == Direction.FAR_LEFT.value
        assert directions["obj_c"] == Direction.CENTER.value
        assert directions["obj_r"] == Direction.FAR_RIGHT.value

    async def test_process_frame_latency_under_300ms(self):
        """Full pipeline with mock components completes within 300ms SLA."""
        processor = SpatialProcessor()
        image = _make_image()

        start = time.time()
        await processor.process_frame(image)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 300, f"Pipeline took {elapsed_ms:.0f}ms, exceeds 300ms SLA"

    async def test_get_quick_warning_fast_path(self):
        """get_quick_warning returns a non-empty string without errors."""
        processor = SpatialProcessor()
        warning = await processor.get_quick_warning(_make_image())

        assert isinstance(warning, str)
        assert len(warning) > 0

    @pytest.mark.integration
    async def test_process_frame_real_models(self):
        """Conditional test: real YOLO+MiDaS if models are available."""
        processor = create_spatial_processor(use_yolo=True, use_midas=True)
        if not processor.is_ready:
            pytest.skip("Real models not available")

        nav = await processor.process_frame(_make_image())
        assert isinstance(nav, NavigationOutput)
        assert isinstance(nav.short_cue, str)
        assert isinstance(nav.telemetry, list)
        assert isinstance(nav.has_critical, bool)
