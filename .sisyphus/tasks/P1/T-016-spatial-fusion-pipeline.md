# T-016: spatial-fusion-pipeline

> Phase: P1 | Cluster: CL-VIS | Risk: Medium | State: not_started

## Objective

Wire `SpatialFuser`, `TemporalFilter` (if added), and `MicroNavFormatter` into a
single end-to-end integration test that exercises `SpatialProcessor.process_frame()`.
The `SpatialProcessor` class exists (lines 914-1063, ~150 lines of orchestration code)
but has never been tested with real detector and depth estimator outputs together. It
runs detection, segmentation, and depth in parallel via `asyncio.gather()`, fuses them
through `SpatialFuser`, and formats the result through `MicroNavFormatter`.

This task validates that the full pipeline produces correct `NavigationOutput` fields
when fed a PIL image, and that the output priority sorting, distance calculations,
and direction assignments are consistent from frame to formatted cue.

## Current State (Codebase Audit 2026-02-25)

- `SpatialProcessor` (lines 914-1063):
  - `__init__` (lines 920-944) accepts optional detector, segmenter, depth_estimator.
    Defaults to `MockObjectDetector`, `EdgeAwareSegmenter`, `SimpleDepthEstimator`.
    Also creates `SpatialFuser()` and `MicroNavFormatter()`.
  - `process_frame()` (lines 961-1062):
    - Checks `self._processing` re-entrancy guard.
    - Step 1: `detections = await self._detector.detect(image)`.
    - Step 2-3: parallel `asyncio.gather(run_segmentation(), run_depth())`.
    - Step 4: `obstacles = self._fuser.fuse(detections, masks, depth_map)`.
    - Step 5: `nav_output = self._formatter.format_all(obstacles)`.
    - Stores `_last_obstacles` (capped at `MAX_DETECTIONS=2`) and `_last_nav_output`.
    - Logs latency warning if > 150 ms.
    - GC after frame if `GC_AFTER_FRAME=True`.
  - `get_quick_warning()` (lines 1064-1104) is a fast path that skips segmentation
    and depth for immediate hazard cues.
- `SpatialFuser` (lines 643-799):
  - `fuse()` (lines 732-798) creates `ObstacleRecord` for each detection. Uses
    `depth_map.get_region_depth(bbox)` to get distance (returns min, median, max;
    uses max as proxy on line 750). Calculates direction from bbox center x position.
    Assigns priority based on distance thresholds (CRITICAL < 1m, NEAR < 2m, FAR < 5m).
    Sorts by priority then distance.
  - `_calculate_direction()` (lines 661-685) maps center_x to Direction enum using
    70-degree horizontal FOV and angle thresholds at -25, -15, -5, 5, 15, 25 degrees.
  - `_generate_action()` (lines 708-730) produces action strings: "stop immediately",
    "step right/left", "proceed with caution", "clear path".
- `MicroNavFormatter` (lines 805-907):
  - `format_short_cue()` (lines 828-864) generates TTS-ready string, max ~15 words.
  - `format_verbose()` (lines 866-892) produces detailed multi-sentence description.
  - `format_telemetry()` (line 894) calls `obs.to_dict()` for JSON output.
  - `format_all()` (lines 898-907) returns `NavigationOutput` dataclass.
- `NavigationOutput` (shared/schemas): `short_cue: str`, `verbose_description: str`,
  `telemetry: List[Dict]`, `has_critical: bool`.
- `ObstacleRecord` (shared/schemas): `id`, `class_name`, `bbox`, `centroid_px`,
  `distance_m`, `direction`, `direction_deg`, `mask_confidence`,
  `detection_confidence`, `priority`, `size_category`, `action_recommendation`.
- `create_spatial_processor()` (lines 1111-1157) factory wires everything together.
- No existing integration tests cover `process_frame()`.

## Implementation Plan

### Step 1: Create integration test with MockObjectDetector + SimpleDepthEstimator

Start with the default mock components to validate the pipeline plumbing. Feed a
640x480 PIL Image, call `process_frame()`, and assert all `NavigationOutput` fields
are populated correctly.

```python
async def test_process_frame_mock_pipeline():
    from core.vision.spatial import create_spatial_processor
    processor = create_spatial_processor()
    image = Image.new("RGB", (640, 480), color=(100, 100, 100))
    nav = await processor.process_frame(image)
    assert isinstance(nav, NavigationOutput)
    assert nav.short_cue  # non-empty string
    assert nav.verbose_description
    assert isinstance(nav.telemetry, list)
    assert isinstance(nav.has_critical, bool)
```

### Step 2: Create integration test with real detector + depth (conditional)

If T-013 and T-014 are complete, write a second test that uses
`create_spatial_processor(use_yolo=True, use_midas=True)` and verifies that
real detections produce meaningful obstacle distances and directions.

```python
@pytest.mark.integration
async def test_process_frame_real_pipeline():
    processor = create_spatial_processor(use_yolo=True, use_midas=True)
    if not processor.is_ready:
        pytest.skip("Real models not available")
    image = Image.open("tests/fixtures/street_scene.jpg")
    nav = await processor.process_frame(image)
    # Real scene should have obstacles
    assert len(nav.telemetry) > 0
    for obs in nav.telemetry:
        assert "distance_m" in obs
        assert "direction" in obs
        assert "priority" in obs
```

### Step 3: Validate obstacle sorting and priority assignment

Write focused tests that verify `SpatialFuser` sorts obstacles correctly:
CRITICAL before NEAR_HAZARD before FAR_HAZARD before SAFE, then by distance
within each priority level.

### Step 4: Validate NavigationOutput field consistency

Ensure `has_critical` is True when any obstacle has `Priority.CRITICAL`, and that
`short_cue` starts with "Stop!" when the top obstacle is critical.

### Step 5: Add end-to-end latency test

Time the full `process_frame()` pipeline and verify it completes within 300 ms
(the pipeline timeout from AGENTS.md).

### Step 6: Test the get_quick_warning() fast path

Verify the fast path returns a sensible string without running segmentation or
depth estimation.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/integration/test_spatial_pipeline.py` | End-to-end tests for SpatialProcessor.process_frame() |
| `tests/fixtures/street_scene.jpg` | Sample test image (640x480, outdoor scene with objects) |

## Files to Modify

| File | Change |
|------|--------|
| `core/vision/AGENTS.md` | Document integration test approach and pipeline invariants |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/integration/test_spatial_pipeline.py` | `test_process_frame_returns_navigation_output` - verify NavigationOutput type and non-empty fields with mock components |
| | `test_process_frame_empty_scene` - feed a blank image, verify "Path clear." in short_cue and has_critical=False |
| | `test_obstacle_priority_sorting` - construct detections at known distances, verify fuser sorts CRITICAL before NEAR before FAR |
| | `test_has_critical_flag_consistency` - verify has_critical=True only when a CRITICAL obstacle exists |
| | `test_direction_assignment_accuracy` - place bbox at known x positions, verify correct Direction enum values |
| | `test_process_frame_latency_under_300ms` - full pipeline completes within SLA |
| | `test_get_quick_warning_fast_path` - verify quick warning returns string, does not run full pipeline |
| | `test_process_frame_real_models` - conditional test with YOLO+MiDaS if available |

## Acceptance Criteria

- [ ] `SpatialProcessor.process_frame()` returns valid `NavigationOutput` for any PIL Image input
- [ ] `short_cue` is a non-empty string for all inputs
- [ ] `verbose_description` provides readable prose description
- [ ] `telemetry` is a list of dicts with `distance_m`, `direction`, `priority` keys
- [ ] `has_critical` is True if and only if any obstacle has `Priority.CRITICAL`
- [ ] Obstacles sorted by priority (CRITICAL first), then by distance
- [ ] Direction assignment correct: left-of-center produces LEFT/SLIGHTLY_LEFT/FAR_LEFT
- [ ] Blank/empty scene produces "Path clear." cue with `has_critical=False`
- [ ] Full pipeline latency < 300 ms on CPU (640x480 input, mock components)
- [ ] `get_quick_warning()` returns a string without raising exceptions
- [ ] Re-entrancy guard works: calling `process_frame` while already processing returns cached output
- [ ] All integration tests pass: `pytest tests/integration/test_spatial_pipeline.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-013 (yolo-onnx-detection-mvp), T-014 (midas-depth-estimation-mvp),
T-015 (edge-aware-segmentation-hardening).

The mock-component tests can be written immediately. The real-model integration tests
require all three upstream tasks to be complete. Structure the test file so mock tests
run unconditionally and real-model tests are gated behind availability checks.

## Downstream Unblocks

T-017 (navigation-output-formatter), T-031 (application-layer integration)

## Estimated Scope

- New code: ~40 LOC (fixture image generation, test utilities)
- Modified code: ~0 lines (no source changes, only tests)
- Tests: ~200 LOC (8 test functions covering mock and real paths)
- Risk: Medium. The mock-component path has low risk since all components exist.
  The real-model path depends on three upstream tasks and model availability. The
  parallel `asyncio.gather()` in `process_frame` could surface timing issues under
  test. Use `pytest-asyncio` auto mode (already configured in pyproject.toml) for
  async test execution.
