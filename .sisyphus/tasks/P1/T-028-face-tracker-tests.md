# T-028: face-tracker-tests

> Phase: P1 | Cluster: CL-FACE | Risk: Low | State: not_started

## Objective

Write comprehensive unit tests for `FaceTracker` in `core/face/face_tracker.py` (212
lines). The tracker uses IoU-based greedy matching to associate face detections across
frames, assigns stable track IDs, and removes faces that disappear for more than
`max_disappeared` consecutive frames. This task writes 8 tests covering the full
tracker lifecycle without modifying any production code.

Testing the tracker validates its core invariants: new faces get unique IDs, consistent
faces keep the same ID across frames, disappeared faces are cleaned up, and the max
tracked limit is respected.

## Current State (Codebase Audit 2026-02-25)

- `core/face/face_tracker.py` (212 lines):
  - `TrackerConfig` dataclass (line 15): `max_tracked` (default 10), `max_disappeared`
    (default 30 frames), `min_iou_threshold` (default 0.3).
  - `TrackedFace` dataclass (line 25): `track_id` (str), `bbox` (BoundingBox),
    `last_seen` (int), `disappeared_count` (int), `first_seen` (int), `confidence` (float).
  - `FaceTracker` class (line 45):
    - `__init__()`: initializes `_tracked` dict, `_next_id` counter, `_frame_count`.
    - `update(detections: list[Detection]) -> list[TrackedFace]` (line 65): main method.
      Computes IoU matrix between tracked faces and new detections, performs greedy
      matching, updates matched tracks, registers new faces, increments disappeared
      count for unmatched tracks, prunes expired tracks.
    - `_compute_iou_matrix()` (line 120): builds NxM IoU matrix between tracked and
      detected bounding boxes using standard area-based IoU.
    - `_register_face()` (line 150): creates new TrackedFace with unique ID.
    - `_deregister_face()` (line 165): removes face from tracking dict.
    - `get_tracked()` (line 175): returns list of all currently tracked faces.
    - `clear()` (line 185): resets all tracking state.
    - `health()` (line 195): returns dict with track count and frame count.
  - `_compute_iou()` static method (line 200): single-pair IoU computation.
- No tests exist for `FaceTracker` in any test directory.
- `TrackedFace` uses `BoundingBox` from `shared/schemas/__init__.py`.
- Tracker is frame-count-based, not time-based. Each `update()` call increments frame counter.

## Implementation Plan

### Step 1: Create test fixtures

Set up fixtures for `FaceTracker` with default config, and helper functions to create
mock `Detection` objects with known bounding boxes.

```python
import pytest
from shared.schemas import Detection, BoundingBox
from core.face.face_tracker import FaceTracker, TrackerConfig

@pytest.fixture
def tracker():
    config = TrackerConfig(max_tracked=5, max_disappeared=3)
    return FaceTracker(config=config)

def make_detection(x1, y1, x2, y2, conf=0.9):
    return Detection(
        id="det_test",
        class_name="face",
        confidence=conf,
        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
    )
```

### Step 2: Write 8 unit tests

Cover initial tracking, multi-frame association, disappearance, max limit, IoU
computation, track ID uniqueness, clear/reset, and health check.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_face_tracker.py` | 8 unit tests for FaceTracker lifecycle |

## Files to Modify

| File | Change |
|------|--------|
| `core/face/AGENTS.md` | Document test coverage for FaceTracker |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_face_tracker.py` | `test_initial_frame_creates_tracks` - first update with 2 detections creates 2 tracked faces with unique IDs |
| | `test_same_face_keeps_track_id` - update with same bbox in consecutive frames, verify track_id unchanged |
| | `test_disappeared_face_removed` - update with face, then 4 empty updates (max_disappeared=3), verify face removed |
| | `test_max_tracked_limit` - send 8 detections to tracker with max_tracked=5, verify only 5 tracked |
| | `test_iou_computation_identical_boxes` - two identical bboxes have IoU=1.0 |
| | `test_iou_computation_no_overlap` - two non-overlapping bboxes have IoU=0.0 |
| | `test_clear_resets_all_state` - add faces, call clear(), verify get_tracked returns empty |
| | `test_health_reports_counts` - add faces, verify health() returns correct track_count and frame_count |

## Acceptance Criteria

- [ ] All 8 tests pass: `pytest tests/unit/test_face_tracker.py -v`
- [ ] Track ID uniqueness verified across multiple update cycles
- [ ] Disappeared face pruning triggers at correct frame count
- [ ] Max tracked limit prevents exceeding configured cap
- [ ] IoU computation returns 1.0 for identical boxes and 0.0 for non-overlapping
- [ ] No modifications to `core/face/face_tracker.py`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean
- [ ] `core/face/AGENTS.md` updated

## Upstream Dependencies

None (entry point task for the Face cluster).

## Downstream Unblocks

T-029 (face-consent-integration) — needs verified tracker behavior before wiring consent.

## Estimated Scope

- New code: ~0 LOC (test-only task)
- Modified code: ~0 lines
- Tests: ~130 LOC
- Risk: Low. Pure test addition, no production code changes.
