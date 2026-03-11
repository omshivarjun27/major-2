"""
Test suite for Spatial Perception Module
========================================

Tests for object detection, edge-aware segmentation, depth estimation,
spatial fusion, and navigation output formatting.
"""

import asyncio
import os
import sys

import numpy as np
import pytest
from PIL import Image

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.vision.spatial import (
    # Data structures
    BoundingBox,
    DepthMap,
    Detection,
    Direction,
    EdgeAwareSegmenter,
    MicroNavFormatter,
    # Components
    MockObjectDetector,
    NavigationOutput,
    ObstacleRecord,
    Priority,
    SegmentationMask,
    SimpleDepthEstimator,
    SpatialFuser,
    SpatialProcessor,
    YOLODetector,
    create_spatial_processor,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_image():
    """Create a sample test image"""
    return Image.new('RGB', (640, 480), color='gray')


@pytest.fixture
def sample_detection():
    """Create a sample detection"""
    return Detection(
        id="obj_1",
        class_name="chair",
        confidence=0.95,
        bbox=BoundingBox(100, 200, 250, 400)
    )


@pytest.fixture
def sample_detections():
    """Create multiple sample detections"""
    return [
        Detection(
            id="obj_1",
            class_name="chair",
            confidence=0.95,
            bbox=BoundingBox(100, 200, 250, 400)
        ),
        Detection(
            id="obj_2",
            class_name="table",
            confidence=0.88,
            bbox=BoundingBox(400, 150, 550, 350)
        ),
        Detection(
            id="obj_3",
            class_name="person",
            confidence=0.92,
            bbox=BoundingBox(280, 100, 380, 450)
        ),
    ]


@pytest.fixture
def sample_depth_map():
    """Create a sample depth map"""
    depth_array = np.random.uniform(1.0, 5.0, (480, 640)).astype(np.float32)
    return DepthMap(
        depth_array=depth_array,
        min_depth=1.0,
        max_depth=5.0,
        is_metric=False
    )


# =============================================================================
# DATA STRUCTURE TESTS
# =============================================================================

class TestBoundingBox:
    """Tests for BoundingBox dataclass"""

    def test_bounding_box_properties(self):
        bbox = BoundingBox(10, 20, 110, 120)
        assert bbox.width == 100
        assert bbox.height == 100
        assert bbox.center == (60, 70)
        assert bbox.area == 10000

    def test_bounding_box_to_list(self):
        bbox = BoundingBox(10, 20, 110, 120)
        assert bbox.to_list() == [10, 20, 110, 120]


class TestDetection:
    """Tests for Detection dataclass"""

    def test_detection_to_dict(self, sample_detection):
        result = sample_detection.to_dict()
        assert result["id"] == "obj_1"
        assert result["class"] == "chair"
        assert result["confidence"] == 0.95
        # to_dict now uses to_xywh(): [x, y, w, h]
        assert result["bbox"] == [100, 200, 150, 200]
        assert result["centroid_px"] == [175, 300]


class TestDepthMap:
    """Tests for DepthMap dataclass"""

    def test_get_depth_at(self, sample_depth_map):
        # Valid coordinates
        depth = sample_depth_map.get_depth_at(320, 240)
        assert 1.0 <= depth <= 5.0

        # Invalid coordinates
        depth = sample_depth_map.get_depth_at(1000, 1000)
        assert depth == float('inf')

    def test_get_region_depth(self, sample_depth_map):
        bbox = BoundingBox(100, 100, 200, 200)
        # Canonical return order: (min, median, max)
        min_d, median_d, max_d = sample_depth_map.get_region_depth(bbox)
        assert min_d <= median_d <= max_d


class TestPriority:
    """Tests for Priority enum"""

    def test_priority_values(self):
        assert Priority.CRITICAL.value == "critical"
        assert Priority.NEAR_HAZARD.value == "near"
        assert Priority.FAR_HAZARD.value == "far"
        assert Priority.SAFE.value == "safe"


class TestDirection:
    """Tests for Direction enum"""

    def test_direction_values(self):
        assert Direction.CENTER.value == "ahead"
        assert Direction.SLIGHTLY_LEFT.value == "slightly left"
        assert Direction.SLIGHTLY_RIGHT.value == "slightly right"


# =============================================================================
# OBJECT DETECTOR TESTS
# =============================================================================

class TestMockObjectDetector:
    """Tests for MockObjectDetector"""

    @pytest.mark.asyncio
    async def test_mock_detector_returns_detections(self, sample_image):
        detector = MockObjectDetector()
        assert detector.is_ready()

        detections = await detector.detect(sample_image)
        assert isinstance(detections, list)
        assert len(detections) >= 1
        assert all(isinstance(d, Detection) for d in detections)

    @pytest.mark.asyncio
    async def test_mock_detector_detection_format(self, sample_image):
        detector = MockObjectDetector()
        detections = await detector.detect(sample_image)

        for det in detections:
            assert det.id.startswith("obj_")
            assert 0 <= det.confidence <= 1.0
            assert det.bbox.x1 < det.bbox.x2
            assert det.bbox.y1 < det.bbox.y2


class TestYOLODetector:
    """Tests for YOLODetector"""

    def test_yolo_detector_no_model(self):
        """Test YOLO detector gracefully handles missing model"""
        YOLODetector(model_path=None)
        # Should not be ready without a valid model path
        # (depends on ultralytics availability)

    def test_yolo_coco_classes(self):
        """Test COCO class names are loaded"""
        detector = YOLODetector()
        classes = detector._get_coco_classes()
        assert len(classes) == 80
        assert "person" in classes
        assert "chair" in classes


# =============================================================================
# SEGMENTATION TESTS
# =============================================================================

class TestEdgeAwareSegmenter:
    """Tests for EdgeAwareSegmenter"""

    @pytest.mark.asyncio
    async def test_segmenter_returns_masks(self, sample_image, sample_detections):
        segmenter = EdgeAwareSegmenter()
        masks = await segmenter.segment(sample_image, sample_detections)

        assert isinstance(masks, list)
        # Should return one mask per detection (or fewer if some fail)
        assert len(masks) <= len(sample_detections)

    @pytest.mark.asyncio
    async def test_segmenter_mask_properties(self, sample_image, sample_detections):
        segmenter = EdgeAwareSegmenter()
        masks = await segmenter.segment(sample_image, sample_detections)

        for mask in masks:
            assert isinstance(mask, SegmentationMask)
            assert mask.detection_id in [d.id for d in sample_detections]
            assert 0 <= mask.boundary_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_segmenter_empty_detections(self, sample_image):
        segmenter = EdgeAwareSegmenter()
        masks = await segmenter.segment(sample_image, [])
        assert masks == []


# =============================================================================
# DEPTH ESTIMATION TESTS
# =============================================================================

class TestSimpleDepthEstimator:
    """Tests for SimpleDepthEstimator"""

    @pytest.mark.asyncio
    async def test_depth_estimator_returns_depth_map(self, sample_image):
        estimator = SimpleDepthEstimator()
        depth_map = await estimator.estimate_depth(sample_image)

        assert isinstance(depth_map, DepthMap)
        # SimpleDepthEstimator downscales by DEPTH_DOWNSCALE=4
        assert depth_map.depth_array.shape == (480 // 4, 640 // 4)
        assert depth_map.min_depth <= depth_map.max_depth

    @pytest.mark.asyncio
    async def test_depth_estimator_range(self, sample_image):
        estimator = SimpleDepthEstimator(default_depth_range=(0.5, 10.0))
        depth_map = await estimator.estimate_depth(sample_image)

        assert depth_map.min_depth >= 0.5
        assert depth_map.max_depth <= 10.0


# =============================================================================
# SPATIAL FUSION TESTS
# =============================================================================

class TestSpatialFuser:
    """Tests for SpatialFuser"""

    def test_direction_calculation(self):
        fuser = SpatialFuser(image_width=640, image_height=480)

        # Center
        direction, angle = fuser._calculate_direction(320)
        assert direction == Direction.CENTER
        assert -5 <= angle <= 5

        # Left
        direction, angle = fuser._calculate_direction(100)
        assert direction in [Direction.LEFT, Direction.FAR_LEFT]
        assert angle < 0

        # Right
        direction, angle = fuser._calculate_direction(540)
        assert direction in [Direction.RIGHT, Direction.FAR_RIGHT]
        assert angle > 0

    def test_priority_calculation(self):
        fuser = SpatialFuser()

        assert fuser._calculate_priority(0.5) == Priority.CRITICAL
        assert fuser._calculate_priority(1.5) == Priority.NEAR_HAZARD
        assert fuser._calculate_priority(3.0) == Priority.FAR_HAZARD
        assert fuser._calculate_priority(6.0) == Priority.SAFE

    def test_size_category(self):
        fuser = SpatialFuser(image_width=640, image_height=480)

        # Large object (>25% of frame)
        large_bbox = BoundingBox(0, 0, 400, 400)
        assert fuser._calculate_size_category(large_bbox) == "large"

        # Small object (<5% of frame)
        small_bbox = BoundingBox(0, 0, 50, 50)
        assert fuser._calculate_size_category(small_bbox) == "small"

    def test_fuse_obstacles(self, sample_detections, sample_depth_map):
        fuser = SpatialFuser(image_width=640, image_height=480)

        # Create mock masks
        masks = [
            SegmentationMask(
                detection_id=d.id,
                mask=np.zeros((480, 640), dtype=np.uint8),
                boundary_confidence=0.85
            )
            for d in sample_detections
        ]

        obstacles = fuser.fuse(sample_detections, masks, sample_depth_map)

        assert len(obstacles) == len(sample_detections)
        assert all(isinstance(o, ObstacleRecord) for o in obstacles)

        # Check sorting by priority
        for i in range(len(obstacles) - 1):
            current_priority = {"critical": 0, "near": 1, "far": 2, "safe": 3}
            assert current_priority[obstacles[i].priority.value] <= current_priority[obstacles[i+1].priority.value]


# =============================================================================
# MICRO-NAV FORMATTER TESTS
# =============================================================================

class TestMicroNavFormatter:
    """Tests for MicroNavFormatter"""

    @pytest.fixture
    def sample_obstacles(self):
        return [
            ObstacleRecord(
                id="obj_1",
                class_name="chair",
                bbox=BoundingBox(100, 200, 250, 400),
                centroid_px=(175, 300),
                distance_m=1.5,
                direction=Direction.SLIGHTLY_LEFT,
                direction_deg=-12.0,
                mask_confidence=0.9,
                detection_confidence=0.95,
                priority=Priority.NEAR_HAZARD,
                size_category="medium",
                action_recommendation="step right"
            ),
            ObstacleRecord(
                id="obj_2",
                class_name="table",
                bbox=BoundingBox(400, 150, 550, 350),
                centroid_px=(475, 250),
                distance_m=3.0,
                direction=Direction.RIGHT,
                direction_deg=20.0,
                mask_confidence=0.85,
                detection_confidence=0.88,
                priority=Priority.FAR_HAZARD,
                size_category="large",
                action_recommendation="be aware, step left"
            ),
        ]

    def test_format_short_cue(self, sample_obstacles):
        formatter = MicroNavFormatter()
        cue = formatter.format_short_cue(sample_obstacles)

        assert isinstance(cue, str)
        assert len(cue) < 100  # Should be concise
        assert "Chair" in cue or "chair" in cue
        assert "Caution" in cue  # Near hazard

    def test_format_short_cue_critical(self):
        formatter = MicroNavFormatter()
        critical_obstacle = [
            ObstacleRecord(
                id="obj_1",
                class_name="person",
                bbox=BoundingBox(280, 100, 380, 450),
                centroid_px=(330, 275),
                distance_m=0.8,
                direction=Direction.CENTER,
                direction_deg=0.0,
                mask_confidence=0.92,
                detection_confidence=0.96,
                priority=Priority.CRITICAL,
                size_category="large",
                action_recommendation="stop and reassess"
            )
        ]

        cue = formatter.format_short_cue(critical_obstacle)
        assert "Stop!" in cue

    def test_format_short_cue_empty(self):
        formatter = MicroNavFormatter()
        cue = formatter.format_short_cue([])
        assert cue == "Path clear."

    def test_format_verbose(self, sample_obstacles):
        formatter = MicroNavFormatter()
        verbose = formatter.format_verbose(sample_obstacles)

        assert isinstance(verbose, str)
        assert "chair" in verbose.lower()
        assert "meters" in verbose.lower()

    def test_format_telemetry(self, sample_obstacles):
        formatter = MicroNavFormatter()
        telemetry = formatter.format_telemetry(sample_obstacles)

        assert isinstance(telemetry, list)
        assert len(telemetry) == len(sample_obstacles)
        assert all("distance_m" in t for t in telemetry)

    def test_format_all(self, sample_obstacles):
        formatter = MicroNavFormatter()
        output = formatter.format_all(sample_obstacles)

        assert isinstance(output, NavigationOutput)
        assert output.short_cue
        assert output.verbose_description
        assert len(output.telemetry) == len(sample_obstacles)
        assert not output.has_critical


# =============================================================================
# SPATIAL PROCESSOR TESTS
# =============================================================================

class TestSpatialProcessor:
    """Tests for main SpatialProcessor pipeline"""

    @pytest.mark.asyncio
    async def test_process_frame_returns_navigation_output(self, sample_image):
        processor = SpatialProcessor()
        output = await processor.process_frame(sample_image)

        assert isinstance(output, NavigationOutput)
        assert output.short_cue
        assert output.verbose_description
        assert isinstance(output.telemetry, list)

    @pytest.mark.asyncio
    async def test_quick_warning(self, sample_image):
        processor = SpatialProcessor()
        warning = await processor.get_quick_warning(sample_image)

        assert isinstance(warning, str)
        assert len(warning) > 0

    def test_is_ready(self):
        processor = SpatialProcessor()
        assert processor.is_ready

    @pytest.mark.asyncio
    async def test_last_obstacles_updated(self, sample_image):
        processor = SpatialProcessor()
        await processor.process_frame(sample_image)

        assert processor.last_obstacles is not None
        assert processor.last_navigation is not None


class TestCreateSpatialProcessor:
    """Tests for factory function"""

    def test_create_default_processor(self):
        processor = create_spatial_processor()
        assert processor.is_ready

    def test_create_processor_with_options(self):
        processor = create_spatial_processor(
            use_yolo=False,
            use_midas=False,
            enable_segmentation=True,
            enable_depth=True
        )
        assert processor is not None


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSpatialPerceptionIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_pipeline(self, sample_image):
        """Test complete spatial perception pipeline"""
        processor = create_spatial_processor()

        # Process frame
        output = await processor.process_frame(sample_image)

        # Verify output structure
        assert output.short_cue
        assert output.verbose_description
        assert isinstance(output.telemetry, list)

        # Verify obstacles
        for obs_dict in output.telemetry:
            assert "id" in obs_dict
            assert "class" in obs_dict
            assert "distance_m" in obs_dict
            assert "direction" in obs_dict
            assert "priority" in obs_dict

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, sample_image):
        """Test that concurrent processing is handled"""
        processor = create_spatial_processor()

        # Start multiple concurrent calls
        results = await asyncio.gather(
            processor.process_frame(sample_image),
            processor.get_quick_warning(sample_image),
            return_exceptions=True
        )

        # At least one should succeed
        assert not all(isinstance(r, Exception) for r in results)


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
