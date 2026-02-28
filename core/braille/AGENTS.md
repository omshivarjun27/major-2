# Core Braille Module — Agent Intelligence

## 1. Folder Purpose
- The Braille submodule handles capture, segmentation, and classification of Braille text to enable screen-reader friendly output for blind users. It orchestrates OCR-readout through a robust end-to-end pipeline while respecting privacy and modular boundaries.

## 2. Contained Components
- Files: `braille_capture.py`, `braille_segmenter.py`, `braille_classifier.py`, `braille_ocr.py`, `embossing_guidance.py`, `__init__.py`
- Key classes:
  - BrailleCapture
  - BrailleSegmenter
  - BrailleClassifier (Grade 1)
  - BrailleOCR (end-to-end)
  - EmbossingGuide

## 3. Dependency Graph
- Depends on: `shared/` (types, utilities, and logging)
- Consumed by: `apps/api/` braille read endpoint (Braille data exposure)
- No imports from `application/`, `infrastructure/`, or `apps/` to preserve module boundaries.

## 4. Task Tracking
- Status: Completed feature, stable

## 5. Design Thinking
- Pipeline: capture → segment → classify → read
- Emphasizes a clean flow with explicit stages and minimal cross-stage coupling
- Supports future extensions for Grade 2 Braille processing and performance tweaks

## 6. Research Notes
- Focused on Grade 1 Braille support; potential expansion to Grade 2 Braille mappings and contractions
- Investigating efficient dot segmentation and robust OCR alignment on varied lighting conditions

## 7. Risk Assessment
- Overall risk: Low
- Rationale: Niche feature with clear input/output boundaries and minimal external dependencies

## 8. Improvement Suggestions
- Consider Grade 2 Braille support and multi-language Braille mappings
- Explore performance optimizations in segmentation and OCR recall
- Add unit tests for end-to-end Braille OCR to ensure reliability across fonts and sizes

## 9. Folder Change Log
- 2026-02-23: Initial AGENTS.md creation for core/braille
