# Phase 3 Summary: Architecture & Data Flow

## Overview

Phase 3 mapped the system's architecture, data flows, data models, and risks
through static analysis of all source files. No source code was modified.

## Artifacts Generated

| # | Artifact | Path | Description |
|---|----------|------|-------------|
| 1 | Component Inventory | `docs/analysis/component_inventory.json` | Full inventory of all services, integrations, databases, caching, and storage layers |
| 2 | System Component Diagram | `docs/PRD/15_diagrams/component_diagram.mmd` | Mermaid diagram showing all 5 architecture layers with component relationships |
| 3 | Sequence Diagram | `docs/PRD/15_diagrams/sequence_user_upload_to_speech.mmd` | Voice→Vision→Speech flow sequence diagram |
| 4 | Data Flow Analysis | `docs/analysis/data_flows.md` | 5 end-to-end data flows with exact file/function paths, transformations, and error gaps |
| 5 | Data Model Inventory | `docs/analysis/data_model_inventory.json` | 52 models: 22 dataclasses, 20 Pydantic, 10 enums, 3 ABCs across all layers |
| 6 | Architecture Risks | `docs/analysis/architecture_risks.md` | 18 risks: 3 critical, 4 high, 6 medium, 5 low with mitigation plans |
| 7 | Render Commands | `docs/PRD/15_diagrams/component_render_cmd.txt` | Mermaid CLI commands for PNG/SVG export |

## Key Findings

### Architecture

- **5-layer monorepo**: `shared → core → application → infrastructure → apps`
- **Import boundaries enforced** by import-linter in CI
- **2 entry points**: FastAPI REST (port 8000) + LiveKit WebRTC Agent (port 8081)
- **Voice-first design**: No frontend UI; interaction via LiveKit playground

### Data Flows Traced

1. **Voice → STT → Intent → LLM → TTS → Audio**: 7-stage pipeline through Deepgram, VoiceRouter, Ollama, ElevenLabs
2. **Camera Frame → Vision/OCR → Explanation → Speech**: 9-stage pipeline through perception, scene graph, spatial fusion, VQA reasoning
3. **QR Scan → Content Classification → Speech**: 8-stage pipeline with 3-level retry (raw, preprocessed, multi-scale)
4. **Memory Store → RAG Retrieval → Response**: Dual pipeline (ingestion: 6 stages, query: 7 stages) with single LLM provider (qwen3.5:cloud via Ollama cloud runtime)
5. **Spatial Perception → Navigation Cue → TTS**: 10-stage pipeline with temporal EMA smoothing and debounce

### Data Model Summary

| Kind | Count | Primary Locations |
|------|-------|-------------------|
| Dataclass | 22 | `shared/schemas`, `core/vqa`, `core/memory`, `application/` |
| Pydantic | 20 | `core/memory/api_schema.py`, `core/vqa/api_schema.py` |
| Enum | 10 | `shared/schemas`, `core/speech`, `core/memory` |
| ABC | 3 | `shared/schemas` (ObjectDetector, Segmenter, DepthEstimator) |

### Top Risks

| Severity | Count | Top Items |
|----------|-------|-----------|
| 🔴 Critical | 3 | API keys in git, Dockerfiles run as root, no QR payload sanitization |
| 🟠 High | 4 | Single-point-of-failure services, FAISS O(n) search, no type checker, in-memory state loss |
| 🟡 Medium | 6 | 1900-line god object, hardcoded camera FOV, duplicate types, no rate limiting |
| 🟢 Low | 5 | Stale test imports, lint backlog, bare excepts |

## Phase 3 Status

**COMPLETE** — All 7 artifacts generated successfully.

---

## Combined Analysis Status (All Phases)

| Phase | Status | Artifacts |
|-------|--------|-----------|
| Phase 1: Repository Scan & Indexing | ✅ Complete | 5 artifacts |
| Phase 2: Static Analysis & CI Health | ✅ Complete | 10 artifacts |
| Phase 3: Architecture & Data Flow | ✅ Complete | 7 artifacts |
| **Total** | **✅ Complete** | **22 artifacts** |


---

## GPU Acceleration

The system supports hybrid cloud/local-GPU architecture:

- **Cloud LLM**: `qwen3.5:cloud` via Ollama cloud runtime (async HTTP calls)
- **Local Embedding**: `qwen3-embedding:4b` via Ollama local (GPU accelerated)
- **GPU**: NVIDIA RTX 4060 (8GB VRAM), CUDA enabled
- **Vision Pipeline**: ONNX Runtime CUDA EP for detection, segmentation, depth estimation
- **Torch CUDA**: Used for embedding inference and face detection
- **Memory-safe batching**: WorkerPool respects VRAM limits with backpressure control
- **Performance**: Reduced embedding latency, parallel frame processing, GPU-aware worker scaling