"""Performance test for YOLODetector latency."""

from __future__ import annotations

import statistics
import time

import pytest

pytest.importorskip("onnxruntime")


@pytest.mark.asyncio
async def test_yolo_median_latency_10_runs(sample_image, yolo_detector):
    timings = []
    for _ in range(10):
        start = time.perf_counter()
        await yolo_detector.detect(sample_image)
        timings.append((time.perf_counter() - start) * 1000)

    median_ms = statistics.median(timings)
    assert median_ms < 100, f"Median YOLO latency {median_ms:.2f}ms"
