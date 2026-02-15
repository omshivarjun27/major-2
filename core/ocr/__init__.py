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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

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
    from PIL import Image as PILImage
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
class OCRResult:
    """Result from a single OCR invocation."""

    text: str
    confidence: float               # 0.0 – 1.0
    bbox: Optional[Tuple[int, int, int, int]] = None  # x1, y1, x2, y2
    language: str = "en"
    latency_ms: float = 0.0
    backend: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "bbox": list(self.bbox) if self.bbox else None,
            "language": self.language,
            "latency_ms": round(self.latency_ms, 1),
            "backend": self.backend,
        }


@dataclass
class OCRPipelineResult:
    """Aggregated result for the full pipeline."""

    results: List[OCRResult] = field(default_factory=list)
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

    def read(self, gray: np.ndarray) -> List[OCRResult]:
        self._ensure_reader()
        raw = self._reader.readtext(gray)
        results: List[OCRResult] = []
        for bbox_pts, text, conf in raw:
            # bbox_pts is list of 4 corner points
            xs = [int(p[0]) for p in bbox_pts]
            ys = [int(p[1]) for p in bbox_pts]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            results.append(OCRResult(
                text=text,
                confidence=float(conf),
                bbox=bbox,
                backend="easyocr",
            ))
        return results


class _TesseractBackend:
    """Tesseract OCR backend."""

    def read(self, gray: np.ndarray) -> List[OCRResult]:
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        results: List[OCRResult] = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            results.append(OCRResult(
                text=text,
                confidence=conf / 100.0,
                bbox=(x, y, x + w, y + h),
                backend="tesseract",
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
        self._backend = self._select_backend(languages)
        self._backend_name = self._backend.__class__.__name__

    @staticmethod
    def _select_backend(languages: Optional[List[str]] = None):
        if EASYOCR_AVAILABLE:
            return _EasyOCRBackend(languages)
        if TESSERACT_AVAILABLE:
            return _TesseractBackend()
        return None

    @property
    def is_ready(self) -> bool:
        return self._backend is not None

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
        try:
            results = await loop.run_in_executor(None, self._backend.read, gray)
        except Exception as exc:
            return OCRPipelineResult(error=f"OCR failed: {exc}", preprocessing_ms=pre_ms)

        # 3. Filter by confidence
        results = [r for r in results if r.confidence >= self._min_confidence]

        # 4. Build aggregate
        total_ms = (time.time() - start) * 1000
        for r in results:
            r.latency_ms = total_ms

        full_text = " ".join(r.text for r in results)

        _log_event(
            "ocr-engine", "ocr_complete",
            component=self._backend_name or "unknown",
            latency_ms=total_ms,
            detections_count=len(results),
            characters=len(full_text),
        )

        return OCRPipelineResult(
            results=results,
            full_text=full_text,
            total_latency_ms=total_ms,
            preprocessing_ms=pre_ms,
            backend_used=self._backend_name,
        )
