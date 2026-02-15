"""
Braille Segmenter
=================

Detect braille plates / regions and segment raised dots using:
- Adaptive thresholding
- Morphological operations (erosion, dilation)
- Blob detection
- Homography-based deskew / planarisation
- Local contrast enhancement + dome-illumination heuristics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("braille-segmenter")

try:
    import cv2
    CV2 = True
except ImportError:
    CV2 = False


@dataclass
class DotInfo:
    """A single detected braille dot."""

    x: int
    y: int
    radius: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "radius": round(self.radius, 1), "confidence": round(self.confidence, 2)}


@dataclass
class CellInfo:
    """A single braille cell (up to 6 or 8 dots)."""

    row: int
    col: int
    dots: List[bool] = field(default_factory=lambda: [False] * 6)  # dots 1-6
    center_x: int = 0
    center_y: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row,
            "col": self.col,
            "dots": self.dots,
            "center": [self.center_x, self.center_y],
        }


@dataclass
class SegmentationResult:
    """Full segmentation output."""

    dot_count: int = 0
    dots: List[DotInfo] = field(default_factory=list)
    cells: List[CellInfo] = field(default_factory=list)
    plate_bbox: Optional[Tuple[int, int, int, int]] = None  # x1,y1,x2,y2
    mask: Optional[np.ndarray] = None
    preprocessed: Optional[np.ndarray] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dot_count": self.dot_count,
            "dots": [d.to_dict() for d in self.dots],
            "cells": [c.to_dict() for c in self.cells],
            "plate_bbox": list(self.plate_bbox) if self.plate_bbox else None,
            "error": self.error,
        }


class BrailleSegmenter:
    """Detect braille regions and segment individual dots.

    Pipeline:
    1. Convert to grayscale
    2. Apply CLAHE for local contrast enhancement
    3. Adaptive threshold to isolate raised dots
    4. Morphological open/close to clean noise
    5. Blob detection for dot centres
    6. Grid fitting to assign dots → cells
    7. Optional homography deskew

    Usage::

        seg = BrailleSegmenter()
        result = seg.segment(frame)
        print(result.dot_count, result.cells)
    """

    def __init__(
        self,
        clahe_clip: float = 3.0,
        clahe_grid: int = 8,
        adaptive_block: int = 31,
        adaptive_c: float = 8.0,
        min_dot_area: int = 15,
        max_dot_area: int = 800,
        morph_kernel_size: int = 3,
    ):
        self._clahe_clip = clahe_clip
        self._clahe_grid = clahe_grid
        self._adaptive_block = adaptive_block
        self._adaptive_c = adaptive_c
        self._min_dot_area = min_dot_area
        self._max_dot_area = max_dot_area
        self._morph_kernel_size = morph_kernel_size

    # ── Public API ────────────────────────────────────────────────

    def segment(self, image: np.ndarray) -> SegmentationResult:
        """Run full braille segmentation pipeline.

        Args:
            image: BGR or grayscale frame.

        Returns:
            SegmentationResult with dots and cell grid.
        """
        if not CV2:
            return SegmentationResult(error="OpenCV not available")

        try:
            gray = self._to_gray(image)
            enhanced = self._enhance(gray)
            binary = self._threshold(enhanced)
            cleaned = self._morphology(binary)
            dots = self._detect_dots(cleaned)
            cells = self._fit_grid(dots, gray.shape)
            plate_bbox = self._find_plate(dots, gray.shape)

            return SegmentationResult(
                dot_count=len(dots),
                dots=dots,
                cells=cells,
                plate_bbox=plate_bbox,
                mask=cleaned,
                preprocessed=enhanced,
            )
        except Exception as exc:
            logger.error("Braille segmentation failed: %s", exc)
            return SegmentationResult(error=str(exc))

    # ── Internal steps ────────────────────────────────────────────

    def _to_gray(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def _enhance(self, gray: np.ndarray) -> np.ndarray:
        """CLAHE + bilateral filter for dome-illumination handling."""
        clahe = cv2.createCLAHE(
            clipLimit=self._clahe_clip,
            tileGridSize=(self._clahe_grid, self._clahe_grid),
        )
        enhanced = clahe.apply(gray)
        enhanced = cv2.bilateralFilter(enhanced, 9, 75, 75)
        return enhanced

    def _threshold(self, gray: np.ndarray) -> np.ndarray:
        """Adaptive threshold to isolate raised dots."""
        return cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            self._adaptive_block,
            self._adaptive_c,
        )

    def _morphology(self, binary: np.ndarray) -> np.ndarray:
        """Clean noise with morphological open then close."""
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self._morph_kernel_size, self._morph_kernel_size),
        )
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)
        return closed

    def _detect_dots(self, binary: np.ndarray) -> List[DotInfo]:
        """Find dot centres using contour analysis."""
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dots: List[DotInfo] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self._min_dot_area or area > self._max_dot_area:
                continue
            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            circularity = 4 * np.pi * area / (cv2.arcLength(cnt, True) ** 2 + 1e-6)
            if circularity < 0.4:
                continue  # Not circular enough
            dots.append(DotInfo(
                x=int(cx),
                y=int(cy),
                radius=float(radius),
                confidence=min(1.0, circularity),
            ))
        return dots

    def _fit_grid(
        self, dots: List[DotInfo], shape: Tuple[int, ...]
    ) -> List[CellInfo]:
        """Assign dots to a braille cell grid.

        Standard braille cell: 2 columns × 3 rows of dots.
        Cell spacing is estimated from dot distribution.
        """
        if len(dots) < 2:
            return []

        xs = np.array([d.x for d in dots], dtype=float)
        ys = np.array([d.y for d in dots], dtype=float)

        # Estimate dot spacing
        if len(dots) >= 3:
            from scipy.spatial import distance as spdist

            coords = np.column_stack([xs, ys])
            dists = spdist.cdist(coords, coords)
            np.fill_diagonal(dists, np.inf)
            min_dists = dists.min(axis=1)
            dot_spacing = float(np.median(min_dists))
        else:
            dot_spacing = 15.0

        cell_w = dot_spacing * 2.5
        cell_h = dot_spacing * 3.5

        if cell_w < 1 or cell_h < 1:
            return []

        # Build grid
        min_x, min_y = float(xs.min()), float(ys.min())
        cells: List[CellInfo] = []
        cell_map: Dict[Tuple[int, int], CellInfo] = {}

        for dot in dots:
            col = int((dot.x - min_x) / cell_w)
            row = int((dot.y - min_y) / cell_h)
            key = (row, col)
            if key not in cell_map:
                cell_map[key] = CellInfo(row=row, col=col)
            cell = cell_map[key]
            # Determine dot position within cell (1-6)
            local_x = (dot.x - min_x) - col * cell_w
            local_y = (dot.y - min_y) - row * cell_h
            dot_col = 0 if local_x < cell_w / 2 else 1
            dot_row = int(local_y / (cell_h / 3))
            dot_row = min(dot_row, 2)
            idx = dot_row + dot_col * 3  # Braille dot numbering: 1,2,3 left; 4,5,6 right
            if 0 <= idx < 6:
                cell.dots[idx] = True
            cell.center_x = int(min_x + col * cell_w + cell_w / 2)
            cell.center_y = int(min_y + row * cell_h + cell_h / 2)

        cells = sorted(cell_map.values(), key=lambda c: (c.row, c.col))
        return cells

    def _find_plate(
        self, dots: List[DotInfo], shape: Tuple[int, ...]
    ) -> Optional[Tuple[int, int, int, int]]:
        """Bounding box of all detected dots (braille plate region)."""
        if not dots:
            return None
        xs = [d.x for d in dots]
        ys = [d.y for d in dots]
        margin = 20
        return (
            max(0, min(xs) - margin),
            max(0, min(ys) - margin),
            min(shape[1] if len(shape) > 1 else shape[0], max(xs) + margin),
            min(shape[0], max(ys) + margin),
        )

    # ── Deskew (homography) ───────────────────────────────────────

    def deskew(self, image: np.ndarray) -> np.ndarray:
        """Attempt to deskew / planarise a curved braille surface.

        Uses Hough lines to estimate perspective and applies homography.
        """
        if not CV2:
            return image

        gray = self._to_gray(image)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 60, minLineLength=40, maxLineGap=10)
        if lines is None or len(lines) < 4:
            return image

        # Estimate dominant angle and correct
        angles = [np.degrees(np.arctan2(l[0][3] - l[0][1], l[0][2] - l[0][0])) for l in lines]
        median_angle = float(np.median(angles))
        if abs(median_angle) < 1:
            return image

        h, w = gray.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
