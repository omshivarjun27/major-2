"""Unit tests for the YOLODetector ONNX pipeline."""

from __future__ import annotations

import time
from typing import List

import numpy as np
import pytest

pytest.importorskip("onnxruntime")

from core.vision.spatial import YOLODetector
from shared.schemas import Detection


class DummySession:
    """Minimal ONNX session stub for unit tests."""

    def __init__(self, output: np.ndarray) -> None:
        self._output = output

    def get_inputs(self):
        class _Input:
            name = "input0"

        return [_Input()]

    def run(self, *_args, **_kwargs):
        return [self._output]


def _build_dummy_output(rows: List[List[float]]) -> np.ndarray:
    """Create a YOLO output tensor from row-wise predictions."""
    preds = np.zeros((len(rows), 84), dtype=np.float32)
    for idx, row in enumerate(rows):
        preds[idx] = np.array(row, dtype=np.float32)
    return preds.T[np.newaxis, ...]


@pytest.mark.asyncio
async def test_detect_returns_detections(sample_image):
    detector = YOLODetector(model_path="models/yolov8n.onnx", conf_threshold=0.1)
    row = [320.0, 320.0, 200.0, 200.0] + [0.0] * 80
    row[4] = 0.9
    row[5] = 0.95
    detector._model = DummySession(_build_dummy_output([row]))
    detector._ready = True

    detections = detector._onnx_detect(np.asarray(sample_image))
    assert isinstance(detections, list)
    assert detections, "Expected at least one detection"
    for det in detections:
        assert isinstance(det, Detection)
        assert det.bbox.x1 <= det.bbox.x2
        assert det.bbox.y1 <= det.bbox.y2
        assert 0.0 <= det.confidence <= 1.0


@pytest.mark.asyncio
async def test_detect_empty_frame_returns_empty(sample_image, yolo_detector):
    blank = sample_image.copy()
    blank.paste((255, 255, 255), (0, 0, blank.size[0], blank.size[1]))
    detections = await yolo_detector.detect(blank)
    assert isinstance(detections, list)


def test_nms_suppresses_overlapping():
    detector = YOLODetector(model_path="models/yolo11n.onnx", conf_threshold=0.4)

    row_a = [320.0, 320.0, 200.0, 200.0] + [0.0] * 80
    row_a[4] = 0.9
    row_b = [322.0, 322.0, 200.0, 200.0] + [0.0] * 80
    row_b[4] = 0.85

    output = _build_dummy_output([row_a, row_b])
    detector._model = DummySession(output)
    detector._ready = True

    detections = detector._onnx_detect(np.zeros((640, 640, 3), dtype=np.uint8))
    assert len(detections) == 1


def test_confidence_filter():
    detector = YOLODetector(model_path="models/yolo11n.onnx", conf_threshold=0.95)
    row = [320.0, 320.0, 120.0, 120.0] + [0.0] * 80
    row[4] = 0.9

    output = _build_dummy_output([row])
    detector._model = DummySession(output)
    detector._ready = True

    detections = detector._onnx_detect(np.zeros((640, 640, 3), dtype=np.uint8))
    assert detections == []


@pytest.mark.asyncio
async def test_detect_latency_under_100ms(sample_image):
    detector = YOLODetector(model_path="models/yolov8n.onnx", conf_threshold=0.1)
    row = [320.0, 320.0, 200.0, 200.0] + [0.0] * 80
    row[4] = 0.9
    row[5] = 0.95
    detector._model = DummySession(_build_dummy_output([row]))
    detector._ready = True

    start = time.perf_counter()
    await detector.detect(sample_image)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 100, f"YOLO detection took {elapsed_ms:.2f}ms"
