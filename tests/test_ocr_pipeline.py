"""
Tests for OCR Engine
=====================

Covers: preprocessing functions, OCRResult/OCRPipelineResult data
structures, pipeline with no backend, and pipeline with mock backends.
"""

import asyncio
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.ocr import (
    OCRPipeline,
    OCRPipelineResult,
    OCRResult,
    _to_numpy,
    apply_clahe,
    denoise,
    deskew,
    preprocess,
    CV2_AVAILABLE,
)


# ============================================================================
# OCRResult
# ============================================================================


class TestOCRResult:
    def test_creation(self):
        r = OCRResult(
            text="Hello",
            confidence=0.95,
            bbox=(10, 20, 100, 50),
            backend="easyocr",
        )
        assert r.text == "Hello"
        assert r.confidence == 0.95
        assert r.bbox == (10, 20, 100, 50)

    def test_to_dict(self):
        r = OCRResult(
            text="World",
            confidence=0.876,
            bbox=(0, 0, 50, 20),
            latency_ms=42.567,
            backend="tesseract",
        )
        d = r.to_dict()
        assert d["text"] == "World"
        assert d["confidence"] == 0.876
        assert d["bbox"] == [0, 0, 50, 20]
        assert d["latency_ms"] == 42.6
        assert d["backend"] == "tesseract"

    def test_to_dict_no_bbox(self):
        r = OCRResult(text="No bbox", confidence=0.5, backend="unknown")
        d = r.to_dict()
        assert d["bbox"] is None


# ============================================================================
# OCRPipelineResult
# ============================================================================


class TestOCRPipelineResult:
    def test_empty_result(self):
        r = OCRPipelineResult()
        assert r.results == []
        assert r.full_text == ""
        assert r.error is None

    def test_error_result(self):
        r = OCRPipelineResult(error="Backend missing")
        d = r.to_dict()
        assert d["error"] == "Backend missing"

    def test_to_dict(self):
        results = [
            OCRResult(text="Hello", confidence=0.9, backend="test"),
            OCRResult(text="World", confidence=0.8, backend="test"),
        ]
        r = OCRPipelineResult(
            results=results,
            full_text="Hello World",
            total_latency_ms=50.3,
            preprocessing_ms=10.2,
            backend_used="test",
        )
        d = r.to_dict()
        assert len(d["results"]) == 2
        assert d["full_text"] == "Hello World"
        assert d["total_latency_ms"] == 50.3
        assert d["preprocessing_ms"] == 10.2


# ============================================================================
# Preprocessing
# ============================================================================


class TestPreprocessing:
    def test_to_numpy_from_ndarray(self):
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        result = _to_numpy(arr)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8

    def test_to_numpy_from_float(self):
        arr = np.zeros((100, 100, 3), dtype=np.float32)
        result = _to_numpy(arr)
        assert result.dtype == np.uint8

    def test_to_numpy_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported image type"):
            _to_numpy("not_an_image")

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="cv2 not installed")
    def test_apply_clahe(self):
        gray = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        result = apply_clahe(gray)
        assert result.shape == gray.shape
        assert result.dtype == np.uint8

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="cv2 not installed")
    def test_denoise(self):
        gray = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        result = denoise(gray)
        assert result.shape == gray.shape

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="cv2 not installed")
    def test_deskew_no_lines(self):
        """Deskew with a blank image: should return same shape."""
        gray = np.zeros((100, 100), dtype=np.uint8)
        result = deskew(gray)
        assert result.shape == gray.shape

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="cv2 not installed")
    def test_preprocess_full_pipeline(self):
        img = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        result = preprocess(img)
        assert len(result.shape) == 2  # Grayscale
        assert result.dtype == np.uint8

    def test_apply_clahe_no_cv2(self):
        """Without cv2, CLAHE returns input unchanged."""
        from unittest.mock import patch
        gray = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
        with patch("ocr_engine.CV2_AVAILABLE", False):
            result = apply_clahe(gray)
            np.testing.assert_array_equal(result, gray)


# ============================================================================
# OCRPipeline
# ============================================================================


class TestOCRPipeline:
    def test_is_ready(self):
        pipeline = OCRPipeline()
        # is_ready depends on backend availability
        assert isinstance(pipeline.is_ready, bool)

    @pytest.mark.asyncio
    async def test_process_no_backend(self):
        """If no backend is available, returns error result."""
        pipeline = OCRPipeline()
        # Force no backend
        pipeline._backend = None
        result = await pipeline.process(np.zeros((100, 100, 3), dtype=np.uint8))
        assert result.error is not None
        assert "No OCR backend" in result.error

    @pytest.mark.asyncio
    async def test_process_with_mock_backend(self):
        """Test pipeline with a mock backend."""

        class MockBackend:
            def read(self, gray):
                return [
                    OCRResult(text="Mock text", confidence=0.85, backend="mock"),
                ]

        pipeline = OCRPipeline()
        pipeline._backend = MockBackend()
        pipeline._backend_name = "MockBackend"

        img = np.random.randint(0, 255, (100, 200, 3), dtype=np.uint8)
        result = await pipeline.process(img)

        assert result.error is None
        assert len(result.results) == 1
        assert result.results[0].text == "Mock text"
        assert result.full_text == "Mock text"
        assert result.total_latency_ms > 0
        assert result.backend_used == "MockBackend"

    @pytest.mark.asyncio
    async def test_process_filters_low_confidence(self):
        """Results below min_confidence are filtered out."""

        class LowConfBackend:
            def read(self, gray):
                return [
                    OCRResult(text="Good", confidence=0.9, backend="test"),
                    OCRResult(text="Bad", confidence=0.1, backend="test"),
                ]

        pipeline = OCRPipeline(min_confidence=0.3)
        pipeline._backend = LowConfBackend()
        pipeline._backend_name = "LowConfBackend"

        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = await pipeline.process(img)
        assert len(result.results) == 1
        assert result.results[0].text == "Good"
        assert result.full_text == "Good"

    @pytest.mark.asyncio
    async def test_process_backend_raises(self):
        """Backend exception returns error result, not crash."""

        class BrokenBackend:
            def read(self, gray):
                raise RuntimeError("OCR exploded")

        pipeline = OCRPipeline()
        pipeline._backend = BrokenBackend()
        pipeline._backend_name = "BrokenBackend"

        img = np.zeros((50, 50, 3), dtype=np.uint8)
        result = await pipeline.process(img)
        assert result.error is not None
        assert "OCR failed" in result.error
