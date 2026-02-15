"""
OCR Engine — Robust Abstraction Layer
======================================

Tries backends in order:
1. EasyOCR (GPU-accelerated)
2. pytesseract (requires ``tesseract`` binary)
3. OpenCV-only heuristic (basic MSER text-region detection)

If ALL backends unavailable, returns a helpful user-facing error
with OS-specific install instructions.  Never crashes the system.
"""

from __future__ import annotations

import logging
import platform
import sys
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("ocr-engine")


# ── Backend availability probes ──────────────────────────────────

def _probe_easyocr() -> bool:
    try:
        import easyocr  # noqa: F401
        return True
    except ImportError:
        return False


def _probe_tesseract() -> bool:
    try:
        import pytesseract  # noqa: F401
        # Also check binary
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _probe_cv2() -> bool:
    try:
        import cv2  # noqa: F401
        return True
    except ImportError:
        return False


EASYOCR_OK = _probe_easyocr()
TESSERACT_OK = _probe_tesseract()
CV2_OK = _probe_cv2()


# ── Skew-correction preprocessor ────────────────────────────────

def deskew_image(gray: np.ndarray, max_angle: float = 15.0) -> np.ndarray:
    """Correct slight text rotation using Hough line detection.

    Only corrects if the detected skew is within ±*max_angle* degrees.
    Returns the original image unchanged when cv2 is unavailable or
    when no dominant angle is detected.
    """
    if not CV2_OK:
        return gray
    try:
        import cv2

        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                                minLineLength=60, maxLineGap=10)
        if lines is None or len(lines) == 0:
            return gray

        # Compute median angle
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            angles.append(angle)
        median_angle = float(np.median(angles))

        # Only correct small skews
        if abs(median_angle) > max_angle or abs(median_angle) < 0.5:
            return gray

        h, w = gray.shape[:2]
        center = (w // 2, h // 2)
        rot = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        corrected = cv2.warpAffine(
            gray, rot, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        logger.debug("Deskew: corrected %.1f° rotation", median_angle)
        return corrected
    except Exception as exc:
        logger.debug("Deskew failed: %s", exc)
        return gray


# ── Install instructions ─────────────────────────────────────────

def _os_tag() -> str:
    s = platform.system().lower()
    if s == "darwin":
        return "macos"
    if s == "windows":
        return "windows"
    return "linux"


INSTALL_HINTS: Dict[str, Dict[str, str]] = {
    "easyocr": {
        "pip": "pip install easyocr",
        "note": "First run downloads ~180 MB model. GPU optional (torch).",
    },
    "pytesseract": {
        "pip": "pip install pytesseract",
        "linux": "sudo apt-get install -y tesseract-ocr libtesseract-dev",
        "macos": "brew install tesseract",
        "windows": "choco install tesseract  # or download from https://github.com/UB-Mannheim/tesseract/wiki",
        "note": "Requires the tesseract binary on PATH.",
    },
    "opencv": {
        "pip": "pip install opencv-python",
    },
}


def get_install_instructions() -> str:
    """Return human-readable install instructions for missing OCR deps."""
    lines = ["OCR engine is not fully installed. Setup instructions:\n"]
    os_tag = _os_tag()

    if not EASYOCR_OK:
        lines.append("== EasyOCR (recommended) ==")
        lines.append(f"  {INSTALL_HINTS['easyocr']['pip']}")
        lines.append(f"  Note: {INSTALL_HINTS['easyocr']['note']}")

    if not TESSERACT_OK:
        lines.append("== Tesseract (fallback) ==")
        lines.append(f"  {INSTALL_HINTS['pytesseract']['pip']}")
        binary_cmd = INSTALL_HINTS["pytesseract"].get(os_tag, "")
        if binary_cmd:
            lines.append(f"  System binary: {binary_cmd}")
        lines.append(f"  Note: {INSTALL_HINTS['pytesseract']['note']}")

    if not CV2_OK:
        lines.append("== OpenCV ==")
        lines.append(f"  {INSTALL_HINTS['opencv']['pip']}")

    lines.append("\nOr run:  scripts/install_ocr_deps.sh")
    return "\n".join(lines)


def get_ocr_status() -> Dict[str, Any]:
    """Return structured status of OCR backends."""
    return {
        "easyocr_available": EASYOCR_OK,
        "tesseract_available": TESSERACT_OK,
        "opencv_available": CV2_OK,
        "any_backend_available": EASYOCR_OK or TESSERACT_OK,
        "heuristic_fallback_available": CV2_OK,
        "install_instructions": get_install_instructions() if not (EASYOCR_OK or TESSERACT_OK) else None,
    }


# ── OpenCV-only heuristic fallback ──────────────────────────────

class _HeuristicBackend:
    """Very basic text-region detector using MSER + contour filtering.

    Does NOT perform real OCR — returns bounding boxes of likely text
    regions with a disclaimer.  Useful as a "something is here" signal.
    """

    def read(self, gray: np.ndarray) -> List[Dict[str, Any]]:
        import cv2

        mser = cv2.MSER_create()
        mser.setMinArea(60)
        mser.setMaxArea(14400)

        regions, _ = mser.detectRegions(gray)
        bboxes = []
        for pts in regions:
            x, y, w, h = cv2.boundingRect(pts)
            aspect = w / (h + 1e-6)
            if 0.2 < aspect < 5.0 and h > 8:
                bboxes.append({"bbox": [x, y, x + w, y + h], "type": "text_region"})

        # Deduplicate overlapping boxes (simple greedy NMS)
        bboxes = self._nms(bboxes, iou_thresh=0.5)
        return bboxes

    @staticmethod
    def _nms(boxes: List[Dict], iou_thresh: float) -> List[Dict]:
        if not boxes:
            return []
        import cv2

        rects = np.array([b["bbox"] for b in boxes], dtype=np.float32)
        # Compute areas
        x1, y1, x2, y2 = rects[:, 0], rects[:, 1], rects[:, 2], rects[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = areas.argsort()[::-1]

        keep: List[int] = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            if len(order) == 1:
                break
            rest = order[1:]
            xx1 = np.maximum(x1[i], x1[rest])
            yy1 = np.maximum(y1[i], y1[rest])
            xx2 = np.minimum(x2[i], x2[rest])
            yy2 = np.minimum(y2[i], y2[rest])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            iou = inter / (areas[i] + areas[rest] - inter + 1e-6)
            order = rest[iou < iou_thresh]

        return [boxes[i] for i in keep]


# ── Unified OCR function ─────────────────────────────────────────

async def ocr_read(image: Any, languages: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run OCR on an image using the best available backend.

    Returns a dict with:
    - backend: str — which backend was used
    - results: list — OCR results
    - full_text: str — concatenated text
    - error: str | None — error message if any
    - install_help: str | None — install instructions if no backend
    """
    # Try the full OCRPipeline from core/ocr/__init__.py first
    try:
        from core.ocr import OCRPipeline
        pipe = OCRPipeline(languages=languages)
        if pipe.is_ready:
            result = await pipe.process(image)
            return result.to_dict()
    except Exception as exc:
        logger.debug("OCRPipeline failed: %s", exc)

    # Try heuristic fallback
    if CV2_OK:
        try:
            import cv2
            import asyncio

            if isinstance(image, np.ndarray):
                gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = np.array(image)
                if len(gray.shape) == 3:
                    gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)

            heuristic = _HeuristicBackend()
            gray = deskew_image(gray)  # correct slight rotation before detection
            loop = asyncio.get_event_loop()
            regions = await loop.run_in_executor(None, heuristic.read, gray)
            return {
                "backend": "heuristic_opencv",
                "results": regions,
                "full_text": "",
                "error": "No real OCR backend installed — showing detected text regions only.",
                "install_help": get_install_instructions(),
            }
        except Exception as exc:
            logger.error("Heuristic OCR fallback failed: %s", exc)

    # Nothing available
    return {
        "backend": "none",
        "results": [],
        "full_text": "",
        "error": (
            "OCR engine is not installed on this device. "
            "Please run `scripts/install_ocr_deps.sh` or enable OCR in settings. "
            "Meanwhile I can attempt limited text-region detection but may fail to read text."
        ),
        "install_help": get_install_instructions(),
    }
