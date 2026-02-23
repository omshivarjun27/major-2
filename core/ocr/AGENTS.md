# core/ocr/AGENTS.md
3-tier fallback OCR pipeline: EasyOCR → Tesseract → MSER/Heuristic → Helpful Error.
**Constraint**: Entire core logic is contained within `core/ocr/__init__.py` for simplicity.

## ENTRY POINT
`OCRPipeline(languages=["en"], min_confidence=0.3)`
→ `await pipeline.process(image)`
→ `OCRPipelineResult` (contains `full_text`, `results` list, and `error` status).

## PREPROCESSING PIPELINE
All images are pre-processed before inference:
1. `grayscale`
2. `CLAHE` (clip=2.0, grid=8) — Local contrast enhancement.
3. `bilateral denoise` (d=9) — Removes noise while preserving edges.
4. `deskew` (Hough lines) — Corrects camera tilt/rotation.

## BACKEND SELECTION
Selection is made at `__init__` time based on availability:
- `_EasyOCRBackend`: Highest accuracy; requires `easyocr` + optional GPU.
- `_TesseractBackend`: Solid fallback; requires `pytesseract` + system binary.
- `Heuristic/Stub`: Last resort; uses MSER for character region identification.

## INSTALLATION & SETUP
- `pip install easyocr>=1.7.0` (Recommended).
- `pip install pytesseract>=0.3.10` + install `tesseract-ocr` binary.
- Or use: `scripts/install_ocr_deps.sh`.

## CONVENTIONS & GOTCHAS
- **Async Execution**: Inference is CPU/GPU intensive and must be wrapped in `run_in_executor()`.
- **Backend Logging**: Check application startup logs to see which OCR backend was successfully initialized.
- **Language Support**: Default is `["en"]`. Dynamic language switching requires re-initializing the pipeline.
