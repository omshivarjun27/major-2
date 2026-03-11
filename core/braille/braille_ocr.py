"""
Braille OCR
===========

CLI / API wrapper that runs the full pipeline:
  capture hints → segmentation → classification → transcription

Returns text + confidence.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .braille_classifier import BrailleChar, BrailleClassifier
from .braille_segmenter import BrailleSegmenter, SegmentationResult

logger = logging.getLogger("braille-ocr")


@dataclass
class BrailleOCRResult:
    """End-to-end braille OCR result."""

    text: str = ""
    confidence: float = 0.0
    char_count: int = 0
    dot_count: int = 0
    cells_detected: int = 0
    latency_ms: float = 0.0
    chars: List[Dict[str, Any]] = field(default_factory=list)
    segmentation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "char_count": self.char_count,
            "dot_count": self.dot_count,
            "cells_detected": self.cells_detected,
            "latency_ms": round(self.latency_ms, 1),
            "chars": self.chars,
            "error": self.error,
        }


class BrailleOCR:
    """Full braille OCR pipeline.

    Usage::

        ocr = BrailleOCR()
        result = await ocr.read(frame)
        print(result.text, result.confidence)
    """

    def __init__(
        self,
        classifier_mode: str = "lookup",
        model_path: Optional[str] = None,
        deskew: bool = True,
    ):
        self._segmenter = BrailleSegmenter()
        self._classifier = BrailleClassifier(mode=classifier_mode, model_path=model_path)
        self._deskew = deskew

    async def read(self, image: np.ndarray) -> BrailleOCRResult:
        """Run full braille OCR on an image.

        Args:
            image: BGR or grayscale frame.

        Returns:
            BrailleOCRResult with transcribed text and metadata.
        """
        start = time.time()

        try:
            loop = asyncio.get_event_loop()

            # Optional deskew
            if self._deskew:
                image = await loop.run_in_executor(None, self._segmenter.deskew, image)

            # Segment
            seg_result: SegmentationResult = await loop.run_in_executor(
                None, self._segmenter.segment, image
            )

            if seg_result.error:
                return BrailleOCRResult(
                    error=seg_result.error,
                    latency_ms=(time.time() - start) * 1000,
                )

            if not seg_result.cells:
                return BrailleOCRResult(
                    text="",
                    confidence=0.0,
                    dot_count=seg_result.dot_count,
                    latency_ms=(time.time() - start) * 1000,
                    error="No braille cells detected in image.",
                )

            # Classify
            chars: List[BrailleChar] = self._classifier.classify(seg_result.cells)
            text = self._classifier.to_text(chars)

            # Compute average confidence
            if chars:
                avg_conf = sum(c.confidence for c in chars) / len(chars)
            else:
                avg_conf = 0.0

            latency = (time.time() - start) * 1000

            return BrailleOCRResult(
                text=text,
                confidence=avg_conf,
                char_count=len(chars),
                dot_count=seg_result.dot_count,
                cells_detected=len(seg_result.cells),
                latency_ms=latency,
                chars=[c.to_dict() for c in chars],
                segmentation=seg_result.to_dict(),
            )

        except Exception as exc:
            logger.error("Braille OCR failed: %s", exc)
            return BrailleOCRResult(
                error=str(exc),
                latency_ms=(time.time() - start) * 1000,
            )

    async def read_with_hints(self, image: np.ndarray) -> Dict[str, Any]:
        """Read braille and include capture quality hints."""
        from .braille_capture import BrailleCapture

        cap = BrailleCapture()
        hints = cap.analyse_frame(image)
        result = await self.read(image)
        return {
            "ocr": result.to_dict(),
            "capture_hints": hints.to_dict(),
        }
