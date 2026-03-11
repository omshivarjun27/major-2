"""
Braille Capture
===============

Data-collection mode to capture high-res frames optimised for braille.
Provides lighting/capture hints, saves standardised dataset items.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("braille-capture")

try:
    import cv2
    CV2 = True
except ImportError:
    CV2 = False


@dataclass
class CaptureHints:
    """Hints returned to the user for optimal braille capture."""

    brightness_ok: bool = True
    contrast_ok: bool = True
    focus_ok: bool = True
    angle_ok: bool = True
    messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brightness_ok": self.brightness_ok,
            "contrast_ok": self.contrast_ok,
            "focus_ok": self.focus_ok,
            "angle_ok": self.angle_ok,
            "messages": self.messages,
        }


@dataclass
class DatasetItem:
    """A single braille dataset sample."""

    image_path: str
    meta_path: str
    timestamp: str
    capture_hints: CaptureHints
    ground_truth: Optional[str] = None
    consent_given: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_path": self.image_path,
            "meta_path": self.meta_path,
            "timestamp": self.timestamp,
            "capture_hints": self.capture_hints.to_dict(),
            "ground_truth": self.ground_truth,
            "consent_given": self.consent_given,
        }


class BrailleCapture:
    """Data-collection mode for braille images.

    Usage::

        cap = BrailleCapture(output_dir="./data/braille_dataset")
        hints = cap.analyse_frame(frame)
        if hints.brightness_ok and hints.contrast_ok:
            item = await cap.save(frame, ground_truth="hello")
    """

    DEFAULT_DIR = "./data/braille_dataset"

    def __init__(self, output_dir: Optional[str] = None):
        self._output_dir = Path(output_dir or self.DEFAULT_DIR)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._items_saved = 0

    # ── Analysis ──────────────────────────────────────────────────

    def analyse_frame(self, frame: np.ndarray) -> CaptureHints:
        """Evaluate whether the frame is suitable for braille capture.

        Returns lighting, contrast, focus, and angle hints.
        """
        hints = CaptureHints()

        if not CV2:
            hints.messages.append("OpenCV not available — skipping quality checks.")
            return hints

        gray = frame if len(frame.shape) == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Brightness
        mean_val = float(np.mean(gray))
        if mean_val < 60:
            hints.brightness_ok = False
            hints.messages.append(
                "Image is too dark. Move to a brighter area or turn on a light."
            )
        elif mean_val > 220:
            hints.brightness_ok = False
            hints.messages.append(
                "Image is overexposed. Reduce direct light or move the camera."
            )

        # Contrast (standard-deviation of pixel values)
        std_val = float(np.std(gray))
        if std_val < 25:
            hints.contrast_ok = False
            hints.messages.append(
                "Low contrast detected. Tilt the surface slightly to cast shadows on braille dots."
            )

        # Focus (Laplacian variance)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if lap_var < 50:
            hints.focus_ok = False
            hints.messages.append(
                "Image appears blurry. Hold the camera steady closer to the braille surface."
            )

        # Angle heuristic: check horizontal line dominance
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 40, minLineLength=30, maxLineGap=10)
        if lines is not None and len(lines) > 3:
            angles = []
            for ln in lines:
                x1, y1, x2, y2 = ln[0]
                a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                angles.append(abs(a))
            median_a = float(np.median(angles))
            if median_a > 15 and median_a < 75:
                hints.angle_ok = False
                hints.messages.append(
                    "Camera angle may be skewed. Try to hold the camera parallel to the braille surface."
                )

        if not hints.messages:
            hints.messages.append("Capture quality looks good. Ready to capture.")

        return hints

    # ── Save ──────────────────────────────────────────────────────

    async def save(
        self,
        frame: np.ndarray,
        ground_truth: Optional[str] = None,
        consent_given: bool = False,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> DatasetItem:
        """Save a frame as a braille dataset item.

        Args:
            frame: BGR or grayscale image.
            ground_truth: Known text (for supervised training).
            consent_given: User consented to data storage.
            extra_meta: Additional metadata.
        """
        item_id = uuid.uuid4().hex[:12]
        ts = datetime.utcnow().isoformat() + "Z"

        img_name = f"{item_id}.png"
        meta_name = f"{item_id}.json"

        img_path = self._output_dir / img_name
        meta_path = self._output_dir / meta_name

        hints = self.analyse_frame(frame)

        loop = asyncio.get_event_loop()

        # Save image
        if CV2:
            await loop.run_in_executor(None, cv2.imwrite, str(img_path), frame)
        else:
            from PIL import Image as PILImage

            img = PILImage.fromarray(frame)
            await loop.run_in_executor(None, img.save, str(img_path))

        # Save metadata
        meta = {
            "id": item_id,
            "timestamp": ts,
            "ground_truth": ground_truth,
            "consent_given": consent_given,
            "capture_hints": hints.to_dict(),
            "image_shape": list(frame.shape),
            **(extra_meta or {}),
        }
        await loop.run_in_executor(
            None, lambda: meta_path.write_text(json.dumps(meta, indent=2))
        )

        self._items_saved += 1
        logger.info("Braille dataset item saved: %s (total=%d)", item_id, self._items_saved)

        return DatasetItem(
            image_path=str(img_path),
            meta_path=str(meta_path),
            timestamp=ts,
            capture_hints=hints,
            ground_truth=ground_truth,
            consent_given=consent_given,
        )

    @property
    def items_saved(self) -> int:
        return self._items_saved
