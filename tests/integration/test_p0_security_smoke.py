"""P0 Security Integration Smoke Test.

Verifies that all P0 security components work together:
- SecretProvider returns expected values
- PII scrubber catches all API key formats
- EncryptionManager encrypts/decrypts consent-format JSON
- Components integrate cleanly (no import errors, no runtime crashes)
"""
import logging

import pytest


class TestSecretProviderIntegration:
    """Verify SecretProvider works end-to-end."""

    SECRET_KEYS = [
        "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY",
        "OLLAMA_API_KEY", "ELEVEN_API_KEY", "OLLAMA_VL_API_KEY", "TAVUS_API_KEY",
    ]

    def test_provider_returns_set_secrets(self, monkeypatch):
        """When env vars are set, EnvironmentProvider returns their values."""
        for key in self.SECRET_KEYS:
            monkeypatch.setenv(key, f"test-value-{key}")
        from shared.config.secret_provider import EnvironmentProvider
        provider = EnvironmentProvider()
        for key in self.SECRET_KEYS:
            assert provider.get_secret(key) == f"test-value-{key}"

    def test_provider_returns_none_for_missing(self, monkeypatch):
        """When env vars are unset, EnvironmentProvider returns None."""
        for key in self.SECRET_KEYS:
            monkeypatch.delenv(key, raising=False)
        from shared.config.secret_provider import EnvironmentProvider
        provider = EnvironmentProvider()
        for key in self.SECRET_KEYS:
            assert provider.get_secret(key) is None

    def test_provider_health_check(self):
        """Provider health check returns boolean."""
        from shared.config.secret_provider import create_secret_provider
        provider = create_secret_provider()
        assert isinstance(provider.health_check(), bool)


class TestPIIScrubberIntegration:
    """Verify PII scrubber catches all API key formats in logs."""

    TEST_KEYS = {
        "LIVEKIT_API_KEY": "APIabcdef1234567890",
        "LIVEKIT_API_SECRET": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
        "DEEPGRAM_API_KEY": "dg_abc123def456ghi789jkl012mno345",
        "OLLAMA_API_KEY": "ol1234567890abcdef1234567890abcdef",
        "ELEVEN_API_KEY": "abcdef1234567890abcdef1234567890",
        "OLLAMA_VL_API_KEY": "ol_abcdef1234567890abcdef1234567890",
        "TAVUS_API_KEY": "tvs_abcdef1234567890abcdef",
    }

    def test_all_key_formats_scrubbed(self):
        """None of the 7 API key formats appear in scrubbed log output."""
        from shared.logging.logging_config import PIIScrubFilter
        scrubber = PIIScrubFilter(enabled=True)
        for key_name, test_value in self.TEST_KEYS.items():
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=f"Connecting with {key_name}={test_value}",
                args=None, exc_info=None,
            )
            scrubber.filter(record)
            assert test_value not in record.msg, \
                f"{key_name} value leaked through PII scrubber: {record.msg}"


class TestEncryptionIntegration:
    """Verify encryption works for consent-format JSON."""

    def test_encrypt_decrypt_consent_json(self, monkeypatch, tmp_path):
        """EncryptionManager roundtrips consent-format JSON."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key-for-p0-smoke")
        from shared.utils.encryption import EncryptionManager, reset_encryption_manager
        reset_encryption_manager()
        enc = EncryptionManager(enabled=True)

        consent = {
            "opt_in": True,
            "save_raw_media": False,
            "reason": "User agreed",
            "timestamp": "2026-02-25T00:00:00Z",
        }
        path = tmp_path / "consent.json"
        enc.save_json_encrypted(path, consent)

        # File should not contain plaintext
        raw = path.read_bytes()
        assert b"opt_in" not in raw, "Consent data not encrypted"

        # Decrypted should match original
        loaded = enc.load_json_decrypted(path)
        assert loaded == consent

    def test_tampered_file_detected(self, monkeypatch, tmp_path):
        """Tampered encrypted files raise on decrypt."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key-for-p0-smoke")
        from shared.utils.encryption import EncryptionManager, reset_encryption_manager
        reset_encryption_manager()
        enc = EncryptionManager(enabled=True)

        path = tmp_path / "tampered.json"
        enc.save_json_encrypted(path, {"test": True})

        # Tamper with the file
        data = path.read_bytes()
        path.write_bytes(data[:-5] + b"XXXXX")

        with pytest.raises(Exception):
            enc.load_json_decrypted(path)


class TestCrossComponentIntegration:
    """Verify components don't conflict with each other."""

    def test_all_security_modules_importable(self):
        """All P0 security modules import without error."""
        from shared.config.secret_provider import SecretProvider, create_secret_provider  # noqa: F401
        from shared.logging.logging_config import PIIScrubFilter, configure_logging  # noqa: F401
        from shared.utils.encryption import EncryptionManager, get_encryption_manager  # noqa: F401
        # No ImportError = pass

    def test_secret_provider_and_encryption_coexist(self, monkeypatch):
        """SecretProvider and EncryptionManager can both be active."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key")
        monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram")
        from shared.config.secret_provider import EnvironmentProvider
        from shared.utils.encryption import EncryptionManager, reset_encryption_manager
        reset_encryption_manager()
        provider = EnvironmentProvider()
        enc = EncryptionManager(enabled=True)
        assert provider.get_secret("DEEPGRAM_API_KEY") == "test-deepgram"
        assert enc.active is True
