# T-015: edge-aware-segmentation-hardening

> Phase: P1 | Cluster: CL-VIS | Risk: Low | State: not_started

## Objective

Harden `EdgeAwareSegmenter` in `core/vision/spatial.py` so it produces actual binary
masks instead of `None`. The current implementation (lines 372-446) computes a
variance-based `boundary_confidence` score but always sets `mask=None` and
`edge_pixels=None` in every `SegmentationMask` it returns. This breaks downstream
consumers that expect a numpy array for mask composition and spatial reasoning.

The fix adds proper binary mask generation using either `cv2.grabCut` (when OpenCV
is available) or a threshold-based refinement fallback. Masks will be numpy arrays
of shape `(H, W)` with dtype `uint8`, values 0 or 255. The existing confidence
calculation stays, but confidence now also accounts for mask edge sharpness.

## Current State (Codebase Audit 2026-02-25)

- `EdgeAwareSegmenter` (lines 372-446) extends `BaseSegmenter` ABC.
  - `__init__` (line 380) sets `_ready = cv2 is not None`, creates empty
    `_cached_masks` list and `_gray_buffer`.
  - `segment()` (lines 385-445):
    - Returns `[]` if not ready or no detections.
    - **Fast path** (lines 392-400): if cached masks exist and count >= detections,
      reuses cache. Still sets `mask=None`.
    - **Slow path** (lines 402-441): downscales image to `MAX_MASK_SIZE=(160,120)`
      using PIL NEAREST, converts to grayscale via `np.mean()`, iterates over
      detections (capped at `MAX_DETECTIONS=2`).
    - For each detection: scales bbox to mask dimensions, extracts ROI from grayscale,
      computes `variance = np.var(roi)`, sets `boundary_conf = min(0.5 + variance/5000, 0.95)`.
    - Creates `SegmentationMask(detection_id=..., mask=None, boundary_confidence=..., edge_pixels=None)`.
  - The `mask=None` pattern appears on lines 396, 435. Every mask returned is None.
- `SegmentationMask` dataclass (in `shared/schemas/__init__.py`) expects:
  - `detection_id: str`
  - `mask: Optional[np.ndarray]` (binary mask, H x W, uint8)
  - `boundary_confidence: float`
  - `edge_pixels: Optional[np.ndarray]` (Nx2 array of boundary pixel coords)
- `SpatialFuser.fuse()` (line 760) only reads `mask.boundary_confidence`, so
  `mask=None` doesn't crash the fuser. But any future mask-based reasoning (area
  refinement, occlusion detection) will fail.
- `MAX_MASK_SIZE = (160, 120)` (line 38) and `MAX_DETECTIONS = 2` (line 37) govern
  the segmentation budget.
- `CV2_AVAILABLE` flag (lines 56-60) controls whether OpenCV is importable.

## Implementation Plan

### Step 1: Add binary mask generation via thresholding

Inside the slow path of `segment()`, after computing the grayscale ROI, apply
Otsu thresholding (or simple adaptive threshold) to produce a binary mask within
the bounding box region. Place this mask into a full-frame-sized array.

```python
# After: roi = gray[y1:y2, x1:x2]
if roi.size > 0 and CV2_AVAILABLE:
    _, binary_roi = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    full_mask = np.zeros(gray.shape, dtype=np.uint8)
    full_mask[y1:y2, x1:x2] = binary_roi
else:
    # Fallback: simple bbox-fill mask
    full_mask = np.zeros(gray.shape, dtype=np.uint8)
    full_mask[y1:y2, x1:x2] = 255
```

### Step 2: Extract edge pixels from binary mask

Use `cv2.findContours` on the binary mask to extract boundary pixel coordinates.
Store as an Nx2 numpy array in the `edge_pixels` field.

```python
if CV2_AVAILABLE:
    contours, _ = cv2.findContours(full_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        edge_px = np.vstack(contours).squeeze()
        if edge_px.ndim == 1:
            edge_px = edge_px.reshape(1, 2)
    else:
        edge_px = np.empty((0, 2), dtype=np.int32)
else:
    edge_px = None
```

### Step 3: Refine boundary confidence using edge sharpness

Combine the existing variance-based confidence with an edge gradient metric.
Compute the mean Sobel gradient magnitude along the mask boundary.

```python
if edge_px is not None and len(edge_px) > 0:
    # Edge sharpness from gradient magnitude
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
    edge_grads = grad_mag[edge_px[:, 1], edge_px[:, 0]]
    sharpness = float(np.mean(edge_grads)) / 255.0
    boundary_conf = min(0.5 + variance / 5000.0 + sharpness * 0.3, 0.95)
```

### Step 4: Update the cached mask path

The fast-path cache (lines 392-400) also needs to return actual masks, not None.
Either invalidate cache when detections change, or always run the slow path. Given
`MAX_DETECTIONS=2`, the slow path is already fast enough at 160x120 resolution.

### Step 5: Write 5 unit tests

Test mask shape, boundary confidence range, empty detection handling, multi-object
output, and performance.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_segmentation.py` | 5 unit tests for EdgeAwareSegmenter hardening |

## Files to Modify

| File | Change |
|------|--------|
| `core/vision/spatial.py` | Replace `mask=None` with actual binary mask in `EdgeAwareSegmenter.segment()` |
| `core/vision/AGENTS.md` | Document mask generation approach and performance characteristics |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_segmentation.py` | `test_mask_shape_matches_downscale` - verify returned mask is numpy uint8 array of shape `MAX_MASK_SIZE` (120, 160) |
| | `test_boundary_confidence_range` - verify confidence is in [0.5, 0.95] for various inputs |
| | `test_empty_detection_list` - pass empty list, verify returns empty list (no crash) |
| | `test_multi_object_masks` - pass 2 detections, verify 2 distinct SegmentationMask objects with non-None masks |
| | `test_segment_latency_under_50ms` - time a single segment call with 2 detections on 640x480, assert < 50 ms |

## Acceptance Criteria

- [ ] `EdgeAwareSegmenter.segment()` returns `SegmentationMask` objects with `mask` as numpy uint8 array, never `None`
- [ ] Mask shape is `(120, 160)` matching `MAX_MASK_SIZE` (height, width order)
- [ ] Mask values are 0 or 255 (binary)
- [ ] `edge_pixels` is a numpy array of shape (N, 2) or None if cv2 unavailable
- [ ] `boundary_confidence` remains in [0.5, 0.95] range
- [ ] Empty detection list returns empty list, no exceptions
- [ ] Segmentation for 2 objects completes in < 50 ms at 160x120 resolution
- [ ] Cached mask path also returns real masks (not None)
- [ ] Graceful fallback (bbox-fill mask) when OpenCV is not available
- [ ] All 5 unit tests pass: `pytest tests/unit/test_segmentation.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean
- [ ] `core/vision/AGENTS.md` updated

## Upstream Dependencies

T-013 (yolo-onnx-detection-mvp). Real detections are needed to test multi-object
segmentation with meaningful bounding boxes. Can be developed in parallel using
MockObjectDetector for initial testing, but full validation requires T-013 output.

## Downstream Unblocks

T-016 (spatial-fusion-pipeline)

## Estimated Scope

- New code: ~60 LOC (mask generation, edge extraction, confidence refinement)
- Modified code: ~40 lines in spatial.py (EdgeAwareSegmenter.segment slow/fast paths)
- Tests: ~80 LOC
- Risk: Low. Changes are confined to one class. The 160x120 downscale keeps
  computation fast. Otsu thresholding is a single OpenCV call. The main risk is
  that threshold-based masks are coarse compared to learned segmentation, but they're
  sufficient for the spatial fusion distance/direction calculations. GrabCut is
  available as a future upgrade path if mask quality needs improvement.
