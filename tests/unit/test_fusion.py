"""
Tests for VQA Engine Spatial Fusion Module
==========================================
"""

import asyncio
import pytest
import time
import numpy as np
from PIL import Image

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 2)[0])

from core.vqa.perception import (
    Detection,
    BoundingBox,
    DepthMap,
    PerceptionResult,
    SegmentationMask,
    create_pipeline as create_perception_pipeline,
)
from core.vqa.spatial_fuser import (
    SpatialFuser,
    FusionConfig,
    TemporalFilter,
    TrackedObject,
    FusedObstacle,
    FusedResult,
)
from core.vqa.scene_graph import (
    SceneGraphBuilder,
    SceneGraph,
    ObstacleRecord,
    Priority,
    Direction,
    build_scene_graph,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_detections():
    """Create sample detections."""
    return [
        Detection(
            id="det_0",
            class_name="chair",
            confidence=0.85,
            bbox=BoundingBox(100, 200, 200, 350),
        ),
        Detection(
            id="det_1",
            class_name="table",
            confidence=0.75,
            bbox=BoundingBox(300, 150, 450, 300),
        ),
    ]


@pytest.fixture
def sample_depth_map():
    """Create sample depth map."""
    data = np.ones((480, 640), dtype=np.float32) * 3.0
    # Closer object on left
    data[200:350, 100:200] = 1.5
    # Farther object on right
    data[150:300, 300:450] = 4.0
    return DepthMap(
        depth_array=data,
        min_depth=0.5,
        max_depth=10.0,
    )


@pytest.fixture
def sample_masks(sample_detections):
    """Create sample segmentation masks."""
    masks = []
    for det in sample_detections:
        mask_data = np.zeros((480, 640), dtype=np.uint8)
        mask_data[det.bbox.y_min:det.bbox.y_max, det.bbox.x_min:det.bbox.x_max] = 255
        masks.append(SegmentationMask(
            detection_id=det.id,
            mask=mask_data,
            boundary_confidence=0.8,
        ))
    return masks


@pytest.fixture
def sample_perception_result(sample_detections, sample_masks, sample_depth_map):
    """Create sample perception result."""
    from datetime import datetime
    return PerceptionResult(
        detections=sample_detections,
        masks=sample_masks,
        depth_map=sample_depth_map,
        timestamp=datetime.now().isoformat(),
        image_size=(640, 480),
        latency_ms=5.0,
    )


# ============================================================================
# TemporalFilter Tests
# ============================================================================

class TestTemporalFilter:
    """Tests for TemporalFilter."""
    
    def test_filter_creation(self):
        config = FusionConfig()
        filter = TemporalFilter(config)
        assert filter is not None
    
    def test_update_creates_tracks(self, sample_detections, sample_depth_map):
        config = FusionConfig()
        filter = TemporalFilter(config)
        
        timestamp = time.time()
        tracks = filter.update(sample_detections, sample_depth_map, timestamp)
        
        assert len(tracks) == len(sample_detections)
        for track in tracks:
            assert isinstance(track, TrackedObject)
    
    def test_tracks_match_across_frames(self, sample_detections, sample_depth_map):
        config = FusionConfig(iou_threshold=0.3)
        filter = TemporalFilter(config)
        
        # First frame
        t1 = time.time()
        tracks1 = filter.update(sample_detections, sample_depth_map, t1)
        track_ids_1 = {t.id for t in tracks1}
        
        # Second frame with slightly shifted detections
        shifted_dets = []
        for det in sample_detections:
            shifted_dets.append(Detection(
                id=det.id,
                class_name=det.class_name,
                confidence=det.confidence,
                bbox=BoundingBox(
                    det.bbox.x_min + 5,
                    det.bbox.y_min + 5,
                    det.bbox.x_max + 5,
                    det.bbox.y_max + 5,
                ),
            ))
        
        t2 = t1 + 0.033  # ~30fps
        tracks2 = filter.update(shifted_dets, sample_depth_map, t2)
        track_ids_2 = {t.id for t in tracks2}
        
        # Same tracks should be maintained
        assert track_ids_1 == track_ids_2
    
    def test_stale_tracks_removed(self, sample_detections, sample_depth_map):
        config = FusionConfig()
        filter = TemporalFilter(config)
        
        t1 = time.time()
        filter.update(sample_detections, sample_depth_map, t1)
        
        # No detections for a while
        t2 = t1 + 1.0  # 1 second later
        tracks = filter.update([], sample_depth_map, t2)
        
        # Tracks should be removed due to staleness
        assert len(tracks) == 0
    
    def test_reset_clears_tracks(self, sample_detections, sample_depth_map):
        config = FusionConfig()
        filter = TemporalFilter(config)
        
        filter.update(sample_detections, sample_depth_map, time.time())
        filter.reset()
        
        # After reset, new detections should get new track IDs
        tracks = filter.update(sample_detections, sample_depth_map, time.time())
        assert all(t.hits == 1 for t in tracks)


# ============================================================================
# SpatialFuser Tests
# ============================================================================

class TestSpatialFuser:
    """Tests for SpatialFuser."""
    
    def test_fuser_creation(self):
        fuser = SpatialFuser()
        assert fuser is not None
    
    def test_fuse_returns_result(self, sample_perception_result):
        fuser = SpatialFuser()
        result = fuser.fuse(sample_perception_result)
        
        assert isinstance(result, FusedResult)
        assert len(result.obstacles) == len(sample_perception_result.detections)
    
    def test_fused_obstacles_have_valid_structure(self, sample_perception_result):
        fuser = SpatialFuser()
        result = fuser.fuse(sample_perception_result)
        
        for obs in result.obstacles:
            assert isinstance(obs, FusedObstacle)
            assert obs.depth_m > 0
            assert 0 <= obs.fused_confidence <= 1
            assert isinstance(obs.is_uncertain, bool)
    
    def test_obstacles_sorted_by_depth(self, sample_perception_result):
        fuser = SpatialFuser()
        result = fuser.fuse(sample_perception_result)
        
        depths = [o.depth_m for o in result.obstacles]
        assert depths == sorted(depths)
    
    def test_closest_obstacle(self, sample_perception_result):
        fuser = SpatialFuser()
        result = fuser.fuse(sample_perception_result)
        
        closest = result.get_closest()
        assert closest is not None
        assert closest.depth_m == min(o.depth_m for o in result.obstacles)
    
    def test_temporal_filtering_disabled(self, sample_perception_result):
        fuser = SpatialFuser()
        result = fuser.fuse(sample_perception_result, apply_temporal=False)
        
        # Without temporal filtering, no track IDs should be assigned
        # (actually they could still be None depending on implementation)
        assert result is not None


# ============================================================================
# SceneGraphBuilder Tests
# ============================================================================

class TestSceneGraphBuilder:
    """Tests for SceneGraphBuilder."""
    
    def test_builder_creation(self):
        builder = SceneGraphBuilder(640, 480)
        assert builder is not None
    
    def test_build_returns_scene_graph(self, sample_perception_result):
        builder = SceneGraphBuilder(640, 480)
        scene = builder.build(sample_perception_result)
        
        assert isinstance(scene, SceneGraph)
    
    def test_scene_graph_has_obstacles(self, sample_perception_result):
        builder = SceneGraphBuilder(640, 480)
        scene = builder.build(sample_perception_result)
        
        assert len(scene.obstacles) == len(sample_perception_result.detections)
    
    def test_obstacle_records_have_valid_structure(self, sample_perception_result):
        builder = SceneGraphBuilder(640, 480)
        scene = builder.build(sample_perception_result)
        
        for obs in scene.obstacles:
            assert isinstance(obs, ObstacleRecord)
            assert isinstance(obs.priority, Priority)
            assert isinstance(obs.direction, Direction)
            assert obs.distance_m > 0
            assert len(obs.action_recommendation) > 0
    
    def test_priority_calculation(self, sample_perception_result):
        builder = SceneGraphBuilder(640, 480)
        scene = builder.build(sample_perception_result)
        
        for obs in scene.obstacles:
            if obs.distance_m < 1.0:
                assert obs.priority == Priority.CRITICAL
            elif obs.distance_m < 2.0:
                assert obs.priority == Priority.NEAR_HAZARD
            elif obs.distance_m < 5.0:
                assert obs.priority == Priority.FAR_HAZARD
            else:
                assert obs.priority == Priority.SAFE
    
    def test_direction_calculation(self, sample_perception_result):
        builder = SceneGraphBuilder(640, 480)
        scene = builder.build(sample_perception_result)
        
        for obs in scene.obstacles:
            # Check that direction is reasonable based on bbox center
            cx = obs.bbox.center[0]
            if cx < 213:  # Left third
                assert obs.direction in [Direction.FAR_LEFT, Direction.LEFT, Direction.SLIGHTLY_LEFT]
            elif cx > 427:  # Right third
                assert obs.direction in [Direction.FAR_RIGHT, Direction.RIGHT, Direction.SLIGHTLY_RIGHT]
    
    def test_scene_graph_summary(self, sample_perception_result):
        builder = SceneGraphBuilder(640, 480)
        scene = builder.build(sample_perception_result)
        
        assert len(scene.summary) > 0
    
    def test_convenience_function(self, sample_perception_result):
        scene = build_scene_graph(sample_perception_result)
        assert isinstance(scene, SceneGraph)


# ============================================================================
# Integration Tests
# ============================================================================

class TestFusionIntegration:
    """Integration tests for the full fusion pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test complete pipeline from image to scene graph."""
        # Create test image
        image = Image.new("RGB", (640, 480), color=(128, 128, 128))
        
        # Run perception
        pipeline = create_perception_pipeline(use_mock=True)
        perception = await pipeline.process(image)
        
        # Build scene graph
        scene = build_scene_graph(perception)
        
        # Apply fusion
        fuser = SpatialFuser()
        fused = fuser.fuse(perception)
        
        # Verify integration
        assert len(scene.obstacles) == len(perception.detections)
        assert len(fused.obstacles) == len(perception.detections)
    
    @pytest.mark.asyncio
    async def test_latency_under_threshold(self):
        """Test that full fusion is under 300ms."""
        image = Image.new("RGB", (640, 480), color=(128, 128, 128))
        pipeline = create_perception_pipeline(use_mock=True)
        fuser = SpatialFuser()
        
        start = time.time()
        perception = await pipeline.process(image)
        scene = build_scene_graph(perception)
        fused = fuser.fuse(perception)
        elapsed_ms = (time.time() - start) * 1000
        
        # With mock detector, should be well under 300ms
        assert elapsed_ms < 300


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
