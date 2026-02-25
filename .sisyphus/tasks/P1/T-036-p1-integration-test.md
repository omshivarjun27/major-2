# T-036: p1-integration-test

> Phase: P1 | Cluster: CL-APV | Risk: Medium | State: not_started

## Objective

Create an end-to-end integration test that processes a mock image through the full P1
pipeline: object detection -> depth estimation -> segmentation -> spatial fusion ->
scene graph construction -> VQA reasoning -> memory storage -> memory retrieval. This
test validates that all P1 core components wire together correctly and produce
consistent results across a single frame.

The test uses mock backends (MockObjectDetector, SimpleDepthEstimator) to avoid ONNX
model dependencies, but exercises the real data flow through every layer. Every
intermediate result is validated for type correctness and field completeness.

## Current State (Codebase Audit 2026-02-25)

- Core pipeline components available after P1:
  - `core/vision/spatial.py`: SpatialProcessor, create_spatial_processor
  - `core/vqa/scene_graph.py`: SceneGraphBuilder, build_scene_graph
  - `core/vqa/vqa_reasoner.py`: VQAReasoner, QuickAnswers
  - `core/vqa/perception.py`: PerceptionPipeline, create_pipeline
  - `core/memory/indexer.py`: FAISSIndexer
  - `core/memory/embeddings.py`: TextEmbedder, MockTextEmbedder
  - `core/memory/retriever.py`: MemoryRetriever
  - `core/memory/ingest.py`: MemoryIngester
  - `core/reasoning/engine.py`: ReasoningEngine (created in T-032)
- All use `shared/schemas/__init__.py` types: Detection, PerceptionResult, ObstacleRecord,
  NavigationOutput, DepthMap, SegmentationMask, etc.
- No end-to-end integration test exists that exercises all these components together.
- P0 has `tests/integration/test_p0_security_smoke.py` as a pattern reference.
- Mock components are available: MockObjectDetector, SimpleDepthEstimator, MockTextEmbedder,
  MockFAISSIndexer.

## Implementation Plan

### Step 1: Set up test fixtures

Create fixtures for each pipeline component using mock backends:

```python
@pytest.fixture
def spatial_processor():
    return create_spatial_processor(use_yolo=False, use_midas=False)

@pytest.fixture
def scene_builder():
    return SceneGraphBuilder()

@pytest.fixture
def memory_system():
    indexer = MockFAISSIndexer()
    embedder = MockTextEmbedder()
    retriever = MemoryRetriever(indexer=indexer, embedder=embedder)
    return indexer, embedder, retriever

@pytest.fixture
def sample_frame():
    return Image.new("RGB", (640, 480), color=(100, 150, 200))
```

### Step 2: Write pipeline flow test

Process a frame through spatial -> scene graph -> navigation output. Validate each
intermediate result type and field presence.

### Step 3: Write memory round-trip test

After spatial processing, store the navigation summary in memory, then retrieve it
and verify the result matches.

### Step 4: Write reasoning engine integration test

Feed a question + image through ReasoningEngine, verify it routes to VQA and returns
a ReasoningResult.

### Step 5: Write frame_id consistency test

Verify that all results from a single frame share the same `frame_id`.

### Step 6: Write latency budget test

Time the full pipeline and assert it completes within 500ms (the hot path SLA).

## Files to Create

| File | Purpose |
|------|---------|
| `tests/integration/test_p1_pipeline.py` | End-to-end integration test for full P1 pipeline |

## Files to Modify

| File | Change |
|------|--------|
| `tests/AGENTS.md` | Document P1 integration test location and scope |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/integration/test_p1_pipeline.py` | `test_spatial_to_scene_graph` - process frame through spatial, feed to scene graph, verify SceneGraph |
| | `test_full_pipeline_types` - process frame through all stages, verify each intermediate is correct type |
| | `test_memory_store_and_retrieve` - store navigation summary, retrieve by query, verify match |
| | `test_reasoning_engine_visual_query` - ReasoningEngine with image + question, verify ReasoningResult |
| | `test_frame_id_consistency` - verify spatial result and scene graph share same frame_id |
| | `test_pipeline_latency_under_500ms` - time full pipeline, assert < 500ms with mock backends |

## Acceptance Criteria

- [ ] Frame flows through spatial -> scene graph -> navigation output without errors
- [ ] All intermediate types are correct (PerceptionResult, SceneGraph, NavigationOutput)
- [ ] Memory round-trip preserves navigation summary content
- [ ] ReasoningEngine dispatches visual question to VQA subsystem
- [ ] frame_id is consistent across all results from same frame
- [ ] Full pipeline with mock backends completes in < 500ms
- [ ] All 6 tests pass: `pytest tests/integration/test_p1_pipeline.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-035 (p1-validation-suite) — validation must confirm all components exist first.

## Downstream Unblocks

T-037 (p1-architecture-check) — architecture check runs after integration is verified.

## Estimated Scope

- New code: ~0 LOC (test-only task)
- Modified code: ~0 lines
- Tests: ~180 LOC
- Risk: Medium. Integration test depends on all P1 components working together.
  Failures here indicate wiring issues between components.
