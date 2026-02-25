# Phase 1: Core Completion

> **Phase Focus**: Fill 71 stubs across 9 modules, implement 5 placeholder module MVPs, stabilize cross-module integration.
> **Task Count**: 25 (T-013 through T-037)
> **Risk Classification**: HIGH, multiple parallel clusters permitted with file-level isolation.
> **Entry Criteria**: All P0 tasks completed, secrets infrastructure operational, Docker hardened.

---

## T-013: yolo-detection-hardening

- **Phase**: P1
- **Cluster**: CL-VIS
- **Objective**: Harden the YOLO v8n detection pipeline for production-grade reliability. Improve small-object handling through input resolution scaling and tiled inference for objects under 32px. Add confidence calibration with per-class threshold tuning to reduce false positives on safety-critical classes (person, car, bicycle). Implement graceful model load failure recovery with fallback to a mock detector, clear error logging, and automatic retry on transient GPU memory errors. This task transforms the current baseline YOLO integration into a dependable perception layer for real-time navigation.
- **Upstream Deps**: [`BASE-002`]
- **Downstream Impact**: [`T-015`, `T-016`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `AGENTS.md#performance-risks`, `docs/vision.md#yolo`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, no file overlap with T-014 if segmentation changes are isolated
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-014: midas-depth-calibration

- **Phase**: P1
- **Cluster**: CL-VIS
- **Objective**: Calibrate MiDaS v2.1 depth maps to produce consistent distance estimates with absolute scale reference points. Add calibration routines that anchor relative depth values to known reference distances using camera-specific focal length and sensor parameters. Implement error bounds for close-range objects under 1 meter where MiDaS accuracy degrades. Add depth confidence scoring per pixel region so downstream fusion can weight depth estimates appropriately. Include a calibration data capture mode for collecting ground-truth depth samples during deployment setup.
- **Upstream Deps**: [`BASE-003`]
- **Downstream Impact**: [`T-016`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `AGENTS.md#performance-risks`, `docs/vision.md#midas`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, operates on depth estimation path independent of detection
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-015: segmentation-stub-fill

- **Phase**: P1
- **Cluster**: CL-VIS
- **Objective**: Replace all stub implementations in the edge-aware segmentation module with functional logic. Implement boundary-preserving segmentation using contour refinement on YOLO bounding boxes, producing per-object binary masks with confidence scores. Connect the segmentation output to the spatial fusion pipeline's mask input interface. Handle edge cases: overlapping objects, partially occluded targets, and objects at frame boundaries. Each mask must carry metadata (object class, bounding box origin, edge sharpness score) for downstream consumers.
- **Upstream Deps**: [`T-013`]
- **Downstream Impact**: [`T-016`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `docs/vision.md#segmentation`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, depends on T-013 detection output format
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-016: spatial-fusion-pipeline

- **Phase**: P1
- **Cluster**: CL-VIS
- **Objective**: Complete the spatial fusion pipeline that combines detection, depth estimation, and segmentation into unified ObstacleRecord objects. For each detected object, fuse the YOLO bounding box with its MiDaS depth estimate and segmentation mask to produce a single record containing: class label, distance in meters, direction angle, priority level (critical/near/far/safe), and action recommendation. Handle timing mismatches between the three input streams using freshness windows. Implement priority sorting so the closest and most dangerous obstacles surface first. This is the core data structure that feeds navigation output.
- **Upstream Deps**: [`T-013`, `T-014`, `T-015`]
- **Downstream Impact**: [`T-017`, `T-023`, `T-031`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `AGENTS.md#data-flow-summary`, `docs/vision.md#spatial-fusion`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, requires outputs from T-013 + T-014 + T-015
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-017: navigation-output-formatter

- **Phase**: P1
- **Cluster**: CL-VIS
- **Objective**: Implement the micro-navigation TTS formatter that converts ObstacleRecord arrays into concise spoken cues for blind users. Build a priority-sorted rendering pipeline that produces three output formats: a short TTS cue under 15 words for immediate voice delivery, a verbose description for detail-on-demand requests, and a structured JSON payload for programmatic consumers. Generate distance strings ("1.5 meters"), direction strings ("slightly left", "directly ahead"), and action recommendations ("step right"). Apply rate limiting to prevent TTS overload: suppress repeat warnings for the same object within a configurable cooldown window.
- **Upstream Deps**: [`T-016`]
- **Downstream Impact**: [`T-035`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vision/AGENTS.md`, `docs/vision.md#navigation-output`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, depends on T-016 ObstacleRecord format
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-018: faiss-indexer-stub-fill

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: Fill all stub implementations in the FAISS indexer module. Implement batch insert for bulk memory ingestion, incremental update that adds vectors without full index rebuild, index persistence to disk with atomic write-rename for crash safety, and error recovery for corrupted index files. Add index metadata tracking (vector count, last modified timestamp, embedding dimension) and a health check method that validates index integrity. Handle the edge case of first-time index creation when no persisted file exists. All operations must be thread-safe given SQLite's single-writer constraint.
- **Upstream Deps**: [`BASE-009`]
- **Downstream Impact**: [`T-019`, `T-021`, `T-022`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `AGENTS.md#stub-inventory`, `docs/memory.md#faiss`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, memory module independent of vision module
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-019: rag-retriever-completion

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: Complete the RAG retriever with similarity search, Maximal Marginal Relevance (MMR) reranking, and context window management. Implement a two-stage retrieval pipeline: first-pass FAISS approximate nearest neighbor search returns top-k candidates, then MMR reranking diversifies results to avoid redundant context. Add citation tracking so each retrieved passage carries its source document ID, chunk index, and retrieval score. Implement context window fitting that truncates or summarizes retrieved passages to stay within the LLM's token budget. Handle empty index gracefully by returning a structured "no memories found" response.
- **Upstream Deps**: [`T-018`]
- **Downstream Impact**: [`T-021`, `T-035`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `docs/memory.md#rag-retrieval`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on T-018 indexer interface
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-020: embedding-async-wrapper

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: Wrap OllamaEmbedder synchronous calls with an async interface to prevent event loop blocking. The current implementation blocks for approximately 150ms per embedding call (PR-2), which stalls the entire async pipeline during memory operations. Implement an async wrapper using `asyncio.to_thread` or a dedicated thread pool executor. Add request batching so multiple embedding requests within a configurable time window are combined into a single Ollama API call. Include timeout handling and fallback behavior when the Ollama service is unreachable.
- **Upstream Deps**: [`BASE-011`]
- **Downstream Impact**: [`T-021`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `AGENTS.md#performance-risks`, `docs/memory.md#embeddings`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, no file overlap with T-018 or T-019
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-021: memory-ingest-pipeline

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: Complete the memory ingestion pipeline that processes raw user interactions into indexed, searchable memories. Implement text chunking with configurable overlap and maximum chunk size. Add deduplication using embedding similarity thresholds to prevent near-duplicate memories from bloating the index. Extract metadata (timestamp, source module, interaction type, user intent category) from each ingested item. Integrate consent checking at the ingest boundary so no data enters the pipeline unless the user has granted explicit consent. Connect chunked, deduplicated, metadata-enriched items to the FAISS indexer (T-018) via the async embedding wrapper (T-020).
- **Upstream Deps**: [`T-018`, `T-020`]
- **Downstream Impact**: [`T-035`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `docs/memory.md#ingestion`, `docs/privacy.md#consent-flow`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on T-018 and T-020
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-022: cloud-sync-foundation

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: Implement the cloud sync foundation for bidirectional FAISS index synchronization. Build an incremental delta tracking system that records which vectors were added, modified, or deleted since the last sync checkpoint. Implement conflict resolution for concurrent edits: last-write-wins with vector-level granularity and a conflict log for manual review. Add a sync state machine with states (idle, syncing, conflict, error) and health reporting. The initial implementation targets a single cloud provider (S3-compatible) with the storage abstraction from T-033 as the transport layer. Include bandwidth-aware sync scheduling that avoids saturating the network during active perception processing.
- **Upstream Deps**: [`T-018`]
- **Downstream Impact**: [`#P3-circuit-breakers`, `#P6-feature-evolution`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `AGENTS.md#in-progress-tasks`, `docs/memory.md#cloud-sync`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, depends on T-018 index persistence
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-023: scene-graph-enhancement

- **Phase**: P1
- **Cluster**: CL-VQA
- **Objective**: Enhance the scene graph with spatial relationships and temporal consistency. Add relationship types: above, below, left-of, right-of, near, far-from, occluding, and containing. Compute relationships from ObstacleRecord positions and segmentation masks. Implement temporal consistency tracking across sequential frames using object identity from the spatial fusion pipeline, so the scene graph reflects stable object positions rather than flickering per-frame snapshots. Add a graph diff method that identifies what changed between consecutive frames for efficient downstream processing.
- **Upstream Deps**: [`BASE-007`, `T-016`]
- **Downstream Impact**: [`T-024`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vqa/AGENTS.md`, `docs/vqa.md#scene-graph`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, VQA module independent of memory module
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-024: perception-orchestrator-completion

- **Phase**: P1
- **Cluster**: CL-VQA
- **Objective**: Complete the perception orchestrator that fuses multiple modalities (vision, audio, memory) into a unified perception state. Implement a priority routing system that allocates processing budget across modalities based on context: navigation mode prioritizes vision, conversation mode prioritizes audio, and recall mode prioritizes memory retrieval. Add graceful degradation so that when one modality fails or times out, the orchestrator continues with available inputs rather than blocking entirely. Include a perception state snapshot that downstream consumers (VQA reasoning, agent) can query for the latest fused understanding of the environment.
- **Upstream Deps**: [`BASE-008`, `T-023`]
- **Downstream Impact**: [`T-025`, `T-032`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vqa/AGENTS.md`, `AGENTS.md#core-capabilities`, `docs/vqa.md#perception`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on T-023 scene graph output
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-025: visual-qa-reasoning

- **Phase**: P1
- **Cluster**: CL-VQA
- **Objective**: Implement the visual Q&A reasoning chain that processes user questions about the visual environment. Build a question parser that classifies intent (identification, counting, spatial, descriptive, comparison) and extracts key entities. Implement scene graph query execution for questions answerable from the local perception state. For complex queries requiring deeper reasoning, integrate with Qwen-VL through the Ollama adapter, passing the current frame and scene graph context as input. Add answer formatting that converts structured query results into natural spoken responses. Handle ambiguous questions with clarification requests rather than guessing.
- **Upstream Deps**: [`T-024`]
- **Downstream Impact**: [`T-035`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vqa/AGENTS.md`, `docs/vqa.md#visual-qa`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on T-024 perception state
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-026: ocr-fallback-hardening

- **Phase**: P1
- **Cluster**: CL-OCR
- **Objective**: Harden the 3-tier OCR fallback chain for production use. Improve EasyOCR accuracy on tilted and rotated text by adding deskew preprocessing with Hough line detection. Add confidence scores to MSER heuristic output so downstream consumers can assess OCR quality uniformly across all three tiers. Unify the output format: every OCR result, regardless of which backend produced it, must carry text content, bounding box, confidence score, and backend identifier. Add timing instrumentation to each tier for latency monitoring. Ensure the fallback cascade correctly advances when a tier returns empty or low-confidence results.
- **Upstream Deps**: [`BASE-004`]
- **Downstream Impact**: [`T-035`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/ocr/AGENTS.md`, `docs/ocr.md#fallback-chain`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, OCR module independent of vision and memory modules
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-027: braille-classifier-training

- **Phase**: P1
- **Cluster**: CL-OCR
- **Objective**: Train the braille dot classifier from the current PyTorch model stub to a functional production model. Prepare a labeled dataset of braille dot patterns covering Grade 1 English braille cells. Implement the PyTorch training loop with data augmentation (rotation, scale, brightness jitter) to handle real-world camera conditions. Export the trained model to ONNX format for inference via ONNX Runtime, consistent with the project's inference strategy. Integrate the trained model into the existing `BrailleOCR.read()` pipeline, replacing the lookup-table-only classification path. Add accuracy metrics logging during training and validation.
- **Upstream Deps**: [`BASE-005`]
- **Downstream Impact**: [`T-035`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/braille/AGENTS.md`, `docs/braille.md#classifier`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, braille module independent of other P1 clusters
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-028: face-tracker-persistence

- **Phase**: P1
- **Cluster**: CL-FACE
- **Objective**: Implement persistent face tracking that re-identifies individuals across video frames. Build a tracklet manager that assigns stable IDs to detected faces and maintains identity through brief occlusions using an embedding cache with configurable TTL. Use cosine similarity on face embeddings to match new detections against known tracklets. Handle tracklet lifecycle: creation on first sighting, update on re-identification, suspension during occlusion, and retirement after prolonged absence. Add a tracklet summary method that returns active face count, tracked duration per identity, and last-seen timestamps for the agent's situational awareness.
- **Upstream Deps**: [`BASE-013`]
- **Downstream Impact**: [`T-029`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/face/AGENTS.md`, `docs/face.md#tracking`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, face module independent of vision fusion pipeline
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-029: face-consent-integration

- **Phase**: P1
- **Cluster**: CL-FACE
- **Objective**: Integrate face detection with the consent management system to ensure face data is never stored without explicit user permission. Gate face embedding persistence behind the consent state managed by `core/memory/api_endpoints.py`: when consent is not granted, face detection runs for real-time counting only and discards all embeddings after the current frame. When consent is granted, embeddings persist to the tracklet cache for re-identification. Add PII-safe logging that never writes raw face embeddings or bounding box coordinates to logs. This task bridges core/face with core/memory consent and shared/logging PII scrubbing, touching three module boundaries.
- **Upstream Deps**: [`T-028`, `BASE-012`, `T-001`]
- **Downstream Impact**: [`T-035`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/face/AGENTS.md`, `core/memory/AGENTS.md`, `docs/privacy.md#face-consent`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on T-028 tracklet interface and T-001 secrets
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-030: pipeline-debouncer-watchdog

- **Phase**: P1
- **Cluster**: CL-APP
- **Objective**: Fill the application pipeline stubs for debouncer, watchdog, and worker pool components. Implement debouncer timing logic that collapses rapid-fire frame events into single processing triggers with configurable quiet periods. Build the watchdog health checker that monitors pipeline stage latency, detects stalled workers, and triggers restart sequences. Complete the worker pool manager with dynamic scaling based on queue depth, graceful shutdown on SIGTERM, and dead letter handling for failed tasks. Include stubs for event bus message routing and session state checkpoints, covering the event_bus and session_mgmt placeholder modules at a foundational level.
- **Upstream Deps**: [`BASE-001`]
- **Downstream Impact**: [`T-031`, `T-035`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`application/pipelines/AGENTS.md`, `application/event_bus/AGENTS.md`, `application/session_mgmt/AGENTS.md`, `AGENTS.md#stub-inventory`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, application layer independent of core modules
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-031: frame-processing-engine

- **Phase**: P1
- **Cluster**: CL-APP
- **Objective**: Complete the frame processing engine that orchestrates per-frame perception workflows. Implement freshness management that timestamps incoming frames and discards stale data beyond a configurable age threshold. Build cascade routing that directs frames through the appropriate processing stages (detection, segmentation, depth, fusion) based on the current operating mode and available GPU budget. Add fusion orchestration that collects results from parallel processing branches and assembles a unified FrameResult before forwarding to downstream consumers. Handle partial results when individual stages time out, producing a best-effort FrameResult with quality flags indicating which stages completed.
- **Upstream Deps**: [`T-030`, `T-016`]
- **Downstream Impact**: [`T-035`, `T-036`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`application/frame_processing/AGENTS.md`, `AGENTS.md#data-flow-summary`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on T-030 pipeline infrastructure and T-016 spatial fusion
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-032: reasoning-engine-mvp

- **Phase**: P1
- **Cluster**: CL-RSN
- **Objective**: Implement the reasoning engine MVP in the currently empty `core/reasoning/` placeholder module. Build multi-frame context accumulation that maintains a sliding window of recent perception states (5-10 frames) for temporal reasoning. Implement simple temporal summaries: "the room has been empty for 30 seconds", "a person entered from the left 5 seconds ago", "the lighting changed from bright to dim." Add a reasoning query interface that the VQA orchestrator can call for temporal questions. This is a foundation, not a full reasoning system. Keep the implementation focused and extensible. Create `__init__.py`, `engine.py`, and `temporal.py` within the module.
- **Upstream Deps**: [`T-024`]
- **Downstream Impact**: [`#P6-feature-evolution`, `T-035`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/reasoning/AGENTS.md`, `AGENTS.md#stub-inventory`, `AGENTS.md#repository-structure`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, depends on T-024 perception state format
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-033: storage-abstraction-mvp

- **Phase**: P1
- **Cluster**: CL-INF
- **Objective**: Implement the storage abstraction MVP in the currently empty `infrastructure/storage/` placeholder module. Define a StorageBackend interface with methods for read, write, delete, list, and exists operations on binary blobs. Provide a concrete LocalFilesystemBackend implementation that wraps file I/O with atomic writes, directory auto-creation, and configurable base path. Add a factory function that selects the backend based on configuration (local for development, S3-compatible for production, stubbed for testing). Include model weight management helpers that handle downloading, caching, and verifying checksums for ONNX model files. Create `__init__.py`, `backend.py`, and `local_backend.py`.
- **Upstream Deps**: [`BASE-001`]
- **Downstream Impact**: [`T-022`, `T-035`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/storage/AGENTS.md`, `AGENTS.md#stub-inventory`, `AGENTS.md#repository-structure`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, infrastructure module independent of core modules
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-034: monitoring-mvp

- **Phase**: P1
- **Cluster**: CL-INF
- **Objective**: Implement the monitoring MVP in the currently empty `infrastructure/monitoring/` placeholder module. Build a health check endpoint that reports component status (YOLO loaded, MiDaS loaded, FAISS index healthy, Ollama reachable, Deepgram reachable, ElevenLabs reachable) as a structured JSON response. Add basic metrics collection for pipeline latency, frame processing rate, memory query count, and GPU VRAM usage. Implement structured log aggregation that collects warn/error level events into a rolling buffer accessible via the health endpoint. Create `__init__.py`, `health.py`, and `metrics.py`. Wire the health endpoint into the FastAPI server.
- **Upstream Deps**: [`BASE-001`]
- **Downstream Impact**: [`T-035`, `#P3-monitoring-expansion`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/monitoring/AGENTS.md`, `AGENTS.md#stub-inventory`, `AGENTS.md#operational-risks`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, infrastructure module independent of core modules
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-035: p1-stub-replacement-validation

- **Phase**: P1
- **Cluster**: CL-TQA
- **Objective**: Assert that all targeted `pass # stub`, `TODO`, and `...` placeholder patterns have been eliminated from the modules addressed by Phase 1 tasks. Run comprehensive grep across core/vision/, core/memory/, core/vqa/, core/ocr/, core/braille/, core/face/, core/reasoning/, application/pipelines/, application/frame_processing/, application/event_bus/, application/session_mgmt/, infrastructure/storage/, and infrastructure/monitoring/. Produce a structured report listing any remaining stubs with file path, line number, and pattern type. The target is reducing the total stub count from 71 to below 10 across the entire codebase. Any remaining stubs must be documented with justification.
- **Upstream Deps**: [`T-017`, `T-021`, `T-025`, `T-027`, `T-029`, `T-031`, `T-032`, `T-033`, `T-034`]
- **Downstream Impact**: [`T-036`]
- **Risk Tier**: High
- **Test Layers**: [Integration, Regression]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `AGENTS.md#stub-inventory`, `docs/baselines/p1_stub_report.md`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, must wait for all stub-filling tasks to complete
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-036: p1-cross-module-integration-test

- **Phase**: P1
- **Cluster**: CL-TQA
- **Objective**: Execute an end-to-end integration test covering the full frame processing path: camera input through spatial fusion, scene graph construction, VQA reasoning, and TTS output. Create `tests/integration/test_p1_frame_path.py` with test scenarios that verify data flows correctly across module boundaries. Test the happy path (frame with detectable objects produces spoken navigation cue), degraded paths (missing depth data, failed segmentation), and error paths (corrupted frame, GPU out of memory). Verify that the perception orchestrator correctly fuses vision and memory inputs. Confirm that ObstacleRecords survive the full pipeline with correct field values at each stage.
- **Upstream Deps**: [`T-035`]
- **Downstream Impact**: [`T-037`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on T-035 confirming stubs are filled
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-037: p1-architecture-compliance-check

- **Phase**: P1
- **Cluster**: CL-GOV
- **Objective**: Run import-linter and confirm zero boundary violations after the extensive stub fills and new module implementations in Phase 1. Verify that the 5-layer hierarchy (shared, core, application, infrastructure, apps) remains intact: no upward imports, no cross-layer shortcuts, no circular dependencies introduced by the 25 new task implementations. Check that the three new placeholder modules (core/reasoning/, infrastructure/storage/, infrastructure/monitoring/) follow the correct import patterns for their respective layers. Update documentation to reflect the expanded module inventory and confirm 100% codebase coverage in the documentation status table.
- **Upstream Deps**: [`T-036`]
- **Downstream Impact**: [`#P2-agent-refactoring`]
- **Risk Tier**: Medium
- **Test Layers**: [Integration, Regression]
- **Doc Mutation Map**: [`docs/architecture.md`, `AGENTS.md#documentation-coverage`, `AGENTS.md#repository-structure`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final gate task for Phase 1
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Zero failing tests across all `test_layers` specified by tasks in this phase
3. Every entry in every task's `doc_mutation_map` has been verified as updated
4. No unresolved `blocked` tasks remain
5. Regression suite shows no coverage drop compared to phase entry baseline
6. Stub count reduced below 10 items (from 71 at phase entry)
7. All 5 placeholder modules (core/reasoning/, infrastructure/storage/, infrastructure/monitoring/, application/event_bus/, application/session_mgmt/) have MVP implementations
8. Test count >= 880 (baseline 840 + 40 new tests minimum)
9. Documentation reflects 100% codebase coverage including new modules

## Downstream Notes

- P2 agent.py refactoring depends on P1 module completions being stable, particularly T-016 (spatial fusion), T-024 (perception orchestrator), and T-031 (frame processing engine)
- P3 circuit breakers need the cloud sync foundation from T-022 and the monitoring MVP from T-034 as integration points
- P4 performance validation builds on the spatial fusion pipeline from T-016 and frame processing engine from T-031
- P6 feature evolution extends the reasoning engine MVP from T-032 and cloud sync from T-022
- The event_bus and session_mgmt placeholder modules receive foundational stubs via T-030 but will need dedicated expansion in P2 or P3
