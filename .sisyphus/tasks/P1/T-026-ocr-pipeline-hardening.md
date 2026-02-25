# T-026: ocr-pipeline-hardening

> Phase: P1 | Cluster: CL-OCR | Risk: Low | State: not_started

## Objective

Harden the OCR pipeline in `core/ocr/engine.py` and `core/ocr/__init__.py`. The current
implementation has a single-shot execution model with no retry logic, no confidence thresholding
at the engine level, no result merging when multiple backends produce overlapping detections, and
no structured `OCRResult` type in the engine module (only in `__init__.py`). This task adds retry
logic for transient failures (e.g., temporary GPU memory exhaustion or backend initialization
hiccups), confidence-based filtering with a configurable threshold, a result merging strategy
that combines outputs from multiple backends when available, and ensures the structured
`OCRResult` / `OCRPipelineResult` types in `__init__.py` are used consistently throughout. The
goal is to make OCR reliable enough for real-world accessibility use, where a missed text reading
can leave a blind user without critical information.

## Current State (Codebase Audit 2026-02-25)

- `core/ocr/engine.py` (292 lines):
  - Three backend probe functions: `_probe_easyocr()` (line 28), `_probe_tesseract()` (line 36), `_probe_cv2()` (line 46).
  - Module-level availability flags: `EASYOCR_OK`, `TESSERACT_OK`, `CV2_OK` (lines 54-56).
  - `deskew_image()` (lines 61-104): Hough-line-based skew correction with max_angle guard.
  - `_HeuristicBackend` (lines 176-230): MSER-based text region detection with NMS. Returns bounding boxes only, no actual OCR.
  - `ocr_read()` async function (lines 234-292): tries `OCRPipeline` from `__init__.py` first, falls back to heuristic, then returns error dict.
  - No retry logic anywhere in the file.
  - No confidence thresholding in `ocr_read()` (it delegates to `OCRPipeline` which filters at `min_confidence=0.3`).
  - `get_install_instructions()` provides OS-specific install hints (lines 136-159).
  - `get_ocr_status()` returns structured backend availability (lines 162-171).

- `core/ocr/__init__.py` (337 lines):
  - `OCRResult` dataclass (lines 73-92): text, confidence, bbox, language, latency_ms, backend.
  - `OCRPipelineResult` dataclass (lines 95-114): results list, full_text, total_latency_ms, preprocessing_ms, backend_used, error.
  - Preprocessing pipeline: `preprocess()` calls grayscale, `apply_clahe()`, `denoise()`, `deskew()` (lines 189-202).
  - `_EasyOCRBackend` (lines 210-236): lazily initializes `easyocr.Reader`, returns `List[OCRResult]`.
  - `_TesseractBackend` (lines 239-258): uses `pytesseract.image_to_data()`, returns `List[OCRResult]`.
  - `OCRPipeline` (lines 266-337): selects best backend at init, `process()` runs preprocessing then OCR in executor, filters by `min_confidence`.
  - No multi-backend merging: pipeline picks one backend and uses it exclusively.
  - No retry on failure: a single exception aborts the pipeline.
  - Structured logging via `_log_event()` at line 323.

- `core/ocr/AGENTS.md` confirms the 3-tier fallback architecture and notes async executor pattern.

## Implementation Plan

### Step 1: Add retry decorator to engine.py

Create a `_retry_async()` utility in `engine.py` that wraps an async callable with configurable
max_retries (default 2) and backoff_ms (default 100). Apply it to the `ocr_read()` function.
The retry should only trigger on transient exceptions (RuntimeError, OSError), not on ValueError
or backend-missing scenarios.

### Step 2: Add confidence threshold to engine.py ocr_read

Add a `min_confidence` parameter to `ocr_read()` (default 0.3). After receiving results from
whichever backend runs, filter out entries below the threshold. This brings the engine-level
function in line with what `OCRPipeline` already does in `__init__.py`.

### Step 3: Add multi-backend merging to OCRPipeline

Modify `OCRPipeline._select_backend()` to store all available backends instead of just the best
one. Add a `_merge_results()` method that runs secondary backends when the primary returns few
results (e.g., fewer than 2 text regions). Merge by deduplicating overlapping bounding boxes
using IoU, keeping the higher-confidence result for each overlap.

### Step 4: Add retry logic to OCRPipeline.process

Wrap the backend `.read()` call in a try/except with one retry attempt. Log the first failure at
WARNING level and retry. On second failure, fall through to the next available backend rather
than returning an error immediately.

### Step 5: Add structured OCRResult to engine.py output

Update `ocr_read()` to return results using the `OCRResult` and `OCRPipelineResult` types from
`core/ocr/__init__.py` instead of raw dicts. This ensures a consistent return type across
both entry points.

### Step 6: Write unit tests

Create `tests/unit/test_ocr_hardening.py` with tests for retry logic (mock a backend that fails
once then succeeds), confidence filtering, multi-backend merging, and the fallback chain.

### Step 7: Update AGENTS.md

Document the new retry behavior, merging strategy, and confidence threshold in
`core/ocr/AGENTS.md`.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_ocr_hardening.py` | Tests for retry, confidence filter, merging |

## Files to Modify

| File | Change |
|------|--------|
| `core/ocr/engine.py` | Add retry decorator, confidence param to `ocr_read()`, use structured types |
| `core/ocr/__init__.py` | Multi-backend merging in `OCRPipeline`, retry wrapper on `.read()` call |
| `core/ocr/AGENTS.md` | Document retry, merging, and threshold behavior |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_ocr_hardening.py` | `TestOCRRetry::test_retry_on_transient_failure` |
| | `TestOCRRetry::test_no_retry_on_value_error` |
| | `TestOCRConfidence::test_filter_low_confidence` |
| | `TestOCRConfidence::test_threshold_parameter` |
| | `TestOCRMerge::test_multi_backend_merge` |
| | `TestOCRMerge::test_dedup_overlapping_boxes` |
| | `TestOCRFallback::test_primary_fail_secondary_succeed` |

## Acceptance Criteria

- [ ] `ocr_read()` retries once on `RuntimeError` or `OSError` before returning error
- [ ] `ocr_read()` accepts `min_confidence` parameter and filters results below threshold
- [ ] `OCRPipeline.process()` tries secondary backend when primary returns fewer than 2 results
- [ ] Result merging deduplicates overlapping bboxes (IoU > 0.5) keeping higher confidence
- [ ] `ocr_read()` returns `OCRPipelineResult.to_dict()` instead of hand-built dict
- [ ] All 7 new tests pass with `pytest tests/unit/test_ocr_hardening.py -v`
- [ ] Existing OCR tests still pass: `pytest tests/ -k "ocr" -v`
- [ ] `ruff check core/ocr/` passes clean
- [ ] `lint-imports` reports no architecture violations
- [ ] AGENTS.md documents new retry, merge, and threshold behavior
- [ ] No breaking changes to `OCRPipeline.process()` return type

## Upstream Dependencies

- None. OCR pipeline is self-contained within `core/ocr/`.

## Downstream Unblocks

- None. T-026 is an isolated hardening task with no downstream dependents.

## Estimated Scope

- **Effort**: ~5 hours
- **Lines changed**: ~120 in engine.py, ~80 in __init__.py, ~180 in tests
- **Version bump**: Patch (backwards-compatible hardening)
- **Risk**: Low. Changes are additive. Existing single-backend path still works. Retry and merging are opt-in improvements.
- **Parallel**: Yes. OCR module has no dependencies on other P1 tasks.
- **Environment**: Local GPU not required. EasyOCR/Tesseract are mocked in tests.
