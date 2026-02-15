"""
Braille Engine
==============

Feature 7: Braille capture, recognition, and tactile guidance.

Modules:
- braille_capture — data-collection mode for high-res braille frames
- braille_segmenter — detect braille plates, segment raised dots
- braille_classifier — dot-pattern → character pipeline
- braille_ocr — CLI/API wrapper for full transcription
- embossing_guidance — layout verification for tactile print

All heavy processing runs via asyncio executors.
"""

from .braille_capture import BrailleCapture, CaptureHints
from .braille_segmenter import BrailleSegmenter, SegmentationResult
from .braille_classifier import BrailleClassifier, BrailleChar
from .braille_ocr import BrailleOCR, BrailleOCRResult
from .embossing_guidance import EmbossingGuide, LayoutVerification

__all__ = [
    "BrailleCapture",
    "CaptureHints",
    "BrailleSegmenter",
    "SegmentationResult",
    "BrailleClassifier",
    "BrailleChar",
    "BrailleOCR",
    "BrailleOCRResult",
    "EmbossingGuide",
    "LayoutVerification",
]
