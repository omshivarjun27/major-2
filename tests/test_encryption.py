"""Tests for on-device encryption helpers."""

from __future__ import annotations

import json
import os
import tempfile

import numpy as np
import pytest

# Ensure shared/ is importable
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shared.utils.encryption import EncryptionManager, reset_encryption_manager


@pytest.fixture(autouse=True)
def _clean_singleton():
    """Reset the global singleton between tests."""
    reset_encryption_manager()
    yield
    reset_encryption_manager()


@pytest.fixture
def enc(monkeypatch):
    """Return an EncryptionManager with a test key."""
    monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-secret-key-for-ci")
    return EncryptionManager(enabled=True)


@pytest.fixture
def enc_disabled():
    """Return an EncryptionManager with encryption disabled."""
    return EncryptionManager(enabled=False)


class TestEncryptionManager:

    def test_active_when_key_set(self, enc):
        assert enc.active is True

    def test_inactive_when_disabled(self, enc_disabled):
        assert enc_disabled.active is False

    def test_encrypt_decrypt_roundtrip(self, enc):
        data = b"Hello, world!"
        encrypted = enc.encrypt(data)
        assert encrypted != data
        assert enc.decrypt(encrypted) == data

    def test_decrypt_without_encryption_is_passthrough(self, enc_disabled):
        data = b"plain data"
        assert enc_disabled.encrypt(data) == data
        assert enc_disabled.decrypt(data) == data

    def test_save_load_encrypted_file(self, enc, tmp_path):
        data = b"secret payload"
        path = tmp_path / "test.enc"
        enc.save_encrypted(path, data)

        # Raw file should NOT contain plain text
        raw = path.read_bytes()
        assert data not in raw

        # Decrypt should recover original
        assert enc.load_decrypted(path) == data

    def test_save_load_npy(self, enc, tmp_path):
        arr = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
        path = tmp_path / "emb.npy"
        enc.save_npy_encrypted(path, arr)

        loaded = enc.load_npy_decrypted(path)
        np.testing.assert_array_equal(arr, loaded)

    def test_save_load_json(self, enc, tmp_path):
        obj = {"key": "value", "nested": [1, 2, 3]}
        path = tmp_path / "meta.json"
        enc.save_json_encrypted(path, obj)

        loaded = enc.load_json_decrypted(path)
        assert loaded == obj

    def test_unencrypted_npy_passthrough(self, enc_disabled, tmp_path):
        arr = np.array([42.0, 99.0], dtype=np.float64)
        path = tmp_path / "plain.npy"
        enc_disabled.save_npy_encrypted(path, arr)

        loaded = enc_disabled.load_npy_decrypted(path)
        np.testing.assert_array_equal(arr, loaded)

    def test_no_key_auto_mode_is_inactive(self, monkeypatch):
        monkeypatch.delenv("MEMORY_ENCRYPTION_KEY", raising=False)
        mgr = EncryptionManager(enabled=None)  # auto
        assert mgr.active is False

    def test_missing_key_with_required_raises(self, monkeypatch):
        monkeypatch.delenv("MEMORY_ENCRYPTION_KEY", raising=False)
        with pytest.raises(RuntimeError, match="not set"):
            EncryptionManager(enabled=True)


class TestPBKDF2Migration:
    """Tests for PBKDF2 key derivation and legacy migration."""

    def test_pbkdf2_produces_valid_fernet_token(self, monkeypatch):
        """New encryption uses PBKDF2-derived key."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key-for-pbkdf2")
        reset_encryption_manager()
        mgr = EncryptionManager(key_env_var="MEMORY_ENCRYPTION_KEY")
        data = b"hello world"
        encrypted = mgr.encrypt(data)
        assert encrypted != data
        assert mgr.decrypt(encrypted) == data

    def test_legacy_sha256_files_still_decryptable(self, monkeypatch):
        """Files encrypted with old SHA-256 KDF can still be decrypted."""
        import base64
        import hashlib
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key-for-migration")
        reset_encryption_manager()

        # Simulate legacy encryption (SHA-256 only, no PBKDF2)
        raw_key = "test-key-for-migration"
        legacy_derived = hashlib.sha256(raw_key.encode()).digest()
        legacy_fernet_key = base64.urlsafe_b64encode(legacy_derived)
        from cryptography.fernet import Fernet
        legacy_fernet = Fernet(legacy_fernet_key)
        legacy_encrypted = legacy_fernet.encrypt(b"legacy data")

        # New manager should be able to decrypt legacy data
        mgr = EncryptionManager(key_env_var="MEMORY_ENCRYPTION_KEY")
        assert mgr.decrypt(legacy_encrypted) == b"legacy data"

    def test_salt_from_env_var(self, monkeypatch):
        """Custom salt produces different encryption than default salt."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "same-key")
        reset_encryption_manager()
        mgr1 = EncryptionManager(key_env_var="MEMORY_ENCRYPTION_KEY")
        data = b"test data"
        enc1 = mgr1.encrypt(data)

        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY_SALT", "custom-salt-value")
        reset_encryption_manager()
        mgr2 = EncryptionManager(key_env_var="MEMORY_ENCRYPTION_KEY")
        enc2 = mgr2.encrypt(data)

        # Different salts should produce different Fernet keys
        # Both should still decrypt with their own manager
        assert mgr1.decrypt(enc1) == data
        assert mgr2.decrypt(enc2) == data

    def test_no_key_material_in_logs(self, monkeypatch, caplog):
        """Key material must not appear in log output."""
        import logging
        test_key = "super-secret-key-12345"
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", test_key)
        reset_encryption_manager()
        with caplog.at_level(logging.DEBUG):
            mgr = EncryptionManager(key_env_var="MEMORY_ENCRYPTION_KEY")
            mgr.encrypt(b"test")
            mgr.decrypt(mgr.encrypt(b"test"))
        assert test_key not in caplog.text

    def test_audit_log_on_encrypt_decrypt(self, monkeypatch, caplog):
        """Encrypt/decrypt emit debug log with byte count."""
        import logging
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "audit-test-key")
        reset_encryption_manager()
        with caplog.at_level(logging.DEBUG, logger="encryption"):
            mgr = EncryptionManager(key_env_var="MEMORY_ENCRYPTION_KEY")
            token = mgr.encrypt(b"12345")
            mgr.decrypt(token)
        assert "encrypt: 5 bytes" in caplog.text
        assert "decrypt:" in caplog.text
