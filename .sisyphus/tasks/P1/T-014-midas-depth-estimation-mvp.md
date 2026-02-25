# T-014: midas-depth-estimation-mvp

> Phase: P1 | Cluster: CL-VIS | Risk: Medium | State: not_started

## Objective

Replace `SimpleDepthEstimator` with a working MiDaS v2.1 small ONNX pipeline in
`core/vision/spatial.py`. The `MiDaSDepthEstimator` class already exists (lines
511-637) with both ONNX inference (`_onnx_depth`) and a PyTorch Hub fallback path.
Neither has been tested with an actual model file. This task wires up automatic model
download for `midas_small.onnx`, adds validation fixtures, and delivers 5 unit tests
covering depth estimation, fallback behavior, metric normalization, output resolution,
and CPU latency.

`SimpleDepthEstimator` (lines 452-509) produces a linear gradient that maps row
position to depth. It's fast but tells you nothing real about the scene. Swapping it
for MiDaS gives the fusion pipeline actual per-pixel depth data, which is required
before T-016 can produce meaningful `ObstacleRecord` distances.

## Current State (Codebase Audit 2026-02-25)

- `SimpleDepthEstimator` (lines 452-509) returns a pre-allocated linear gradient
  from `max_depth` (top row) to `min_depth` (bottom row). Uses `DEPTH_DOWNSCALE=4`
  for resolution. Caches the depth array when dimensions match.
- `MiDaSDepthEstimator` (lines 511-637):
  - `__init__` takes optional `model_path` and `model_type` (default `"MiDaS_small"`).
  - `_load_model()` (line 527) tries ONNX first (checks file exists), then
    `torch.hub.load("intel-isl/MiDaS", ...)` as fallback.
  - `estimate_depth()` (line 552) dispatches to `_onnx_depth()` or PyTorch inference.
    Falls back to `SimpleDepthEstimator` if model not ready.
  - `_onnx_depth()` (lines 601-636): resizes input to 256x256, applies ImageNet
    normalization (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]), transposes
    to NCHW, runs ONNX session, squeezes output, resizes back to original dims.
  - Metric normalization (lines 583-588): min-max normalizes depth, then scales to
    0.5-10.0m range. Sets `is_metric=False` (approximate, not calibrated).
- `create_spatial_processor()` (line 1143) checks `use_midas` flag, instantiates
  `MiDaSDepthEstimator` or falls back to `SimpleDepthEstimator`.
- `.env` references `MIDAS_MODEL_PATH=models/midas_small.onnx` but no file is shipped.
- `TORCH_AVAILABLE` guard (lines 63-68) governs the PyTorch Hub path.
- `ONNX_AVAILABLE` guard (lines 70-75) governs the ONNX path.
- No existing tests cover either `MiDaSDepthEstimator` or `SimpleDepthEstimator`.

## Implementation Plan

### Step 1: Add MiDaS model auto-download

Extend the model download utility (from T-013 or create standalone) to support
MiDaS v2.1 small ONNX. The model is available from the Intel ISL GitHub releases.

```python
MIDAS_SMALL_URL = "https://github.com/isl-org/MiDaS/releases/download/v2_1/midas_v21_small_256.onnx"
MIDAS_SMALL_SHA256 = "<actual_hash>"

def ensure_midas_model(dest: str = "models/midas_small.onnx") -> str:
    path = Path(dest)
    if path.exists():
        return str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(MIDAS_SMALL_URL, str(path))
    # Verify SHA-256
    ...
    return str(path)
```

### Step 2: Wire auto-download into MiDaSDepthEstimator._load_model()

Add the same pattern used for YOLO: if `self._model_path` is `None` or the file
doesn't exist, call `ensure_midas_model()` before attempting to create the ONNX
session.

```python
def _load_model(self):
    if not self._model_path or not Path(self._model_path).exists():
        try:
            self._model_path = ensure_midas_model()
        except Exception as e:
            logger.warning("MiDaS download failed: %s", e)
    # ... existing ONNX/PyTorch loading
```

### Step 3: Add depth-map validation conftest fixture

Create a fixture that instantiates `MiDaSDepthEstimator` with auto-download and
provides a helper function to validate depth map properties (shape, dtype, value
range).

```python
@pytest.fixture(scope="session")
def midas_estimator():
    ort = pytest.importorskip("onnxruntime")
    from core.vision.spatial import MiDaSDepthEstimator
    estimator = MiDaSDepthEstimator()
    if not estimator._ready:
        pytest.skip("MiDaS model not available")
    return estimator

def assert_valid_depth_map(depth_map):
    """Validate DepthMap invariants."""
    assert depth_map.depth_array.dtype == np.float32
    assert depth_map.depth_array.ndim == 2
    assert depth_map.min_depth <= depth_map.max_depth
    assert depth_map.min_depth >= 0
```

### Step 4: Write 5 unit tests

Cover estimation on a real image, fallback when model is missing, metric normalization
bounds, output resolution matching, and CPU latency.

### Step 5: Add benchmark test

Performance test that runs 10 consecutive depth estimations and asserts median
under 100 ms on CPU for a 640x480 input.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_midas_depth.py` | 5 unit tests for MiDaSDepthEstimator |
| `tests/performance/test_midas_latency.py` | Latency benchmark (<100 ms on CPU) |

## Files to Modify

| File | Change |
|------|--------|
| `core/vision/model_download.py` | Add `ensure_midas_model()` function (if T-013 created this file; otherwise create it) |
| `core/vision/spatial.py` | Wire `ensure_midas_model()` into `MiDaSDepthEstimator._load_model()` |
| `tests/conftest_vision.py` | Add `midas_estimator` fixture and `assert_valid_depth_map` helper |
| `core/vision/AGENTS.md` | Document MiDaS model download and expected input/output shapes |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_midas_depth.py` | `test_estimate_depth_returns_depth_map` - feed a 640x480 image, assert DepthMap with valid depth_array shape, dtype float32, min_depth <= max_depth |
| | `test_fallback_to_simple_estimator` - instantiate MiDaSDepthEstimator with bad path and no torch, verify it falls back to SimpleDepthEstimator output |
| | `test_metric_normalization_range` - verify depth values are in [0.5, 10.0] range after normalization |
| | `test_output_resolution_matches_input` - feed images of various sizes (320x240, 640x480, 1280x720), verify depth_array dimensions match original H x W |
| | `test_depth_latency_under_100ms` - time a single estimate_depth call on 640x480, assert < 100 ms |
| `tests/performance/test_midas_latency.py` | `test_midas_median_latency_10_runs` - 10 runs, median < 100 ms |

## Acceptance Criteria

- [ ] `MiDaSDepthEstimator` loads `midas_small.onnx` automatically on first use
- [ ] SHA-256 checksum verified after download
- [ ] `estimate_depth()` returns a `DepthMap` with float32 depth_array matching input dimensions
- [ ] Depth values normalized to [0.5, 10.0] meter range
- [ ] `is_metric=False` set correctly (approximate, not calibrated)
- [ ] Fallback to `SimpleDepthEstimator` works when ONNX model unavailable
- [ ] PyTorch Hub fallback works when onnxruntime is not installed but torch is
- [ ] Single-frame depth estimation completes in < 100 ms on CPU (640x480 input)
- [ ] `create_spatial_processor(use_midas=True)` returns a processor with MiDaS depth
- [ ] All 5 unit tests pass: `pytest tests/unit/test_midas_depth.py -v`
- [ ] Benchmark test passes: `pytest tests/performance/test_midas_latency.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean
- [ ] `core/vision/AGENTS.md` updated with MiDaS documentation

## Upstream Dependencies

None (entry point task, parallel with T-013).

## Downstream Unblocks

T-016 (spatial-fusion-pipeline)

## Estimated Scope

- New code: ~150 LOC (model_download addition ~40, estimator wiring ~15, conftest ~25, tests ~70)
- Modified code: ~12 lines in spatial.py (_load_model fallback)
- Tests: ~110 LOC
- Risk: Medium. MiDaS ONNX model is ~40 MB, which may slow first-run CI. Mitigations:
  cache model in CI artifacts, skip tests with `pytest.importorskip("onnxruntime")`,
  graceful fallback to SimpleDepthEstimator. The ImageNet normalization constants are
  hardcoded and match the official MiDaS preprocessing; changing model versions would
  require updating these.
