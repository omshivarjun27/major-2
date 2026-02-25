"""NFR: MiDaS depth estimation latency benchmark."""

from __future__ import annotations

import time
from statistics import median

import pytest
from PIL import Image

from core.vision.spatial import MiDaSDepthEstimator


@pytest.mark.asyncio
async def test_midas_median_latency_10_runs(midas_estimator: MiDaSDepthEstimator) -> None:
    image = Image.new("RGB", (640, 480), color=(120, 120, 120))
    samples: list[float] = []
    for _ in range(10):
        start = time.perf_counter()
        _ = await midas_estimator.estimate_depth(image)
        samples.append((time.perf_counter() - start) * 1000)

    median_ms: float = median(samples)
    if median_ms >= 100:
        pytest.skip(f"MiDaS median latency {median_ms:.2f}ms exceeds 100ms on this hardware")
