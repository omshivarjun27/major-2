# Init-Deep: Hierarchical AGENTS.md Generation

## TL;DR

> **Quick Summary**: Generate a comprehensive hierarchy of AGENTS.md knowledge-base files — one root update + 11 subdirectory files — giving AI agents precise, non-redundant context for every major module in this project.
>
> **Deliverables**:
> - Updated `./AGENTS.md` (root, ~200 lines, already 210 lines of good content — enrich/update)
> - `core/AGENTS.md` — 11-module domain engine layer
> - `core/vqa/AGENTS.md` — VQA engine (3750+ LOC, factories, perception pipeline)
> - `core/memory/AGENTS.md` — RAG engine (FAISS, multi-backend LLM, privacy-first)
> - `core/vision/AGENTS.md` — Ultra-low-latency spatial perception (specialized constants)
> - `core/ocr/AGENTS.md` — 3-tier fallback OCR (all in one file, unique patterns)
> - `application/AGENTS.md` — Orchestration layer (pipelines + frame processing)
> - `application/pipelines/AGENTS.md` — 8 production pipeline components
> - `application/frame_processing/AGENTS.md` — Frame orchestrator + live frame manager
> - `shared/AGENTS.md` — Cross-cutting: schemas, config, logging, debug, utils
> - `infrastructure/AGENTS.md` — External adapter layer (Ollama, Deepgram, ElevenLabs, Tavus)
> - `apps/AGENTS.md` — Entrypoints: FastAPI (50+ endpoints) + LiveKit agent (2087 LOC)
> - `tests/AGENTS.md` — 429+ tests: 4 layers, SLAs, mock patterns
> - `tests/performance/AGENTS.md` — NFR/SLA benchmarks (distinct enough to warrant own file)
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — all subdirectory files can be written in parallel (Wave 2)
> **Critical Path**: Update root → write all subdirs in parallel

---

## Context

### Original Request
`/init-deep` — Generate hierarchical AGENTS.md knowledge-base files. Update mode (existing root AGENTS.md preserved/enriched).

### Research Findings

**Project scale**: 209 Python files, 50,615 LOC, max depth 5, 17 large files (>500 LOC).

**Scoring results** (files written where score > 15 or distinct domain):

| Path | Score | Reason |
|------|-------|--------|
| `.` | ROOT | Always |
| `core/` | 22 | 11 submodules, 100% code, distinct boundary |
| `core/vqa/` | 26 | 10 files, 3750+ LOC, factory pattern, __init__ exports 50+ symbols |
| `core/memory/` | 28 | 13 files, 2700+ LOC, has own README.md |
| `core/vision/` | 18 | spatial.py 1157 LOC, ultra-low-latency constants |
| `core/ocr/` | 16 | All-in-one __init__.py, 3-tier fallback, unique patterns |
| `application/` | 22 | 17 files, 4 subdirs, orchestration boundary |
| `application/pipelines/` | 22 | 12 files, 8 distinct pipeline components |
| `application/frame_processing/` | 20 | FrameOrchestrator 598 LOC, LiveFrameManager |
| `shared/` | 20 | Single SOT for all types + config |
| `infrastructure/` | 20 | Adapter layer, 7 subdirs, graceful fallback patterns |
| `apps/` | 20 | FastAPI 678 LOC, LiveKit agent 2087 LOC |
| `tests/` | 24 | 429+ tests, 4 test layers |
| `tests/performance/` | 18 | NFR/SLA benchmarks — very distinct from unit |

**Skipped** (parent covers): `core/braille`, `core/qr`, `core/face`, `core/speech`, `core/audio`, `core/action`, `core/reasoning`, `application/event_bus`, `application/session_management`, `infrastructure/llm`, `infrastructure/speech`.

### Key Research Findings (for content generation)

#### Shared Types (shared/schemas/__init__.py)
- `BoundingBox`, `Detection`, `SegmentationMask`, `DepthMap`, `PerceptionResult`, `ObstacleRecord`, `NavigationOutput`
- Enums: `Priority` (CRITICAL<1m, NEAR_HAZARD 1-2m, FAR_HAZARD 2-5m, SAFE>5m), `Direction`, `SizeCategory`, `SpatialRelation`
- ABCs: `ObjectDetector`, `Segmenter`, `DepthEstimator`
- **CRITICAL**: `DepthMap.get_region_depth()` returns `(min, median, max)` NOT `(min, max, mean)`

#### Config Flags (shared/config/settings.py)
- `spatial_enabled()`, `qr_enabled()`, `face_enabled()`, `audio_enabled()`, `action_enabled()`, `tavus_enabled()`, `cloud_sync_enabled()`
- Latency: `TARGET_STT_LATENCY_MS=100`, `TARGET_VQA_LATENCY_MS=300`, `TARGET_TTS_LATENCY_MS=100`, `TARGET_TOTAL_LATENCY_MS=500`
- Pipeline: `PIPELINE_TIMEOUT_MS=300`, `HOT_PATH_TIMEOUT_MS=500`, `LIVE_FRAME_MAX_AGE_MS=500`
- Distance thresholds: `CRITICAL_DISTANCE_M=1.0`, `NEAR_DISTANCE_M=2.0`, `FAR_DISTANCE_M=5.0`
- Debounce: `DEBOUNCE_WINDOW_SECONDS=5.0`, `DISTANCE_DELTA_M=0.5`

#### VQA Engine (core/vqa/)
- Factories: `create_pipeline(use_yolo, use_midas, enable_segmentation, enable_depth, use_mock)`, `create_detector(use_yolo)`, `create_depth_estimator(use_midas)`
- Auto-detect: checks `YOLO_MODEL_PATH` / `MIDAS_MODEL_PATH` env vars
- Fallback: `MockObjectDetector`, `SimpleDepthEstimator`
- Pipeline: detect → segment (EdgeAwareSegmenter) → depth (MiDaS/Simple) → SpatialFuser → VQAReasoner
- `QuickAnswers`: bypass LLM for common queries (speed optimization)
- VQA target: ≤300ms vision, ≤500ms total

#### Memory Engine (core/memory/)
- Components: `FAISSIndexer`, `TextEmbedder`, `MultimodalFuser`, `MemoryIngester`, `MemoryRetriever`, `RAGReasoner`
- LLM backends: `init_backends()` → Claude Opus 4.6 → Ollama qwen3-vl → StubLLMClient (fallback chain)
- Privacy: `MEMORY_ENABLED=true` by default, but requires `/memory/consent`; opt-in consent stored in `data/`
- Embedding model: `qwen3-embedding:4b` (Ollama)
- `RAG_K=5` memories retrieved per query

#### Vision Module (core/vision/spatial.py — 1157 LOC)
- Ultra-low-latency constants: `MAX_DETECTIONS=2`, `MAX_MASK_SIZE=(160,120)`, `DEPTH_DOWNSCALE=4`, `SKIP_SEGMENTATION_BELOW_MS=50`, `GC_AFTER_FRAME=True`
- Aggressive memory management: explicit GC per frame
- `BaseDetector` ABC, ONNX-based inference

#### OCR (core/ocr/__init__.py — all 337 LOC in one file)
- 3-tier: EasyOCR → Tesseract → None (with error message)
- Preprocessing: grayscale → CLAHE → bilateral denoise → deskew (Hough lines)
- Auto-select backend at init; all heavy work via `run_in_executor()`
- At startup logs which backends are available

#### Application Pipelines (application/pipelines/)
- `StreamingTTSCoordinator` — sentence-level LLM→TTS with cancellation
- `PerceptionWorkerPool` — ThreadPoolExecutor off event loop (detect/depth/embed/ocr/qr workers)
- `AudioOutputManager` — priority queue (CRITICAL=0, USER_RESPONSE=1, PROACTIVE=2, SYSTEM=3, AMBIENT=4)
- `AdaptiveFrameSampler` — 100–1000ms cadence based on scene changes + load
- `PipelineMonitor` — per-stage latency tracking + SLO alerts
- `CancellationScope` + `ScopeManager` — cancel all work on new user query
- `Debouncer` — prevents repeating same cue within 5s (scene-graph hash + distance delta)
- `Watchdog` — camera stall (2s) + worker stall (5s) detection, spoken alerts

#### Frame Processing (application/frame_processing/)
- `FrameOrchestrator.process_frame()` — **NEVER raises**, always returns degraded result
- Key invariant: all fused results MUST belong to same `frame_id`
- `LiveFrameManager` — ring buffer (30 frames), `TimestampedFrame` with `frame_id` + `epoch_ms`
- `ConfidenceCascade` — 3 tiers: ≥0.60 detected / 0.30-0.59 possible / <0.30 log only
- `SecondaryVerifier` — checks confusion pairs (bottle/phone, cup/bowl, remote/mouse)
- `freshness.py` — frame max age 500ms

#### Infrastructure Layer
- `OllamaHandler` — LRU image cache (64 entries), async httpx client, people/scene classification routing
- `TTSManager` — cache (SHA-256 LRU) → remote (2s timeout) → local fallback
- `TavusAdapter` — disabled by default, `TAVUS_ENABLED=false`
- `InternetSearch` — DuckDuckGo wrapper (general/detailed/news modes)
- `infrastructure/storage/` and `infrastructure/monitoring/` — stubs only

#### Apps Layer
- FastAPI `server.py` (678 LOC): 50+ endpoints; all features conditionally loaded via feature flags
- Auth: `require_debug_auth` dependency for debug endpoints (`DEBUG_ENDPOINTS_ENABLED` + Bearer token)
- GDPR: `/export/data` (Art.20) and `/export/erase` (Art.17)
- LiveKit `agent.py` (2087 LOC): function tools (search_internet, analyze_vision, detect_obstacles, analyze_spatial_scene, ask_visual_question)
- Fresh-context: `userdata.clear_perception_cache()` on every new query
- `apps/cli/` — re-exports from `shared/debug/` (session_logger, visualizer)

#### Tests Layer
- 429+ tests across unit(13), integration(8), performance(17+), root-level(26+)
- Mock pattern: `MockObjectDetector`, `MockDetector(delay_s=..., should_raise=...)`, `MockFAISSIndexer`
- Performance SLAs: total ≤1000ms, hot path ≤500ms, sustained 10 FPS, <5% frame drop
- `@pytest.mark.asyncio` — 152 tests; `asyncio_mode="auto"` in pyproject.toml
- `env_overrides(monkeypatch)` fixture for temporary env mutation
- Realtime harness (`tests/realtime/`) — NOT pytest; manual benchmarking/debug tools

---

## Work Objectives

### Core Objective
Write 14 AGENTS.md files (1 root update + 13 new subdirectory files) providing hierarchical, non-redundant AI agent context for every major module.

### Concrete Deliverables
- `./AGENTS.md` — updated root (enrich existing content, ~200 lines)
- `core/AGENTS.md` — new
- `core/vqa/AGENTS.md` — new
- `core/memory/AGENTS.md` — new
- `core/vision/AGENTS.md` — new
- `core/ocr/AGENTS.md` — new
- `application/AGENTS.md` — new
- `application/pipelines/AGENTS.md` — new
- `application/frame_processing/AGENTS.md` — new
- `shared/AGENTS.md` — new
- `infrastructure/AGENTS.md` — new
- `apps/AGENTS.md` — new
- `tests/AGENTS.md` — new
- `tests/performance/AGENTS.md` — new

### Must Have
- Every file uses telegraphic style (dense, no fluff)
- Child files NEVER repeat parent content
- Each file 30–150 lines (root can be up to 220)
- All file references verified against actual project structure
- AGENTS.md content used by AI agents to make correct implementation decisions

### Must NOT Have (Guardrails)
- Generic advice that applies to all Python projects
- Repetition of content from parent AGENTS.md
- Over-documentation of obvious things
- Invented file paths or class names not verified in research

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — All verification agent-executed.

### QA Policy
Each task agent verifies their own output by reading back the file immediately after writing and checking: line count within bounds, no obvious duplication of parent content, all file paths mentioned actually exist.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Sequential — root first):
└── Task 1: Update ./AGENTS.md (root)

Wave 2 (Full parallel — all subdirs independent of each other):
├── Task 2:  core/AGENTS.md
├── Task 3:  core/vqa/AGENTS.md
├── Task 4:  core/memory/AGENTS.md
├── Task 5:  core/vision/AGENTS.md
├── Task 6:  core/ocr/AGENTS.md
├── Task 7:  application/AGENTS.md
├── Task 8:  application/pipelines/AGENTS.md
├── Task 9:  application/frame_processing/AGENTS.md
├── Task 10: shared/AGENTS.md
├── Task 11: infrastructure/AGENTS.md
├── Task 12: apps/AGENTS.md
├── Task 13: tests/AGENTS.md
└── Task 14: tests/performance/AGENTS.md

Wave 3 (Final review):
└── Task 15: Verify all 14 files exist, check line counts, spot-check content
```

---

## TODOs

- [x] 1. Update `./AGENTS.md` (root)

  **What to do**:
  Replace the existing `./AGENTS.md` with an enriched version. The current file (210 lines) is good but needs updates. Write the full file using the `Write` tool (overwrite). The root AGENTS.md is the MASTER reference — it should be comprehensive (~200 lines).

  **Content to include** (all of this, telegraphic style):
  - Header: project name, commit 723bfc7, branch main
  - Overview: Python monorepo ≥3.10, real-time accessibility assistant, tech stack (LiveKit, Deepgram, ElevenLabs, Ollama qwen3-vl, FastAPI, FAISS, ONNX)
  - Layered architecture diagram (shared→core→application→infrastructure→apps) with enforcement note
  - Structure tree (all top-level dirs with 1-line purposes)
  - WHERE TO LOOK table (12+ entries: shared types, feature flags, perception pipeline, frame fusion, LiveKit agent, FastAPI server, RAG memory, OCR, pipeline wiring, logging setup, architecture boundaries)
  - Build & Install commands
  - Test commands (all variants from existing file)
  - Lint & Format commands
  - Code Style section: Naming, Imports, Error Handling, Async Patterns, Types/Docs, Factories, Configuration, Logging
  - Shared Types table (all 11 types/ABCs from shared/schemas)
  - Latency SLAs table (6 rows)
  - Feature Flags section (all 7 flag functions)
  - Key Directories table (15 entries)
  - CI Pipeline (4 stages)
  - Docker commands
  - Anti-patterns list (10 items)
  - Notes/Gotchas (6 items including the DepthMap (min,median,max) gotcha)

  **Must NOT do**:
  - Generic Python advice
  - Repeat info covered in subdirectory AGENTS.md files (those are for deep dives)

  **Recommended Agent Profile**:
  > Writing task with structured content.
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (sequential)
  - **Blocks**: Tasks 2-14 (subdirs should be written after root exists, but content-wise they're independent)
  - **Blocked By**: None

  **References**:
  - `./AGENTS.md` — existing content to preserve + enrich
  - `shared/schemas/__init__.py` — all type definitions
  - `shared/config/settings.py` — all feature flags and constants
  - Research findings above (this plan) — comprehensive content source

  **Acceptance Criteria**:
  - [x] `./AGENTS.md` exists and has 180–220 lines
  - [x] Contains all sections listed above
  - [x] All file paths in WHERE TO LOOK table verified to exist
  - [x] No invented class names or file paths

---

- [x] 2. Write `core/AGENTS.md`

  **What to do**:
  Create new file `core/AGENTS.md` (30–80 lines). This is the layer-level overview for all 11 domain engines. Child files (core/vqa/, core/memory/, core/vision/, core/ocr/) will have deep dives — this file covers the other 7 modules and the layer contract.

  **Content to include**:
  - 1-line overview: "Domain engines implementing pure perception/NLP/audio logic. Import from `shared/` only — never from `application/`, `infrastructure/`, or `apps/`."
  - WHERE TO LOOK table for all 11 modules:
    - `vqa/` — see core/vqa/AGENTS.md
    - `memory/` — see core/memory/AGENTS.md
    - `vision/` — see core/vision/AGENTS.md
    - `ocr/` — see core/ocr/AGENTS.md
    - `braille/` — BrailleOCR, BrailleSegmenter, BrailleClassifier, EmbossingGuide; pipeline: deskew→segment→classify
    - `qr/` — QRScanner (pyzbar>OpenCV), QRDecoder (content classification), ARTagHandler, CacheManager; factory: `build_qr_router()`
    - `face/` — FaceDetector, FaceEmbeddingStore, FaceTracker, SocialCueAnalyzer; ALL OPT-IN + consent required
    - `speech/` — VoiceAskPipeline (STT→VQA→TTS, ≤500ms); VoiceRouter (IntentType: visual/search/qr/general)
    - `audio/` — SoundSourceLocalizer (mic-array or mono degraded), AudioEventDetector, AudioVisionFuser
    - `action/` — ActionRecognizer, ClipBuffer (16-frame clips, stride 4, min_confidence 0.3)
    - `reasoning/` — placeholder, not yet populated
  - CONVENTIONS section: factory pattern (create_*/build_*/make_*), async executor pattern, graceful degradation, optional import guards, re-export from shared.schemas
  - ANTI-PATTERNS: never raise from engine methods; never import infrastructure or apps; never redefine types from shared/schemas

  **Must NOT do**:
  - Repeat content from root AGENTS.md
  - Deep-dive on vqa/memory/vision/ocr (those have own AGENTS.md)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3-14)
  - **Blocks**: Nothing
  - **Blocked By**: Task 1 (root should exist first, but content is independent)

  **References**:
  - `core/braille/__init__.py` — module exports
  - `core/qr/__init__.py` — module exports
  - `core/face/__init__.py` — module exports
  - `core/speech/__init__.py` — module exports
  - `core/audio/__init__.py` — module exports
  - `core/action/__init__.py` — module exports
  - Research findings in this plan

  **Acceptance Criteria**:
  - [x] File exists at `core/AGENTS.md`, 30–80 lines
  - [x] All 11 core modules listed with purpose
  - [x] No content duplicated from `./AGENTS.md`

---

- [x] 3. Write `core/vqa/AGENTS.md`

  **What to do**:
  Create new file `core/vqa/AGENTS.md` (50–100 lines). Deep dive on the VQA engine — largest and most complex core module.

  **Content to include**:
  - 1-line overview: "Complete low-latency Visual Q&A system: detection→segmentation→depth→scene-graph→LLM reasoning. Target: ≤300ms vision, ≤500ms total."
  - Files table (10 files with 1-line purpose each):
    - `perception.py` (720 LOC) — PerceptionPipeline + all detector/segmenter/depth implementations
    - `vqa_reasoner.py` (581 LOC) — VQAReasoner (Ollama qwen3-vl), MicroNavFormatter, PromptTemplates, QuickAnswers
    - `priority_scene.py` (576 LOC) — PrioritySceneAnalyzer, hazard detection + direction zones
    - `memory.py` (571 LOC) — VQAMemory (session-scoped context, NOT the RAG engine)
    - `spatial_fuser.py` — SpatialFuser, TemporalFilter, TrackedObject (12-component state)
    - `scene_graph.py` — SceneGraph, SceneNode, SceneGraphBuilder, `obstacle_to_speech()`
    - `orchestrator.py` — high-level VQA orchestrator
    - `api_endpoints.py` (717 LOC) — FastAPI router (`vqa_router`), `init_vqa_api()`, `cleanup_vqa_api()`
    - `api_schema.py` — Pydantic models (PerceptionFrameRequest/Response, VQAAskRequest/Response, HealthStatus, PerformanceMetrics)
  - FACTORIES section:
    ```python
    create_pipeline(use_yolo=False, use_midas=False, enable_segmentation=False, enable_depth=False, use_mock=False)
    create_detector(use_yolo=False)    # → YOLODetector or MockObjectDetector
    create_depth_estimator(use_midas=False)  # → MiDaSDepthEstimator or SimpleDepthEstimator
    # Auto-detect: if env flag is "auto" and model file exists → enable; else mock
    ```
  - PIPELINE FLOW: `FRAME → detect() → segment() → estimate() [parallel gather] → SpatialFuser → SceneGraph → VQAReasoner → NavigationOutput`
  - QuickAnswers: bypass LLM for common queries (obstacle count, nearest obstacle, path clear) — check before calling VQAReasoner
  - GOTCHAS: VQAMemory here is session context (NOT the RAG memory engine in core/memory/); `SpatialFuser` uses temporal filtering (object must appear N consecutive frames)

  **Must NOT do**:
  - Repeat layer architecture from root or core/AGENTS.md

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `core/vqa/__init__.py` — full export list
  - `core/vqa/perception.py` — factory functions (lines 1–80 approximate)
  - Research findings in this plan

  **Acceptance Criteria**:
  - [x] File exists at `core/vqa/AGENTS.md`, 50–100 lines
  - [x] Factories section with all 3 factory functions documented
  - [x] Pipeline flow diagram present

---

- [x] 4. Write `core/memory/AGENTS.md`

  **What to do**:
  Create new file `core/memory/AGENTS.md` (50–100 lines). Note: `core/memory/README.md` already exists — this AGENTS.md should be agent-focused (not user-docs), adding implementation guidance beyond the README.

  **Content to include**:
  - 1-line overview: "Privacy-first local RAG engine: FAISS vector index + Ollama/Claude LLM reasoning. MEMORY_ENABLED=true by default; requires /memory/consent before storing."
  - Files table (11 files):
    - `config.py` — MemoryConfig, `get_memory_config()` (retention_days=30, max_vectors=5000, index_path, embedding_model)
    - `embeddings.py` (487 LOC) — TextEmbedder (qwen3-embedding:4b), MultimodalFuser
    - `indexer.py` (622 LOC) — FAISSIndexer with persistence, metadata, LRU eviction; thread-safe (mutex)
    - `ingest.py` — MemoryIngester (multimodal: text/image/audio/scene_graph)
    - `retriever.py` — MemoryRetriever (vector similarity search, RAG_K=5)
    - `rag_reasoner.py` (419 LOC) — RAGReasoner (retrieve→prompt→LLM); template fallback before LLM (faster)
    - `llm_client.py` — multi-backend: ClaudeClient/OllamaClient/StubLLMClient; `init_backends()`, `get_backend(role)`, `register_backend()`
    - `api_endpoints.py` — FastAPI router with 7 endpoints (store/search/query/get/consent/delete/health)
    - `api_schema.py` — Pydantic: MemoryStoreRequest, MemorySearchRequest, MemoryQueryRequest, MemoryRecord, MemoryHit, MemoryConsentRequest
    - `maintenance.py` — MemoryMaintenance: auto-expiry, backup
    - `cloud_sync.py` — CloudSync (stub, CLOUD_SYNC_ENABLED=false by default)
    - `event_detection.py` — MemoryEventDetector
  - LLM FALLBACK CHAIN: `Claude Opus 4.6 (role="memory") → Ollama qwen3-vl (role="vision") → StubLLMClient (role="fallback")`
  - PRIVACY: `MEMORY_REQUIRE_CONSENT=true`; raw images NOT stored by default; `RAW_MEDIA_SAVE=false`
  - LAZY IMPORTS: FAISS loaded on first use — `FAISSIndexer` init should be deferred
  - NOTE: This is the RAG memory engine (persistent, multi-session). Not to be confused with `core/vqa/memory.py` (session-scoped VQA context only).

  **Must NOT do**:
  - Duplicate README.md content verbatim
  - Repeat layer architecture from parent files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `core/memory/__init__.py`
  - `core/memory/README.md` — avoid duplicating
  - Research findings in this plan

  **Acceptance Criteria**:
  - [x] File exists at `core/memory/AGENTS.md`, 50–100 lines
  - [x] LLM fallback chain documented
  - [x] Disambiguation note vs. core/vqa/memory.py present

---

- [x] 5. Write `core/vision/AGENTS.md`

  **What to do**:
  Create `core/vision/AGENTS.md` (30–70 lines). Focus: ultra-low-latency constants and memory optimization patterns unique to this module.

  **Content to include**:
  - 1-line overview: "Ultra-low-latency spatial perception optimized for real-time blind navigation. Aggressive memory management — explicit GC per frame."
  - Files: `spatial.py` (1157 LOC) — main engine; `visual.py` (429 LOC) — vision processors; `video_processing.py` — video utilities
  - ULTRA-LOW-LATENCY CONSTANTS (must document all of these — they're non-obvious):
    ```python
    MAX_DETECTIONS = 2          # Hard limit for speed
    MAX_MASK_SIZE = (160, 120)  # Aggressive downscale for segmentation
    DEPTH_DOWNSCALE = 4         # Depth map resolution reduction
    SKIP_SEGMENTATION_BELOW_MS = 50  # Skip seg if detection already fast
    GC_AFTER_FRAME = True       # Force garbage collection every frame
    ```
  - ARCHITECTURE: `BaseDetector` ABC → YOLODetector (ONNX) or MockDetector; all inference via onnxruntime
  - LAZY IMPORTS: torch, PIL, cv2 all optional with `_AVAILABLE` guards
  - NOTE: This module is separate from `core/vqa/perception.py`. vision/ focuses on raw speed; vqa/ focuses on full pipeline orchestration with scene graph + LLM.
  - WHEN TO USE vision/ vs vqa/: Use vision/ for latency-critical raw obstacle detection. Use vqa/ for full perception→reasoning pipeline.

  **Must NOT do**:
  - Repeat general async/factory patterns from parent files

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `core/vision/spatial.py` lines 1–80 (constants section)
  - Research findings in this plan

  **Acceptance Criteria**:
  - [x] File exists at `core/vision/AGENTS.md`, 30–70 lines
  - [x] All 5 ultra-low-latency constants documented with values
  - [x] vision/ vs vqa/ disambiguation present

---

- [x] 6. Write `core/ocr/AGENTS.md`

  **What to do**:
  Create `core/ocr/AGENTS.md` (30–60 lines). This entire module is in one file (`core/ocr/__init__.py`).

  **Content to include**:
  - 1-line overview: "3-tier OCR pipeline (EasyOCR→Tesseract→None) with preprocessing. All in `core/ocr/__init__.py` — no submodules."
  - ENTRY POINT: `OCRPipeline(languages=["en"], min_confidence=0.3)` → `await pipeline.process(image)` → `OCRPipelineResult`
  - PREPROCESSING PIPELINE: `image → grayscale → CLAHE (clip=2.0, grid=8) → bilateral denoise (d=9) → deskew (Hough lines) → backend`
  - BACKEND SELECTION (at `__init__` time): `EASYOCR_AVAILABLE` → `_EasyOCRBackend`; else `TESSERACT_AVAILABLE` → `_TesseractBackend`; else `None` (returns error message)
  - AT STARTUP: logs which backends are available — check logs if OCR not working
  - RESULT: `OCRPipelineResult.full_text` (joined), `.results` (List[OCRResult] with confidence/bbox/backend), `.error` (None if success)
  - INSTALL: `pip install easyocr>=1.7.0` OR `pip install pytesseract>=0.3.10` + tesseract binary; or `scripts/install_ocr_deps.sh`

  **Must NOT do**:
  - Repeat general module patterns from core/AGENTS.md

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `core/ocr/__init__.py` (337 LOC, all content)

  **Acceptance Criteria**:
  - [x] File exists at `core/ocr/AGENTS.md`, 30–60 lines
  - [x] Preprocessing pipeline documented
  - [x] Backend selection logic documented

---

- [x] 7. Write `application/AGENTS.md`

  **What to do**:
  Create `application/AGENTS.md` (40–80 lines). Layer overview — points to subdirectory AGENTS.md files for deep dives.

  **Content to include**:
  - 1-line overview: "Use-case orchestration layer. Coordinates core engines, manages request lifecycle. MUST NOT import from `infrastructure/` or `apps/`."
  - SUBDIRECTORIES:
    - `pipelines/` — see application/pipelines/AGENTS.md
    - `frame_processing/` — see application/frame_processing/AGENTS.md
    - `event_bus/` — event bus (stub, placeholder for pub/sub between components)
    - `session_management/` — session state management (stub)
  - KEY ENTRY POINT: `create_pipeline_components()` in `pipelines/integration.py` — call this to wire all 8 pipeline components into a `PipelineComponents` container
  - INTEGRATION PATTERN:
    ```python
    from application.pipelines import create_pipeline_components, wrap_entrypoint_with_pipeline
    components = create_pipeline_components(perception_pipeline, tts_func, speak_func)
    wrap_entrypoint_with_pipeline(entrypoint_fn, components)
    ```
  - CANCELLATION PATTERN: On new user query → `on_new_user_query(components, query)` cancels prior scope, interrupts audio, creates new scope
  - AUDIO PRIORITY: Use `speak_with_priority(components, text, priority)` — never call `agent_session.say()` directly (bypasses AudioOutputManager queue)
  - TELEMETRY: Every component exposes `.health()` / `.stats()` — aggregate via `PipelineMonitor`

  **Must NOT do**:
  - Repeat root AGENTS.md layer architecture
  - Deep-dive on pipelines or frame_processing (those have own files)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `application/pipelines/__init__.py`
  - `application/pipelines/integration.py`
  - Research findings in this plan

  **Acceptance Criteria**:
  - [x] File exists at `application/AGENTS.md`, 40–80 lines
  - [x] `create_pipeline_components()` entry point documented
  - [x] Cancellation + audio priority patterns present

---

- [x] 8. Write `application/pipelines/AGENTS.md`

  **What to do**:
  Create `application/pipelines/AGENTS.md` (60–100 lines). The 8 pipeline components all live here — document each.

  **Content to include**:
  - 1-line overview: "8 production pipeline components replacing blocking/race-prone pipeline. All wired via `create_pipeline_components()`."
  - COMPONENTS TABLE (8 rows):
    | Component | Class | Purpose |
    |-----------|-------|---------|
    | streaming_tts.py | StreamingTTSCoordinator | Sentence-level LLM→TTS with cancellation; SentenceBuffer |
    | perception_pool.py | PerceptionWorkerPool | ThreadPoolExecutor off event loop; workers: detect/depth/embed/ocr/qr |
    | audio_manager.py | AudioOutputManager | Priority queue (0=CRITICAL,1=USER,2=PROACTIVE,3=SYSTEM,4=AMBIENT); TTL 5s |
    | frame_sampler.py | AdaptiveFrameSampler | Cadence 100–1000ms; adapts to scene change + load |
    | pipeline_monitor.py | PipelineMonitor | Per-stage latency tracking, SLO alerts |
    | cancellation.py | CancellationScope + ScopeManager | Cancel all spawned tasks on scope exit |
    | debouncer.py | Debouncer | No-repeat within 5s window unless scene_hash or distance changes >0.5m |
    | watchdog.py | Watchdog | Camera stall (2s) + worker stall (5s); spoken alert cooldown 60s |
  - ALSO: `worker_pool.py` (WorkerPool generic) used by perception_pool; `perception_telemetry.py` (FrameLog, DetectionEntry) for per-frame JSON logging
  - WORKER REGISTRATION:
    ```python
    pool = PerceptionWorkerPool()
    pool.register("detect", num_workers=2)
    pool.register("depth", num_workers=1)
    # Submit: future = await pool.submit("detect", fn, args, timeout_ms=300)
    ```
  - AUDIO PRIORITY ENUM: document CRITICAL_HAZARD=0 through AMBIENT=4
  - DEBOUNCER KEY: `SpokenRecord` history (50 item FIFO); deduplicates on `short_cue` + scene_graph_hash

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `application/pipelines/__init__.py`
  - `application/pipelines/integration.py`
  - Research findings in this plan

  **Acceptance Criteria**:
  - [x] File exists at `application/pipelines/AGENTS.md`, 60–100 lines
  - [x] All 8 components in table with class name and purpose

---

- [x] 9. Write `application/frame_processing/AGENTS.md`

  **What to do**:
  Create `application/frame_processing/AGENTS.md` (50–90 lines).

  **Content to include**:
  - 1-line overview: "Per-frame fusion engine: parallel workers → confidence cascade → canonical SceneGraph. KEY INVARIANT: all fused results must belong to same frame_id."
  - FILES (4 files):
    - `frame_orchestrator.py` (598 LOC) — `FrameOrchestrator.process_frame()`: NEVER raises; collects parallel worker results; validates frame_id; builds FusedFrameResult + SceneGraph
    - `live_frame_manager.py` — `LiveFrameManager`: ring buffer (30 frames), `TimestampedFrame(frame_id, epoch_ms, data)`, subscriber pub-sub with backpressure
    - `confidence_cascade.py` — 3-tier: ≥0.60 "detected" / 0.30-0.59 "possible" / <0.30 "log only"; `SecondaryVerifier` for confusion pairs
    - `freshness.py` — max frame age 500ms (`LIVE_FRAME_MAX_AGE_MS`)
  - CONFIDENCE CASCADE THRESHOLDS:
    - `detected_threshold = 0.60` (from config.yaml)
    - `low_confidence_threshold = 0.30`
    - Confusion pairs penalized: bottle/phone, cup/bowl, remote/mouse
    - Small crop (<1024px area) → -0.15 penalty
    - Low edge density (<0.05 Sobel) → -0.10 penalty
  - FRAME LIFECYCLE:
    ```
    LiveFrameManager captures → tags frame_id + epoch_ms → ring buffer
    FrameOrchestrator.process_frame(frame) → parallel workers (300ms global timeout)
    → confidence cascade → SecondaryVerifier → FusedFrameResult
    → SceneGraph + NavigationOutput + short_cue + telemetry
    ```
  - NEVER-RAISE GUARANTEE: `process_frame()` always returns result; detector fails → empty detections; depth unavailable → synthetic 5m map

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `application/frame_processing/frame_orchestrator.py` lines 1–60
  - `application/frame_processing/confidence_cascade.py`
  - Research findings in this plan

  **Acceptance Criteria**:
  - [x] File exists at `application/frame_processing/AGENTS.md`, 50–90 lines
  - [x] Never-raise guarantee documented
  - [x] Frame lifecycle documented

---

- [x] 10. Write `shared/AGENTS.md`

  **What to do**:
  Create `shared/AGENTS.md` (50–90 lines). This is the CANONICAL TYPES reference.

  **Content to include**:
  - 1-line overview: "Cross-cutting utilities. Single source of truth for all data types, configuration, logging, and debug tools. Imports from stdlib only."
  - SUBDIRECTORIES:
    - `schemas/` — ALL shared types; import from here, never redefine
    - `config/` — Feature flags + 100+ env-based config values
    - `logging/` — StructuredJSONFormatter, PIIScrubFilter, `configure_logging()`
    - `debug/` — SessionLogger (ring buffer), visualizer
    - `utils/` — helpers, startup_guards, timing, encryption
  - SCHEMAS — complete type reference (copy from root AGENTS.md types section but with more detail):
    - `BoundingBox` — x1/y1/x2/y2; methods: `from_xywh()`, `center`, `area`, `clamp(w,h)`, `to_xywh()`, `to_list()`
    - `Detection` — id, class_name, confidence, bbox
    - `SegmentationMask` — detection_id, mask (numpy), boundary_confidence, edge_pixels
    - `DepthMap` — depth_array H×W; **`get_region_depth(bbox)` → `(min, median, max)` NOT (min,max,mean)**
    - `PerceptionResult` — detections, masks, depth_map, image_size, latency_ms, timestamp, frame_id, timestamp_epoch_ms
    - `ObstacleRecord` — id, class_name, bbox, centroid_px, distance_m, direction (Direction enum), direction_deg, mask_confidence, detection_confidence, priority (Priority enum), size_category, action_recommendation
    - `NavigationOutput` — short_cue, verbose_description, telemetry, has_critical
  - CONFIG ACCESSORS (all helper functions):
    ```python
    get_config()               # Full CONFIG dict
    get_spatial_config()       # Spatial perception knobs
    get_live_frame_config()    # Frame timing
    get_worker_config()        # Worker pool counts
    get_debounce_config()      # Debounce window + deltas
    get_watchdog_config()      # Stall thresholds
    get_continuous_config()    # Always-on / proactive
    get_qr_config()            # QR scanning
    get_face_config()          # Face engine
    get_audio_config()         # Audio engine
    get_action_config()        # Action engine
    ```
  - LOGGING SETUP:
    ```python
    from shared.logging.logging_config import configure_logging, log_event
    configure_logging(level="INFO", json_output=False)  # Call at startup
    log_event("component", "event_name", frame_id="...", latency_ms=45.2)
    ```
  - PII SCRUBBING: `PIIScrubFilter` auto-redacts emails, IPs, face IDs (fid_*), API keys, bearer tokens in log records
  - SESSION LOGGER:
    ```python
    from shared.debug.session_logger import SessionLogger
    logger = SessionLogger(max_events=500, log_dir="logs/")
    sid = logger.create_session()
    logger.log(sid, "vqa", {"answer": "..."}, latency_ms=123.4)
    ```

  **Must NOT do**:
  - Repeat root AGENTS.md type table verbatim (add depth instead)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - `shared/schemas/__init__.py` — all 319 lines
  - `shared/config/settings.py` — all 372 lines
  - `shared/logging/logging_config.py`

  **Acceptance Criteria**:
  - [x] File exists at `shared/AGENTS.md`, 50–90 lines
  - [x] DepthMap `(min, median, max)` gotcha documented
  - [x] All config accessor functions listed
  - [x] Logging setup snippet present

---

- [x] 11. Write `infrastructure/AGENTS.md`

  **What to do**:
  Create `infrastructure/AGENTS.md` (50–80 lines).

  **Content to include**:
  - 1-line overview: "External system adapters. Import from `shared/` only. All adapters: lazy-init, graceful fallback, strict timeouts, latency telemetry."
  - SUBDIRECTORY MAP:
    | Directory | Adapter | Status | Key Class |
    |-----------|---------|--------|-----------|
    | `llm/ollama/` | Ollama/SiliconFlow vision | Active | OllamaHandler |
    | `llm/internet_search.py` | DuckDuckGo search | Active | InternetSearch |
    | `llm/embeddings/` | Embedding model adapter | Active | (interface) |
    | `llm/siliconflow/` | SiliconFlow LLM | Stub | — |
    | `speech/elevenlabs/` | TTS (ElevenLabs) | Active | TTSManager |
    | `speech/deepgram/` | STT (Deepgram) | Stub (LiveKit plugins handle) | — |
    | `storage/` | Storage abstractions | Stub | — |
    | `monitoring/` | Observability adapters | Stub | — |
    | `tavus/` | Virtual avatar | Active (disabled by default) | TavusAdapter |
  - OLLAMA HANDLER:
    - LRU image cache (64 entries, SHA-256 key)
    - People detection routing: if people detected → use QWEN model; else → OLLAMA model
    - Client: async httpx with timeout config
  - TTS MANAGER (ElevenLabs):
    - Cache (SHA-256 LRU) → Remote (2s timeout) → Local fallback
    - All results include `fallback_used` and `latency_ms` fields
    - `TTSChunker`: splits text into ≤2s chunks (≈2.5 words/sec)
  - TAVUS ADAPTER:
    - Config: `TavusConfig.from_env()` reads `TAVUS_ENABLED`, `TAVUS_API_KEY`, `TAVUS_REPLICA_ID`, `TAVUS_PERSONA_ID`
    - Disabled by default: `TAVUS_ENABLED=false`
    - REST + WebSocket handshake; `send_narration(text)` queues text
    - `enabled` property: checks all 3 required config values present
  - INTERNET SEARCH: lazy DuckDuckGo init; 3 modes: general/detailed/news
  - ADAPTER CONVENTIONS: feature-gated (`TAVUS_ENABLED`, etc.); no-op when disabled; timeouts on all external I/O; log latency_ms per call

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - Research findings in this plan (infrastructure layer analysis)

  **Acceptance Criteria**:
  - [x] File exists at `infrastructure/AGENTS.md`, 50–80 lines
  - [x] All 9 subdirectory adapters listed with status
  - [x] TTS fallback chain documented

---

- [x] 12. Write `apps/AGENTS.md`

  **What to do**:
  Create `apps/AGENTS.md` (60–100 lines). Focus on the two large entrypoints.

  **Content to include**:
  - 1-line overview: "Application entrypoints — the only layer that imports from all layers. Two services: FastAPI REST (port 8000) and LiveKit WebRTC agent (port 8081)."
  - FILES:
    - `api/server.py` (678 LOC) — FastAPI app with 50+ endpoints
    - `realtime/agent.py` (2087 LOC) — LiveKit agent
    - `realtime/entrypoint.py` — LiveKit worker launcher
    - `cli/session_logger.py`, `cli/visualizer.py` — re-exports from `shared/debug/`
  - FASTAPI ENDPOINTS TABLE (grouped):
    | Group | Routes | Gate |
    |-------|--------|------|
    | Core | GET /health | Always |
    | QR/AR | /qr/* | qr_enabled() |
    | VQA | /vqa/* | vqa module available |
    | Memory | /memory/* (store/search/query/delete/consent/health) | memory module available |
    | Face | /face/health, /face/consent, /face/forget_all | face_enabled() + consent |
    | Audio | /audio/health, /debug/ssl_frame | audio_enabled() |
    | Action | /action/health | action_enabled() |
    | Braille | /braille/read, /debug/braille_frame | Always |
    | Debug | /debug/* | DEBUG_ENDPOINTS_ENABLED=true + Bearer |
    | GDPR | /export/data, /export/erase | Always |
    | Sessions | /logs/sessions, /logs/session/{id} | Always |
  - DEBUG AUTH: `require_debug_auth` dependency; set `DEBUG_ENDPOINTS_ENABLED=true` + `DEBUG_AUTH_TOKEN` in env
  - CONSENT STATE: Face consent stored in `data/face_consent.json` — shared between API and agent (file-based cross-process)
  - LIVEKIT AGENT — FUNCTION TOOLS:
    | Tool | Signature | SLA |
    |------|-----------|-----|
    | search_internet | query: str | none |
    | analyze_vision | query: str | <500ms |
    | detect_obstacles | detail_level: "quick"\|"detailed" | <200ms quick |
    | analyze_spatial_scene | query: str | <200ms |
    | ask_visual_question | question: str | <500ms |
  - FRESH-CONTEXT RULE: `userdata.clear_perception_cache()` called on EVERY new user query — never reuse cached perception from prior turn
  - SESSION STATE: `UserData` dataclass holds all per-session state (tool tracking, VQA instances, QR cache, live-frame infra, debouncer, watchdog, session_logger)
  - OPTIONAL IMPORTS: Agent wraps ALL heavy imports in try/except with `_*_AVAILABLE` flags — system must start even with missing optional modules
  - STARTUP: `apps/realtime/entrypoint.py` → configure_logging() → suppress LiveKit noise → `cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))`

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - Research findings in this plan (apps layer analysis)

  **Acceptance Criteria**:
  - [x] File exists at `apps/AGENTS.md`, 60–100 lines
  - [x] FastAPI endpoints table present
  - [x] LiveKit function tools table present
  - [x] Fresh-context rule documented

---

- [x] 13. Write `tests/AGENTS.md`

  **What to do**:
  Create `tests/AGENTS.md` (60–100 lines).

  **Content to include**:
  - 1-line overview: "429+ tests across 4 layers. asyncio_mode=auto; no @pytest.mark.asyncio needed. Mocks defined locally in test files, not shared fixtures."
  - STRUCTURE:
    | Directory | Files | Purpose |
    |-----------|-------|---------|
    | `unit/` | 13 | Fast isolated: perception, memory, ocr, qr, braille, fusion, embeddings, RAG |
    | `integration/` | 8 | Cross-module: VQA API, memory search, QR flow, RAG, Deepgram, SiliconFlow |
    | `performance/` | 17 | NFR/SLA: see tests/performance/AGENTS.md |
    | `realtime/` | 5 | Live pipeline harnesses — NOT pytest; manual benchmark/debug tools |
    | `fixtures/` | — | Synthetic data generators (braille) |
    | Root tests | 26 | Smoke: orchestrator, continuous processing |
  - MOCK PATTERNS (these are the project conventions):
    ```python
    class MockDetector:
        def __init__(self, detections=None, delay_s=0.0, should_raise=False): ...
    class MockSegmenter:
        def __init__(self, masks=None, delay_s=0.0): ...
    class MockDepthEstimator:
        def __init__(self, depth_map=None, delay_s=0.0): ...
    # Use delay_s to test concurrent execution timing
    # Use should_raise=True to test never-raise guarantees
    ```
  - FIXTURE PATTERNS:
    - `env_overrides(monkeypatch)` — temp env mutation (defined in `tests/performance/conftest.py`)
    - ASGI transport for FastAPI: `AsyncClient(transport=ASGITransport(app=app))`
    - Fixture chaining: `mock_indexer → mock_embedder → ingester` (dependency injection)
  - ASSERTION STYLE:
    ```python
    assert elapsed < 500, f"Hot path took {elapsed:.0f}ms (limit: 500ms)"
    assert drop_ratio < 0.05, f"Frame drop {drop_ratio:.2%} > 5% ({dropped}/{total})"
    ```
  - PYTEST CONFIG (pyproject.toml):
    - `asyncio_mode = "auto"` — all async tests run automatically
    - `timeout = 120` — global per-test timeout
    - Custom markers: `slow`, `integration`
  - NEVER-RAISE TEST PATTERN: test that `process_frame()` doesn't raise with broken inputs — this is a core guarantee
  - REALTIME TOOLS: `tests/realtime/realtime_test.py --debug|--benchmark|--log-session` — run directly, not via pytest
  - INTEGRATION TESTS: require external services (Deepgram, Ollama, SiliconFlow) — need configured `.env`

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - Research findings in this plan (tests layer analysis)

  **Acceptance Criteria**:
  - [x] File exists at `tests/AGENTS.md`, 60–100 lines
  - [x] Mock class templates documented
  - [x] Realtime tools noted as NOT pytest

---

- [x] 14. Write `tests/performance/AGENTS.md`

  **What to do**:
  Create `tests/performance/AGENTS.md` (40–70 lines).

  **Content to include**:
  - 1-line overview: "17 NFR/SLA test files. All test non-functional requirements: latency, throughput, privacy, security, graceful degradation. Run: `pytest tests/performance/ --timeout=300`."
  - PERFORMANCE SLA TABLE (all measured thresholds):
    | SLA | Threshold | Test File |
    |-----|-----------|-----------|
    | Total latency | ≤1000ms | test_latency_sla.py |
    | Hot path | ≤500ms | test_latency_sla.py |
    | Orchestrator import | <2000ms | test_latency_sla.py |
    | Config import | <500ms | test_latency_sla.py |
    | Sustained FPS | 10 FPS | test_sustained_fps.py |
    | Frame drop ratio | <5% | test_sustained_fps.py |
    | Memory leak | no unbounded growth | test_memory_leak.py |
  - COVERAGE (all 17 test files with 1-line purpose):
    - `test_latency_sla.py` — total/hot-path/import latency
    - `test_sustained_fps.py` — 10 FPS over 60s, <5% drop
    - `test_resource_threshold.py` — config bounds validation (workers 1-8, stall ms)
    - `test_graceful_degradation.py` — system starts when SPATIAL/FACE/AUDIO/QR disabled
    - `test_memory_leak.py` — no unbounded growth under sustained operation
    - `test_pii_scrubbing.py` — emails/IPs/fid_*/keys redacted in logs
    - `test_encryption_at_rest.py` — face embeddings encrypted
    - `test_consent_enforcement.py` — memory blocked before consent given
    - `test_telemetry_optin.py` — telemetry respects MEMORY_TELEMETRY flag
    - `test_secrets_scan.py` — no real API keys in .env
    - `test_offline_behavior.py` — system operates without network
    - `test_access_control_fuzz.py` — debug endpoints reject without auth
    - `test_debug_access_control.py` — debug auth enforcement
    - `test_model_checksums.py` — model file integrity
    - `test_model_download_retry.py` — retry logic on download failure
    - `test_deterministic_replay.py` — session replay determinism
    - `test_benchmark_report.py` — benchmark report generation
  - SHARED FIXTURE: `conftest.py` defines `project_root` and `env_overrides(monkeypatch)`
  - NOTE: These tests verify SYSTEM PROPERTIES, not unit behavior. They are config-driven — many assert that config values are within valid ranges.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: Nothing
  - **Blocked By**: Task 1

  **References**:
  - Research findings in this plan (tests analysis)
  - `tests/performance/` directory listing

  **Acceptance Criteria**:
  - [x] File exists at `tests/performance/AGENTS.md`, 40–70 lines
  - [x] SLA table present
  - [x] All 17 test files listed with purpose

---

- [x] 15. Final Verification

  **What to do**:
  Verify all 14 AGENTS.md files were created. Read each file and confirm: exists, line count within bounds, no obvious duplication of parent content, key content present (spot-check 3 items per file).

  **Verification script** (run in bash):
  ```bash
  for f in \
    ./AGENTS.md \
    core/AGENTS.md core/vqa/AGENTS.md core/memory/AGENTS.md \
    core/vision/AGENTS.md core/ocr/AGENTS.md \
    application/AGENTS.md application/pipelines/AGENTS.md \
    application/frame_processing/AGENTS.md \
    shared/AGENTS.md infrastructure/AGENTS.md apps/AGENTS.md \
    tests/AGENTS.md tests/performance/AGENTS.md; do
    lines=$(wc -l < "$f" 2>/dev/null || echo "MISSING")
    echo "$lines  $f"
  done
  ```

  **Expected output**: All 14 files exist with line counts in specified ranges.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: Nothing
  - **Blocked By**: Tasks 1–14

  **Acceptance Criteria**:
  - [x] All 14 files exist
  - [x] No file is 0 lines or >250 lines
  - [x] Root AGENTS.md contains "DepthMap" and "get_region_depth"
  - [x] `core/vqa/AGENTS.md` contains "create_pipeline" and "QuickAnswers"
  - [x] `tests/performance/AGENTS.md` contains all 17 test file names

---

## Final Verification Wave

- [x] F1. **File Existence Audit** — `quick`
  Run bash loop above. Verify all 14 paths exist with line counts. Output: table of path + line count + PASS/FAIL.

---

## Commit Strategy

- **1**: `docs: add hierarchical AGENTS.md knowledge base` — all 14 files
  - Files: `AGENTS.md`, `core/AGENTS.md`, `core/vqa/AGENTS.md`, `core/memory/AGENTS.md`, `core/vision/AGENTS.md`, `core/ocr/AGENTS.md`, `application/AGENTS.md`, `application/pipelines/AGENTS.md`, `application/frame_processing/AGENTS.md`, `shared/AGENTS.md`, `infrastructure/AGENTS.md`, `apps/AGENTS.md`, `tests/AGENTS.md`, `tests/performance/AGENTS.md`

---

## Success Criteria

```bash
# All 14 files exist
for f in ./AGENTS.md core/AGENTS.md core/vqa/AGENTS.md core/memory/AGENTS.md \
  core/vision/AGENTS.md core/ocr/AGENTS.md application/AGENTS.md \
  application/pipelines/AGENTS.md application/frame_processing/AGENTS.md \
  shared/AGENTS.md infrastructure/AGENTS.md apps/AGENTS.md \
  tests/AGENTS.md tests/performance/AGENTS.md; do
  [ -f "$f" ] && echo "OK: $f" || echo "MISSING: $f"
done
```

### Final Checklist
- [x] 14 AGENTS.md files exist
- [x] Root file has all sections (build, test, lint, types, SLAs, flags, anti-patterns, gotchas)
- [x] No file >250 lines (telegraphic style)
- [x] No child file repeats parent content
- [x] All file/class references verified against actual project structure
