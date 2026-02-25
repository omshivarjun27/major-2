# T-013: yolo-onnx-detection-mvp

> Phase: P1 | Cluster: CL-VIS | Risk: Medium | State: not_started

## Objective

Replace `MockObjectDetector` with a working ONNX YOLOv8n inference pipeline in
`core/vision/spatial.py`. The `YOLODetector` class already exists (lines 154-366)
with full pre/post-processing and greedy NMS, but it has never been integration-tested
against an actual `.onnx` model file. This task wires up automatic model download,
adds a pytest conftest fixture for the ONNX session, and delivers 5 unit tests that
prove detection works end-to-end on CPU within the 100 ms latency budget.

Completing this task unblocks both the segmentation hardening work (T-015) and the
full spatial fusion pipeline (T-016), since both depend on real detection output
rather than the single hardcoded bounding box produced by the mock.

## Current State (Codebase Audit 2026-02-25)

- `MockObjectDetector` (lines 121-152) returns exactly 1 hardcoded detection every call:
  class `"person"`, confidence 0.85, centered 100x100 box. Used as the default fallback.
- `YOLODetector` (lines 154-366) accepts an optional `model_path` and `conf_threshold`.
  - `_load_model()` (line 187) tries ONNX first, then Ultralytics `YOLO(...)` as fallback.
  - `detect()` (line 210) dispatches to `_onnx_detect()` or Ultralytics `.predict()`.
  - `_onnx_detect()` (lines 263-356) implements the full pipeline: letterbox resize to
    640x640, HWC to NCHW conversion, 0-1 normalization, ONNX session run, transpose
    from (1, 84, 8400), confidence filter, cx/cy/w/h to x1/y1/x2/y2, greedy NMS at
    IoU 0.45, re-scale to original dimensions, capped at 25 detections.
  - `_iou()` static method (lines 358-365) computes intersection-over-union.
  - `_get_coco_classes()` (lines 170-185) returns all 80 COCO class names.
- `create_spatial_processor()` factory (lines 1111-1157) checks `use_yolo` flag and
  falls back to `MockObjectDetector` if the YOLO model fails to load.
- No model auto-download logic exists. The `.env` file references
  `YOLO_MODEL_PATH=models/yolov8n.onnx` but the file is not shipped.
- `ONNX_AVAILABLE` guard (lines 70-75) imports `onnxruntime` optionally.
- `MAX_DETECTIONS = 2` (line 37) caps the final stored obstacles, but raw detection
  is bounded at 25 in the NMS loop (line 336).
- No existing tests cover `YOLODetector` with a real ONNX session.

## Implementation Plan

### Step 1: Add model auto-download utility

Create a small helper that downloads `yolov8n.onnx` from the Ultralytics GitHub
releases to `models/yolov8n.onnx` if the file is missing. Use `urllib.request` to
avoid adding a new dependency. Include a SHA-256 checksum verification step.

```python
import hashlib
import urllib.request
from pathlib import Path

YOLOV8N_URL = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx"
YOLOV8N_SHA256 = "<actual_hash>"  # Pin after first download

def ensure_yolo_model(dest: str = "models/yolov8n.onnx") -> str:
    path = Path(dest)
    if path.exists():
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(YOLOV8N_URL, str(path))
    # Verify checksum
    ...
    return str(path)
```

### Step 2: Wire auto-download into YOLODetector._load_model()

Before the existing ONNX session creation, call `ensure_yolo_model()` if
`self._model_path` is `None` or points to a missing file. This keeps the existing
code path intact while adding the convenience of first-run setup.

```python
def _load_model(self):
    if not self._model_path or not Path(self._model_path).exists():
        self._model_path = ensure_yolo_model()
    # ... existing ONNX loading logic
```

### Step 3: Add conftest fixture for ONNX detector

Create a conftest fixture that instantiates `YOLODetector` with the auto-downloaded
model and skips if `onnxruntime` is not installed. Also add a reusable test image
fixture (a 640x480 PIL Image with random noise or a solid color block).

```python
import pytest

@pytest.fixture(scope="session")
def yolo_detector():
    ort = pytest.importorskip("onnxruntime")
    from core.vision.spatial import YOLODetector
    detector = YOLODetector()  # auto-downloads model
    if not detector.is_ready():
        pytest.skip("YOLO model not available")
    return detector

@pytest.fixture
def sample_image():
    from PIL import Image
    return Image.new("RGB", (640, 480), color=(128, 128, 128))
```

### Step 4: Write 5 unit tests

Cover the critical paths: successful detection, empty-frame handling, NMS behavior,
confidence filtering, and CPU latency assertion.

### Step 5: Add benchmark test

Add a performance test in `tests/performance/` that runs 10 consecutive detections
and asserts the median is under 100 ms on CPU.

## Files to Create

| File | Purpose |
|------|---------|
| `core/vision/model_download.py` | Auto-download + checksum utility for ONNX models |
| `tests/unit/test_yolo_detector.py` | 5 unit tests for YOLODetector ONNX pipeline |
| `tests/performance/test_yolo_latency.py` | Latency benchmark (<100 ms on CPU) |
| `tests/conftest_vision.py` | Shared fixtures: yolo_detector, sample_image |

## Files to Modify

| File | Change |
|------|--------|
| `core/vision/spatial.py` | Wire `ensure_yolo_model()` into `YOLODetector._load_model()` fallback path |
| `core/vision/__init__.py` | Export `model_download` utilities |
| `core/vision/AGENTS.md` | Document model download behavior and YOLOv8n specs |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_yolo_detector.py` | `test_detect_returns_detections` - feed a real image, assert non-empty list of Detection objects with valid bbox, class_name, confidence |
| | `test_detect_empty_frame` - feed a blank white image, assert the result is an empty list or has very low confidence |
| | `test_nms_suppresses_overlapping` - create a scenario with overlapping boxes and verify NMS reduces the count |
| | `test_confidence_filter` - set conf_threshold=0.99 and verify most detections are filtered out |
| | `test_detect_latency_under_100ms` - time a single detect call on 640x480 input, assert < 100 ms |
| `tests/performance/test_yolo_latency.py` | `test_yolo_median_latency_10_runs` - 10 runs, median < 100 ms |

## Acceptance Criteria

- [ ] `YOLODetector` loads `yolov8n.onnx` automatically on first use (auto-download)
- [ ] SHA-256 checksum verified after download
- [ ] `detect()` returns `List[Detection]` with valid `BoundingBox`, `class_name`, `confidence`
- [ ] Empty/blank frames produce an empty detection list (no crashes)
- [ ] NMS correctly suppresses overlapping boxes at IoU > 0.45
- [ ] Confidence filter respects the `conf_threshold` parameter
- [ ] Single-frame detection completes in < 100 ms on CPU (640x480 input)
- [ ] `create_spatial_processor(use_yolo=True)` returns a processor with a ready detector
- [ ] All 5 unit tests pass: `pytest tests/unit/test_yolo_detector.py -v`
- [ ] Benchmark test passes: `pytest tests/performance/test_yolo_latency.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean (no architecture boundary violations)
- [ ] `core/vision/AGENTS.md` updated with model download documentation

## Upstream Dependencies

None (entry point task for the Vision cluster).

## Downstream Unblocks

T-015 (edge-aware-segmentation-hardening), T-016 (spatial-fusion-pipeline)

## Estimated Scope

- New code: ~180 LOC (model_download.py ~60, detector wiring ~20, conftest ~30, tests ~70)
- Modified code: ~15 lines in spatial.py (_load_model fallback)
- Tests: ~120 LOC
- Risk: Medium. ONNX model download adds a network dependency to first-run setup.
  Mitigation: checksum verification, graceful fallback to MockObjectDetector if download
  fails, `pytest.importorskip("onnxruntime")` in test fixtures.
