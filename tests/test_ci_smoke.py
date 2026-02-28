#!/usr/bin/env python3
"""
CI Smoke Tests — run on every push / PR.

Validates that **critical perception wiring** is intact so the
zero-detection regression can never ship again.

Usage:
    pytest tests/test_ci_smoke.py -v

These tests are **deterministic** (no network, no GPU, no model files required).
They use only the mock/fallback backends.
"""

import asyncio
import importlib
import os
import sys
import time

import pytest

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ============================================================================
# 1. PerceptionPipeline public API contract
# ============================================================================


class TestPerceptionPipelineAPI:
    """Verify that PerceptionPipeline exposes the attributes main.py expects."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from core.vqa.perception import PerceptionPipeline, MockObjectDetector
        self.pipeline = PerceptionPipeline(detector=MockObjectDetector())

    def test_has_detect_method(self):
        assert hasattr(self.pipeline, "detect"), "Pipeline must expose .detect()"
        assert callable(self.pipeline.detect)

    def test_has_estimate_depth_method(self):
        assert hasattr(self.pipeline, "estimate_depth"), "Pipeline must expose .estimate_depth()"
        assert callable(self.pipeline.estimate_depth)

    def test_has_detector_property(self):
        assert hasattr(self.pipeline, "detector"), "Pipeline must expose .detector property"
        assert self.pipeline.detector is not None

    def test_has_depth_estimator_property(self):
        assert hasattr(self.pipeline, "depth_estimator"), "Pipeline must expose .depth_estimator property"

    def test_detector_has_detect(self):
        det = self.pipeline.detector
        assert hasattr(det, "detect"), "detector must have .detect() method"

    def test_depth_estimator_has_estimate(self):
        de = self.pipeline.depth_estimator
        if de is not None:
            assert hasattr(de, "estimate"), "depth_estimator must have .estimate() method"

    def test_detect_returns_list(self):
        """Calling .detect() on mock should return a non-empty list."""
        import numpy as np
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        result = asyncio.get_event_loop().run_until_complete(self.pipeline.detect(img))
        assert isinstance(result, list)
        assert len(result) > 0, "MockObjectDetector must return at least one detection"

    def test_process_returns_perception_result(self):
        """Full pipeline .process() returns PerceptionResult with detections."""
        import numpy as np
        from shared.schemas import PerceptionResult
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        result = asyncio.get_event_loop().run_until_complete(self.pipeline.process(img))
        assert isinstance(result, PerceptionResult)
        assert len(result.detections) > 0, "process() must produce detections with MockObjectDetector"


# ============================================================================
# 2. create_perception_pipeline wiring
# ============================================================================


class TestCreatePipeline:
    """Ensure factory function creates a pipeline with working detector."""

    def test_mock_pipeline_detect(self):
        from core.vqa import create_perception_pipeline
        pipe = create_perception_pipeline(use_mock=True)
        assert hasattr(pipe, "detect")
        assert hasattr(pipe, "detector")
        assert pipe.detector is not None

    def test_non_mock_pipeline_has_detector(self):
        """When use_mock=False, pipeline should still have a detector (mock fallback if no models)."""
        from core.vqa import create_perception_pipeline
        pipe = create_perception_pipeline(use_mock=False)
        assert pipe.detector is not None
        assert hasattr(pipe.detector, "detect")

    def test_pipeline_detect_callable(self):
        """The .detect() method must be async-callable and return a list."""
        import numpy as np
        from core.vqa import create_perception_pipeline
        pipe = create_perception_pipeline(use_mock=True)
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = asyncio.get_event_loop().run_until_complete(pipe.detect(img))
        assert isinstance(detections, list)


# ============================================================================
# 3. Frame Orchestrator wiring simulation
# ============================================================================


class TestOrchestratorWiring:
    """Simulate the exact code path from main.py that wires detector_fn."""

    def test_detector_fn_is_wired(self):
        """
        Reproduce the logic from main.py _continuous_consumer that builds
        detector_fn from a VQA pipeline. After the fix, detector_fn must
        NOT be None.
        """
        from core.vqa import create_perception_pipeline

        pipeline = create_perception_pipeline(use_mock=True)

        # Replicate the exact wiring logic from main.py
        detector_fn = None
        depth_fn = None

        if hasattr(pipeline, "detect"):
            detector_fn = pipeline.detect
        elif hasattr(pipeline, "detector") and pipeline.detector is not None:
            _det = pipeline.detector
            if hasattr(_det, "detect"):
                async def _detect(img, _d=_det):
                    return await _d.detect(img)
                detector_fn = _detect

        if hasattr(pipeline, "estimate_depth"):
            depth_fn = pipeline.estimate_depth
        elif hasattr(pipeline, "depth_estimator") and pipeline.depth_estimator is not None:
            _de = pipeline.depth_estimator
            if hasattr(_de, "estimate"):
                async def _depth(img, _e=_de):
                    return await _e.estimate(img)
                depth_fn = _depth

        assert detector_fn is not None, (
            "CRITICAL: detector_fn is None — the zero-detection bug has regressed! "
            "PerceptionPipeline must expose .detect() or a public .detector property."
        )

    def test_depth_fn_is_wired(self):
        """Depth estimation function should also be resolved."""
        from core.vqa import create_perception_pipeline

        pipeline = create_perception_pipeline(use_mock=True)

        depth_fn = None
        if hasattr(pipeline, "estimate_depth"):
            depth_fn = pipeline.estimate_depth
        elif hasattr(pipeline, "depth_estimator") and pipeline.depth_estimator is not None:
            _de = pipeline.depth_estimator
            if hasattr(_de, "estimate"):
                async def _depth(img, _e=_de):
                    return await _e.estimate(img)
                depth_fn = _depth

        # depth_fn may be None if depth estimation is disabled — that's OK
        # But if depth_estimator exists, depth_fn should be wired
        if pipeline.depth_estimator is not None:
            assert depth_fn is not None, "depth_fn should be wired when depth_estimator exists"


# ============================================================================
# 4. Orchestrator produces non-zero detections with mock detector
# ============================================================================


class TestOrchestratorDetections:
    """End-to-end: frame → orchestrator → detections > 0."""

    def test_process_frame_produces_detections(self):
        """With a mock detector wired, process_frame must yield detections."""
        import numpy as np
        from application.frame_processing.frame_orchestrator import FrameOrchestrator, FrameOrchestratorConfig
        from application.frame_processing.live_frame_manager import TimestampedFrame
        from core.vqa import create_perception_pipeline

        pipeline = create_perception_pipeline(use_mock=True)
        orch = FrameOrchestrator(config=FrameOrchestratorConfig())

        frame = TimestampedFrame(
            frame_id="test_001",
            sequence_num=1,
            image=np.zeros((480, 640, 3), dtype=np.uint8),
            width=640,
            height=480,
            timestamp_epoch_ms=time.time() * 1000,
        )

        result = asyncio.get_event_loop().run_until_complete(
            orch.process_frame(
                frame,
                detector=pipeline.detect,
                depth_estimator=pipeline.estimate_depth,
            )
        )

        assert result.detections is not None, "Detections should not be None"
        assert len(result.detections) > 0, (
            f"CRITICAL: detections_count=0 with mock detector — "
            f"modules_ok={len(result.telemetry.modules_succeeded)}, "
            f"modules_failed={result.telemetry.modules_failed}"
        )
        assert len(result.telemetry.modules_succeeded) > 0, "At least 'detection' module must succeed"


# ============================================================================
# 5. OCR engine import health check
# ============================================================================


class TestOCRHealth:
    """Verify OCR module loads without crashing."""

    def test_ocr_engine_imports(self):
        import core.ocr as ocr_engine
        assert hasattr(ocr_engine, "OCRResult") or hasattr(ocr_engine, "EASYOCR_AVAILABLE")

    def test_ocr_has_backend_flags(self):
        from core.ocr import EASYOCR_AVAILABLE, TESSERACT_AVAILABLE
        # At least inform — we don't hard-fail if neither is installed
        # but the CI smoke should warn
        if not EASYOCR_AVAILABLE and not TESSERACT_AVAILABLE:
            pytest.skip("No OCR backend installed — install easyocr or pytesseract")


# ============================================================================
# 6. Shared module integrity
# ============================================================================


class TestSharedTypes:
    """Core shared types must be importable and consistent."""

    def test_detection_type(self):
        from shared.schemas import Detection, BoundingBox
        d = Detection(
            id="det_001",
            class_name="person",
            confidence=0.9,
            bbox=BoundingBox(x1=0, y1=0, x2=100, y2=200),
        )
        assert d.class_name == "person"

    def test_perception_result_type(self):
        from shared.schemas import PerceptionResult, DepthMap
        import numpy as np
        pr = PerceptionResult(
            detections=[],
            masks=[],
            depth_map=DepthMap(
                depth_array=np.zeros((60, 80), dtype=np.float32),
                min_depth=0.0, max_depth=10.0, is_metric=False,
            ),
            image_size=(640, 480),
            latency_ms=0.0,
            timestamp="test",
        )
        assert pr.image_size == (640, 480)
