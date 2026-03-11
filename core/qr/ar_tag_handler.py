"""
AR Tag Handler – detects ArUco / AprilTag markers from images.

Uses OpenCV's ArUco module (built-in since OpenCV 4.x).
This is a lightweight layer; heavy AR processing is out of scope.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger("ar-tag-handler")

# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------


@dataclass
class ARDetection:
    """Single AR marker detection."""

    marker_id: int
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    corners: Optional[np.ndarray] = None  # 4×2 corner points
    dictionary: str = "ARUCO_4X4_50"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "marker_id": self.marker_id,
            "bbox": self.bbox,
            "dictionary": self.dictionary,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

# Mapping of friendly names → OpenCV enum values.  Populated lazily to avoid
# import errors when cv2 is missing.
_ARUCO_DICTS: Dict[str, int] = {}


def _load_aruco_dicts():
    """Populate the dict mapping on first use."""
    if _ARUCO_DICTS:
        return
    try:
        import cv2

        candidates = {
            "ARUCO_4X4_50": getattr(cv2.aruco, "DICT_4X4_50", None),
            "ARUCO_4X4_100": getattr(cv2.aruco, "DICT_4X4_100", None),
            "ARUCO_5X5_50": getattr(cv2.aruco, "DICT_5X5_50", None),
            "ARUCO_6X6_50": getattr(cv2.aruco, "DICT_6X6_50", None),
            "ARUCO_ORIGINAL": getattr(cv2.aruco, "DICT_ARUCO_ORIGINAL", None),
        }
        for name, val in candidates.items():
            if val is not None:
                _ARUCO_DICTS[name] = val
    except ImportError:
        logger.warning("OpenCV ArUco module not available")


class ARTagHandler:
    """
    Detect ArUco markers in a camera frame.

    The handler is intentionally lightweight — it returns marker IDs
    and bounding boxes so higher-level code can map them to actions.
    """

    def __init__(self, dictionary: str = "ARUCO_4X4_50") -> None:
        self._ready = False
        self._dict_name = dictionary

        _load_aruco_dicts()

        try:
            import cv2

            dict_id = _ARUCO_DICTS.get(dictionary)
            if dict_id is None:
                dict_id = _ARUCO_DICTS.get("ARUCO_4X4_50")
                self._dict_name = "ARUCO_4X4_50"

            if dict_id is not None:
                self._aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
                self._aruco_params = cv2.aruco.DetectorParameters()
                # OpenCV 4.7+ has ArucoDetector class
                if hasattr(cv2.aruco, "ArucoDetector"):
                    self._detector = cv2.aruco.ArucoDetector(
                        self._aruco_dict, self._aruco_params
                    )
                else:
                    self._detector = None  # will use legacy API
                self._ready = True
                logger.info(f"AR tag handler initialised (dict={self._dict_name})")
            else:
                logger.warning("No ArUco dictionaries available in OpenCV build")
        except Exception as exc:
            logger.warning(f"AR tag handler init failed: {exc}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, image: Image.Image) -> List[ARDetection]:
        """Detect ArUco markers in a PIL Image."""
        if not self._ready:
            return []

        import cv2

        start = time.time()
        arr = np.array(image)
        if len(arr.shape) == 3 and arr.shape[2] == 4:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
        elif len(arr.shape) == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr

        # Detect
        if self._detector is not None:
            corners, ids, _ = self._detector.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(
                gray, self._aruco_dict, parameters=self._aruco_params
            )

        results: List[ARDetection] = []
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                pts = corners[i].reshape(-1, 2)
                x_min, y_min = pts.min(axis=0).astype(int)
                x_max, y_max = pts.max(axis=0).astype(int)
                results.append(
                    ARDetection(
                        marker_id=int(marker_id),
                        bbox=(int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)),
                        corners=pts,
                        dictionary=self._dict_name,
                    )
                )

        elapsed_ms = (time.time() - start) * 1000
        if results:
            logger.info(f"AR detect: {len(results)} marker(s) in {elapsed_ms:.0f}ms")
        return results

    async def detect_async(self, image: Image.Image) -> List[ARDetection]:
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.detect, image)
