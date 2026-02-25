"""Shared vision fixtures for tests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from core.vision.model_download import MIDAS_SMALL_SHA256
from core.vision.spatial import MiDaSDepthEstimator, YOLODetector
from shared.schemas import DepthMap


@pytest.fixture(scope="session")
def midas_estimator() -> MiDaSDepthEstimator:
    """Provide a MiDaS estimator if onnxruntime is available."""
    pytest.importorskip("onnxruntime")

    model_path = Path("models/midas_v21_small_256.onnx")
    if not model_path.exists():
        pytest.skip("MiDaS model not available")
    if _sha256_file(model_path) != MIDAS_SMALL_SHA256:
        pytest.skip("MiDaS model checksum mismatch")

    estimator = MiDaSDepthEstimator(model_path=str(model_path))
    if not estimator.is_ready():
        pytest.skip("MiDaS model not available")

    return estimator


@pytest.fixture(scope="session")
def sample_image() -> Any:
    """Provide a synthetic RGB image for detector tests."""
    pytest.importorskip("onnxruntime")
    from PIL import Image as PILImage

    return PILImage.new("RGB", (640, 480), color=(0, 0, 0))


@pytest.fixture(scope="session")
def yolo_detector() -> YOLODetector:
    """Provide YOLO detector if ONNX model is available."""
    pytest.importorskip("onnxruntime")
    model_path = Path("models/yolov8n.onnx")
    if not model_path.exists():
        pytest.skip("YOLO model not available")

    detector = YOLODetector(model_path=str(model_path), conf_threshold=0.5)
    if not detector.is_ready():
        pytest.skip("YOLO detector not ready")
    return detector


def assert_valid_depth_map(depth_map: "DepthMap") -> None:
    """Validate DepthMap invariants."""
    assert depth_map.depth_array is not None
    assert isinstance(depth_map.depth_array, np.ndarray)
    assert depth_map.depth_array.dtype == np.float32
    assert depth_map.depth_array.ndim == 2
    assert depth_map.min_depth <= depth_map.max_depth
    assert depth_map.min_depth >= 0


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
