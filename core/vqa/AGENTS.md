# core/vqa/AGENTS.md
Complete low-latency Visual Q&A system: detection→segmentation→depth→scene-graph→LLM reasoning.
**Target**: ≤300ms vision processing, ≤500ms total latency.

## WHERE TO LOOK
| File | Purpose |
|------|---------|
| `perception.py` | Core pipeline orchestrator & implementation factories. |
| `vqa_reasoner.py` | LMM (Ollama qwen3-vl), prompts, and QuickAnswers logic. |
| `priority_scene.py` | Hazard detection, priority sorting, and direction mapping. |
| `spatial_fuser.py` | Fuses bbox+mask+depth with temporal filtering. |
| `scene_graph.py` | Structured representation of the current frame context. |
| `vqa_memory.py` | **Session-scoped** visual context (NOT the RAG engine). |
| `api_endpoints.py` | FastAPI router for VQA operations. |
| `api_schema.py` | Pydantic models for VQA requests/responses. |

## FACTORIES
```python
from core.vqa.perception import create_pipeline, create_detector, create_depth_estimator

# Full pipeline: collect detections, masks, and depth in parallel
pipeline = create_pipeline(use_yolo=True, use_midas=True, enable_segmentation=True)

# Individual component factories (use mock if models missing)
detector = create_detector(use_yolo=False)        # YOLODetector or MockObjectDetector
depth_est = create_depth_estimator(use_midas=True) # MiDaSDepthEstimator or SimpleDepthEstimator
```

## PIPELINE FLOW
`FRAME → detect() → segment() → estimate_depth() [parallel] → SpatialFuser → SceneGraph → VQAReasoner → NavigationOutput`

## KEY LOGIC
- **QuickAnswers**: Bypasses the LMM for deterministic queries (e.g., "how many objects?", "what is closest?").
- **Temporal Filtering**: Objects must appear in `N` consecutive frames (or have high confidence) before being reported.
- **Direction Mapping**: Translates degrees/centroids to natural language cues (e.g., "ahead", "slightly left").
- **Priority Sorting**: Obstacles <1m are marked as `CRITICAL` and reported immediately.

## GOTCHAS
- **Memory Disambiguation**: `core.vqa.vqa_memory` is a session-level visual cache. Persistent multi-session memory is handled in `core.memory`.
- **Latency Hard-Cap**: Pipeline strictly timed out at 300ms; if a component hangs, the system returns the last valid or a degraded result.
