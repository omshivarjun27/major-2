# T-023: scene-graph-builder-tests

> Phase: P1 | Cluster: CL-VQA | Risk: Low | State: not_started

## Objective

Write comprehensive unit tests for `SceneGraphBuilder` in `core/vqa/scene_graph.py`. This class
is the translation layer between raw perception outputs and the structured scene representation
consumed by VQA reasoning. It calculates directions from pixel centroids, assigns obstacle
priorities based on depth thresholds, categorizes object sizes relative to the frame, generates
action recommendations, and infers pairwise spatial relations between scene nodes. The tests
must cover the full surface area of the builder: normal multi-detection builds, empty-scene
edge cases, critical-obstacle handling, direction bucketing across the 7-zone horizontal FOV,
size categorization boundaries, spatial relation inference logic, summary generation, and
frame_id propagation from `PerceptionResult` through to the output `SceneGraph`.

## Current State (Codebase Audit 2026-02-25)

- `core/vqa/scene_graph.py` is 356 lines, containing `SceneNode`, `SceneGraph`, and `SceneGraphBuilder`.
- `SceneGraphBuilder.__init__` accepts `image_width` (default 640) and `image_height` (default 480).
- `SceneGraphBuilder.build()` iterates over `PerceptionResult.detections`, extracts median depth via `DepthMap.get_region_depth()`, handles invalid depth (inf or >100) with y-position fallback (lines 177-180).
- `_calculate_direction()` normalizes center_x to [-1, 1], multiplies by `HORIZONTAL_FOV / 2` (35 degrees), and buckets into 7 `Direction` enum values using thresholds at -25, -15, -5, 5, 15, 25 degrees.
- `_calculate_priority()` uses three thresholds: `CRITICAL_THRESHOLD = 1.0`, `NEAR_THRESHOLD = 2.0`, `FAR_THRESHOLD = 5.0` (lines 153-155).
- `_calculate_size()` computes `bbox.area / (img_width * img_height)` and returns `LARGE` (>0.25), `MEDIUM` (>0.05), or `SMALL`.
- `_generate_action()` returns "safe to proceed" for SAFE, "stop and reassess" for critical center obstacles, and directional step recommendations otherwise (lines 303-322).
- `_infer_relations()` checks horizontal offset (>50px threshold), depth difference (>1.0m), and centroid proximity (<100px) to assign `LEFT_OF`, `RIGHT_OF`, `IN_FRONT_OF`, `BEHIND`, and `NEAR` relations (lines 324-350).
- `SceneGraph.generate_summary()` produces natural language text with distance formatting and action recommendations.
- `SceneGraph.frame_id` is populated from `perception.frame_id` via `getattr()` fallback (line 249).
- No existing test file for `scene_graph.py` was found in `tests/unit/`.
- Convenience function `build_scene_graph()` at line 353 wraps builder instantiation.
- All data types (`Detection`, `BoundingBox`, `DepthMap`, `PerceptionResult`, `Priority`, `Direction`, `SizeCategory`, `SpatialRelation`, `ObstacleRecord`) come from `shared.schemas`.

## Implementation Plan

### Step 1: Create test file and fixtures

Create `tests/unit/test_scene_graph.py` with shared fixtures for mock `PerceptionResult` objects.
Build helpers that produce minimal `Detection`, `SegmentationMask`, and `DepthMap` instances for
controlled testing. Each fixture should allow overriding specific fields (e.g., bbox center, depth
values) so individual tests can exercise specific code paths.

### Step 2: Test normal build with detections

Construct a `PerceptionResult` with 2-3 detections at known pixel positions and depths. Verify
the returned `SceneGraph` has the correct number of nodes and obstacles. Check that obstacles are
sorted by priority then distance. Validate that each `ObstacleRecord` contains correct class_name,
distance_m, direction, priority, size_category, and action_recommendation.

### Step 3: Test empty scene

Pass a `PerceptionResult` with zero detections. Confirm the `SceneGraph` has empty nodes and
obstacles lists. Verify `generate_summary()` returns the "path appears clear" message.

### Step 4: Test critical obstacle

Place a detection at depth 0.5m directly ahead (center of frame). Verify `priority == CRITICAL`,
`direction == CENTER`, and `action_recommendation == "stop and reassess"`. Check that
`SceneGraph.get_critical_obstacles()` returns exactly one entry.

### Step 5: Test direction mapping across zones

Create 7 detections with center_x values that map to each `Direction` bucket (FAR_LEFT through
FAR_RIGHT). Verify each detection gets the expected direction enum. Validate the angle calculation
against the 70-degree FOV assumption.

### Step 6: Test size categorization

Create detections with bounding boxes covering >25%, 5-25%, and <5% of the frame area. Verify
LARGE, MEDIUM, and SMALL size categories respectively.

### Step 7: Test spatial relations

Place two detections: one left, one right, with a >50px horizontal gap and >1.0m depth difference.
Verify `LEFT_OF`/`RIGHT_OF` and `IN_FRONT_OF`/`BEHIND` relations are assigned. Also test the
proximity relation with two nodes <100px apart.

### Step 8: Test summary generation and frame_id

Build a scene with one near-hazard obstacle. Verify the summary contains the class name and distance.
Set `frame_id` on the `PerceptionResult` and confirm it propagates to `SceneGraph.frame_id`.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_scene_graph.py` | 8 test cases covering SceneGraphBuilder |

## Files to Modify

| File | Change |
|------|--------|
| `core/vqa/AGENTS.md` | Add test coverage note for scene_graph.py |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_scene_graph.py` | `TestSceneGraphBuilder::test_build_with_detections` |
| | `TestSceneGraphBuilder::test_build_empty_scene` |
| | `TestSceneGraphBuilder::test_critical_obstacle` |
| | `TestSceneGraphBuilder::test_direction_mapping` |
| | `TestSceneGraphBuilder::test_size_categorization` |
| | `TestSceneGraphBuilder::test_spatial_relations` |
| | `TestSceneGraphBuilder::test_summary_generation` |
| | `TestSceneGraphBuilder::test_frame_id_propagation` |

## Acceptance Criteria

- [ ] All 8 tests pass with `pytest tests/unit/test_scene_graph.py -v`
- [ ] Tests use only `shared.schemas` types, no local type redefinitions
- [ ] Each direction zone (FAR_LEFT through FAR_RIGHT) is covered by at least one assertion
- [ ] Critical priority test verifies depth < 1.0m triggers `Priority.CRITICAL`
- [ ] Size categorization test covers all three `SizeCategory` enum values
- [ ] Spatial relation test verifies at least 3 of 5 relation types (`LEFT_OF`, `RIGHT_OF`, `IN_FRONT_OF`, `BEHIND`, `NEAR`)
- [ ] Empty scene test asserts zero nodes, zero obstacles, and "clear" summary
- [ ] frame_id propagation test sets a known frame_id and checks `SceneGraph.frame_id`
- [ ] No test exceeds 60s timeout
- [ ] `ruff check tests/unit/test_scene_graph.py` passes clean
- [ ] `lint-imports` passes (no architecture violations)

## Upstream Dependencies

- **T-016** (shared schemas): `Detection`, `BoundingBox`, `DepthMap`, `PerceptionResult`, and all enum types must be stable and importable from `shared.schemas`.

## Downstream Unblocks

- **T-024** (perception-orchestrator-tests): Can proceed once scene graph tests validate the data structures that the perception pipeline produces.

## Estimated Scope

- **Effort**: ~3 hours
- **Lines of test code**: 200-280
- **Risk**: Low. Pure unit tests with no external dependencies, all data types are well-defined in shared.schemas.
- **Parallel**: Yes. Can run alongside any non-VQA task.
- **Environment**: Local GPU not required. CPU-only pytest execution.
