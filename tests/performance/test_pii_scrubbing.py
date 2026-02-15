"""NFR: PII Log-Scrubbing — verifies PII is redacted from log output."""

from __future__ import annotations

import logging
import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestPIIScrubbing:
    """Verify that PII patterns are scrubbed from log output."""

    def _capture_log(self, message: str, pii_scrub: bool = True) -> str:
        """Configure a logger with PII scrubbing and capture output."""
        from shared.logging.logging_config import PIIScrubFilter

        handler = logging.StreamHandler()
        handler.addFilter(PIIScrubFilter(enabled=pii_scrub))

        logger = logging.getLogger(f"test.pii.{id(self)}")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # Capture output
        import io
        buf = io.StringIO()
        handler.stream = buf
        logger.info(message)
        return buf.getvalue()

    def test_email_redacted(self):
        output = self._capture_log("User email is alice@example.com")
        assert "alice@example.com" not in output
        assert "[EMAIL_REDACTED]" in output

    def test_ip_address_redacted(self):
        output = self._capture_log("Connection from 192.168.1.100")
        assert "192.168.1.100" not in output
        assert "[IP_REDACTED]" in output

    def test_face_id_redacted(self):
        output = self._capture_log("Registered face fid_a1b2c3d4e5f6")
        assert "fid_a1b2c3d4e5f6" not in output
        assert "[FACE_ID_REDACTED]" in output

    def test_api_key_redacted(self):
        output = self._capture_log("Using key sk_abcdefghijklmnopqrstuvwxyz")
        assert "sk_abcdefghijklmnopqrstuvwxyz" not in output
        assert "[API_KEY_REDACTED]" in output

    def test_bearer_token_redacted(self):
        output = self._capture_log("Auth: Bearer eyJhbGciOiJIUzI1NiJ9.test")
        assert "eyJhbGciOiJIUzI1NiJ9" not in output
        assert "[TOKEN_REDACTED]" in output

    def test_clean_message_passes_through(self):
        output = self._capture_log("Processed 42 frames in 1.5 seconds")
        assert "Processed 42 frames" in output

    def test_disabled_filter_passes_pii(self):
        output = self._capture_log("User email is alice@example.com", pii_scrub=False)
        assert "alice@example.com" in output

    def test_multiple_pii_in_one_message(self):
        output = self._capture_log(
            "User alice@example.com connected from 10.0.0.1 with face fid_deadbeef00"
        )
        assert "alice@example.com" not in output
        assert "10.0.0.1" not in output
        assert "fid_deadbeef00" not in output
