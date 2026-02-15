"""
Tests for shared types module
==============================

Covers: BoundingBox, Detection, SegmentationMask, DepthMap,
PerceptionResult, ObstacleRecord, NavigationOutput, enums, ABCs.
"""

import math
import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.schemas import (
    BoundingBox,
    Detection,
    DepthMap,
    Direction,
    NavigationOutput,
    ObstacleRecord,
    PerceptionResult,
    Priority,
    SegmentationMask,
    SizeCategory,
    SpatialRelation,
    ObjectDetector,
    Segmenter,
    DepthEstimator,
)


# ============================================================================
# BoundingBox
# ============================================================================


class TestBoundingBox:
    def test_basic_attributes(self):
        bb = BoundingBox(10, 20, 110, 220)
        assert bb.x1 == 10
        assert bb.y1 == 20
        assert bb.x2 == 110
        assert bb.y2 == 220

    def test_backward_compat_aliases(self):
        bb = BoundingBox(5, 10, 100, 200)
        assert bb.x_min == 5
        assert bb.y_min == 10
        assert bb.x_max == 100
        assert bb.y_max == 200

    def test_width_height(self):
        bb = BoundingBox(10, 20, 60, 80)
        assert bb.width == 50
        assert bb.height == 60

    def test_zero_area_box(self):
        bb = BoundingBox(10, 10, 10, 10)
        assert bb.width == 0
        assert bb.height == 0
        assert bb.area == 0

    def test_center(self):
        bb = BoundingBox(0, 0, 100, 200)
        assert bb.center == (50, 100)

    def test_area(self):
        bb = BoundingBox(0, 0, 10, 20)
        assert bb.area == 200

    def test_to_list(self):
        bb = BoundingBox(1, 2, 3, 4)
        assert bb.to_list() == [1, 2, 3, 4]

    def test_to_xywh(self):
        bb = BoundingBox(100, 200, 250, 400)
        assert bb.to_xywh() == [100, 200, 150, 200]

    def test_from_xywh(self):
        bb = BoundingBox.from_xywh(100, 200, 150, 200)
        assert bb.x1 == 100
        assert bb.y1 == 200
        assert bb.x2 == 250
        assert bb.y2 == 400

    def test_from_xywh_roundtrip(self):
        original = BoundingBox(10, 20, 60, 80)
        xywh = original.to_xywh()
        restored = BoundingBox.from_xywh(*xywh)
        assert restored == original

    def test_clamp(self):
        bb = BoundingBox(-5, -10, 700, 500)
        clamped = bb.clamp(640, 480)
        assert clamped.x1 == 0
        assert clamped.y1 == 0
        assert clamped.x2 == 640
        assert clamped.y2 == 480

    def test_clamp_no_change(self):
        bb = BoundingBox(10, 10, 100, 100)
        clamped = bb.clamp(640, 480)
        assert clamped == bb


# ============================================================================
# Detection
# ============================================================================


class TestDetection:
    def test_creation(self):
        d = Detection(
            id="obj_1",
            class_name="chair",
            confidence=0.95,
            bbox=BoundingBox(10, 20, 110, 120),
        )
        assert d.id == "obj_1"
        assert d.class_name == "chair"
        assert d.confidence == 0.95

    def test_to_dict(self):
        d = Detection(
            id="obj_1",
            class_name="person",
            confidence=0.876,
            bbox=BoundingBox(100, 200, 250, 400),
        )
        result = d.to_dict()
        assert result["id"] == "obj_1"
        assert result["class"] == "person"
        assert result["confidence"] == 0.876
        # to_xywh format
        assert result["bbox"] == [100, 200, 150, 200]
        assert result["centroid_px"] == [175, 300]


# ============================================================================
# SegmentationMask
# ============================================================================


class TestSegmentationMask:
    def test_creation(self):
        mask = SegmentationMask(detection_id="obj_1")
        assert mask.detection_id == "obj_1"
        assert mask.mask is None
        assert mask.boundary_confidence == 0.5

    def test_to_dict_no_mask(self):
        mask = SegmentationMask(detection_id="obj_1")
        d = mask.to_dict()
        assert d["mask_area_px"] == 0

    def test_to_dict_with_mask(self):
        m = np.ones((10, 10), dtype=np.uint8)
        mask = SegmentationMask(detection_id="obj_1", mask=m, boundary_confidence=0.9)
        d = mask.to_dict()
        assert d["mask_area_px"] == 100
        assert d["boundary_confidence"] == 0.9


# ============================================================================
# DepthMap
# ============================================================================


class TestDepthMap:
    @pytest.fixture
    def sample_depth_map(self):
        arr = np.random.uniform(1.0, 5.0, (480, 640)).astype(np.float32)
        return DepthMap(depth_array=arr, min_depth=1.0, max_depth=5.0)

    def test_get_depth_at_valid(self, sample_depth_map):
        depth = sample_depth_map.get_depth_at(320, 240)
        assert 1.0 <= depth <= 5.0

    def test_get_depth_at_out_of_bounds(self, sample_depth_map):
        depth = sample_depth_map.get_depth_at(-1, -1)
        assert depth == float("inf")

    def test_get_depth_at_large_coords(self, sample_depth_map):
        depth = sample_depth_map.get_depth_at(9999, 9999)
        assert depth == float("inf")

    def test_get_region_depth_canonical_order(self, sample_depth_map):
        """Returns (min, median, max) — canonical order."""
        bbox = BoundingBox(100, 100, 200, 200)
        min_d, median_d, max_d = sample_depth_map.get_region_depth(bbox)
        assert min_d <= median_d <= max_d
        assert 1.0 <= min_d
        assert max_d <= 5.0

    def test_get_region_depth_none_array(self):
        dm = DepthMap(depth_array=None)
        result = dm.get_region_depth(BoundingBox(0, 0, 10, 10))
        assert all(math.isinf(v) for v in result)

    def test_get_region_depth_empty_region(self, sample_depth_map):
        bbox = BoundingBox(0, 0, 0, 0)  # zero-size
        result = sample_depth_map.get_region_depth(bbox)
        assert all(math.isinf(v) for v in result)

    def test_create_factory(self):
        arr = np.zeros((10, 10), dtype=np.float32)
        dm = DepthMap.create(depth_array=arr)
        assert dm.depth_array is arr

    def test_create_factory_data_alias(self):
        arr = np.zeros((10, 10), dtype=np.float32)
        dm = DepthMap.create(data=arr)
        assert dm.data is arr

    def test_data_property(self):
        arr = np.ones((5, 5), dtype=np.float32)
        dm = DepthMap(depth_array=arr)
        assert dm.data is arr
        new_arr = np.zeros((3, 3), dtype=np.float32)
        dm.data = new_arr
        assert dm.depth_array is new_arr


# ============================================================================
# Enums
# ============================================================================


class TestEnums:
    def test_priority_values(self):
        assert Priority.CRITICAL.value == "critical"
        assert Priority.NEAR_HAZARD.value == "near"
        assert Priority.FAR_HAZARD.value == "far"
        assert Priority.SAFE.value == "safe"

    def test_direction_values(self):
        assert Direction.CENTER.value == "ahead"
        assert Direction.LEFT.value == "left"
        assert Direction.RIGHT.value == "right"
        assert Direction.FAR_LEFT.value == "far left"
        assert Direction.FAR_RIGHT.value == "far right"

    def test_direction_all_members(self):
        assert len(Direction) == 7

    def test_size_category_values(self):
        assert SizeCategory.SMALL.value == "small"
        assert SizeCategory.MEDIUM.value == "medium"
        assert SizeCategory.LARGE.value == "large"

    def test_spatial_relation_values(self):
        assert SpatialRelation.LEFT_OF.value == "left of"
        assert SpatialRelation.BLOCKING.value == "blocking"


# ============================================================================
# ObstacleRecord
# ============================================================================


class TestObstacleRecord:
    @pytest.fixture
    def sample_obstacle(self):
        return ObstacleRecord(
            id="obs_1",
            class_name="chair",
            bbox=BoundingBox(100, 200, 250, 400),
            centroid_px=(175, 300),
            distance_m=2.5,
            direction=Direction.CENTER,
            direction_deg=0.0,
            mask_confidence=0.8,
            detection_confidence=0.95,
            priority=Priority.FAR_HAZARD,
            size_category=SizeCategory.MEDIUM,
            action_recommendation="Proceed cautiously",
        )

    def test_creation(self, sample_obstacle):
        assert sample_obstacle.class_name == "chair"
        assert sample_obstacle.detection_confidence == 0.95

    def test_backward_compat_detection_score(self, sample_obstacle):
        """detection_score property returns detection_confidence."""
        assert sample_obstacle.detection_score == 0.95

    def test_to_dict(self, sample_obstacle):
        d = sample_obstacle.to_dict()
        assert d["class"] == "chair"
        assert d["distance_m"] == 2.5
        assert d["direction"] == "ahead"
        assert d["priority"] == "far"
        assert d["confidence"] == 0.95
        assert d["size_category"] == "medium"
        # bbox in xywh format
        assert d["bbox"] == [100, 200, 150, 200]

    def test_to_dict_string_size_category(self):
        obs = ObstacleRecord(
            id="obs_2",
            class_name="table",
            bbox=BoundingBox(0, 0, 50, 50),
            centroid_px=(25, 25),
            distance_m=3.0,
            direction=Direction.LEFT,
            direction_deg=-20.0,
            mask_confidence=0.5,
            detection_confidence=0.8,
            priority=Priority.SAFE,
            size_category="custom_size",
            action_recommendation="No action",
        )
        d = obs.to_dict()
        assert d["size_category"] == "custom_size"


# ============================================================================
# NavigationOutput
# ============================================================================


class TestNavigationOutput:
    def test_creation_and_to_dict(self):
        nav = NavigationOutput(
            short_cue="Chair ahead 2 meters",
            verbose_description="A chair is located ahead at 2 meters distance.",
            telemetry=[{"id": "obs_1", "distance_m": 2.0}],
            has_critical=False,
        )
        d = nav.to_dict()
        assert d["short_cue"] == "Chair ahead 2 meters"
        assert d["has_critical"] is False
        assert len(d["telemetry"]) == 1


# ============================================================================
# PerceptionResult
# ============================================================================


class TestPerceptionResult:
    def test_creation(self):
        pr = PerceptionResult(
            detections=[],
            masks=[],
            depth_map=DepthMap(),
            image_size=(640, 480),
            latency_ms=50.5,
            timestamp="2025-01-01T00:00:00",
        )
        assert pr.image_size == (640, 480)
        assert pr.latency_ms == 50.5
        assert len(pr.detections) == 0


# ============================================================================
# ABCs
# ============================================================================


class TestABCs:
    def test_object_detector_is_abstract(self):
        with pytest.raises(TypeError):
            ObjectDetector()

    def test_segmenter_is_abstract(self):
        with pytest.raises(TypeError):
            Segmenter()

    def test_depth_estimator_is_abstract(self):
        with pytest.raises(TypeError):
            DepthEstimator()

    def test_detector_name_property(self):
        class DummyDetector(ObjectDetector):
            async def detect(self, image):
                return []
            def is_ready(self):
                return True
        d = DummyDetector()
        assert d.name == "DummyDetector"
        assert d.is_ready() is True
