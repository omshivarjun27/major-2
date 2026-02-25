# T-024: perception-orchestrator-tests

> Phase: P1 | Cluster: CL-VQA | Risk: Low | State: not_started

## Objective

Write unit and benchmark tests for `PerceptionPipeline` in `core/vqa/perception.py`. This
720-line module is the orchestrator that runs object detection, edge-aware segmentation, and depth
estimation in parallel via `asyncio.gather`. Tests must cover the `create_pipeline` factory
function, the `process()` method with mock detectors, empty detection fast path, parallel
execution timing, VideoFrame-to-numpy conversion logic, and a benchmark assertion that the
full pipeline completes within the 300ms latency SLA. The pipeline is the critical hot path
for the entire VQA system, so these tests validate both correctness and performance.

## Current State (Codebase Audit 2026-02-25)

- `core/vqa/perception.py` is 720 lines containing 6 classes and 3 factory functions.
- `MockObjectDetector` (lines 117-175): returns deterministic detections based on image dimensions. Has `CLASSES` tuple with 8 class names. Generates 1-3 detections depending on image width.
- `YOLODetector` (lines 178-279): ONNX/PyTorch YOLO with 80 COCO classes. Falls back gracefully when model isn't loaded.
- `EdgeAwareSegmenter` (lines 286-364): processes at reduced resolution (160x120). Uses Canny or variance-based boundary confidence.
- `SimpleDepthEstimator` (lines 371-414): heuristic y-position depth (top=far, bottom=near). No caching, `DOWNSCALE = 4`.
- `MiDaSDepthEstimator` (lines 417-493): PyTorch hub MiDaS with ONNX fallback. Falls back to `SimpleDepthEstimator` when not ready.
- `PerceptionPipeline` (lines 500-653): accepts detector, segmenter, depth_estimator. The `process()` method runs detection first, then `asyncio.gather(run_segmentation(), run_depth())` in parallel (line 625). Returns `PerceptionResult` with timing.
- `_to_numpy()` helper at line 46 handles numpy arrays, PIL Images, and LiveKit VideoFrame objects.
- Factory functions: `create_detector()` (line 660), `create_depth_estimator()` (line 670), `create_pipeline()` (line 680). `create_pipeline` auto-detects YOLO/MiDaS model files on disk.
- `PerceptionPipeline.process()` has a fast-path exit for empty detections (lines 595-609) returning a default 5.0m depth map.
- Public accessors: `.detector`, `.depth_estimator`, `.segmenter`, `.is_ready` (lines 527-544).
- `MAX_DETECTIONS = 5` (line 80), `DETECTION_CONFIDENCE_THRESHOLD = 0.5` (line 81).
- Structured event logging via `_log_event()` at line 639.
- No existing dedicated test file for perception.py found in `tests/unit/`.

## Implementation Plan

### Step 1: Create test file with async fixtures

Create `tests/unit/test_perception.py`. Since pytest async mode is `auto`, tests can be plain
`async def`. Build fixtures that produce numpy test images of known dimensions (e.g., 640x480
black image, 800x600 gradient image). Create a fixture that returns a pipeline built with
`create_pipeline(use_mock=True)`.

### Step 2: Test create_pipeline factory

Verify `create_pipeline(use_mock=True)` returns a `PerceptionPipeline` with a `MockObjectDetector`.
Check that `pipeline.is_ready` is True. Verify `pipeline.detector` is an instance of `MockObjectDetector`.
Test that `create_pipeline(use_yolo=True)` falls back to mock when no model file exists.

### Step 3: Test process with mock detector

Call `pipeline.process()` with a 640x480 numpy image. Verify the result is a `PerceptionResult`
with 3 detections (mock returns 3 for width > 500). Check `result.image_size == (640, 480)`.
Confirm `result.latency_ms > 0`. Verify masks list has entries and depth_map is populated.

### Step 4: Test process with empty detections

Create a custom detector that returns an empty list. Build a pipeline with it. Verify the fast
path returns zero detections, zero masks, and a default depth map with value 5.0.

### Step 5: Test parallel execution timing

Inject slow mock segmenter and depth estimator (each sleeping ~50ms). Measure total pipeline
time. Assert it's significantly less than the sum of individual sleeps, proving parallel execution
via `asyncio.gather`.

### Step 6: Test VideoFrame conversion

Create a mock object with a `.convert()` method but no `.shape` or `.size` attributes, simulating
a LiveKit VideoFrame. Pass it through `_to_numpy()` and verify the result is a valid numpy array.
Also test the fallback path that returns a 480x640 zeros array on conversion failure.

### Step 7: Test latency SLA benchmark

Run `pipeline.process()` with mock components 10 times. Assert the average and p95 latency
are both under 300ms. Mark this test with `@pytest.mark.slow` for selective execution.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_perception.py` | 6 unit tests + 1 benchmark for PerceptionPipeline |

## Files to Modify

| File | Change |
|------|--------|
| `core/vqa/AGENTS.md` | Add test coverage note for perception.py |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_perception.py` | `TestPerceptionPipeline::test_create_pipeline` |
| | `TestPerceptionPipeline::test_process_with_mock_detector` |
| | `TestPerceptionPipeline::test_process_empty_detections` |
| | `TestPerceptionPipeline::test_parallel_execution_timing` |
| | `TestPerceptionPipeline::test_videoframe_conversion` |
| | `TestPerceptionPipeline::test_latency_under_300ms` |

## Acceptance Criteria

- [ ] All 6 tests pass with `pytest tests/unit/test_perception.py -v`
- [ ] `test_create_pipeline` validates factory returns correct detector type
- [ ] `test_process_with_mock_detector` asserts 3 detections for a 640x480 image
- [ ] `test_process_empty_detections` confirms fast path returns default depth map
- [ ] `test_parallel_execution_timing` proves gather-based parallelism (total < sum of parts)
- [ ] `test_videoframe_conversion` covers both success and fallback paths of `_to_numpy()`
- [ ] `test_latency_under_300ms` asserts average mock-pipeline latency < 300ms
- [ ] No test imports from `application/`, `infrastructure/`, or `apps/`
- [ ] All tests use `async def` (pytest asyncio auto mode)
- [ ] `ruff check tests/unit/test_perception.py` passes clean
- [ ] `lint-imports` passes with no violations

## Upstream Dependencies

- **T-023** (scene-graph-builder-tests): Scene graph tests validate the `PerceptionResult` data structures that this pipeline produces. Completing T-023 first confirms the downstream consumer works correctly.

## Downstream Unblocks

- **T-025** (visual-qa-reasoner-tests): Reasoner tests depend on understanding how `PerceptionResult` and `SceneGraph` are produced.
- **T-032** (frame-processing integration): Integration tests consume `PerceptionPipeline.process()` output.

## Estimated Scope

- **Effort**: ~4 hours
- **Lines of test code**: 220-300
- **Risk**: Low. MockObjectDetector provides deterministic results. Async tests are straightforward with pytest auto mode.
- **Parallel**: Yes. Can run alongside non-VQA tasks.
- **Environment**: Local GPU not required. Mock components only.
