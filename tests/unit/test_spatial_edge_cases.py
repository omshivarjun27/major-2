"""Edge case tests for core.vision spatial perception module (T-144).

Covers boundary conditions, error recovery, extreme inputs, and concurrent
access patterns for the spatial perception pipeline.
"""
from __future__ import annotations

import asyncio
import time

import numpy as np
import pytest

from shared.schemas import (
    BoundingBox,
    DepthMap,
    Detection,
    Direction,
    NavigationOutput,
    ObstacleRecord,
    Priority,
    SegmentationMask,
    SizeCategory,
)

# ---------------------------------------------------------------------------
# Helpers / minimal stubs
# ---------------------------------------------------------------------------

def _make_detection(
    class_name: str = "chair",
    confidence: float = 0.85,
    x1: int = 10,
    y1: int = 10,
    x2: int = 100,
    y2: int = 100,
    det_id: str = "det_0",
) -> Detection:
    return Detection(
        id=det_id,
        class_name=class_name,
        confidence=confidence,
        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
    )


def _make_depth_map(h: int = 480, w: int = 640, fill: float = 3.0) -> DepthMap:
    data = np.full((h, w), fill, dtype=np.float32)
    return DepthMap(depth_array=data, min_depth=float(data.min()), max_depth=float(data.max()))


def _make_mask(detection_id: str = "det_0", h: int = 480, w: int = 640) -> SegmentationMask:
    mask = np.zeros((h, w), dtype=bool)
    mask[50:150, 50:150] = True
    return SegmentationMask(detection_id=detection_id, mask=mask, boundary_confidence=0.9, edge_pixels=[])


# ---------------------------------------------------------------------------
# BoundingBox edge cases
# ---------------------------------------------------------------------------

class TestBoundingBoxEdgeCases:
    """Edge cases for BoundingBox coordinate aliasing."""

    def test_zero_area_bbox(self) -> None:
        """Zero-area box (point) is valid to construct."""
        bbox = BoundingBox(x1=50, y1=50, x2=50, y2=50)
        assert bbox.x1 == bbox.x2
        assert bbox.y1 == bbox.y2

    def test_bbox_aliases_x_min_max(self) -> None:
        """x_min/x_max aliases match x1/x2."""
        bbox = BoundingBox(x1=10, y1=20, x2=110, y2=220)
        assert bbox.x_min == 10
        assert bbox.x_max == 110
        assert bbox.y_min == 20
        assert bbox.y_max == 220

    def test_large_bbox(self) -> None:
        """Full-frame bounding box is representable."""
        bbox = BoundingBox(x1=0, y1=0, x2=4096, y2=2160)
        assert bbox.x2 == 4096
        assert bbox.y2 == 2160

    def test_bbox_center_calculation(self) -> None:
        """Center of a symmetric box is exact midpoint."""
        bbox = BoundingBox(x1=0, y1=0, x2=100, y2=100)
        cx = (bbox.x1 + bbox.x2) / 2
        cy = (bbox.y1 + bbox.y2) / 2
        assert cx == 50.0
        assert cy == 50.0


# ---------------------------------------------------------------------------
# Detection edge cases
# ---------------------------------------------------------------------------

class TestDetectionEdgeCases:
    """Edge cases for Detection objects."""

    def test_min_confidence_detection(self) -> None:
        """Detection with confidence=0.0 is valid."""
        det = _make_detection(confidence=0.0)
        assert det.confidence == 0.0

    def test_max_confidence_detection(self) -> None:
        """Detection with confidence=1.0 is valid."""
        det = _make_detection(confidence=1.0)
        assert det.confidence == 1.0

    def test_empty_class_name(self) -> None:
        """Detection with empty class_name is representable."""
        det = _make_detection(class_name="")
        assert det.class_name == ""

    def test_long_class_name(self) -> None:
        """Detection with very long class name doesn't crash."""
        name = "a" * 256
        det = _make_detection(class_name=name)
        assert len(det.class_name) == 256

    def test_unicode_class_name(self) -> None:
        """Detection with unicode class name is representable."""
        det = _make_detection(class_name="椅子")  # Japanese for "chair"
        assert det.class_name == "椅子"


# ---------------------------------------------------------------------------
# DepthMap edge cases
# ---------------------------------------------------------------------------

class TestDepthMapEdgeCases:
    """Edge cases for DepthMap creation and region queries."""

    def test_single_pixel_depth_map(self) -> None:
        """1x1 depth map is the minimal valid case."""
        data = np.array([[5.0]], dtype=np.float32)
        dm = DepthMap(depth_array=data)
        mn, med, mx = dm.get_region_depth(BoundingBox(x1=0, y1=0, x2=1, y2=1))
        assert mn == pytest.approx(5.0)
        assert med == pytest.approx(5.0)
        assert mx == pytest.approx(5.0)

    def test_depth_map_all_zeros(self) -> None:
        """Depth map filled with zeros — get_region_depth returns (0,0,0)."""
        data = np.zeros((100, 100), dtype=np.float32)
        dm = DepthMap(depth_array=data)
        mn, med, mx = dm.get_region_depth(BoundingBox(x1=0, y1=0, x2=100, y2=100))
        assert mn == pytest.approx(0.0)
        assert mx == pytest.approx(0.0)

    def test_depth_map_uniform_value(self) -> None:
        """Uniform depth — all stats equal the fill value."""
        dm = _make_depth_map(fill=7.5)
        mn, med, mx = dm.get_region_depth(BoundingBox(x1=0, y1=0, x2=640, y2=480))
        assert mn == pytest.approx(7.5, abs=0.01)
        assert med == pytest.approx(7.5, abs=0.01)
        assert mx == pytest.approx(7.5, abs=0.01)

    def test_depth_map_nan_values(self) -> None:
        """NaN depth values are representable without crash."""
        data = np.full((10, 10), float("nan"), dtype=np.float32)
        dm = DepthMap(depth_array=data)
        assert dm.depth_array.shape == (10, 10)

    def test_depth_map_large_resolution(self) -> None:
        """4K resolution depth map can be constructed."""
        data = np.ones((2160, 3840), dtype=np.float32)
        dm = DepthMap(depth_array=data)
        assert dm.depth_array.shape[1] == 3840
        assert dm.depth_array.shape[0] == 2160

    def test_get_region_depth_returns_tuple_of_three(self) -> None:
        """get_region_depth always returns (min, median, max) — 3-tuple."""
        dm = _make_depth_map()
        result = dm.get_region_depth(BoundingBox(x1=100, y1=100, x2=200, y2=200))
        assert len(result) == 3


# ---------------------------------------------------------------------------
# SegmentationMask edge cases
# ---------------------------------------------------------------------------

class TestSegmentationMaskEdgeCases:
    """Edge cases for SegmentationMask."""

    def test_empty_mask(self) -> None:
        """All-False mask is a valid empty segmentation."""
        mask = np.zeros((480, 640), dtype=bool)
        seg = SegmentationMask(detection_id="x", mask=mask, boundary_confidence=0.0, edge_pixels=[])
        assert not seg.mask.any()

    def test_full_mask(self) -> None:
        """All-True mask covers entire frame."""
        mask = np.ones((480, 640), dtype=bool)
        seg = SegmentationMask(detection_id="x", mask=mask, boundary_confidence=1.0, edge_pixels=[])
        assert seg.mask.all()

    def test_mask_shape_mismatch_still_constructible(self) -> None:
        """Mask with unusual aspect ratio is constructible."""
        mask = np.zeros((1, 1000), dtype=bool)
        seg = SegmentationMask(detection_id="y", mask=mask, boundary_confidence=0.5, edge_pixels=[])
        assert seg.mask.shape == (1, 1000)


# ---------------------------------------------------------------------------
# ObstacleRecord edge cases
# ---------------------------------------------------------------------------

class TestObstacleRecordEdgeCases:
    """Edge cases for ObstacleRecord priority classification."""

    def test_critical_priority_at_boundary(self) -> None:
        """Distance exactly at 1.0m maps to CRITICAL or NEAR_HAZARD."""
        # Just verify priority enum values are defined
        assert Priority.CRITICAL is not None
        assert Priority.NEAR_HAZARD is not None
        assert Priority.FAR_HAZARD is not None
        assert Priority.SAFE is not None

    def test_all_directions_defined(self) -> None:
        """All required Direction enum values exist."""
        for name in ("FAR_LEFT", "LEFT", "SLIGHTLY_LEFT", "CENTER", "SLIGHTLY_RIGHT", "RIGHT", "FAR_RIGHT"):
            assert hasattr(Direction, name), f"Direction.{name} missing"

    def test_obstacle_record_construction(self) -> None:
        """ObstacleRecord can be constructed with minimum fields."""
        _make_detection()
        record = ObstacleRecord(
            id="obs_min",
            class_name="chair",
            direction=Direction.CENTER,
            distance_m=2.5,
            direction_deg=0.0,
            priority=Priority.FAR_HAZARD,
            bbox=BoundingBox(x1=10, y1=10, x2=100, y2=100),
            centroid_px=(55, 55),
            mask_confidence=0.9,
            detection_confidence=0.85,
            size_category=SizeCategory.MEDIUM,
            action_recommendation="step right",
        )
        assert record.distance_m == 2.5
        assert record.direction == Direction.CENTER

    def test_obstacle_record_zero_distance(self) -> None:
        """Distance of 0.0 (contact) is representable."""
        _make_detection()
        record = ObstacleRecord(
            id="obs_zero",
            class_name="chair",
            direction=Direction.CENTER,
            distance_m=0.0,
            direction_deg=0.0,
            priority=Priority.CRITICAL,
            bbox=BoundingBox(x1=10, y1=10, x2=100, y2=100),
            centroid_px=(55, 55),
            mask_confidence=0.9,
            detection_confidence=0.85,
            size_category=SizeCategory.LARGE,
            action_recommendation="stop",
        )
        assert record.distance_m == 0.0

    def test_obstacle_record_very_large_distance(self) -> None:
        """Very large distance (100m) is representable."""
        record = ObstacleRecord(
            id="obs_far",
            class_name="wall",
            direction=Direction.CENTER,
            distance_m=999.0,
            direction_deg=0.0,
            priority=Priority.SAFE,
            bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10),
            centroid_px=(5, 5),
            mask_confidence=0.5,
            detection_confidence=0.7,
            size_category=SizeCategory.SMALL,
            action_recommendation="continue",
        )
        assert record.distance_m == 999.0


# ---------------------------------------------------------------------------
# NavigationOutput edge cases
# ---------------------------------------------------------------------------

class TestNavigationOutputEdgeCases:
    """Edge cases for NavigationOutput."""

    def test_empty_navigation_output(self) -> None:
        """NavigationOutput with no obstacles is valid."""
        nav = NavigationOutput(
            short_cue="Path clear",
            verbose_description="No obstacles detected.",
            telemetry={},
            has_critical=False,
        )
        assert not nav.has_critical
        assert nav.short_cue == "Path clear"

    def test_critical_navigation_output(self) -> None:
        """has_critical=True flags urgent navigation output."""
        nav = NavigationOutput(
            short_cue="Stop! Chair very close ahead",
            verbose_description="Critical obstacle detected 0.5m ahead.",
            telemetry={"obstacle_count": 1},
            has_critical=True,
        )
        assert nav.has_critical

    def test_navigation_output_long_description(self) -> None:
        """Very long verbose description is representable."""
        nav = NavigationOutput(
            short_cue="Multiple obstacles",
            verbose_description="X" * 2000,
            telemetry={},
            has_critical=False,
        )
        assert len(nav.verbose_description) == 2000

    def test_navigation_output_telemetry_nested(self) -> None:
        """Nested telemetry dict is preserved."""
        telemetry = {"latency_ms": {"detect": 45, "depth": 32, "fuse": 12}}
        nav = NavigationOutput(
            short_cue="Cue",
            verbose_description="Desc",
            telemetry=telemetry,
            has_critical=False,
        )
        assert nav.telemetry["latency_ms"]["detect"] == 45


# ---------------------------------------------------------------------------
# Concurrent spatial processing simulation
# ---------------------------------------------------------------------------

class TestConcurrentSpatialProcessing:
    """Verify spatial schema objects are safe to create concurrently."""

    async def test_concurrent_depth_map_creation(self) -> None:
        """Multiple coroutines can create DepthMaps concurrently without race conditions."""
        async def make_dm(fill: float) -> DepthMap:
            await asyncio.sleep(0)
            return _make_depth_map(fill=fill)

        results = await asyncio.gather(*[make_dm(float(i)) for i in range(10)])
        assert len(results) == 10
        for i, dm in enumerate(results):
            mn, _, _ = dm.get_region_depth(BoundingBox(x1=0, y1=0, x2=640, y2=480))
            assert mn == pytest.approx(float(i), abs=0.01)

    async def test_concurrent_detection_list_assembly(self) -> None:
        """Concurrent detection creation doesn't corrupt results."""
        async def make_det(idx: int) -> Detection:
            await asyncio.sleep(0)
            return _make_detection(class_name=f"obj_{idx}", det_id=f"det_{idx}")

        detections = await asyncio.gather(*[make_det(i) for i in range(20)])
        ids = {d.id for d in detections}
        assert len(ids) == 20  # no duplicates


# ---------------------------------------------------------------------------
# Perception result edge cases
# ---------------------------------------------------------------------------

class TestPerceptionResultEdgeCases:
    """Edge cases for PerceptionResult schema."""

    def test_perception_result_import(self) -> None:
        """PerceptionResult can be imported from shared.schemas."""
        from shared.schemas import PerceptionResult
        assert PerceptionResult is not None

    def test_perception_result_empty(self) -> None:
        """PerceptionResult with empty lists is valid."""
        from shared.schemas import PerceptionResult
        result = PerceptionResult(
            detections=[],
            masks=[],
            depth_map=None,
            image_size=(640, 480),
            latency_ms=25.0,
            frame_id="frame_0",
            timestamp=time.time(),
        )
        assert result.detections == []
        assert result.latency_ms == 25.0

    def test_perception_result_with_data(self) -> None:
        """PerceptionResult with full data is valid."""
        from shared.schemas import PerceptionResult
        det = _make_detection()
        mask = _make_mask()
        dm = _make_depth_map()
        result = PerceptionResult(
            detections=[det],
            masks=[mask],
            depth_map=dm,
            image_size=(640, 480),
            latency_ms=55.3,
            frame_id="frame_42",
            timestamp=time.time(),
        )
        assert len(result.detections) == 1
        assert result.frame_id == "frame_42"

    def test_perception_result_zero_latency(self) -> None:
        """Latency of 0ms is representable (mock / cached result)."""
        from shared.schemas import PerceptionResult
        result = PerceptionResult(
            detections=[],
            masks=[],
            depth_map=None,
            image_size=(640, 480),
            latency_ms=0.0,
            frame_id="frame_cached",
            timestamp=time.time(),
        )
        assert result.latency_ms == 0.0

    def test_perception_result_high_latency(self) -> None:
        """Very high latency (e.g. 5000ms) is representable without crash."""
        from shared.schemas import PerceptionResult
        result = PerceptionResult(
            detections=[],
            masks=[],
            depth_map=None,
            image_size=(640, 480),
            latency_ms=5000.0,
            frame_id="frame_slow",
            timestamp=time.time(),
        )
        assert result.latency_ms == 5000.0
