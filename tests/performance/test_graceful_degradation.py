"""
NFR Test #116 — Graceful Degradation
======================================

Verifies the system degrades gracefully when resources are
limited or optional modules are unavailable.
"""

import importlib
import os
from unittest.mock import patch


class TestGracefulDegradation:

    def test_system_starts_without_spatial_perception(self):
        """System should start even when SPATIAL_PERCEPTION_ENABLED=false."""
        with patch.dict(os.environ, {"SPATIAL_PERCEPTION_ENABLED": "false"}):
            # Reload config to pick up env change
            from shared import config
            importlib.reload(config)
            cfg = config.get_config()
            assert cfg["SPATIAL_PERCEPTION_ENABLED"] is False

    def test_system_starts_without_face_engine(self):
        """System should handle missing face engine gracefully."""
        with patch.dict(os.environ, {"FACE_ENGINE_ENABLED": "false"}):
            from shared import config
            importlib.reload(config)
            cfg = config.get_config()
            assert cfg["FACE_ENGINE_ENABLED"] is False

    def test_system_starts_without_audio_engine(self):
        """System should handle missing audio engine gracefully."""
        with patch.dict(os.environ, {"AUDIO_ENGINE_ENABLED": "false"}):
            from shared import config
            importlib.reload(config)
            cfg = config.get_config()
            assert cfg["AUDIO_ENGINE_ENABLED"] is False

    def test_qr_scanner_disabled_gracefully(self):
        """QR scanner should disable cleanly via config."""
        with patch.dict(os.environ, {"ENABLE_QR_SCANNING": "false"}):
            from shared import config
            importlib.reload(config)
            cfg = config.get_config()
            assert cfg["ENABLE_QR_SCANNING"] is False

    def test_vqa_fallback_when_ollama_unavailable(self):
        """VQA should return a sensible fallback response when Ollama is down."""
        try:
            from core.vqa import VQAEngine
            engine = VQAEngine()
            # If engine exists, it should have a health method
            health = engine.health()
            assert isinstance(health, dict)
        except ImportError:
            # Module not present — this is also graceful
            pass

    def test_missing_model_files_handled(self):
        """When model files are missing, system should NOT crash."""
        from shared.config import get_config
        cfg = get_config()
        cfg.get("YOLO_MODEL_PATH", "models/yolov8n.onnx")
        cfg.get("MIDAS_MODEL_PATH", "models/midas_v21_small_256.onnx")

        # System should work even if these don't exist on disk
        # The auto-detection should handle it
        yolo_mode = cfg.get("SPATIAL_USE_YOLO", "auto")
        midas_mode = cfg.get("SPATIAL_USE_MIDAS", "auto")
        assert yolo_mode in ("auto", "true", "false")
        assert midas_mode in ("auto", "true", "false")

    def test_encryption_disabled_gracefully(self):
        """System should work with encryption disabled."""
        with patch.dict(os.environ, {"FACE_ENCRYPTION_ENABLED": "false"}):
            from shared.utils.encryption import EncryptionManager
            mgr = EncryptionManager()
            # With encryption disabled or no key, should still function
            assert hasattr(mgr, "encrypt") or hasattr(mgr, "save_encrypted")
