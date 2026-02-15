"""
Tests for PerceptionOrchestrator
=================================

Covers: concurrent execution, per-stage timeouts, fallback depth,
telemetry counters, never-raise guarantee.
"""

import asyncio
import sys
import os
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.schemas import BoundingBox, DepthMap, Detection, SegmentationMask
from core.vqa.orchestrator import (
    OrchestratorConfig,
    PerceptionOrchestrator,
    _get_image_size,
)


# ============================================================================
# Mock pipeline stages
# ============================================================================


class MockDetector:
    """Detector returning canned results after optional delay."""

    def __init__(self, detections=None, delay_s=0.0, should_raise=False):
        self._detections = detections or []
        self._delay = delay_s
        self._should_raise = should_raise

    async def detect(self, image):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._should_raise:
            raise RuntimeError("Detector error")
        return self._detections

    def is_ready(self):
        return True


class MockSegmenter:
    """Segmenter returning canned masks after optional delay."""

    def __init__(self, masks=None, delay_s=0.0, should_raise=False):
        self._masks = masks or []
        self._delay = delay_s
        self._should_raise = should_raise

    async def segment(self, image, detections):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._should_raise:
            raise RuntimeError("Segmenter error")
        return self._masks


class MockDepthEstimator:
    """Depth estimator returning canned DepthMap after optional delay."""

    def __init__(self, depth_map=None, delay_s=0.0, should_raise=False):
        self._depth_map = depth_map
        self._delay = delay_s
        self._should_raise = should_raise

    async def estimate(self, image):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._should_raise:
            raise RuntimeError("Depth error")
        return self._depth_map


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_image():
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_detections():
    return [
        Detection(
            id="obj_1",
            class_name="chair",
            confidence=0.9,
            bbox=BoundingBox(100, 100, 200, 200),
        )
    ]


@pytest.fixture
def sample_depth_map():
    arr = np.full((480, 640), 3.0, dtype=np.float32)
    return DepthMap(depth_array=arr, min_depth=3.0, max_depth=3.0, is_metric=True)


@pytest.fixture
def sample_masks():
    return [
        SegmentationMask(detection_id="obj_1", boundary_confidence=0.8)
    ]


# ============================================================================
# Config tests
# ============================================================================


class TestOrchestratorConfig:
    def test_defaults(self):
        cfg = OrchestratorConfig()
        assert cfg.detection_timeout_ms == 100.0
        assert cfg.segmentation_timeout_ms == 100.0
        assert cfg.depth_timeout_ms == 100.0
        assert cfg.pipeline_timeout_ms == 300.0
        assert cfg.fast_path_budget_ms == 50.0
        assert cfg.retry_on_timeout is False

    def test_custom_values(self):
        cfg = OrchestratorConfig(
            detection_timeout_ms=200,
            pipeline_timeout_ms=500,
        )
        assert cfg.detection_timeout_ms == 200
        assert cfg.pipeline_timeout_ms == 500


# ============================================================================
# Orchestrator tests
# ============================================================================


class TestPerceptionOrchestrator:
    @pytest.mark.asyncio
    async def test_basic_run(self, sample_image, sample_detections, sample_depth_map, sample_masks):
        """All stages complete normally."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(detections=sample_detections),
            segmenter=MockSegmenter(masks=sample_masks),
            depth_estimator=MockDepthEstimator(depth_map=sample_depth_map),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        result = await orch.run(sample_image)
        assert len(result.detections) == 1
        assert result.detections[0].class_name == "chair"
        assert len(result.masks) == 1
        assert result.depth_map.depth_array is not None
        assert result.image_size == (640, 480)
        assert result.latency_ms >= 0
        assert orch.total_runs == 1

    @pytest.mark.asyncio
    async def test_detector_only(self, sample_image, sample_detections):
        """Run without segmenter or depth estimator."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(detections=sample_detections),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        result = await orch.run(sample_image)
        assert len(result.detections) == 1
        assert len(result.masks) == 0
        # Fallback depth map should be created
        assert result.depth_map is not None
        assert result.depth_map.depth_array is not None

    @pytest.mark.asyncio
    async def test_detector_timeout(self, sample_image):
        """Detector exceeds timeout — returns empty detections."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(delay_s=1.0),
            config=OrchestratorConfig(
                detection_timeout_ms=10,
                pipeline_timeout_ms=5000,
            ),
        )
        result = await orch.run(sample_image)
        assert len(result.detections) == 0
        assert orch.timeout_count >= 1

    @pytest.mark.asyncio
    async def test_detector_error(self, sample_image):
        """Detector raises — returns empty detections, no crash."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(should_raise=True),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        result = await orch.run(sample_image)
        assert len(result.detections) == 0
        assert result.depth_map is not None

    @pytest.mark.asyncio
    async def test_segmenter_error(self, sample_image, sample_detections):
        """Segmenter raises — masks are empty, rest still works."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(detections=sample_detections),
            segmenter=MockSegmenter(should_raise=True),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        result = await orch.run(sample_image)
        assert len(result.detections) == 1
        assert len(result.masks) == 0

    @pytest.mark.asyncio
    async def test_depth_error(self, sample_image, sample_detections):
        """Depth estimator raises — fallback depth map is used."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(detections=sample_detections),
            depth_estimator=MockDepthEstimator(should_raise=True),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        result = await orch.run(sample_image)
        assert result.depth_map is not None
        assert result.depth_map.depth_array is not None

    @pytest.mark.asyncio
    async def test_global_pipeline_timeout(self, sample_image):
        """Global timeout triggers when all stages are slow."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(delay_s=2.0),
            segmenter=MockSegmenter(delay_s=2.0),
            depth_estimator=MockDepthEstimator(delay_s=2.0),
            config=OrchestratorConfig(
                detection_timeout_ms=5000,
                segmentation_timeout_ms=5000,
                depth_timeout_ms=5000,
                pipeline_timeout_ms=50,
            ),
        )
        result = await orch.run(sample_image)
        # Should complete (not hang) with empty/fallback results
        assert result is not None
        assert orch.timeout_count >= 1

    @pytest.mark.asyncio
    async def test_never_raises(self, sample_image):
        """Orchestrator should NEVER raise, regardless of inputs."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(should_raise=True),
            segmenter=MockSegmenter(should_raise=True),
            depth_estimator=MockDepthEstimator(should_raise=True),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        result = await orch.run(sample_image)
        assert result is not None
        assert isinstance(result.detections, list)
        assert isinstance(result.masks, list)

    @pytest.mark.asyncio
    async def test_concurrent_execution(self, sample_image, sample_detections, sample_depth_map):
        """Detection and depth run concurrently, not sequentially."""
        delay = 0.1
        orch = PerceptionOrchestrator(
            detector=MockDetector(detections=sample_detections, delay_s=delay),
            depth_estimator=MockDepthEstimator(depth_map=sample_depth_map, delay_s=delay),
            config=OrchestratorConfig(
                detection_timeout_ms=2000,
                depth_timeout_ms=2000,
                pipeline_timeout_ms=5000,
            ),
        )
        start = time.time()
        result = await orch.run(sample_image)
        elapsed = time.time() - start
        # If sequential, would take ~2*delay. Concurrent should be ~delay.
        assert elapsed < delay * 1.8, f"Took {elapsed:.3f}s — not concurrent"
        assert len(result.detections) == 1
        assert result.depth_map is sample_depth_map

    @pytest.mark.asyncio
    async def test_get_stats(self, sample_image):
        orch = PerceptionOrchestrator(
            detector=MockDetector(),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        await orch.run(sample_image)
        await orch.run(sample_image)
        stats = orch.get_stats()
        assert stats["total_runs"] == 2
        assert "timeout_count" in stats
        assert "fallback_count" in stats

    @pytest.mark.asyncio
    async def test_segmentation_waits_for_detection(self, sample_image, sample_detections, sample_masks):
        """Segmentation should wait for detection to finish (Event dependency)."""
        orch = PerceptionOrchestrator(
            detector=MockDetector(detections=sample_detections, delay_s=0.05),
            segmenter=MockSegmenter(masks=sample_masks),
            config=OrchestratorConfig(pipeline_timeout_ms=5000),
        )
        result = await orch.run(sample_image)
        # Segmenter got access to detections because it waited
        assert len(result.masks) == 1


# ============================================================================
# Helper tests
# ============================================================================


class TestGetImageSize:
    def test_numpy_image(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        assert _get_image_size(img) == (640, 480)

    def test_pil_like_image(self):
        class FakeImage:
            size = (1920, 1080)
        assert _get_image_size(FakeImage()) == (1920, 1080)

    def test_unknown_type(self):
        assert _get_image_size("not_an_image") == (640, 480)
