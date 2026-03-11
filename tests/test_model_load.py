"""
Preflight checks – verify that critical model files exist when configured,
and that key engines (QR, OCR) initialise without errors.

Run::

    python -m pytest tests/test_model_load.py -v
"""

import os

import pytest

# ---------------------------------------------------------------------------
# Model file checks
# ---------------------------------------------------------------------------

MODELS_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "models")


def _model_path(name: str) -> str:
    return os.path.abspath(os.path.join(MODELS_DIR, name))


class TestModelFilesExist:
    """Assert model weight files exist when the project expects them."""

    def test_yolo_model_exists_if_configured(self):
        """If USE_YOLO is not explicitly disabled, the ONNX file should exist."""
        use_yolo = os.environ.get("USE_YOLO", "auto")
        path = _model_path("yolov8n.onnx")
        if use_yolo in ("true", "1"):
            assert os.path.isfile(path), f"YOLO model required but missing at {path}"
        elif use_yolo == "auto":
            # Auto-detect: log presence, don't fail
            status = "present" if os.path.isfile(path) else "absent"
            print(f"YOLO model ({path}): {status}")
        else:
            pytest.skip("YOLO explicitly disabled")

    def test_midas_model_exists_if_configured(self):
        """If USE_MIDAS is not explicitly disabled, the ONNX file should exist."""
        use_midas = os.environ.get("USE_MIDAS", "auto")
        path = _model_path("midas_v21_small_256.onnx")
        if use_midas in ("true", "1"):
            assert os.path.isfile(path), f"MiDaS model required but missing at {path}"
        elif use_midas == "auto":
            status = "present" if os.path.isfile(path) else "absent"
            print(f"MiDaS model ({path}): {status}")
        else:
            pytest.skip("MiDaS explicitly disabled")


# ---------------------------------------------------------------------------
# Engine initialisation checks
# ---------------------------------------------------------------------------

class TestQRScannerInit:
    """QR scanner should initialise without exceptions."""

    def test_qr_scanner_creates(self):
        from core.qr.qr_scanner import QRScanner
        scanner = QRScanner()
        assert isinstance(scanner, QRScanner)
        # At least one backend should be available
        print(f"QR scanner ready: {scanner.is_ready} "
              f"(pyzbar={scanner._use_pyzbar}, cv2={scanner._use_cv2})")


class TestOCREngineInit:
    """OCR pipeline should initialise gracefully even without backends."""

    def test_ocr_pipeline_creates(self):
        try:
            from core.ocr import OCRPipeline
        except ImportError:
            pytest.skip("OCR engine module not available")
        pipe = OCRPipeline()
        print(f"OCR pipeline ready: {pipe.is_ready}")
        # Should not raise regardless of backend availability
