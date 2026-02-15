"""
Embossing Guidance
==================

Layout guidance & verification for tactile print / embossing.
Outputs printable layout files and verification overlays.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("embossing-guidance")

try:
    import cv2
    CV2 = True
except ImportError:
    CV2 = False

from .braille_classifier import CHAR_TO_DOTS


@dataclass
class LayoutVerification:
    """Result of embossing layout verification."""

    valid: bool = True
    issues: List[str] = field(default_factory=list)
    dot_positions: List[Dict[str, Any]] = field(default_factory=list)
    overlay_image: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": self.issues,
            "dot_count": len(self.dot_positions),
        }


class EmbossingGuide:
    """Generate and verify braille embossing layouts.

    Produces:
    - Dot position coordinates for embossing machines
    - Printable overlay images for visual verification
    - Layout validation (spacing, alignment checks)

    Standard braille cell dimensions (in mm):
    - Dot diameter: 1.5 mm
    - Dot spacing (within cell): 2.5 mm horizontal, 2.5 mm vertical
    - Cell spacing: 6.1 mm horizontal, 10.0 mm vertical
    """

    # Standard dimensions in mm
    DOT_DIAMETER_MM = 1.5
    DOT_SPACING_H_MM = 2.5
    DOT_SPACING_V_MM = 2.5
    CELL_SPACING_H_MM = 6.1
    CELL_SPACING_V_MM = 10.0

    def __init__(self, dpi: int = 300):
        self._dpi = dpi
        self._mm_to_px = dpi / 25.4  # 1 inch = 25.4 mm

    def text_to_layout(
        self,
        text: str,
        margin_mm: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """Convert text to braille dot positions for embossing.

        Args:
            text: Plain text to convert to braille.
            margin_mm: Page margin in mm.

        Returns:
            List of dot position dicts with x_mm, y_mm coordinates.
        """
        positions: List[Dict[str, Any]] = []
        col = 0
        row = 0

        for ch in text.lower():
            if ch == "\n":
                row += 1
                col = 0
                continue

            dots_tuple = CHAR_TO_DOTS.get(ch)
            if dots_tuple is None:
                col += 1
                continue

            # Calculate cell origin
            cell_x = margin_mm + col * self.CELL_SPACING_H_MM
            cell_y = margin_mm + row * self.CELL_SPACING_V_MM

            # Place dots
            for idx, active in enumerate(dots_tuple):
                if not active:
                    continue
                # Dot numbering: 0,1,2 = left column top-to-bottom
                #                3,4,5 = right column top-to-bottom
                dot_col = 0 if idx < 3 else 1
                dot_row = idx % 3
                x = cell_x + dot_col * self.DOT_SPACING_H_MM
                y = cell_y + dot_row * self.DOT_SPACING_V_MM
                positions.append({
                    "x_mm": round(x, 2),
                    "y_mm": round(y, 2),
                    "char": ch,
                    "dot_index": idx + 1,
                    "cell_row": row,
                    "cell_col": col,
                })

            col += 1

        return positions

    def generate_overlay(
        self,
        text: str,
        page_width_mm: float = 210.0,  # A4
        page_height_mm: float = 297.0,
        margin_mm: float = 10.0,
    ) -> np.ndarray:
        """Generate a printable braille overlay image.

        Args:
            text: Text to render as braille.
            page_width_mm: Page width.
            page_height_mm: Page height.
            margin_mm: Page margin.

        Returns:
            BGR image (numpy array) of the braille layout.
        """
        positions = self.text_to_layout(text, margin_mm)

        w = int(page_width_mm * self._mm_to_px)
        h = int(page_height_mm * self._mm_to_px)
        img = np.ones((h, w, 3), dtype=np.uint8) * 255  # White page

        dot_radius_px = max(1, int(self.DOT_DIAMETER_MM / 2 * self._mm_to_px))

        for pos in positions:
            px = int(pos["x_mm"] * self._mm_to_px)
            py = int(pos["y_mm"] * self._mm_to_px)
            if CV2:
                cv2.circle(img, (px, py), dot_radius_px, (0, 0, 0), -1)
            else:
                # Fallback: draw a small square
                r = dot_radius_px
                img[max(0, py - r):py + r, max(0, px - r):px + r] = 0

        return img

    def verify_layout(
        self,
        positions: List[Dict[str, Any]],
        tolerance_mm: float = 0.5,
    ) -> LayoutVerification:
        """Verify that dot positions meet braille spacing standards.

        Args:
            positions: Dot positions from text_to_layout.
            tolerance_mm: Acceptable deviation from standard.

        Returns:
            LayoutVerification with issues.
        """
        result = LayoutVerification(dot_positions=positions)

        if not positions:
            result.valid = False
            result.issues.append("No dots in layout.")
            return result

        # Check dot spacing within cells
        cells: Dict[Tuple[int, int], List[Dict]] = {}
        for pos in positions:
            key = (pos["cell_row"], pos["cell_col"])
            cells.setdefault(key, []).append(pos)

        for key, cell_dots in cells.items():
            if len(cell_dots) < 2:
                continue
            for i, d1 in enumerate(cell_dots):
                for d2 in cell_dots[i + 1:]:
                    dist = ((d1["x_mm"] - d2["x_mm"]) ** 2 + (d1["y_mm"] - d2["y_mm"]) ** 2) ** 0.5
                    if dist < self.DOT_SPACING_H_MM - tolerance_mm:
                        result.issues.append(
                            f"Dots too close in cell ({key}): {dist:.2f}mm (min {self.DOT_SPACING_H_MM}mm)"
                        )
                        result.valid = False

        if not result.issues:
            result.issues.append("Layout passes all spacing checks.")

        return result
