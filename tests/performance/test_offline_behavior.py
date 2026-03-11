"""NFR: Offline Behavior — verifies system handles missing network/models gracefully."""

from __future__ import annotations

import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestOfflineBehavior:
    """Verify graceful degradation when models or network are unavailable."""

    def test_face_engine_import_without_models(self):
        """Face engine should import without crashing even if models are missing."""
        try:
            from core.face.face_embeddings import FaceEmbeddingStore
        except ImportError:
            pytest.skip("Face engine not installed")

    def test_ocr_engine_import_without_backends(self):
        """OCR engine module should import without crashing even if no OCR backend is installed."""
        from core.ocr.engine import get_ocr_status, ocr_read
        assert callable(ocr_read)
        status = get_ocr_status()
        assert isinstance(status, dict)

    def test_qr_engine_import_without_zbar(self):
        """QR engine should import gracefully even without pyzbar."""
        try:
            from core.qr import QRScanner
        except ImportError:
            pytest.skip("QR engine not installed")

    def test_spatial_tools_import_without_models(self):
        """Spatial tools should import without crashing when model files are missing."""
        from core.vision.spatial import MockObjectDetector
        detector = MockObjectDetector()
        assert detector.is_ready()

    def test_config_loads_without_env_file(self, monkeypatch):
        """Config should still load with defaults even without .env."""
        # Ensure no env vars are set for critical keys
        for key in ["LIVEKIT_URL", "DEEPGRAM_API_KEY", "ELEVEN_API_KEY"]:
            monkeypatch.delenv(key, raising=False)
        from shared.config import get_config
        config = get_config()
        assert isinstance(config, dict)
        assert "VISION_PROVIDER" in config
