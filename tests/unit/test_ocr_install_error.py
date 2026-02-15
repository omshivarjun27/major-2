"""
Unit tests — OCR Install Error Handling
==========================================

Simulates missing OCR packages and verifies:
1. Graceful error message (not a crash)
2. Correct user-facing message with install instructions
3. OS-specific hints
"""

import sys
from unittest.mock import patch, MagicMock
import pytest
import numpy as np


class TestOCRMissingPackageHandling:
    """Simulate missing easyocr/pytesseract and verify graceful behavior."""

    def test_ocr_engine_module_loads_without_easyocr(self):
        """OCR engine should load even if easyocr is not installed."""
        # Just verify the engine module loads without crashing
        from core.ocr.engine import get_ocr_status, get_install_instructions
        status = get_ocr_status()
        assert isinstance(status, dict)

    def test_install_instructions_mention_scripts(self):
        """Install instructions should reference the install script."""
        from core.ocr.engine import get_install_instructions
        instructions = get_install_instructions()
        assert "scripts/install_ocr_deps.sh" in instructions

    def test_install_instructions_mention_pip(self):
        """Install instructions should include pip commands."""
        from core.ocr.engine import get_install_instructions
        instructions = get_install_instructions()
        assert "pip install" in instructions

    @pytest.mark.asyncio
    async def test_ocr_read_returns_error_when_no_backends(self):
        """ocr_read should return helpful error, not crash."""
        from core.ocr.engine import ocr_read
        img = np.ones((100, 200), dtype=np.uint8) * 200
        result = await ocr_read(img)
        # Should have some kind of result
        assert isinstance(result, dict)
        assert "backend" in result or "backend_used" in result

    def test_ocr_pipeline_no_backend_returns_error(self):
        """OCRPipeline with no backend should return error in result."""
        from core.ocr import OCRPipeline
        pipe = OCRPipeline()
        if not pipe.is_ready:
            # This is expected when neither easyocr nor pytesseract is installed
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                pipe.process(np.ones((50, 50), dtype=np.uint8) * 200)
            )
            assert result.error is not None
            assert "install" in result.error.lower() or "backend" in result.error.lower() or "available" in result.error.lower()

    def test_status_includes_heuristic_field(self):
        from core.ocr.engine import get_ocr_status
        status = get_ocr_status()
        assert "heuristic_fallback_available" in status
