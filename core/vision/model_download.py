"""Model download utilities for vision components."""

from __future__ import annotations

import hashlib
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger("vision-model-download")

YOLOV8N_URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.onnx"
YOLOV8N_SHA256 = "634279b40c07c6391472c51ad45b81ebc48706a9a1fe72dd3396322acd0c053b"
DEFAULT_YOLO_MODEL_PATH = "models/yolov8n.onnx"

MIDAS_SMALL_URL = "https://huggingface.co/julienkay/sentis-MiDaS/resolve/main/onnx/midas_v21_small_256.onnx"
MIDAS_SMALL_SHA256 = "b0a5b3f12625137e626805167907fe0410665bec671685d59daaa2daab19f977"
DEFAULT_MIDAS_MODEL_PATH = "models/midas_v21_small_256.onnx"
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def ensure_yolo_model(dest: str = DEFAULT_YOLO_MODEL_PATH) -> str:
    """Ensure the YOLO ONNX model exists locally and passes checksum verification."""
    path = Path(dest)
    if path.exists():
        if _sha256_matches(path, YOLOV8N_SHA256):
            return str(path)
        logger.warning("YOLO model checksum mismatch, re-downloading: %s", path)
        try:
            path.unlink()
        except OSError as exc:
            logger.error("Failed to remove invalid YOLO model %s: %s", path, exc)
            raise

    path.parent.mkdir(parents=True, exist_ok=True)
    _download_with_checksum(YOLOV8N_URL, path, YOLOV8N_SHA256)
    return str(path)


def ensure_midas_model(dest: str = DEFAULT_MIDAS_MODEL_PATH) -> str:
    """Ensure the MiDaS ONNX model exists locally and passes checksum verification."""
    path = Path(dest)
    if path.exists():
        if _sha256_matches(path, MIDAS_SMALL_SHA256):
            return str(path)
        logger.warning("MiDaS model checksum mismatch, re-downloading: %s", path)
        try:
            path.unlink()
        except OSError as exc:
            logger.error("Failed to remove invalid MiDaS model %s: %s", path, exc)
            raise

    path.parent.mkdir(parents=True, exist_ok=True)
    _download_with_checksum(MIDAS_SMALL_URL, path, MIDAS_SMALL_SHA256)
    return str(path)


def _download_with_checksum(url: str, destination: Path, expected_sha256: str) -> None:
    """Download a model file and verify its checksum before finalizing."""
    temp_path = destination.with_suffix(destination.suffix + ".tmp")
    try:
        logger.info("Downloading YOLO model from %s", url)
        digest = hashlib.sha256()
        with urllib.request.urlopen(url) as response, temp_path.open("wb") as handle:
            while True:
                chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)

        checksum = digest.hexdigest()
        expected = _normalize_sha256(expected_sha256)
        if checksum != expected:
            temp_path.unlink(missing_ok=True)
            raise ValueError(
                "YOLO model checksum mismatch: expected %s, got %s" % (expected, checksum)
            )

        if destination.exists():
            destination.unlink()
        temp_path.replace(destination)
        logger.info("YOLO model downloaded to %s", destination)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _sha256_matches(path: Path, expected_sha256: str) -> bool:
    """Return True if the file's SHA-256 matches the expected digest."""
    checksum = _sha256_file(path)
    return checksum == _normalize_sha256(expected_sha256)


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 for a file path."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_DOWNLOAD_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_sha256(value: str) -> str:
    """Normalize SHA-256 strings by stripping prefixes and whitespace."""
    normalized = value.strip().lower()
    if normalized.startswith("sha256:"):
        return normalized.split("sha256:", 1)[1]
    return normalized
