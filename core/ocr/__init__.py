"""
OCR Engine
==========

Optical Character Recognition pipeline with preprocessing:
- CLAHE contrast normalisation
- Bilateral denoising
- Automatic rotation correction (deskew)
- Tesseract or EasyOCR backend (graceful fallback)

All heavy work runs in ``asyncio.get_event_loop().run_in_executor``
so the event-loop is never blocked.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from shared.schemas import BoundingBox, OCRResult, OCRWord

logger = logging.getLogger("ocr-engine")

try:
    from shared.logging.logging_config import log_event as _log_event
except ImportError:
    def _log_event(*a, **kw): pass

# ── Optional imports ──────────────────────────────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

try:
    from PIL import Image as PILImage  # noqa: F401
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# ── Startup backend status ────────────────────────────────────────────
logger.info("OCR backends: easyocr=%s tesseract=%s cv2=%s", EASYOCR_AVAILABLE, TESSERACT_AVAILABLE, CV2_AVAILABLE)
if not EASYOCR_AVAILABLE and not TESSERACT_AVAILABLE:
    logger.error(
        "NO OCR BACKEND AVAILABLE. Text reading will not work. "
        "Install: pip install easyocr>=1.7.0  OR  pip install pytesseract>=0.3.10 + tesseract binary. "
        "Or run: scripts/install_ocr_deps.sh"
    )


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class OCRPipelineResult:
    """Aggregated result for the full pipeline."""

    results: List[OCRWord] = field(default_factory=list)
    full_text: str = ""
    total_latency_ms: float = 0.0
    preprocessing_ms: float = 0.0
    backend_used: str = "none"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "full_text": self.full_text,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "preprocessing_ms": round(self.preprocessing_ms, 1),
            "backend_used": self.backend_used,
            "error": self.error,
        }

    def to_ocr_result(self) -> OCRResult:
        confidence = 0.0
        if self.results:
            confidence = sum(r.confidence for r in self.results) / len(self.results)
        return OCRResult(
            full_text=self.full_text,
            words=self.results,
            confidence=confidence,
            backend=self.backend_used,
            latency_ms=self.total_latency_ms,
        )


# ============================================================================
# Preprocessing
# ============================================================================


def _to_numpy(image: Any) -> np.ndarray:
    """Convert various image types to numpy uint8 BGR."""
    if isinstance(image, np.ndarray):
        arr = image
    elif PIL_AVAILABLE and hasattr(image, "convert"):
        arr = np.array(image.convert("RGB"))
    else:
        raise ValueError(f"Unsupported image type: {type(image)}")

    # Ensure uint8
    if arr.dtype != np.uint8:
        arr = arr.astype(np.uint8)

    # RGB → BGR for OpenCV (if 3-channel)
    if len(arr.shape) == 3 and arr.shape[2] == 3:
        if CV2_AVAILABLE:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return arr


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalisation)."""
    if not CV2_AVAILABLE:
        return gray
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    return clahe.apply(gray)


def denoise(gray: np.ndarray, d: int = 9, sigma_color: float = 75, sigma_space: float = 75) -> np.ndarray:
    """Bilateral filter denoising (edge-preserving)."""
    if not CV2_AVAILABLE:
        return gray
    return cv2.bilateralFilter(gray, d, sigma_color, sigma_space)


def deskew(gray: np.ndarray) -> np.ndarray:
    """Automatic rotation correction using Hough-line angle estimation."""
    if not CV2_AVAILABLE:
        return gray
    try:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=50, maxLineGap=10)
        if lines is None or len(lines) == 0:
            return gray

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 30:  # Only near-horizontal lines
                angles.append(angle)

        if not angles:
            return gray

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return gray  # Already straight

        h, w = gray.shape[:2]
        centre = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(centre, median_angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return gray


def preprocess(image: Any) -> np.ndarray:
    """Full preprocessing pipeline: grayscale → CLAHE → denoise → deskew."""
    arr = _to_numpy(image)
    if len(arr.shape) == 3:
        if CV2_AVAILABLE:
            gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        else:
            gray = np.mean(arr, axis=2).astype(np.uint8)
    else:
        gray = arr
    gray = apply_clahe(gray)
    gray = denoise(gray)
    gray = deskew(gray)
    return gray


# ============================================================================
# OCR Backends
# ============================================================================


class _EasyOCRBackend:
    """EasyOCR backend (GPU-accelerated if available)."""

    def __init__(self, languages: Optional[List[str]] = None):
        self._languages = languages or ["en"]
        self._reader = None

    def _ensure_reader(self):
        if self._reader is None:
            self._reader = easyocr.Reader(self._languages, gpu=False)

    def read(self, gray: np.ndarray) -> List[OCRWord]:
        self._ensure_reader()
        raw = self._reader.readtext(gray)
        results: List[OCRWord] = []
        for bbox_pts, text, conf in raw:
            # bbox_pts is list of 4 corner points
            xs = [int(p[0]) for p in bbox_pts]
            ys = [int(p[1]) for p in bbox_pts]
            bbox = BoundingBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys))
            results.append(OCRWord(
                text=text,
                confidence=float(conf),
                bbox=bbox,
            ))
        return results


class _TesseractBackend:
    """Tesseract OCR backend."""

    def read(self, gray: np.ndarray) -> List[OCRWord]:
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        results: List[OCRWord] = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            results.append(OCRWord(
                text=text,
                confidence=conf / 100.0,
                bbox=BoundingBox.from_xywh(x=x, y=y, w=w, h=h),
            ))
        return results


# ============================================================================
# Pipeline
# ============================================================================


class OCRPipeline:
    """End-to-end OCR pipeline: preprocess → backend → aggregate.

    Automatically selects the best available backend
    (EasyOCR > Tesseract > mock fallback).
    """

    def __init__(self, languages: Optional[List[str]] = None, min_confidence: float = 0.3):
        self._min_confidence = min_confidence
        self._backends = self._select_backends(languages)
        self._backend = self._backends[0] if self._backends else None
        self._backend_name = self._backend.__class__.__name__ if self._backend else "none"

    @staticmethod
    def _select_backends(languages: Optional[List[str]] = None) -> List[Any]:
        backends: List[Any] = []
        if EASYOCR_AVAILABLE:
            backends.append(_EasyOCRBackend(languages))
        if TESSERACT_AVAILABLE:
            backends.append(_TesseractBackend())
        return backends

    @property
    def is_ready(self) -> bool:
        return self._backend is not None

    @staticmethod
    def _box_iou(first: OCRWord, second: OCRWord) -> float:
        if first.bbox is None or second.bbox is None:
            return 0.0
        x1 = max(first.bbox.x1, second.bbox.x1)
        y1 = max(first.bbox.y1, second.bbox.y1)
        x2 = min(first.bbox.x2, second.bbox.x2)
        y2 = min(first.bbox.y2, second.bbox.y2)
        inter_w = max(0, x2 - x1)
        inter_h = max(0, y2 - y1)
        inter = inter_w * inter_h
        if inter == 0:
            return 0.0
        area_a = first.bbox.area
        area_b = second.bbox.area
        union = area_a + area_b - inter
        return inter / max(union, 1e-6)

    def _merge_results(self, primary: List[OCRWord], secondary: List[OCRWord]) -> List[OCRWord]:
        merged = list(primary)
        for candidate in secondary:
            replaced = False
            for idx, existing in enumerate(merged):
                if self._box_iou(candidate, existing) > 0.5:
                    if candidate.confidence > existing.confidence:
                        merged[idx] = candidate
                    replaced = True
                    break
            if not replaced:
                merged.append(candidate)
        return merged

    async def process(self, image: Any) -> OCRPipelineResult:
        """Run the full OCR pipeline asynchronously."""
        start = time.time()

        if self._backend is None:
            return OCRPipelineResult(error="No OCR backend available (install easyocr or pytesseract)")

        loop = asyncio.get_event_loop()

        # 1. Preprocess
        pre_start = time.time()
        try:
            gray = await loop.run_in_executor(None, preprocess, image)
        except Exception as exc:
            return OCRPipelineResult(error=f"Preprocessing failed: {exc}")
        pre_ms = (time.time() - pre_start) * 1000

        # 2. OCR
        results: List[OCRWord] = []
        backend_used = "none"
        for backend in self._backends:
            backend_name = backend.__class__.__name__
            try:
                results = await loop.run_in_executor(None, backend.read, gray)
            except Exception as exc:
                logger.warning("OCR backend failed: %s", exc)
                try:
                    results = await loop.run_in_executor(None, backend.read, gray)
                except Exception as exc:
                    logger.error("OCR backend retry failed: %s", exc)
                    continue
            backend_used = backend_name
            self._backend = backend
            if len(results) >= 2:
                break
        if not results:
            return OCRPipelineResult(error="OCR failed: all backends failed", preprocessing_ms=pre_ms)
        if len(results) < 2 and len(self._backends) > 1:
            for backend in self._backends:
                if backend.__class__.__name__ == backend_used:
                    continue
                try:
                    secondary = await loop.run_in_executor(None, backend.read, gray)
                    results = self._merge_results(results, secondary)
                except Exception as exc:
                    logger.warning("Secondary OCR backend failed: %s", exc)

        # 3. Filter by confidence
        results = [r for r in results if r.confidence >= self._min_confidence]

        # 4. Build aggregate
        total_ms = (time.time() - start) * 1000
        full_text = " ".join(r.text for r in results)

        _log_event(
            "ocr-engine", "ocr_complete",
            component=backend_used or "unknown",
            latency_ms=total_ms,
            detections_count=len(results),
            characters=len(full_text),
        )

        return OCRPipelineResult(
            results=results,
            full_text=full_text,
            total_latency_ms=total_ms,
            preprocessing_ms=pre_ms,
            backend_used=backend_used or self._backend_name,
        )
