"""Unit tests for EdgeAwareSegmenter segmentation masks."""

# pyright: reportAny=false

from __future__ import annotations

import time

import numpy as np
import pytest

from core.vision.spatial import EdgeAwareSegmenter
from shared.schemas import BoundingBox, Detection


@pytest.fixture
def sample_image() -> np.ndarray:
    """Provide a synthetic 640x480 RGB image."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def single_detection() -> list[Detection]:
    """Provide a single detection for segmentation."""
    return [
        Detection(
            id="det_1",
            class_name="chair",
            confidence=0.9,
            bbox=BoundingBox(100, 100, 200, 200),
        )
    ]


def _two_detections() -> list[Detection]:
    return [
        Detection(
            id="det_1",
            class_name="chair",
            confidence=0.9,
            bbox=BoundingBox(100, 100, 200, 200),
        ),
        Detection(
            id="det_2",
            class_name="table",
            confidence=0.85,
            bbox=BoundingBox(300, 200, 420, 320),
        ),
    ]


@pytest.mark.asyncio
async def test_mask_shape_matches_downscale(sample_image: np.ndarray, single_detection: list[Detection]) -> None:
    segmenter = EdgeAwareSegmenter()
    masks = await segmenter.segment(sample_image, single_detection)

    assert len(masks) == 1
    mask = masks[0].mask
    assert isinstance(mask, np.ndarray)
    assert mask.dtype == np.uint8
    assert mask.shape == (120, 160)
    invalid_values = (mask != 0) & (mask != 255)
    invalid_count = 0
    for row in invalid_values:
        for value in row:
            if value:
                invalid_count += 1
    assert invalid_count == 0


@pytest.mark.asyncio
async def test_boundary_confidence_range(sample_image: np.ndarray, single_detection: list[Detection]) -> None:
    segmenter = EdgeAwareSegmenter()
    masks = await segmenter.segment(sample_image, single_detection)

    assert len(masks) == 1
    confidence = masks[0].boundary_confidence
    assert 0.5 <= confidence <= 0.95


@pytest.mark.asyncio
async def test_empty_detection_list(sample_image: np.ndarray) -> None:
    segmenter = EdgeAwareSegmenter()
    masks = await segmenter.segment(sample_image, [])

    assert masks == []


@pytest.mark.asyncio
async def test_multi_object_masks(sample_image: np.ndarray) -> None:
    segmenter = EdgeAwareSegmenter()
    detections = _two_detections()
    masks = await segmenter.segment(sample_image, detections)

    assert len(masks) == len(detections)
    for mask in masks:
        assert mask.mask is not None
        assert isinstance(mask.mask, np.ndarray)


@pytest.mark.asyncio
async def test_segment_latency_under_50ms(sample_image: np.ndarray) -> None:
    segmenter = EdgeAwareSegmenter()
    detections = _two_detections()

    start = time.perf_counter()
    _ = await segmenter.segment(sample_image, detections)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 50, f"Segmentation took {elapsed_ms:.2f}ms"
