# T-031: frame-processing-integration

> Phase: P1 | Cluster: CL-APP | Risk: Medium | State: not_started

## Objective

Wire the `FrameOrchestrator` in `application/frame_processing/` to use the real
`SpatialProcessor` from `core/vision/spatial.py` instead of relying on externally
injected mock callables. The orchestrator already has a complete parallel dispatch
system (598 LOC) that accepts detector, depth_estimator, and segmenter as callable
parameters. This task creates a thin integration shim that binds `SpatialProcessor`
components to those callable slots and adds an end-to-end integration test that
processes a frame through the full application layer.

The goal is to close the gap between the working core vision pipeline and the
application orchestration layer, proving that a real image can flow from
`LiveFrameManager` capture through detection, depth, segmentation, fusion,
scene graph construction, and output formatting without manual wiring at the
caller site.

## Current State (Codebase Audit 2026-02-25)

- `application/frame_processing/frame_orchestrator.py` (598 lines):
  - `FrameOrchestrator.process_frame()` (line 202) accepts optional callables:
    `detector`, `depth_estimator`, `segmenter`, `ocr_fn`, `qr_fn`, `face_fn`, `action_fn`.
  - Currently, callers must pass these functions manually. No default wiring exists.
  - `_timed_call()` (line 501) wraps each module call with latency tracking.
  - `_assign_result()` (line 514) maps module results to `FusedFrameResult` slots.
  - Scene graph is built at lines 300-338 using an injected `scene_graph_builder`.
  - Confidence cascade integration at lines 343-381 applies heuristics and filtering.
- `application/frame_processing/live_frame_manager.py`: Manages frame ring buffer
  (30 frames) with `TimestampedFrame` dataclass. Provides `is_fresh()` checks.
- `application/frame_processing/freshness.py`: Enforces max frame age (500ms default).
- `application/frame_processing/confidence_cascade.py`: 3-tier confidence filtering.
- `core/vision/spatial.py` (1157 lines):
  - `SpatialProcessor` (line 914) orchestrates: detect -> segment -> depth -> fuse -> format.
  - `create_spatial_processor()` factory (line 1111) returns a configured processor.
  - `MockObjectDetector` (line 121) returns 1 hardcoded detection.
  - `SpatialProcessor.process_frame()` (line 961) runs parallel segmentation and depth.
- `core/vqa/scene_graph.py` (356 lines): `SceneGraph` builder that accepts `PerceptionResult`.
- No existing integration test covers `FrameOrchestrator` + `SpatialProcessor` together.
- `application/frame_processing/AGENTS.md` documents the frame lifecycle but doesn't
  mention how to wire real detectors.
- The `application/` layer may import from `core/` and `shared/` only.

## Implementation Plan

### Step 1: Create integration shim module

Create `application/frame_processing/spatial_binding.py` that wraps `SpatialProcessor`
components into the callable interface expected by `FrameOrchestrator.process_frame()`.

```python
from typing import Any, List, Optional
from core.vision.spatial import (
    SpatialProcessor, create_spatial_processor,
    BaseDetector, BaseSegmenter, BaseDepthEstimator,
)
from shared.schemas import Detection, SegmentationMask, DepthMap


def create_frame_bindings(
    processor: Optional[SpatialProcessor] = None,
) -> dict:
    """Return a dict of callables suitable for FrameOrchestrator.process_frame().

    Returns dict with keys: detector, depth_estimator, segmenter.
    """
    proc = processor or create_spatial_processor()

    async def detect(image: Any) -> List[Detection]:
        return await proc._detector.detect(image)

    async def estimate_depth(image: Any) -> DepthMap:
        return await proc._depth_estimator.estimate_depth(image)

    async def segment(image: Any) -> List[SegmentationMask]:
        # Needs detections first, so run detection inline
        dets = await proc._detector.detect(image)
        return await proc._segmenter.segment(image, dets)

    return {
        "detector": detect,
        "depth_estimator": estimate_depth,
        "segmenter": segment,
    }
```

### Step 2: Add convenience factory

Add a `create_wired_orchestrator()` factory function that returns a `FrameOrchestrator`
pre-configured with `SpatialProcessor` bindings and a `SceneGraph` builder. This
provides a single-call setup for callers like the LiveKit agent.

### Step 3: Update process_frame default behavior

Add optional `default_bindings` to `FrameOrchestratorConfig` so the orchestrator can
fall back to wired spatial components when callers don't pass explicit callables.
This preserves backward compatibility while enabling zero-config usage.

### Step 4: Write integration test

Create an integration test that:
1. Creates a `SpatialProcessor` with `MockObjectDetector`
2. Creates a `FrameOrchestrator` with the spatial bindings
3. Feeds a synthetic `TimestampedFrame` (640x480 PIL Image)
4. Asserts the `FusedFrameResult` contains detections, depth_map, and a scene graph
5. Verifies telemetry records correct module latencies

### Step 5: Update AGENTS.md

Document the spatial binding module and the `create_wired_orchestrator()` factory
in `application/frame_processing/AGENTS.md`.

## Files to Create

| File | Purpose |
|------|---------|
| `application/frame_processing/spatial_binding.py` | Wraps SpatialProcessor into FrameOrchestrator-compatible callables |
| `tests/integration/test_frame_spatial_integration.py` | End-to-end test: frame -> orchestrator -> spatial -> result |

## Files to Modify

| File | Change |
|------|--------|
| `application/frame_processing/__init__.py` | Export `create_frame_bindings`, `create_wired_orchestrator` |
| `application/frame_processing/frame_orchestrator.py` | Add optional `default_bindings` config support |
| `application/frame_processing/AGENTS.md` | Document spatial binding, wiring pattern, and factory |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/integration/test_frame_spatial_integration.py` | `test_wired_orchestrator_detects_objects` - process frame through full pipeline, assert detections in FusedFrameResult |
| | `test_wired_orchestrator_produces_depth` - verify depth_map is populated with valid DepthMap |
| | `test_wired_orchestrator_builds_scene_graph` - verify scene_graph is populated when scene builder is provided |
| | `test_wired_orchestrator_records_telemetry` - verify telemetry has latencies for detection, depth modules |
| | `test_stale_frame_rejected` - pass a very old TimestampedFrame, verify freshness gate triggers |
| | `test_create_frame_bindings_returns_callables` - verify returned dict has correct keys and values are async callables |
| | `test_pipeline_timeout_returns_partial` - set very low timeout, verify partial results returned without crash |
| | `test_fused_result_freshness` - verify FusedFrameResult.is_fresh() works correctly |

## Acceptance Criteria

- [ ] `spatial_binding.py` wraps SpatialProcessor components into FrameOrchestrator-compatible callables
- [ ] `create_wired_orchestrator()` returns a ready-to-use FrameOrchestrator with spatial bindings
- [ ] Processing a 640x480 frame through the wired orchestrator produces a non-empty `FusedFrameResult`
- [ ] `FusedFrameResult.detections` contains at least 1 Detection (from MockObjectDetector)
- [ ] `FusedFrameResult.depth_map` is a valid DepthMap (not None)
- [ ] Telemetry records latency for each module (detection, depth)
- [ ] Stale frames are rejected by the freshness gate
- [ ] Pipeline timeout does not raise; returns partial results
- [ ] 8 integration tests pass: `pytest tests/integration/test_frame_spatial_integration.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean (application imports only from core and shared)
- [ ] `application/frame_processing/AGENTS.md` updated with wiring documentation

## Upstream Dependencies

T-016 (spatial-fusion-pipeline), T-030 (pipeline-stub-replacement), T-032 (reasoning-engine-mvp).

## Downstream Unblocks

None (terminal task in the CL-APP cluster).

## Estimated Scope

- New code: ~150 LOC (spatial_binding.py ~80, factory additions ~40, __init__.py ~30)
- Modified code: ~20 lines in frame_orchestrator.py (default_bindings config)
- Tests: ~180 LOC
- Risk: Medium. The main concern is latency introduced by double-detection in the
  segmenter binding (needs detections before segmenting). Mitigation: cache detection
  results or restructure the binding to pass detections downstream. Also, ensuring
  the `SpatialProcessor` internal components are accessible for binding requires
  careful API design to avoid exposing private members.
