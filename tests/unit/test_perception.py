"""
Tests for VQA Engine Perception Module
======================================
"""

import asyncio
import pytest
import numpy as np
from PIL import Image

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 2)[0])

from core.vqa.perception import (
    MockObjectDetector,
    EdgeAwareSegmenter,
    SimpleDepthEstimator,
    PerceptionPipeline,
    Detection,
    BoundingBox,
    create_pipeline as create_perception_pipeline,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_image():
    """Create a sample test image."""
    img = Image.new("RGB", (640, 480), color=(128, 128, 128))
    # Add some variation
    pixels = img.load()
    for x in range(100, 200):
        for y in range(100, 200):
            pixels[x, y] = (255, 0, 0)  # Red square
    return img


@pytest.fixture
def sample_numpy_image():
    """Create a sample numpy array image."""
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


# ============================================================================
# BoundingBox Tests
# ============================================================================

class TestBoundingBox:
    """Tests for BoundingBox class."""
    
    def test_creation(self):
        bbox = BoundingBox(10, 20, 100, 150)
        assert bbox.x_min == 10
        assert bbox.y_min == 20
        assert bbox.x_max == 100
        assert bbox.y_max == 150
    
    def test_width_height(self):
        bbox = BoundingBox(0, 0, 100, 80)
        assert bbox.width == 100
        assert bbox.height == 80
    
    def test_area(self):
        bbox = BoundingBox(0, 0, 100, 50)
        assert bbox.area == 5000
    
    def test_center(self):
        bbox = BoundingBox(0, 0, 100, 100)
        assert bbox.center == (50, 50)
    
    def test_to_xywh(self):
        bbox = BoundingBox(10, 20, 110, 120)
        xywh = bbox.to_xywh()
        assert xywh == [10, 20, 100, 100]
    
    def test_from_xywh(self):
        bbox = BoundingBox.from_xywh(10, 20, 100, 100)
        assert bbox.x_min == 10
        assert bbox.y_min == 20
        assert bbox.x_max == 110
        assert bbox.y_max == 120
    
    def test_clamp(self):
        bbox = BoundingBox(-10, -10, 700, 500)
        clamped = bbox.clamp(640, 480)
        assert clamped.x_min == 0
        assert clamped.y_min == 0
        assert clamped.x_max == 640
        assert clamped.y_max == 480


# ============================================================================
# MockObjectDetector Tests
# ============================================================================

class TestMockObjectDetector:
    """Tests for MockObjectDetector."""
    
    @pytest.mark.asyncio
    async def test_detection_returns_list(self, sample_image):
        detector = MockObjectDetector()
        detections = await detector.detect(sample_image)
        assert isinstance(detections, list)
    
    @pytest.mark.asyncio
    async def test_detection_has_valid_structure(self, sample_image):
        detector = MockObjectDetector()
        detections = await detector.detect(sample_image)
        
        for det in detections:
            assert isinstance(det, Detection)
            assert det.id.startswith("obj_")
            assert isinstance(det.class_name, str)
            assert 0.0 <= det.confidence <= 1.0
            assert isinstance(det.bbox, BoundingBox)
    
    @pytest.mark.asyncio
    async def test_detection_respects_max_detections(self, sample_image):
        detector = MockObjectDetector()
        detections = await detector.detect(sample_image, max_detections=2)
        assert len(detections) <= 2
    
    @pytest.mark.asyncio
    async def test_detection_within_image_bounds(self, sample_image):
        detector = MockObjectDetector()
        detections = await detector.detect(sample_image)
        
        w, h = sample_image.size
        for det in detections:
            assert det.bbox.x_min >= 0
            assert det.bbox.y_min >= 0
            assert det.bbox.x_max <= w
            assert det.bbox.y_max <= h
    
    @pytest.mark.asyncio
    async def test_detection_latency_under_threshold(self, sample_image):
        import time
        detector = MockObjectDetector()
        
        start = time.time()
        await detector.detect(sample_image)
        elapsed_ms = (time.time() - start) * 1000
        
        # Mock detector should be <50ms
        assert elapsed_ms < 50


# ============================================================================
# EdgeAwareSegmenter Tests
# ============================================================================

class TestEdgeAwareSegmenter:
    """Tests for EdgeAwareSegmenter."""
    
    @pytest.fixture
    def sample_detections(self):
        return [
            Detection(
                id="det_0",
                class_name="chair",
                confidence=0.8,
                bbox=BoundingBox(100, 100, 200, 200),
            ),
        ]
    
    @pytest.mark.asyncio
    async def test_segmentation_returns_masks(self, sample_image, sample_detections):
        segmenter = EdgeAwareSegmenter()
        masks = await segmenter.segment(sample_image, sample_detections)
        
        assert isinstance(masks, list)
        assert len(masks) == len(sample_detections)
    
    @pytest.mark.asyncio
    async def test_mask_has_valid_structure(self, sample_image, sample_detections):
        segmenter = EdgeAwareSegmenter()
        masks = await segmenter.segment(sample_image, sample_detections)
        
        for mask in masks:
            assert mask.detection_id == sample_detections[0].id
            assert isinstance(mask.mask, np.ndarray)
            assert mask.mask.dtype == np.uint8
            assert 0.0 <= mask.boundary_confidence <= 1.0


# ============================================================================
# SimpleDepthEstimator Tests
# ============================================================================

class TestSimpleDepthEstimator:
    """Tests for SimpleDepthEstimator."""
    
    @pytest.mark.asyncio
    async def test_depth_estimation_returns_depth_map(self, sample_image):
        estimator = SimpleDepthEstimator()
        depth_map = await estimator.estimate(sample_image)
        
        assert depth_map is not None
        assert isinstance(depth_map.data, np.ndarray)
    
    @pytest.mark.asyncio
    async def test_depth_values_in_valid_range(self, sample_image):
        estimator = SimpleDepthEstimator()
        depth_map = await estimator.estimate(sample_image)
        
        # Depth should be between 0.5 and 10m
        assert depth_map.data.min() >= 0.5
        assert depth_map.data.max() <= 10.0
    
    @pytest.mark.asyncio
    async def test_get_region_depth(self, sample_image):
        estimator = SimpleDepthEstimator()
        depth_map = await estimator.estimate(sample_image)
        
        bbox = BoundingBox(100, 100, 200, 200)
        min_d, median_d, var_d = depth_map.get_region_depth(bbox)
        
        assert min_d > 0
        assert median_d >= min_d
        assert var_d >= 0


# ============================================================================
# PerceptionPipeline Tests
# ============================================================================

class TestPerceptionPipeline:
    """Tests for complete PerceptionPipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_returns_result(self, sample_image):
        pipeline = create_perception_pipeline(use_mock=True)
        result = await pipeline.process(sample_image)
        
        assert result is not None
        assert isinstance(result.detections, list)
        assert isinstance(result.masks, list)
        assert result.depth_map is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_includes_timestamp(self, sample_image):
        pipeline = create_perception_pipeline(use_mock=True)
        result = await pipeline.process(sample_image)
        
        assert result.timestamp is not None
        assert len(result.timestamp) > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_image_size(self, sample_image):
        pipeline = create_perception_pipeline(use_mock=True)
        result = await pipeline.process(sample_image)
        
        assert result.image_size == sample_image.size
    
    @pytest.mark.asyncio
    async def test_pipeline_latency_under_threshold(self, sample_image):
        import time
        pipeline = create_perception_pipeline(use_mock=True)
        
        start = time.time()
        await pipeline.process(sample_image)
        elapsed_ms = (time.time() - start) * 1000
        
        # Full pipeline with mock should be <100ms
        assert elapsed_ms < 100
    
    @pytest.mark.asyncio
    async def test_pipeline_handles_numpy_input(self, sample_numpy_image):
        pipeline = create_perception_pipeline(use_mock=True)
        result = await pipeline.process(sample_numpy_image)
        
        assert result is not None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
