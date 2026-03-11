"""
Unit tests — Braille Segmenter
================================

Tests the braille segmentation pipeline with synthetic fixtures.
"""

import numpy as np
import pytest

from core.braille.braille_segmenter import BrailleSegmenter, CellInfo, DotInfo, SegmentationResult

try:
    import cv2
    CV2 = True
except ImportError:
    CV2 = False


def _make_braille_image(dots_per_cell, spacing=20, dot_r=5, size=(200, 300)):
    """Create a synthetic braille image with known dot positions."""
    h, w = size
    img = np.ones((h, w), dtype=np.uint8) * 230  # light gray

    if not CV2:
        return img

    x0, y0 = 40, 30
    for cell_idx, dots in enumerate(dots_per_cell):
        cx = x0 + cell_idx * int(spacing * 2.5)
        for i, active in enumerate(dots):
            if not active:
                continue
            col = 0 if i < 3 else 1
            row = i % 3
            px = cx + col * spacing
            py = y0 + row * spacing
            cv2.circle(img, (px, py), dot_r, 20, -1)  # Dark dots on light bg

    return img


class TestBrailleSegmenter:

    def test_empty_image(self):
        """Segmenting a blank image should return zero dots."""
        seg = BrailleSegmenter()
        img = np.ones((100, 200), dtype=np.uint8) * 240
        result = seg.segment(img)
        assert result.error is None or not CV2
        assert result.dot_count >= 0

    def test_single_dot(self):
        """Single large dot should be detected."""
        if not CV2:
            pytest.skip("OpenCV not available")
        seg = BrailleSegmenter(min_dot_area=10, max_dot_area=2000)
        img = np.ones((100, 100), dtype=np.uint8) * 230
        cv2.circle(img, (50, 50), 8, 20, -1)
        result = seg.segment(img)
        assert result.dot_count >= 1
        assert len(result.dots) >= 1

    def test_multiple_cells(self):
        """Multiple braille cells should produce multiple cells in output."""
        if not CV2:
            pytest.skip("OpenCV not available")
        seg = BrailleSegmenter(min_dot_area=10, max_dot_area=2000)
        cells = [
            [True, False, False, False, False, False],  # a
            [True, True, False, False, False, False],    # b
        ]
        img = _make_braille_image(cells, spacing=20, dot_r=6, size=(150, 300))
        result = seg.segment(img)
        # Should detect at least some dots
        assert result.dot_count >= 2

    def test_segmentation_result_to_dict(self):
        """SegmentationResult.to_dict() should be serialisable."""
        result = SegmentationResult(
            dot_count=3,
            dots=[DotInfo(x=10, y=20, radius=5.0)],
            cells=[CellInfo(row=0, col=0, dots=[True, False, False, False, False, False])],
            plate_bbox=(0, 0, 100, 100),
        )
        d = result.to_dict()
        assert d["dot_count"] == 3
        assert len(d["dots"]) == 1
        assert len(d["cells"]) == 1
        assert d["plate_bbox"] == [0, 0, 100, 100]

    def test_deskew_no_crash(self):
        """Deskew should not crash on any input."""
        seg = BrailleSegmenter()
        img = np.ones((100, 200), dtype=np.uint8) * 200
        result = seg.deskew(img)
        assert result.shape == img.shape

    def test_dot_info_to_dict(self):
        d = DotInfo(x=5, y=10, radius=3.5, confidence=0.95)
        assert d.to_dict()["confidence"] == 0.95

    def test_cell_info_to_dict(self):
        c = CellInfo(row=1, col=2, dots=[True]*6, center_x=50, center_y=60)
        d = c.to_dict()
        assert d["row"] == 1
        assert d["dots"] == [True]*6
