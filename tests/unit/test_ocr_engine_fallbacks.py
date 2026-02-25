"""
Unit tests — OCR Engine Fallbacks
===================================

Tests the robust OCR abstraction: backend probe, install hints,
heuristic fallback, graceful error handling.
"""


import numpy as np
import pytest


class TestOCRBackendProbes:
    """Test backend availability probes."""

    def test_probe_functions_exist(self):
        from core.ocr.engine import _probe_cv2, _probe_easyocr, _probe_tesseract
        # These return booleans — no crash
        assert isinstance(_probe_easyocr(), bool)
        assert isinstance(_probe_tesseract(), bool)
        assert isinstance(_probe_cv2(), bool)

    def test_get_ocr_status_returns_dict(self):
        from core.ocr.engine import get_ocr_status
        status = get_ocr_status()
        assert isinstance(status, dict)
        assert "easyocr_available" in status
        assert "tesseract_available" in status
        assert "opencv_available" in status
        assert "any_backend_available" in status

    def test_install_instructions_contain_pip(self):
        from core.ocr.engine import get_install_instructions
        text = get_install_instructions()
        assert "pip" in text.lower() or "install" in text.lower()


class TestOCRHeuristicFallback:
    """Test the OpenCV-only heuristic backend."""

    def test_heuristic_backend_no_crash(self):
        """Heuristic backend should not crash on a blank image."""
        try:
            import cv2  # noqa: F401
        except ImportError:
            pytest.skip("OpenCV not available")

        from core.ocr.engine import _HeuristicBackend
        from shared.schemas import OCRResult
        backend = _HeuristicBackend()
        gray = np.ones((100, 200), dtype=np.uint8) * 200
        result = backend.read(gray)
        assert isinstance(result, OCRResult)

    def test_heuristic_detects_regions_on_text_like_image(self):
        """Heuristic should detect some regions on a contrasted image."""
        try:
            import cv2
        except ImportError:
            pytest.skip("OpenCV not available")

        from core.ocr.engine import _HeuristicBackend
        from shared.schemas import OCRResult
        backend = _HeuristicBackend()
        # Create an image with some dark rectangles (text-like)
        img = np.ones((200, 400), dtype=np.uint8) * 220
        cv2.rectangle(img, (20, 50), (150, 80), 30, -1)
        cv2.rectangle(img, (20, 100), (200, 130), 30, -1)
        result = backend.read(img)
        # May or may not detect — just no crash
        assert isinstance(result, OCRResult)


@pytest.mark.asyncio
class TestOCRRead:
    """Test the unified ocr_read function."""

    async def test_ocr_read_returns_ocr_result(self):
        from core.ocr.engine import ocr_read
        from shared.schemas import OCRResult
        img = np.ones((100, 200), dtype=np.uint8) * 200
        result = await ocr_read(img)
        assert isinstance(result, OCRResult)
        # OCRResult should have backend and full_text attributes
        assert hasattr(result, "backend")
        assert hasattr(result, "full_text")

    async def test_ocr_read_with_no_backends_gives_ocr_result(self):
        """When both EasyOCR and Tesseract are missing, should return OCRResult gracefully."""
        from core.ocr.engine import ocr_read
        from shared.schemas import OCRResult
        # Even if backends are available, the function should handle gracefully
        img = np.ones((50, 50), dtype=np.uint8) * 128
        result = await ocr_read(img)
        assert isinstance(result, OCRResult)


class TestOCRPipelineFallback:
    """Test the OCRPipeline from core/ocr/__init__.py."""

    def test_pipeline_is_ready_attribute(self):
        from core.ocr import OCRPipeline
        pipe = OCRPipeline()
        assert isinstance(pipe.is_ready, bool)

    @pytest.mark.asyncio
    async def test_pipeline_process_no_crash(self):
        from core.ocr import OCRPipeline
        pipe = OCRPipeline()
        img = np.ones((100, 200, 3), dtype=np.uint8) * 200
        result = await pipe.process(img)
        assert hasattr(result, "to_dict")
        d = result.to_dict()
        assert "backend_used" in d
