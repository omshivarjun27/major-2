"""
QR Code Scanner – detects and reads QR codes from PIL images or raw frames.

Uses `pyzbar` (wraps zbar C library) for fast, dependency-light decoding.
Falls back to OpenCV's built-in QR detector when pyzbar is unavailable.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger("qr-scanner")

# ---------------------------------------------------------------------------
# Detection result
# ---------------------------------------------------------------------------


@dataclass
class QRDetection:
    """Single QR code detection result."""

    raw_data: str
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float = 1.0
    format_type: str = "QR"
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class QRScanner:
    """
    Camera-based QR / barcode detector.

    Priority:
     1. pyzbar  – faster, more formats
     2. cv2.QRCodeDetector – built-in fallback
    """

    def __init__(self) -> None:
        self._use_pyzbar: bool = False
        self._use_cv2: bool = False
        self._decode_fn = None

        # Try pyzbar first
        try:
            from pyzbar import pyzbar as _pyzbar  # noqa: F401

            self._use_pyzbar = True
            self._decode_fn = _pyzbar.decode
            logger.info("QR scanner initialised with pyzbar backend")
        except ImportError:
            pass

        # Fallback to OpenCV QR detector
        if not self._use_pyzbar:
            try:
                import cv2  # noqa: F401

                self._use_cv2 = True
                self._cv2_detector = cv2.QRCodeDetector()
                logger.info("QR scanner initialised with OpenCV backend")
            except ImportError:
                logger.warning(
                    "Neither pyzbar nor cv2 QRCodeDetector available – "
                    "QR scanning will be non-functional"
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def edge_density(crop: Image.Image) -> float:
        """Compute edge-density ratio for a crop (Canny edges / total pixels).

        Useful for filtering YOLO bounding-box candidates: QR codes
        typically have high edge density (> ~0.03) due to their
        black/white grid pattern.  Reject crops below a threshold before
        attempting expensive QR decode.

        Falls back to 0.0 if cv2 is unavailable.
        """
        try:
            import cv2
        except ImportError:
            return 0.0
        arr = np.array(crop.convert("L"))
        edges = cv2.Canny(arr, 100, 200)
        return float(edges.sum()) / (edges.size * 255) if edges.size > 0 else 0.0

    @property
    def is_ready(self) -> bool:
        return self._use_pyzbar or self._use_cv2

    @staticmethod
    def preprocess_for_qr(image: Image.Image) -> Image.Image:
        """Preprocess image for better QR detection in poor conditions.

        Steps: grayscale → contrast stretch → adaptive threshold → morph open.
        Falls back to contrast-stretched grayscale if cv2 is unavailable.
        """
        arr = np.array(image.convert("L"))  # grayscale
        # Contrast stretching (2nd–98th percentile)
        p2, p98 = np.percentile(arr, (2, 98))
        arr = np.clip(
            (arr.astype(np.float32) - p2) * 255.0 / (p98 - p2 + 1e-6), 0, 255
        ).astype(np.uint8)
        try:
            import cv2
            th = cv2.adaptiveThreshold(
                arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )
            kernel = np.ones((3, 3), np.uint8)
            th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
            return Image.fromarray(th)
        except ImportError:
            return Image.fromarray(arr)

    def scan(self, image: Image.Image) -> List[QRDetection]:
        """
        Scan a PIL Image for QR codes / barcodes.
        Returns a list of QRDetection objects (may be empty).
        """
        if not self.is_ready:
            logger.warning("QR scan called but scanner is not ready (no backend)")
            return []

        # Validate input type
        if not isinstance(image, Image.Image):
            logger.error(
                f"QR scan received wrong image type: {type(image).__name__} "
                f"(expected PIL.Image.Image). Convert before calling scan()."
            )
            return []

        backend = "pyzbar" if self._use_pyzbar else "cv2"
        logger.info(
            f"QR scan starting — backend={backend}, "
            f"image={image.size[0]}x{image.size[1]} mode={image.mode}"
        )
        start = time.time()

        try:
            if self._use_pyzbar:
                results = self._scan_pyzbar(image)
            else:
                results = self._scan_cv2(image)
        except Exception as exc:
            logger.error(f"QR scan error ({backend}): {exc}", exc_info=True)
            results = []

        # ── Retry with preprocessing if initial scan found nothing ────
        if not results:
            try:
                preprocessed = self.preprocess_for_qr(image)
                if self._use_pyzbar:
                    results = self._scan_pyzbar(preprocessed)
                else:
                    results = self._scan_cv2(preprocessed)
                if results:
                    logger.info("QR found after preprocessing retry")
            except Exception as pre_exc:
                logger.debug("QR preprocessing retry failed: %s", pre_exc)

        # ── Multi-scale retry (shrink to find distant codes) ──────────
        if not results:
            for scale in (0.75, 0.5):
                try:
                    w, h = image.size
                    scaled = image.resize((int(w * scale), int(h * scale)))
                    pre = self.preprocess_for_qr(scaled)
                    if self._use_pyzbar:
                        results = self._scan_pyzbar(pre)
                    else:
                        results = self._scan_cv2(pre)
                    if results:
                        logger.info("QR found at %.0f%% scale", scale * 100)
                        break
                except Exception:
                    pass

        elapsed_ms = (time.time() - start) * 1000
        if results:
            logger.info(
                f"QR scan found {len(results)} code(s) in {elapsed_ms:.0f}ms"
            )
        else:
            logger.info(f"QR scan completed in {elapsed_ms:.0f}ms — no codes found")
        return results

    async def scan_async(self, image: Image.Image) -> List[QRDetection]:
        """Async wrapper – runs scan in the default executor."""
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.scan, image)

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    def _scan_pyzbar(self, image: Image.Image) -> List[QRDetection]:
        decoded = self._decode_fn(image)
        detections: List[QRDetection] = []
        for obj in decoded:
            try:
                raw = obj.data.decode("utf-8", errors="replace")
            except Exception:
                raw = str(obj.data)
            rect = obj.rect
            detections.append(
                QRDetection(
                    raw_data=raw,
                    bbox=(rect.left, rect.top, rect.width, rect.height),
                    format_type=obj.type,
                )
            )
        return detections

    def _scan_cv2(self, image: Image.Image) -> List[QRDetection]:
        import cv2

        arr = np.array(image)
        if len(arr.shape) == 3 and arr.shape[2] == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        elif len(arr.shape) == 3 and arr.shape[2] == 3:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        data, points, _ = self._cv2_detector.detectAndDecode(arr)
        if not data:
            return []

        detections: List[QRDetection] = []
        if isinstance(data, str):
            data = [data]
            if points is not None:
                points = [points]

        for i, d in enumerate(data):
            if not d:
                continue
            bbox = (0, 0, 0, 0)
            if points is not None and i < len(points):
                pts = points[i]
                if pts is not None and len(pts) > 0:
                    pts = pts.reshape(-1, 2)
                    x_min, y_min = pts.min(axis=0).astype(int)
                    x_max, y_max = pts.max(axis=0).astype(int)
                    bbox = (int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min))
            detections.append(QRDetection(raw_data=d, bbox=bbox))
        return detections
