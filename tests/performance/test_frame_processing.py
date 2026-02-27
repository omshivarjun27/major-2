"""P4: Frame Processing Optimization Tests (T-083).

Tests for frame processing pipeline optimization including parallel execution,
image preprocessing, and frame skipping under load.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Frame Processing Models
# ---------------------------------------------------------------------------

@dataclass
class FrameProcessingMetrics:
    """Metrics for frame processing pipeline."""
    preprocess_ms: float = 0.0
    detection_ms: float = 0.0
    segmentation_ms: float = 0.0
    depth_ms: float = 0.0
    fusion_ms: float = 0.0
    total_ms: float = 0.0
    
    @property
    def within_budget(self) -> bool:
        """Check if within 300ms vision budget."""
        return self.total_ms < 300.0
    
    @property
    def parallel_stages_ms(self) -> float:
        """Time for stages that can run in parallel (detection + depth)."""
        return max(self.detection_ms, self.depth_ms)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "preprocess_ms": round(self.preprocess_ms, 2),
            "detection_ms": round(self.detection_ms, 2),
            "segmentation_ms": round(self.segmentation_ms, 2),
            "depth_ms": round(self.depth_ms, 2),
            "fusion_ms": round(self.fusion_ms, 2),
            "total_ms": round(self.total_ms, 2),
            "within_budget": self.within_budget,
        }


@dataclass
class FrameSkipStats:
    """Statistics for frame skipping."""
    total_frames: int = 0
    processed_frames: int = 0
    skipped_frames: int = 0
    avg_latency_ms: float = 0.0
    
    @property
    def skip_rate(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return self.skipped_frames / self.total_frames
    
    @property
    def within_acceptable_skip_rate(self) -> bool:
        """Skip rate should be < 5%."""
        return self.skip_rate < 0.05


# ---------------------------------------------------------------------------
# Mock Pipeline Components
# ---------------------------------------------------------------------------

class MockImagePreprocessor:
    """Mock image preprocessor for testing."""
    
    def __init__(self, latency_ms: float = 5.0):
        self.latency_ms = latency_ms
        self.call_count = 0
    
    async def preprocess(self, image: np.ndarray, target_size: Tuple[int, int] = (640, 480)) -> np.ndarray:
        """Resize and normalize image."""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        # Simulate resize
        return np.zeros((*target_size, 3), dtype=np.float32)


class MockDetector:
    """Mock object detector for testing."""
    
    def __init__(self, latency_ms: float = 50.0, detection_count: int = 3):
        self.latency_ms = latency_ms
        self.detection_count = detection_count
        self.call_count = 0
    
    async def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Run object detection."""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return [
            {"class": f"object_{i}", "confidence": 0.9 - i * 0.1, "bbox": [i * 100, i * 100, i * 100 + 50, i * 100 + 50]}
            for i in range(self.detection_count)
        ]


class MockDepthEstimator:
    """Mock depth estimator for testing."""
    
    def __init__(self, latency_ms: float = 60.0):
        self.latency_ms = latency_ms
        self.call_count = 0
    
    async def estimate(self, image: np.ndarray) -> np.ndarray:
        """Estimate depth map."""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        h, w = image.shape[:2] if len(image.shape) >= 2 else (480, 640)
        return np.random.uniform(0.5, 10.0, (h // 4, w // 4)).astype(np.float32)


class MockSegmenter:
    """Mock segmentation for testing."""
    
    def __init__(self, latency_ms: float = 30.0):
        self.latency_ms = latency_ms
        self.call_count = 0
    
    async def segment(self, image: np.ndarray, detections: List[Dict]) -> List[np.ndarray]:
        """Generate segmentation masks."""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return [np.zeros((120, 160), dtype=np.uint8) for _ in detections]


class MockSpatialFuser:
    """Mock spatial fusion for testing."""
    
    def __init__(self, latency_ms: float = 10.0):
        self.latency_ms = latency_ms
        self.call_count = 0
    
    async def fuse(
        self,
        detections: List[Dict],
        depth_map: np.ndarray,
        masks: List[np.ndarray]
    ) -> List[Dict[str, Any]]:
        """Fuse detection, depth, and segmentation."""
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return [
            {**det, "distance_m": 2.0 + i * 0.5, "direction": "ahead"}
            for i, det in enumerate(detections)
        ]


class MockFramePipeline:
    """Mock frame processing pipeline."""
    
    def __init__(
        self,
        preprocess_ms: float = 5.0,
        detect_ms: float = 50.0,
        depth_ms: float = 60.0,
        segment_ms: float = 30.0,
        fuse_ms: float = 10.0,
        parallel_detect_depth: bool = True
    ):
        self.preprocessor = MockImagePreprocessor(preprocess_ms)
        self.detector = MockDetector(detect_ms)
        self.depth_estimator = MockDepthEstimator(depth_ms)
        self.segmenter = MockSegmenter(segment_ms)
        self.fuser = MockSpatialFuser(fuse_ms)
        self.parallel_detect_depth = parallel_detect_depth
        self._metrics: List[FrameProcessingMetrics] = []
    
    async def process_frame(self, image: np.ndarray) -> Tuple[List[Dict], FrameProcessingMetrics]:
        """Process a single frame through the pipeline."""
        metrics = FrameProcessingMetrics()
        start = time.perf_counter()
        
        # Preprocess
        t0 = time.perf_counter()
        processed = await self.preprocessor.preprocess(image)
        metrics.preprocess_ms = (time.perf_counter() - t0) * 1000
        
        # Detection and depth (parallel or sequential)
        if self.parallel_detect_depth:
            t0 = time.perf_counter()
            detections, depth_map = await asyncio.gather(
                self.detector.detect(processed),
                self.depth_estimator.estimate(processed)
            )
            parallel_time = (time.perf_counter() - t0) * 1000
            # Approximate individual times (we ran in parallel)
            metrics.detection_ms = self.detector.latency_ms
            metrics.depth_ms = self.depth_estimator.latency_ms
        else:
            t0 = time.perf_counter()
            detections = await self.detector.detect(processed)
            metrics.detection_ms = (time.perf_counter() - t0) * 1000
            
            t0 = time.perf_counter()
            depth_map = await self.depth_estimator.estimate(processed)
            metrics.depth_ms = (time.perf_counter() - t0) * 1000
        
        # Segmentation
        t0 = time.perf_counter()
        masks = await self.segmenter.segment(processed, detections)
        metrics.segmentation_ms = (time.perf_counter() - t0) * 1000
        
        # Fusion
        t0 = time.perf_counter()
        fused = await self.fuser.fuse(detections, depth_map, masks)
        metrics.fusion_ms = (time.perf_counter() - t0) * 1000
        
        metrics.total_ms = (time.perf_counter() - start) * 1000
        self._metrics.append(metrics)
        
        return fused, metrics
    
    def get_average_metrics(self) -> FrameProcessingMetrics:
        """Get average metrics across all processed frames."""
        if not self._metrics:
            return FrameProcessingMetrics()
        
        n = len(self._metrics)
        return FrameProcessingMetrics(
            preprocess_ms=sum(m.preprocess_ms for m in self._metrics) / n,
            detection_ms=sum(m.detection_ms for m in self._metrics) / n,
            segmentation_ms=sum(m.segmentation_ms for m in self._metrics) / n,
            depth_ms=sum(m.depth_ms for m in self._metrics) / n,
            fusion_ms=sum(m.fusion_ms for m in self._metrics) / n,
            total_ms=sum(m.total_ms for m in self._metrics) / n,
        )


class MockFrameSkipper:
    """Mock frame skipper for overload situations."""
    
    def __init__(self, max_queue_size: int = 3, max_latency_ms: float = 300.0):
        self.max_queue_size = max_queue_size
        self.max_latency_ms = max_latency_ms
        self._queue: List[float] = []  # timestamps
        self._stats = FrameSkipStats()
    
    def should_skip(self, frame_timestamp: float) -> bool:
        """Determine if frame should be skipped."""
        self._stats.total_frames += 1
        
        # Skip if queue is full
        if len(self._queue) >= self.max_queue_size:
            self._stats.skipped_frames += 1
            return True
        
        # Skip if frame is too old
        age_ms = (time.time() - frame_timestamp) * 1000
        if age_ms > self.max_latency_ms:
            self._stats.skipped_frames += 1
            return True
        
        self._queue.append(frame_timestamp)
        return False
    
    def frame_completed(self, latency_ms: float):
        """Mark frame as completed."""
        if self._queue:
            self._queue.pop(0)
        self._stats.processed_frames += 1
        # Update running average
        n = self._stats.processed_frames
        self._stats.avg_latency_ms = (
            (self._stats.avg_latency_ms * (n - 1) + latency_ms) / n
        )
    
    def get_stats(self) -> FrameSkipStats:
        return self._stats


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------

class TestFrameProcessingMetrics:
    """Tests for frame processing metrics."""
    
    def test_metrics_within_budget(self):
        """Test budget check."""
        metrics = FrameProcessingMetrics(total_ms=250.0)
        assert metrics.within_budget
        
        metrics = FrameProcessingMetrics(total_ms=350.0)
        assert not metrics.within_budget
    
    def test_parallel_stages_calculation(self):
        """Test parallel stages time calculation."""
        metrics = FrameProcessingMetrics(detection_ms=50.0, depth_ms=60.0)
        assert metrics.parallel_stages_ms == 60.0
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = FrameProcessingMetrics(
            preprocess_ms=5.123,
            detection_ms=50.456,
            total_ms=200.789
        )
        d = metrics.to_dict()
        assert d["preprocess_ms"] == 5.12
        assert d["detection_ms"] == 50.46
        assert d["total_ms"] == 200.79
        assert d["within_budget"] is True


class TestMockImagePreprocessor:
    """Tests for image preprocessing."""
    
    async def test_preprocess_latency(self):
        """Test preprocessing latency."""
        preprocessor = MockImagePreprocessor(latency_ms=10.0)
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        start = time.perf_counter()
        result = await preprocessor.preprocess(image)
        elapsed = (time.perf_counter() - start) * 1000
        
        assert elapsed >= 9.0  # Allow small timing variance
        assert result.shape == (640, 480, 3)
    
    async def test_preprocess_call_tracking(self):
        """Test preprocessing call count tracking."""
        preprocessor = MockImagePreprocessor(latency_ms=1.0)
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        for _ in range(5):
            await preprocessor.preprocess(image)
        
        assert preprocessor.call_count == 5


class TestMockDetector:
    """Tests for object detection."""
    
    async def test_detection_count(self):
        """Test detection count."""
        detector = MockDetector(latency_ms=10.0, detection_count=5)
        image = np.zeros((480, 640, 3), dtype=np.float32)
        
        detections = await detector.detect(image)
        assert len(detections) == 5
    
    async def test_detection_format(self):
        """Test detection output format."""
        detector = MockDetector(latency_ms=10.0, detection_count=1)
        image = np.zeros((480, 640, 3), dtype=np.float32)
        
        detections = await detector.detect(image)
        assert "class" in detections[0]
        assert "confidence" in detections[0]
        assert "bbox" in detections[0]


class TestMockDepthEstimator:
    """Tests for depth estimation."""
    
    async def test_depth_output_shape(self):
        """Test depth map output shape."""
        estimator = MockDepthEstimator(latency_ms=10.0)
        image = np.zeros((480, 640, 3), dtype=np.float32)
        
        depth = await estimator.estimate(image)
        assert depth.shape == (120, 160)  # 1/4 downscale
    
    async def test_depth_value_range(self):
        """Test depth values are in expected range."""
        estimator = MockDepthEstimator(latency_ms=10.0)
        image = np.zeros((480, 640, 3), dtype=np.float32)
        
        depth = await estimator.estimate(image)
        assert depth.min() >= 0.5
        assert depth.max() <= 10.0


class TestMockFramePipeline:
    """Tests for frame processing pipeline."""
    
    async def test_pipeline_parallel_execution(self):
        """Test parallel detection and depth execution."""
        # Sequential pipeline
        seq_pipeline = MockFramePipeline(
            detect_ms=50.0,
            depth_ms=60.0,
            parallel_detect_depth=False
        )
        
        # Parallel pipeline
        par_pipeline = MockFramePipeline(
            detect_ms=50.0,
            depth_ms=60.0,
            parallel_detect_depth=True
        )
        
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Process with sequential
        _, seq_metrics = await seq_pipeline.process_frame(image)
        
        # Process with parallel
        _, par_metrics = await par_pipeline.process_frame(image)
        
        # Parallel should be faster
        assert par_metrics.total_ms < seq_metrics.total_ms
    
    async def test_pipeline_within_budget(self):
        """Test pipeline meets 300ms budget."""
        pipeline = MockFramePipeline(
            preprocess_ms=5.0,
            detect_ms=50.0,
            depth_ms=60.0,
            segment_ms=30.0,
            fuse_ms=10.0,
            parallel_detect_depth=True
        )
        
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        _, metrics = await pipeline.process_frame(image)
        
        assert metrics.within_budget, f"Pipeline took {metrics.total_ms}ms, budget is 300ms"
    
    async def test_pipeline_average_metrics(self):
        """Test average metrics calculation."""
        pipeline = MockFramePipeline(preprocess_ms=5.0, detect_ms=50.0)
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        for _ in range(3):
            await pipeline.process_frame(image)
        
        avg = pipeline.get_average_metrics()
        assert avg.preprocess_ms >= 4.0  # Allow variance
        assert avg.detection_ms >= 45.0
    
    async def test_pipeline_component_calls(self):
        """Test all pipeline components are called."""
        pipeline = MockFramePipeline()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        await pipeline.process_frame(image)
        
        assert pipeline.preprocessor.call_count == 1
        assert pipeline.detector.call_count == 1
        assert pipeline.depth_estimator.call_count == 1
        assert pipeline.segmenter.call_count == 1
        assert pipeline.fuser.call_count == 1


class TestFrameSkipper:
    """Tests for frame skipping."""
    
    def test_skip_on_full_queue(self):
        """Test frame skipping when queue is full."""
        skipper = MockFrameSkipper(max_queue_size=2)
        now = time.time()
        
        assert not skipper.should_skip(now)
        assert not skipper.should_skip(now)
        assert skipper.should_skip(now)  # Queue full
    
    def test_skip_on_old_frame(self):
        """Test frame skipping for old frames."""
        skipper = MockFrameSkipper(max_latency_ms=100.0)
        old_timestamp = time.time() - 0.2  # 200ms old
        
        assert skipper.should_skip(old_timestamp)
    
    def test_frame_completion_tracking(self):
        """Test frame completion updates stats."""
        skipper = MockFrameSkipper()
        now = time.time()
        
        skipper.should_skip(now)
        skipper.frame_completed(50.0)
        
        stats = skipper.get_stats()
        assert stats.processed_frames == 1
        assert stats.avg_latency_ms == 50.0
    
    def test_skip_rate_calculation(self):
        """Test skip rate calculation."""
        skipper = MockFrameSkipper(max_queue_size=1)
        now = time.time()
        
        # First frame accepted
        skipper.should_skip(now)
        # Second and third skipped (queue full)
        skipper.should_skip(now)
        skipper.should_skip(now)
        
        stats = skipper.get_stats()
        assert stats.skip_rate == pytest.approx(2/3, rel=0.01)
    
    def test_acceptable_skip_rate(self):
        """Test acceptable skip rate threshold."""
        stats = FrameSkipStats(total_frames=100, skipped_frames=4)
        assert stats.within_acceptable_skip_rate
        
        stats = FrameSkipStats(total_frames=100, skipped_frames=10)
        assert not stats.within_acceptable_skip_rate


class TestParallelExecution:
    """Tests for parallel execution patterns."""
    
    async def test_gather_vs_sequential(self):
        """Test asyncio.gather vs sequential execution."""
        async def task(delay_ms: float) -> float:
            await asyncio.sleep(delay_ms / 1000)
            return delay_ms
        
        # Sequential
        start = time.perf_counter()
        await task(50)
        await task(60)
        seq_time = (time.perf_counter() - start) * 1000
        
        # Parallel
        start = time.perf_counter()
        await asyncio.gather(task(50), task(60))
        par_time = (time.perf_counter() - start) * 1000
        
        # Parallel should be ~40% faster (60ms vs 110ms)
        assert par_time < seq_time * 0.7
    
    async def test_parallel_with_timeout(self):
        """Test parallel execution with timeout."""
        async def slow_task():
            await asyncio.sleep(1.0)
            return "slow"
        
        async def fast_task():
            await asyncio.sleep(0.01)
            return "fast"
        
        start = time.perf_counter()
        try:
            await asyncio.wait_for(
                asyncio.gather(slow_task(), fast_task()),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            elapsed = (time.perf_counter() - start) * 1000
            assert elapsed < 150  # Should timeout around 100ms


class TestImagePreprocessingOptimization:
    """Tests for image preprocessing optimization."""
    
    async def test_batch_preprocessing(self):
        """Test batch preprocessing efficiency."""
        preprocessor = MockImagePreprocessor(latency_ms=5.0)
        images = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(4)]
        
        # Sequential
        start = time.perf_counter()
        for img in images:
            await preprocessor.preprocess(img)
        seq_time = (time.perf_counter() - start) * 1000
        
        # Reset
        preprocessor.call_count = 0
        
        # Parallel (simulated batch)
        start = time.perf_counter()
        await asyncio.gather(*[preprocessor.preprocess(img) for img in images])
        par_time = (time.perf_counter() - start) * 1000
        
        # Parallel should be faster
        assert par_time < seq_time * 0.5
    
    def test_resize_dimensions(self):
        """Test optimal resize dimensions."""
        # Standard input
        input_size = (1920, 1080)
        target_size = (640, 480)
        
        # Calculate scale factor
        scale_x = target_size[0] / input_size[0]
        scale_y = target_size[1] / input_size[1]
        
        assert scale_x == pytest.approx(0.333, rel=0.01)
        assert scale_y == pytest.approx(0.444, rel=0.01)


class TestPipelineInstrumentation:
    """Tests for pipeline timing instrumentation."""
    
    async def test_timing_accuracy(self):
        """Test timing measurement accuracy."""
        delay_ms = 50.0
        
        start = time.perf_counter()
        await asyncio.sleep(delay_ms / 1000)
        measured = (time.perf_counter() - start) * 1000
        
        # Allow 20% variance for system scheduling
        assert measured >= delay_ms * 0.8
        assert measured <= delay_ms * 1.3
    
    async def test_pipeline_breakdown_accuracy(self):
        """Test pipeline breakdown adds up correctly."""
        pipeline = MockFramePipeline(
            preprocess_ms=5.0,
            detect_ms=50.0,
            depth_ms=60.0,
            segment_ms=30.0,
            fuse_ms=10.0,
            parallel_detect_depth=True
        )
        
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        _, metrics = await pipeline.process_frame(image)
        
        # Total should be roughly: preprocess + max(detect, depth) + segment + fuse
        # Plus some overhead
        expected_min = 5 + 60 + 30 + 10  # 105ms
        expected_max = expected_min * 1.5  # Allow 50% overhead
        
        assert metrics.total_ms >= expected_min * 0.8
        assert metrics.total_ms <= expected_max


class TestFrameProcessingBudget:
    """Tests for 300ms vision budget compliance."""
    
    async def test_optimized_pipeline_meets_budget(self):
        """Test optimized pipeline meets 300ms budget."""
        # Realistic latencies for optimized pipeline
        pipeline = MockFramePipeline(
            preprocess_ms=10.0,
            detect_ms=80.0,
            depth_ms=100.0,
            segment_ms=50.0,
            fuse_ms=20.0,
            parallel_detect_depth=True
        )
        
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Process multiple frames
        latencies = []
        for _ in range(5):
            _, metrics = await pipeline.process_frame(image)
            latencies.append(metrics.total_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 300.0, f"Average latency {avg_latency}ms exceeds 300ms budget"
    
    async def test_p95_latency_under_budget(self):
        """Test p95 latency is under budget."""
        pipeline = MockFramePipeline(
            preprocess_ms=10.0,
            detect_ms=80.0,
            depth_ms=100.0,
            segment_ms=50.0,
            fuse_ms=20.0,
            parallel_detect_depth=True
        )
        
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        latencies = []
        for _ in range(20):
            _, metrics = await pipeline.process_frame(image)
            latencies.append(metrics.total_ms)
        
        latencies.sort()
        p95_idx = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_idx]
        
        assert p95_latency < 300.0, f"p95 latency {p95_latency}ms exceeds 300ms budget"
