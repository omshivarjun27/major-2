"""NFR: Model Checksum Verification — verifies download_models.py has checksum support."""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestModelChecksums:
    """Verify model download has checksum verification capability."""

    def test_sha256_function_exists(self):
        """download_models should expose a _sha256 function."""
        from scripts.download_models import _sha256
        assert callable(_sha256)

    def test_sha256_computes_correct_hash(self, tmp_path):
        """_sha256 should produce correct hash for a known file."""
        from scripts.download_models import _sha256
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"hello world")
        # Known SHA256 of "hello world"
        assert _sha256(str(test_file)) == \
            "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_verify_checksum_passes_for_correct_hash(self, tmp_path, capsys):
        """_verify_checksum should return True for matching hash."""
        from scripts import download_models
        test_file = tmp_path / "test.onnx"
        test_file.write_bytes(b"model data")
        expected = download_models._sha256(str(test_file))

        # Temporarily set checksum
        orig = download_models.MODEL_CHECKSUMS.copy()
        download_models.MODEL_CHECKSUMS["test.onnx"] = expected
        try:
            result = download_models._verify_checksum(str(test_file), "test.onnx")
            assert result is True
        finally:
            download_models.MODEL_CHECKSUMS.update(orig)

    def test_verify_checksum_fails_for_wrong_hash(self, tmp_path, capsys):
        """_verify_checksum should return False and delete file for wrong hash."""
        from scripts import download_models
        test_file = tmp_path / "bad.onnx"
        test_file.write_bytes(b"tampered data")

        orig = download_models.MODEL_CHECKSUMS.copy()
        download_models.MODEL_CHECKSUMS["bad.onnx"] = "0" * 64  # wrong hash
        try:
            result = download_models._verify_checksum(str(test_file), "bad.onnx")
            assert result is False
            assert not test_file.exists(), "File should be deleted on checksum mismatch"
        finally:
            download_models.MODEL_CHECKSUMS.update(orig)

    def test_verify_checksum_passes_when_no_hash_registered(self, tmp_path):
        """_verify_checksum should return True when no hash is registered (None)."""
        from scripts.download_models import _verify_checksum
        test_file = tmp_path / "unknown.onnx"
        test_file.write_bytes(b"some model")
        result = _verify_checksum(str(test_file), "unknown.onnx")
        assert result is True

    def test_model_checksums_dict_has_entries(self):
        """MODEL_CHECKSUMS should have entries for known models."""
        from scripts.download_models import MIDAS_DEST_NAME, MODEL_CHECKSUMS, YOLO_DEST_NAME
        assert MIDAS_DEST_NAME in MODEL_CHECKSUMS
        assert YOLO_DEST_NAME in MODEL_CHECKSUMS
