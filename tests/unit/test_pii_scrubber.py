"""Regression tests for PII scrubber — verifies all 7 API key formats are redacted."""
import logging

import pytest

from shared.logging.logging_config import PIIScrubFilter

# Realistic test API keys matching each provider's format
TEST_API_KEYS = {
    "LIVEKIT_API_KEY": "APIabcdef1234567890",
    "LIVEKIT_API_SECRET": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
    "DEEPGRAM_API_KEY": "dg_abc123def456ghi789jkl012mno345",
    "OLLAMA_API_KEY": "sk_proj_1234567890abcdef1234567890abcdef",
    "ELEVEN_API_KEY": "abcdef1234567890abcdef1234567890ab",
    "OLLAMA_VL_API_KEY": "sk_live_abcdef1234567890abcdef1234567890",
    "TAVUS_API_KEY": "abcdef12345678901234567890abcdef",
}


def _make_record(msg: str) -> logging.LogRecord:
    """Create a minimal log record for testing."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )
    return record


class TestPIIScrubberAPIKeys:
    """Verify each of the 7 API key formats is redacted."""

    @pytest.fixture()
    def scrubber(self):
        return PIIScrubFilter(enabled=True)

    @pytest.mark.parametrize("key_name,test_value", list(TEST_API_KEYS.items()))
    def test_api_key_redacted(self, scrubber, key_name, test_value):
        record = _make_record(f"Connecting with {key_name}={test_value}")
        scrubber.filter(record)
        assert test_value not in record.msg, f"{key_name} value leaked through PII scrubber"

    def test_all_keys_redacted_in_combined_message(self, scrubber):
        parts = [f"{k}={v}" for k, v in TEST_API_KEYS.items()]
        msg = "Config loaded: " + ", ".join(parts)
        record = _make_record(msg)
        scrubber.filter(record)
        for key_name, test_value in TEST_API_KEYS.items():
            assert test_value not in record.msg, f"{key_name} leaked in combined message"


class TestPIIScrubberExistingPatterns:
    """Verify existing PII patterns still work after changes."""

    @pytest.fixture()
    def scrubber(self):
        return PIIScrubFilter(enabled=True)

    def test_email_redacted(self, scrubber):
        record = _make_record("User email: user@example.com logged in")
        scrubber.filter(record)
        assert "user@example.com" not in record.msg
        assert "[EMAIL_REDACTED]" in record.msg

    def test_ip_address_redacted(self, scrubber):
        record = _make_record("Connection from 192.168.1.100 accepted")
        scrubber.filter(record)
        assert "192.168.1.100" not in record.msg
        assert "[IP_REDACTED]" in record.msg

    def test_face_id_redacted(self, scrubber):
        record = _make_record("Identified face fid_abcdef1234567890")
        scrubber.filter(record)
        assert "fid_abcdef1234567890" not in record.msg
        assert "[FACE_ID_REDACTED]" in record.msg

    def test_bearer_token_redacted(self, scrubber):
        record = _make_record("Auth: Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig")
        scrubber.filter(record)
        assert "eyJhbGciOiJSUzI1NiJ9" not in record.msg
        assert "Bearer [TOKEN_REDACTED]" in record.msg

    def test_sk_prefix_key_redacted(self, scrubber):
        record = _make_record("Using key sk_abcdefghijklmnopqrstuvwxyz")
        scrubber.filter(record)
        assert "sk_abcdefghijklmnopqrstuvwxyz" not in record.msg


class TestPIIScrubberNewPatterns:
    """Test the newly added patterns."""

    @pytest.fixture()
    def scrubber(self):
        return PIIScrubFilter(enabled=True)

    def test_deepgram_key_redacted(self, scrubber):
        record = _make_record("Deepgram key: dg_abcdefghij1234567890")
        scrubber.filter(record)
        assert "dg_abcdefghij1234567890" not in record.msg

    def test_long_hex_redacted(self, scrubber):
        hex_key = "a" * 32  # 32-char hex string
        record = _make_record(f"Secret: {hex_key}")
        scrubber.filter(record)
        assert hex_key not in record.msg
        assert "[HEX_SECRET_REDACTED]" in record.msg

    def test_key_value_pattern_redacted(self, scrubber):
        record = _make_record("api_key=mysecretvalue12345678")
        scrubber.filter(record)
        assert "mysecretvalue12345678" not in record.msg

    def test_websocket_credentials_redacted(self, scrubber):
        record = _make_record("Connecting to ws://user:secretpass@host:7880")
        scrubber.filter(record)
        assert "secretpass" not in record.msg


class TestPIIScrubberDisabled:
    """Verify scrubber can be disabled."""

    def test_disabled_passes_through(self):
        scrubber = PIIScrubFilter(enabled=False)
        record = _make_record("user@example.com with key sk_abcdefghijklmnopqrstuvwxyz")
        scrubber.filter(record)
        assert "user@example.com" in record.msg
        assert "sk_abcdefghijklmnopqrstuvwxyz" in record.msg


class TestPIIScrubberNoFalsePositives:
    """Verify common non-PII strings are NOT redacted."""

    @pytest.fixture()
    def scrubber(self):
        return PIIScrubFilter(enabled=True)

    def test_short_strings_not_redacted(self, scrubber):
        record = _make_record("Port 8000 version 3.11 count=42")
        scrubber.filter(record)
        assert "8000" in record.msg
        assert "3.11" in record.msg
        assert "42" in record.msg

    def test_normal_log_message_preserved(self, scrubber):
        record = _make_record("Detection complete: 5 objects found in 45ms")
        scrubber.filter(record)
        assert "Detection complete: 5 objects found in 45ms" == record.msg

    def test_file_paths_preserved(self, scrubber):
        record = _make_record("Loading model from models/yolov8n.onnx")
        scrubber.filter(record)
        assert "models/yolov8n.onnx" in record.msg
