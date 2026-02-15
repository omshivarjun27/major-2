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
