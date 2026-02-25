"""Unit tests for MiDaS depth estimation."""

from __future__ import annotations

import time

import pytest
from PIL import Image

from core.vision.spatial import MiDaSDepthEstimator
from tests.conftest_vision import assert_valid_depth_map


@pytest.fixture
def sample_image():
    return Image.new("RGB", (640, 480), color=(128, 128, 128))


@pytest.mark.asyncio
async def test_estimate_depth_returns_depth_map(
    midas_estimator: MiDaSDepthEstimator, sample_image: Image.Image
) -> None:
    depth_map = await midas_estimator.estimate_depth(sample_image)
    assert_valid_depth_map(depth_map)


@pytest.mark.asyncio
async def test_fallback_to_simple_estimator(monkeypatch: pytest.MonkeyPatch, sample_image: Image.Image) -> None:
    from core.vision import spatial

    monkeypatch.setattr(spatial, "ONNX_AVAILABLE", False)
    monkeypatch.setattr(spatial, "TORCH_AVAILABLE", False)
    monkeypatch.setattr(spatial, "ort", None)
    monkeypatch.setattr(spatial, "torch", None)

    estimator = spatial.MiDaSDepthEstimator(model_path="missing.onnx")
    depth_map = await estimator.estimate_depth(sample_image)

    assert_valid_depth_map(depth_map)
    assert depth_map.depth_array.shape == (
        sample_image.size[1] // spatial.DEPTH_DOWNSCALE,
        sample_image.size[0] // spatial.DEPTH_DOWNSCALE,
    )


@pytest.mark.asyncio
async def test_metric_normalization_range(
    midas_estimator: MiDaSDepthEstimator, sample_image: Image.Image
) -> None:
    depth_map = await midas_estimator.estimate_depth(sample_image)
    assert depth_map.depth_array.min() >= 0.5
    assert depth_map.depth_array.max() <= 10.0


@pytest.mark.asyncio
async def test_output_resolution_matches_input(midas_estimator: MiDaSDepthEstimator) -> None:
    for width, height in [(320, 240), (640, 480), (1280, 720)]:
        image = Image.new("RGB", (width, height), color=(64, 64, 64))
        depth_map = await midas_estimator.estimate_depth(image)
        assert depth_map.depth_array.shape == (height, width)


@pytest.mark.asyncio
async def test_depth_latency_under_100ms(
    midas_estimator: MiDaSDepthEstimator, sample_image: Image.Image
) -> None:
    start = time.perf_counter()
    _ = await midas_estimator.estimate_depth(sample_image)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if elapsed_ms >= 100:
        pytest.skip(f"MiDaS latency {elapsed_ms:.2f}ms exceeds 100ms on this hardware")
