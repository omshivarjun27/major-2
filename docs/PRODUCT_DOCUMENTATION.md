# Ally Vision — Product Documentation Package

**Date:** 2025-01-20
**Version:** 1.0.0
**Repository:** Voice-Vision-Assistant-for-Blind

---

## Table of Contents

1. [Product Requirements Document (PRD)](#1-product-requirements-document)
2. [Prioritized Issue Backlog](#2-prioritized-issue-backlog)
3. [Test Plan and CI Checklist](#3-test-plan-and-ci-checklist)
4. [Refactor Plan](#4-refactor-plan)

---

# 1. Product Requirements Document

## 1.1 Title

**Ally Vision — Real-Time Voice and Vision Assistant for Blind and Visually Impaired Users**

## 1.2 Overview

Ally Vision is an AI-powered assistive application that processes live camera frames, microphone input, and sensor data in real time to deliver spoken scene understanding, obstacle warnings, text reading, and memory-assisted recall to blind and visually impaired users. The system runs as a LiveKit voice agent communicating with a user over WebRTC, complemented by a REST API for programmatic access.

## 1.3 Problem Statement

Blind and visually impaired individuals face continuous challenges navigating physical spaces, reading printed or displayed text, identifying people and objects, and recalling where they last encountered items. Existing assistive tools address these needs in isolation and often introduce unacceptable latency or require constant internet connectivity. There is no single, real-time, multi-modal system that fuses vision, audio, spatial perception, and long-term memory into a unified spoken interface.

## 1.4 Goals

1. Deliver sub-250ms end-to-end frame processing so spoken cues arrive before the user has moved past a hazard.
2. Provide at least twelve distinct assistive capabilities (object detection, depth estimation, OCR, QR scanning, braille reading, face recognition with consent, sound localization, action recognition, RAG memory, VQA, TTS, internet search) through a single conversational interface.
3. Run entirely on-device where possible, using Ollama-hosted models, with cloud fallbacks gated by strict timeouts.
4. Enforce privacy-by-default: face recognition is opt-in, memory data is encrypted at rest, and all personal data can be purged on demand.
5. Maintain a Clean Architecture codebase (five layers, enforced by import-linter) so each capability can be developed, tested, and deployed independently.

## 1.5 Target Users

| Persona | Description | Key Needs |
|---------|-------------|-----------|
| **Primary — Blind pedestrian** | Person with total or near-total vision loss navigating indoor/outdoor spaces | Real-time obstacle warnings, path-clear confirmation, distance and direction cues |
| **Primary — Low-vision reader** | Person with partial sight who cannot reliably read printed text | OCR for documents, QR/barcode scanning, braille reading assistance |
| **Secondary — Caregiver / family** | Support person who configures the system and reviews session logs | REST API access, debug metrics, session replay, consent management |
| **Secondary — Developer / integrator** | Engineer extending or embedding Ally Vision in another product | Clean API boundaries, documented schemas, modular core packages |

## 1.6 User Stories with Acceptance Criteria

### US-01: Real-Time Obstacle Detection

**As a** blind pedestrian,
**I want** spoken warnings about obstacles in my path,
**so that** I can avoid collisions.

**Acceptance Criteria:**
- The system captures a camera frame, runs YOLOv8n object detection (core/vision/spatial.py, class `ONNXYOLODetector`), and MiDaS depth estimation to produce distance values.
- Objects closer than one meter are announced as "Stop! [object] [distance] [direction]" within 250ms of frame capture.
- Objects at one to two meters are announced as "Caution, [object] [distance] [direction]."
- When no obstacles are detected the system says "Path clear."
- The function tool `detect_obstacles` in apps/realtime/agent.py (line 767) times out after 500ms and returns a failsafe message rather than hanging.
- Duplicate cues within the debounce window (default 5 seconds, configurable via `DEBOUNCE_WINDOW_SECONDS`) are suppressed by the Debouncer (application/pipelines/debouncer.py).

### US-02: Visual Scene Description

**As a** blind user,
**I want** to ask "What do you see?" and receive a spoken description,
**so that** I understand my surroundings.

**Acceptance Criteria:**
- The `analyze_vision` function tool (agent.py line 690) captures a frame, checks freshness via `is_frame_fresh()` (application/frame_processing/freshness.py), and sends the image plus the user's query to qwen3-vl:235b-instruct-cloud via the OpenAI-compatible Ollama endpoint.
- The response is streamed chunk-by-chunk to the TTS pipeline so the user hears partial answers while generation continues.
- If the frame is stale (older than the configured `max_age_ms`, default 500ms), the system returns the camera fallback message instead of describing an outdated scene.

### US-03: Visual Question Answering (VQA)

**As a** blind user,
**I want** to ask specific questions about what the camera sees ("What color is my shirt?", "Is the door open?"),
**so that** I get precise, grounded answers.

**Acceptance Criteria:**
- The `ask_visual_question` function tool (agent.py line 968) runs the full VQA pipeline: PerceptionPipeline (core/vqa/perception.py) for detection, SceneGraphBuilder (core/vqa/scene_graph.py) for spatial relationships, SpatialFuser (core/vqa/spatial_fuser.py) for fusion, and VQAReasoner (core/vqa/vqa_reasoner.py) for answer generation.
- The answer includes provenance (which model produced each fact with confidence and bounding-box references).
- Results are stored in VQAMemory (core/vqa/memory.py) for cross-session recall.
- If the VQA engine is not available, the system falls back to direct Ollama analysis via `_analyze_with_ollama`.

### US-04: Text Reading via OCR

**As a** low-vision reader,
**I want** to point my camera at text and hear it read aloud,
**so that** I can read documents, signs, and labels.

**Acceptance Criteria:**
- The `read_text` function tool (agent.py line 1257) captures a frame and passes it to OCRPipeline (core/ocr/engine.py).
- The OCR engine tries backends in cascade order: EasyOCR, pytesseract, OpenCV MSER heuristic.
- Detected text is returned as "Text reads: [content]" and spoken via TTS.
- If no text is detected, the system says "No readable text detected."
- Timeout is capped at 2 seconds.

### US-05: QR and AR Tag Scanning

**As a** blind user,
**I want** to scan QR codes and AR tags by pointing my camera,
**so that** I can access encoded information such as URLs, product details, or navigation markers.

**Acceptance Criteria:**
- The `scan_qr_code` function tool (agent.py line 1092) captures a frame and runs it through QRScanner (core/qr/qr_scanner.py) with pyzbar as the primary backend and OpenCV QRCodeDetector as fallback.
- Decoded payloads are sanitized before being spoken (no automatic URL navigation).
- Results are cached by CacheManager (core/qr/cache_manager.py) with a configurable TTL (default 86400 seconds) to avoid reprocessing identical codes.
- AR tags are handled by ARTagHandler (core/qr/ar_tag_handler.py).
- The REST API exposes QR endpoints at `/qr/*` via `build_qr_router()` (core/qr/qr_api.py).

### US-06: Braille Reading

**As a** blind user encountering embossed braille,
**I want** the system to photograph the braille and read it to me,
**so that** I can access braille content I cannot feel clearly.

**Acceptance Criteria:**
- The braille pipeline consists of BrailleSegmenter (core/braille/braille_segmenter.py) for dot detection, BrailleClassifier (core/braille/braille_classifier.py) for character recognition, and BrailleOCR (core/braille/braille_ocr.py) for end-to-end transcription.
- The result includes text, confidence score, character count, and dot count (BrailleOCRResult dataclass).
- If lighting or curvature degrades accuracy, the system returns a corrective prompt.
- EmbossingGuidance (core/braille/embossing_guidance.py) provides feedback on image quality for capture.

### US-07: Face Detection and Opt-In Recognition

**As a** blind user,
**I want** to know when there is a person in front of me and optionally identify known people,
**so that** I can greet them appropriately.

**Acceptance Criteria:**
- Face detection runs by default using FaceDetector (core/face/face_detector.py) with MTCNN, RetinaFace, or Haar cascade backends.
- Face recognition (embedding matching via FaceEmbeddingStore in core/face/face_embeddings.py) requires explicit opt-in consent recorded via `POST /face/consent` (apps/api/server.py line 165).
- Face embeddings are encrypted at rest using EncryptionManager (shared/encryption.py) with Fernet (AES-128-CBC + HMAC-SHA256).
- All face data can be purged via `DELETE /face/forget_all` (server.py line 217).
- FaceTracker (core/face/face_tracker.py) maintains identity across frames.
- FaceSocialCues (core/face/face_social_cues.py) detects gaze direction and expressions.
- The `FACE_ENCRYPTION_ENABLED` and `FACE_ENCRYPTION_KEY` environment variables control encryption.
- Consent state is persisted to `data/face_consent.json` so the agent and API share the same consent view.

### US-08: Sound Localization and Event Detection

**As a** blind user,
**I want** to be alerted when safety-critical sounds occur (car horn, siren, alarm),
**so that** I can react to dangers I cannot see.

**Acceptance Criteria:**
- AudioEventDetector (core/audio/audio_event_detector.py) classifies ambient sounds into categories: car_horn, siren, alarm, voice, footsteps, dog_bark, door, traffic, silence, unknown.
- Critical events (car_horn, siren, alarm) trigger immediate spoken alerts.
- SoundSourceLocalizer (core/audio/ssl.py) estimates direction-of-arrival using GCC-PHAT.
- AudioVisionFuser (core/audio/audio_fusion.py) correlates audio events with visual detections.
- The `/audio/health` REST endpoint reports subsystem status.

### US-09: Action Recognition

**As a** blind user,
**I want** to know when someone is approaching, running toward me, or falling nearby,
**so that** I can respond to dynamic situations.

**Acceptance Criteria:**
- ActionRecognizer (core/action/action_recognizer.py) buffers short video clips and uses optical flow plus a classifier to detect actions: approaching, walking_away, waving, running, cycling, standing, sitting, falling, reaching.
- Safety-critical actions (approaching, running, cycling, falling) trigger immediate vocal alerts.
- The `/action/health` REST endpoint reports subsystem status.

### US-10: Long-Term Memory and RAG Recall

**As a** blind user,
**I want** to ask "Where did I leave my keys?" and have the system recall past observations,
**so that** I can find misplaced items.

**Acceptance Criteria:**
- Observations are ingested by MemoryIngest (core/memory/ingest.py) and embedded using TextEmbedder (core/memory/embeddings.py) which calls the Ollama embedding API with model `qwen3-embedding:4b`.
- Embeddings are indexed in FAISS (core/memory/indexer.py) with configurable `MEMORY_MAX_VECTORS` (default 5000).
- Retrieval is handled by MemoryRetriever (core/memory/retriever.py) with RAG top-K (default 5) configurable via `RAG_K`.
- RAGReasoner (core/memory/rag_reasoner.py) combines retrieved memories with qwen3-vl to generate cited answers.
- Memory is encrypted at rest when `MEMORY_ENCRYPTION=true`.
- Retention policy enforces `MEMORY_RETENTION_DAYS` (default 30 days) via MemoryMaintenance (core/memory/maintenance.py).
- REST endpoints at `/memory/*` (core/memory/api_endpoints.py) expose search, ingest, and maintenance operations.
- CloudSync (core/memory/cloud_sync.py) is available but disabled by default.

### US-11: Internet Search

**As a** blind user,
**I want** to ask about current events or facts the system doesn't know from its camera,
**so that** I get up-to-date information.

**Acceptance Criteria:**
- The `search_internet` function tool (agent.py line 632) delegates to InternetSearch (infrastructure/llm/internet_search.py) which uses DuckDuckGo.
- Results are formatted with source links and spoken aloud.
- The feature does not require any API key.

### US-12: Continuous Frame Processing and Proactive Announcements

**As a** blind pedestrian in always-on mode,
**I want** the system to continuously monitor the camera and proactively warn me of hazards without being asked,
**so that** I stay safe while walking.

**Acceptance Criteria:**
- LiveFrameManager (application/frame_processing/live_frame_manager.py) captures frames at a configurable cadence (default 100ms).
- FrameOrchestrator (application/frame_processing/frame_orchestrator.py) runs detection and depth on each frame.
- The proactive announcer loop (agent.py, lines ~1795-1860) speaks hazard cues via `agent_session.say()` when `always_on` and `proactive_announce` are enabled in config.
- Cues are debounced, and a minimum three-second cooldown prevents TTS spam.
- Watchdog (application/pipelines/watchdog.py) monitors camera and worker health; if the camera stalls for more than 2 seconds, it resets the video stream and speaks a warning.

## 1.7 Non-Functional Requirements

### NFR-01: Latency

- End-to-end frame processing must complete within 250ms (configurable via `configs/config.yaml` → `latency.frame_budget_ms`).
- TTS must emit the first audio chunk within 300ms for short texts (configurable via `latency.tts_first_chunk_ms`).
- Remote TTS timeout is 2 seconds (configurable via `latency.tts_remote_timeout_ms`); on timeout, the system falls back to local TTS.
- Obstacle detection targets less than 200ms (timeout 500ms in agent.py).
- VQA targets less than 500ms total.

### NFR-02: Privacy and Security

- Face recognition is opt-in only; `privacy.face_recognition_opt_in` defaults to `false` in config.yaml.
- Memory data is AES-128-CBC encrypted at rest via Fernet (shared/encryption.py) when `MEMORY_ENCRYPTION=true`.
- Face embeddings are encrypted using the same mechanism when `FACE_ENCRYPTION_ENABLED=true`.
- Debug endpoints require Bearer token authentication (apps/api/server.py, `require_debug_auth` dependency).
- Banned modules (e.g., `antigravity`) are rejected at startup (shared/utils/startup_guards.py).
- All personal data (face embeddings, memory index, consent records) can be purged via API endpoints.

### NFR-03: Reliability and Graceful Degradation

- Every subsystem initializes inside a try/except with an `_AVAILABLE` flag (e.g., `VQA_ENGINE_AVAILABLE`, `QR_ENGINE_AVAILABLE`, `OCR_ENGINE_AVAILABLE` in agent.py).
- If a model or dependency fails to load, the system enters degraded mode and returns a spoken message "Degraded mode: perception limited."
- The OCR engine tries three backends in cascade (EasyOCR → pytesseract → OpenCV MSER); at least one must succeed.
- The QR scanner tries pyzbar then OpenCV QRCodeDetector.
- The face detector tries MTCNN → RetinaFace → Haar cascades.
- All function tools return a human-readable failsafe string on error rather than raising exceptions to the LLM.

### NFR-04: Observability

- Structured JSON logging is configured via shared/logging/logging_config.py (JSON in production, colored text in dev).
- Per-frame JSON telemetry includes timestamp, frame_id, device, venv status, detections, QR results, TTS status, errors, and meta (conflicts, alerts).
- The `/debug/metrics` REST endpoint exposes aggregate perception and TTS metrics.
- PerceptionTelemetry (application/pipelines/perception_telemetry.py) tracks latency, TTS failures, and misclassification rates.
- SessionLogger (apps/cli/session_logger.py) records all events for session replay.
- RuntimeDiagnostics (shared/utils/runtime_diagnostics.py) runs preflight checks at startup and reports system status.

### NFR-05: Configurability

- All thresholds are centralized in `configs/config.yaml` and can be overridden by environment variables.
- Feature toggles (spatial_perception, qr_scanning, ocr, face_detection, face_recognition, audio_engine, action_engine, braille, memory_rag, tavus, cloud_sync) are in config.yaml under `features`.
- Confidence thresholds, latency budgets, privacy settings, confusion pairs, and banned modules are all configurable.
- The `.env` file controls API keys, model paths, and service URLs.

### NFR-06: Portability

- CPU-first design: GPU is optional (torch and ultralytics are commented out in requirements.txt).
- ONNX Runtime is the primary inference runtime for YOLO and MiDaS (models/yolov8n.onnx, models/midas_v21_small_256.onnx).
- Dockerfile is provided for containerized deployment.
- The system detects device capabilities (CPU/CUDA) at startup and logs the result.

## 1.8 Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-01 | LiveKit SDK breaking changes | Medium | High | Pin `livekit-agents>=1.0.0` in requirements.txt; integration tests cover agent startup |
| R-02 | Ollama model unavailability | Medium | High | Failsafe strings in every function tool; `OllamaHandler` has retry and timeout logic |
| R-03 | ElevenLabs TTS latency spikes | High | Medium | 2-second timeout; proactive announcer has 3-second cooldown and TTS lock |
| R-04 | Camera stall on mobile WebRTC | Medium | High | Watchdog monitors camera with 2-second stall threshold; resets stream automatically |
| R-05 | FAISS index corruption | Low | High | EncryptionManager writes atomically (tmp → replace); maintenance has backup logic in `data/memory_backup/` |
| R-06 | Privacy regulation non-compliance | Low | Critical | Face recognition is off by default; consent is file-backed and audit-logged; purge endpoints exist |
| R-07 | Model size exceeds device memory | Medium | High | ONNX models are small (yolov8n ~6MB, midas_small ~30MB); embedding runs server-side via Ollama API |
| R-08 | Dependency supply-chain attack | Low | Critical | `sentence-transformers` is still listed in pyproject.toml dependencies but no longer used (was replaced by Ollama in session 6); should be removed |

## 1.9 Implementation Priorities

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 0** | Clean Architecture migration (5 layers, import-linter enforcement) | Done |
| **Phase 1** | Core perception loop: object detection + depth + obstacle warnings | Implemented |
| **Phase 2** | VQA engine, OCR, QR scanning, internet search | Implemented |
| **Phase 3** | Memory engine (RAG), face engine (consent-gated), TTS streaming | Implemented |
| **Phase 4** | Continuous frame processing, proactive announcements, debouncing, watchdog | Implemented |
| **Phase 5** | Audio engine (SSL, event detection), action recognition, braille OCR | Implemented (not wired to agent function tools) |
| **Phase 6** | Tavus virtual avatar integration | Implemented (optional, disabled by default) |
| **Phase 7** | Cloud sync, advanced memory analytics, mobile-optimized inference | Partially implemented |

---

# 2. Prioritized Issue Backlog

## Priority Legend

- **P0 — Blocker**: Prevents deployment or causes data loss / safety risk. Fix immediately.
- **P1 — High**: Degrades a primary user flow or violates a documented requirement. Fix this sprint.
- **P2 — Medium**: Improves quality, removes tech debt, or enables a secondary flow. Plan for next sprint.

---

### P0 — Blockers

#### P0-01: Remove stale `sentence-transformers` dependency

**Problem:** `pyproject.toml` (line 60) and `requirements.txt` (line 88) still list `sentence-transformers>=2.2.0` as a runtime dependency. This package is no longer used anywhere in the codebase since the embedding model was migrated to `qwen3-embedding:4b` via the Ollama API in core/memory/embeddings.py. The package pulls in PyTorch (~2GB), making Docker images unnecessarily large and creating a false dependency.

**Evidence:** `grep -r "sentence.transformers" core/ application/ infrastructure/ shared/ apps/` returns zero matches. The only import was in the old `TextEmbedder` class, which now calls `ollama.embed()`.

**Fix:** Remove `sentence-transformers>=2.2.0` from `pyproject.toml` dependencies and from `requirements.txt`. Run `pip install -e ".[dev]"` to verify no breakage.

---

#### P0-02: Pre-existing test failures block CI green

**Problem:** The latest test run reports 15 failures and 20 errors that pre-date recent changes. Key failures include:
- `ModuleNotFoundError: No module named 'application.frame_processing.debouncer'` — the file exists at `application/pipelines/debouncer.py`, but tests import it from the wrong path.
- `test_tavus_adapter.py` cannot import `infrastructure.tavus.tavus_adapter` — the file is named `adapter.py`, not `tavus_adapter.py`.
- Debug auth endpoint tests fail when `DEBUG_AUTH_TOKEN` is not set.

**Evidence:** Test output from the last full `pytest` run (1711 passed, 15 failed, 20 errors).

**Fix:**
1. Update test imports from `application.frame_processing.debouncer` to `application.pipelines.debouncer`.
2. Update test imports from `infrastructure.tavus.tavus_adapter` to `infrastructure.tavus.adapter`.
3. Set `DEBUG_AUTH_TOKEN=test-token` and `DEBUG_ENDPOINTS_ENABLED=true` in test fixtures or conftest.py for debug endpoint tests.

---

#### P0-03: Audio, action, and braille engines not wired to agent function tools

**Problem:** The core modules for audio event detection (core/audio/), action recognition (core/action/), and braille OCR (core/braille/) are fully implemented with classes, tests, and REST endpoints, but there are no `@function_tool()` methods in `AllyVisionAgent` (apps/realtime/agent.py) that expose them to the conversational interface. A blind user cannot trigger these features by voice.

**Evidence:** Searching for `audio_event` or `action_recogn` or `braille` in agent.py yields zero matches outside import comments. The eight function tools are: `search_internet`, `analyze_vision`, `detect_obstacles`, `analyze_spatial_scene`, `ask_visual_question`, `get_navigation_cue`, `scan_qr_code`, `read_text`.

**Fix:** Add three new function tools: `detect_sounds`, `recognize_actions`, `read_braille`. Each should follow the existing pattern: capture input, check availability flag, call the core module, return a human-readable string, and handle timeouts with failsafe messages.

---

### P1 — High Priority

#### P1-01: `livekit-plugins-openai` used only for OpenAI-compatible API wrapper

**Problem:** `livekit-plugins-openai>=1.0.0` is listed as a dependency and imported in agent.py (`from livekit.plugins import ... openai ...`) solely to use its `openai.LLM()` class as a generic OpenAI-compatible wrapper against the Ollama endpoint. This creates a confusing dependency name suggesting OpenAI's proprietary API is in use.

**Evidence:** `LLM_BASE_URL` defaults to `http://localhost:11434/v1` (Ollama), and `LLM_API_KEY` defaults to `"ollama"`. No OpenAI models are referenced.

**Fix:** Document clearly in README.md and `.env.example` that this plugin is used as a generic OpenAI-compatible client, not for OpenAI API access. Alternatively, evaluate whether the Ollama Python client can replace this plugin to eliminate confusion.

---

#### P1-02: Face engine function tools missing from agent

**Problem:** The face engine (core/face/) has four modules (detector, embeddings, social_cues, tracker) and REST endpoints (server.py lines 140-228), but there is no `@function_tool()` in the agent that lets a user say "Who is that?" or "Is anyone looking at me?" The only face interaction is through REST API calls.

**Evidence:** No `face` function tool exists in agent.py. The UserData dataclass has no face-related fields.

**Fix:** Add a `detect_faces` function tool that captures a frame, runs FaceDetector, checks consent before running FaceEmbeddingStore matching, and returns a spoken description.

---

#### P1-03: No integration test for the end-to-end LiveKit agent startup

**Problem:** The `entrypoint()` function in agent.py is approximately 500 lines long and initializes eleven subsystems sequentially. There is no integration test that boots the agent with mocked LiveKit room and verifies all subsystems initialize without errors.

**Evidence:** Tests in `tests/` cover individual modules (embeddings, OCR, QR, etc.) but not the agent entrypoint. The `tests/realtime/` directory exists but contains no agent startup test.

**Fix:** Create `tests/integration/test_agent_startup.py` that mocks `JobContext`, `Room`, and external services, then calls `entrypoint()` and asserts all `_AVAILABLE` flags and `UserData` fields are set correctly.

---

#### P1-04: No type checking or mypy in CI

**Problem:** The codebase uses type hints extensively (dataclasses, Annotated types, Optional fields), but there is no mypy or pyright configuration in `pyproject.toml` and no type-checking step in CI. Type errors can silently pass.

**Evidence:** `pyproject.toml` has `[tool.ruff]` and `[tool.pytest]` but no `[tool.mypy]` section. No mypy in requirements-extras.txt.

**Fix:** Add `[tool.mypy]` config to pyproject.toml with `strict = false` initially and add mypy to the dev dependencies and CI pipeline. Enable strict mode incrementally per package.

---

#### P1-05: Hardcoded ElevenLabs voice configuration

**Problem:** The ElevenLabs voice ID (`21m00Tcm4TlvDq8ikWAM`, the "Rachel" voice) and model (`eleven_turbo_v2_5`) are hardcoded in multiple places: agent.py lines ~1840 and ~1850, TTSConfig dataclass in core/speech/tts_handler.py, and the runtime diagnostics preflight. These should be configurable.

**Evidence:** The voice_id string appears three times in agent.py and once in tts_handler.py.

**Fix:** Add `ELEVENLABS_VOICE_ID` and `ELEVENLABS_MODEL` to `.env.example` and `configs/config.yaml`, then read them from config in agent.py and tts_handler.py.

---

#### P1-06: Memory engine `event_detection.py` exists but is never imported

**Problem:** `core/memory/event_detection.py` exists as a file but is never imported or used by any other module. Its purpose (detecting memory-worthy events) is handled inline in the VQA memory store and the `MemoryIngest` class.

**Evidence:** `grep -r "event_detection" core/ apps/ application/` returns only the file itself and its `__init__.py` re-export.

**Fix:** Either integrate event_detection.py into the ingest pipeline (likely the intent), or remove it to reduce dead code. Investigate whether it was superseded by inline logic in `ingest.py`.

---

### P2 — Medium Priority

#### P2-01: Root-level legacy test files

**Problem:** Approximately 25 test files remain in the `tests/` root directory (e.g., `test_confidence_cascade.py`, `test_continuous_processing.py`, `test_debouncer.py`) instead of being organized under `tests/unit/` or `tests/integration/`. This makes test discovery inconsistent.

**Evidence:** `list_dir tests/` shows test files alongside `unit/`, `integration/`, `realtime/`, and `performance/` subdirectories.

**Fix:** Move each root test file to `tests/unit/` or `tests/integration/` based on whether it requires external services. Update any relative imports.

---

#### P2-02: Duplicate RAG reasoner test files

**Problem:** `test_rag_reasoner_claude.py` exists in both `tests/unit/` and `tests/integration/`. These may be identical or divergent copies.

**Evidence:** Both files exist; content comparison has not been done.

**Fix:** Compare the files, merge unique test cases into one, and remove the duplicate.

---

#### P2-03: `cloud_sync.py` is a stub

**Problem:** `core/memory/cloud_sync.py` is present but the cloud sync feature is disabled by default (`features.cloud_sync: false` in config.yaml). The implementation status is unclear.

**Evidence:** The `/health` endpoint reports `"cloud_sync": config.get("CLOUD_SYNC_ENABLED", False)`. No test covers cloud sync.

**Fix:** Either implement cloud sync to a defined spec (S3 or GCS backup of FAISS index + metadata) or mark it as "future" in the feature toggle docs and add a clear "not implemented" guard in the code.

---

#### P2-04: Dockerfile does not use multi-stage build

**Problem:** The Dockerfile exists but does not use multi-stage builds to separate build-time dependencies (gcc, build-essential) from the runtime image. This increases deployment image size.

**Evidence:** Dockerfile in repository root.

**Fix:** Refactor to use a builder stage for pip install and a slim runtime stage that copies only the installed site-packages and the application code.

---

#### P2-05: No ruff format/lint step in CI

**Problem:** Ruff is configured in `pyproject.toml` with rules for E, F, W, I but there is no evidence of a CI step that runs `ruff check` or `ruff format --check`.

**Evidence:** `pyproject.toml` has `[tool.ruff]` config. No CI configuration file (`.github/workflows/*.yml`) has been examined, but the project uses `docker-compose.test.yml` for testing.

**Fix:** Add `ruff check .` and `ruff format --check .` to the CI pipeline alongside `lint-imports` and `pytest`.

---

#### P2-06: `infrastructure/monitoring/__init__.py` is empty

**Problem:** The monitoring infrastructure package contains only an empty `__init__.py`. No monitoring implementation exists despite the observability NFR.

**Evidence:** `list_dir infrastructure/monitoring/` returns only `__init__.py`.

**Fix:** Implement Prometheus metrics export or structured metric counters and wire them to the `/debug/metrics` endpoint. Alternatively, move PerceptionTelemetry from `application/pipelines/` to `infrastructure/monitoring/` and expose it.

---

#### P2-07: `infrastructure/storage/__init__.py` is empty

**Problem:** The storage infrastructure package contains only an empty `__init__.py`. Local file I/O and FAISS persistence are handled directly in core/memory/ modules.

**Evidence:** `list_dir infrastructure/storage/` returns only `__init__.py`.

**Fix:** Either implement a storage abstraction (local filesystem, S3, GCS) and have core/memory/ depend on it through dependency injection, or remove the empty package to avoid confusion.

---

#### P2-08: System prompt is duplicated

**Problem:** The `VISION_SYSTEM_PROMPT` string (approximately 200 lines) is defined at module level in agent.py and then a nearly identical copy is passed to `AllyVisionAgent.__init__` as the `instructions` parameter. This duplication will drift.

**Evidence:** Compare agent.py lines 104-418 (module-level `VISION_SYSTEM_PROMPT`) and lines 430-520 (inline `instructions` string in `__init__`).

**Fix:** Pass `VISION_SYSTEM_PROMPT` as the `instructions` argument in `AllyVisionAgent.__init__` instead of duplicating the text.

---

#### P2-09: `SiliconFlow` infrastructure exists but is unused

**Problem:** `infrastructure/llm/siliconflow/` directory exists with handlers for a SiliconFlow vision API, but no feature or function tool references it.

**Evidence:** The directory exists; `grep -r "siliconflow" apps/` returns no matches in agent.py or server.py. Two test files (`test_siliconflow.py` in root and integration) reference it.

**Fix:** Either wire SiliconFlow as an alternative vision provider or remove the dead code.

---

#### P2-10: `apps/cli/` purpose and contents unclear

**Problem:** `apps/cli/` contains `session_logger.py` (imported by agent.py and server.py) but the directory name suggests a CLI application that does not exist.

**Evidence:** `apps/cli/` contains `__init__.py`, `session_logger.py`, and `visualizer.py`.

**Fix:** Rename to `apps/common/` or move `session_logger.py` and `visualizer.py` to `shared/debug/` since they are utility modules, not a CLI application.

---

# 3. Test Plan and CI Checklist

## 3.1 Core Flows to Test

### Flow 1: Live Camera Frame Capture and Obstacle Detection

**What to verify:** A fresh camera frame is captured, passed through YOLO object detection and MiDaS depth estimation, and a spoken cue is produced within the latency budget.

**Entry point:** `AllyVisionAgent.detect_obstacles()` (apps/realtime/agent.py line 767)

**Modules exercised:**
- `core/vision/spatial.py` — `ONNXYOLODetector.detect()`, `PipelineSpatialPerception.process_full()`
- `application/frame_processing/freshness.py` — `is_frame_fresh()`
- `application/pipelines/debouncer.py` — `Debouncer.should_speak()`

**Test approach:**
1. Unit test: Mock camera frame, mock YOLO detector returning known detections, mock MiDaS returning known depth map. Assert output string matches "Stop! chair 0.5m ahead" pattern. Assert latency under 250ms.
2. Unit test: Pass a stale timestamp (older than max_age_ms). Assert the function returns `FALLBACK_MESSAGE`.
3. Unit test: Call twice with the same cue within debounce window. Assert second call is debounced.

**Existing coverage:** `tests/test_spatial_perception.py`, `tests/test_freshness.py`, `tests/test_debouncer.py`, `tests/unit/test_perception.py`

---

### Flow 2: OCR Text Reading

**What to verify:** A camera frame containing text is processed by the OCR cascade and the extracted text is returned as a speakable string.

**Entry point:** `AllyVisionAgent.read_text()` (apps/realtime/agent.py line 1257)

**Modules exercised:**
- `core/ocr/engine.py` — `OCRPipeline.process()`
- Backend cascade: EasyOCR → pytesseract → OpenCV MSER

**Test approach:**
1. Unit test: Provide a synthetic image with known text. Mock one backend as available. Assert extracted text matches expected content.
2. Unit test: All backends unavailable. Assert `OCRPipeline.is_ready` is `False` and the function returns "Text reading is not available."
3. Unit test: Backend returns empty text. Assert "No readable text detected."
4. Unit test: Processing exceeds 2-second timeout. Assert failsafe message returned.

**Existing coverage:** `tests/unit/test_ocr_engine_fallbacks.py`, `tests/unit/test_ocr_install_error.py`

---

### Flow 3: QR Code Scanning

**What to verify:** A camera frame with a QR code is decoded, the payload is sanitized, and the result is cached.

**Entry point:** `AllyVisionAgent.scan_qr_code()` (apps/realtime/agent.py line 1092)

**Modules exercised:**
- `core/qr/qr_scanner.py` — `QRScanner.scan()`
- `core/qr/qr_decoder.py` — `QRDecoder.decode()`
- `core/qr/cache_manager.py` — `CacheManager.get()` / `CacheManager.put()`
- `core/qr/ar_tag_handler.py` — `ARTagHandler.detect()`

**Test approach:**
1. Unit test: Provide a synthetic QR image. Mock pyzbar decode. Assert decoded payload matches expected value.
2. Unit test: pyzbar unavailable, OpenCV fallback. Assert decode still succeeds.
3. Unit test: Same QR scanned twice. Assert second scan returns cached result.
4. Integration test: End-to-end scan with real pyzbar on a generated QR image.

**Existing coverage:** `tests/unit/test_qr_scanner.py`, `tests/unit/test_qr_decoder.py`, `tests/unit/test_cache_manager.py`, `tests/integration/test_qr_flow.py`

---

### Flow 4: TTS Streaming Output

**What to verify:** Generated text is chunked and streamed to ElevenLabs TTS (or local fallback) with first-chunk latency under 300ms.

**Entry point:** `AgentSession` configured in `entrypoint()` with `elevenlabs.TTS()`

**Modules exercised:**
- `infrastructure/speech/elevenlabs/` — ElevenLabs TTS plugin
- `core/speech/tts_handler.py` — `TTSHandler` (chunking, caching)
- `application/pipelines/streaming_tts.py` — streaming pipeline

**Test approach:**
1. Unit test: Provide a short text string. Mock ElevenLabs API. Assert first chunk emitted within 300ms.
2. Unit test: ElevenLabs API times out after 2 seconds. Assert fallback to local TTS and `meta.tts_fallback=true` in telemetry.
3. Unit test: Identical text sent twice. Assert second call uses cached audio.

**Existing coverage:** Limited. `tests/test_deepgram.py` exists for STT but no dedicated TTS test found.

---

### Flow 5: Face Privacy Consent Flow

**What to verify:** Face detection proceeds without consent, but face recognition is blocked until consent is explicitly granted. Consent is persisted and can be revoked with data purge.

**Entry point:** REST API endpoints: `POST /face/consent`, `GET /face/consent/log`, `POST /face/detect`, `DELETE /face/forget_all` (apps/api/server.py lines 140-228)

**Modules exercised:**
- `core/face/face_detector.py` — `FaceDetector.detect()`
- `core/face/face_embeddings.py` — `FaceEmbeddingStore.match()`, `.record_consent()`, `.forget_all()`
- `shared/encryption.py` — `EncryptionManager.save_encrypted()`, `.load_decrypted()`
- File-backed consent: `data/face_consent.json`

**Test approach:**
1. Unit test: Call `POST /face/detect` without consent granted. Assert HTTP 403 with "consent_required" status.
2. Unit test: Call `POST /face/consent` with `user_consent=true`, then `POST /face/detect`. Assert HTTP 200.
3. Unit test: Call `DELETE /face/forget_all`. Assert consent file is cleared and embeddings are purged.
4. Unit test: Verify EncryptionManager encrypts and decrypts face embedding data correctly.

**Existing coverage:** `tests/unit/test_debug_endpoints.py` covers debug auth but not face consent flow. No dedicated face consent test found.

---

### Flow 6: RAG Memory Query

**What to verify:** A user question about a past observation is matched against stored memories via FAISS, and the RAG reasoner produces a cited answer.

**Entry point:** Memory REST API at `/memory/*` (core/memory/api_endpoints.py) and inline memory storage in `ask_visual_question` (agent.py)

**Modules exercised:**
- `core/memory/embeddings.py` — `TextEmbedder.embed()`
- `core/memory/indexer.py` — `MemoryIndexer.add()`, `.search()`
- `core/memory/retriever.py` — `MemoryRetriever.retrieve()`
- `core/memory/rag_reasoner.py` — `RAGReasoner.answer()`
- `core/memory/config.py` — `get_memory_config()`

**Test approach:**
1. Unit test: Ingest a known observation ("keys are on the kitchen table"). Embed and index it. Query "Where are my keys?" Assert retrieved memory matches the ingested observation.
2. Unit test: Mock Ollama embed API. Assert TextEmbedder produces a numpy array of the correct dimension.
3. Unit test: Query with no matching memories. Assert response says "I don't recall that."
4. Integration test: End-to-end ingest, index, retrieve, reason flow with mocked Ollama.

**Existing coverage:** `tests/unit/test_embeddings.py`, `tests/unit/test_memory_ingest.py`, `tests/unit/test_rag_reasoner_claude.py`, `tests/integration/test_memory_search.py`, `tests/integration/test_rag_reasoner.py`

---

## 3.2 CI Checklist

The following checks should pass on every pull request before merge:

| Step | Command | Pass Criteria |
|------|---------|---------------|
| 1. Install dependencies | `pip install -e ".[dev]"` | Exit code 0 |
| 2. Import-linter | `lint-imports` | All 4 contracts pass (0 violations) |
| 3. Ruff lint | `ruff check .` | 0 errors |
| 4. Ruff format | `ruff format --check .` | 0 reformatted files |
| 5. Unit tests | `pytest tests/unit/ -x --timeout=60` | All pass, exit code 0 |
| 6. Integration tests | `pytest tests/integration/ -x --timeout=120` | All pass (may require Ollama running) |
| 7. Root tests (temporary) | `pytest tests/ --ignore=tests/unit --ignore=tests/integration --ignore=tests/realtime --ignore=tests/performance -x --timeout=120` | All pass |
| 8. Coverage | `pytest tests/unit/ --cov=core --cov=application --cov=shared --cov-report=term-missing` | Report generated; target 70% line coverage for core/ |
| 9. Type check (future) | `mypy core/ shared/ --ignore-missing-imports` | 0 errors (once P1-04 is implemented) |

---

# 4. Refactor Plan

## 4.1 Current State

The codebase has already undergone a comprehensive Clean Architecture migration (Phases 1-4 completed in prior sessions):

- **Phase 1:** Restructured from flat layout to five architectural layers: `core/` (domain logic), `application/` (orchestration), `infrastructure/` (external services), `shared/` (cross-cutting), `apps/` (entry points).
- **Phase 2:** Migrated 355 import statements across the entire codebase.
- **Phase 3:** Removed 13 legacy root directories and 13 root Python files.
- **Phase 4:** Created `pyproject.toml` with editable install, configured import-linter with 4 contracts, all passing.

The migration is **complete and enforced**. The following refactor plan addresses remaining structural improvements.

## 4.2 Remaining Structural Improvements

### R-01: Organize test directory (Priority: P2)

**Current state:** Tests are split between `tests/` root (approximately 25 files) and organized subdirectories (`tests/unit/`, `tests/integration/`, `tests/realtime/`, `tests/performance/`).

**Target state:** All tests under the appropriate subdirectory. No test files in `tests/` root.

**Steps:**
1. List all test files in `tests/` root.
2. Classify each as unit or integration based on whether it mocks external dependencies.
3. Move files to `tests/unit/` or `tests/integration/`.
4. Update any relative imports.
5. Run `pytest` to verify no tests break.

---

### R-02: Wire remaining core modules to agent (Priority: P0)

**Current state:** Three core modules (audio, action, braille) have full implementations but no agent function tools.

**Target state:** Every core module that provides a user-facing capability has a corresponding `@function_tool()` in `AllyVisionAgent`.

**Steps:**
1. Add `detect_sounds` function tool: import `AudioEventDetector`, capture audio, classify, return spoken result.
2. Add `recognize_actions` function tool: import `ActionRecognizer`, process video clip buffer, return spoken result.
3. Add `read_braille` function tool: import `BrailleOCR`, capture frame, process, return spoken result.
4. Add `detect_faces` function tool: import `FaceDetector`, capture frame, check consent, return spoken result.
5. Add corresponding fields to `UserData` dataclass and initialization logic to `entrypoint()`.
6. Add unit tests for each new function tool.

---

### R-03: Extract system prompt to a separate file (Priority: P2)

**Current state:** The system prompt is a ~200-line string literal defined twice in agent.py (once at module level, once inline in `AllyVisionAgent.__init__`).

**Target state:** A single file `configs/system_prompt.txt` (or similar) loaded at startup. One definition, no duplication.

**Steps:**
1. Create `configs/system_prompt.txt` with the prompt text.
2. Create `configs/micro_nav_prompt.txt` for the micro-navigation prompt.
3. In agent.py, load each file at module level using `Path.read_text()`.
4. Pass the loaded string to `AllyVisionAgent.__init__`.
5. Delete the duplicated inline string.

---

### R-04: Clean up dead infrastructure packages (Priority: P2)

**Current state:** `infrastructure/monitoring/` and `infrastructure/storage/` contain only empty `__init__.py` files. `infrastructure/llm/siliconflow/` exists but is unused.

**Target state:** Every package under `infrastructure/` contains meaningful code or is removed.

**Steps:**
1. Delete `infrastructure/monitoring/__init__.py` if no monitoring code is planned. Otherwise, move `application/pipelines/perception_telemetry.py` here.
2. Delete `infrastructure/storage/__init__.py` if no storage abstraction is planned.
3. Evaluate `infrastructure/llm/siliconflow/`: if it is a planned alternative vision provider, add it to config.yaml as a feature toggle; otherwise delete it.
4. Run `lint-imports` and `pytest` to verify.

---

### R-05: Centralize TTS and voice configuration (Priority: P1)

**Current state:** ElevenLabs voice ID, model, and audio settings are hardcoded in multiple files.

**Target state:** TTS configuration is defined once in `configs/config.yaml` under a `tts:` section and read via `shared/config/`.

**Steps:**
1. Add `tts.voice_id`, `tts.model`, `tts.sample_rate`, `tts.codec` to `configs/config.yaml`.
2. Add environment variable overrides: `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL`.
3. Add `get_tts_config()` to `shared/config/settings.py`.
4. Update agent.py `entrypoint()` and `core/speech/tts_handler.py` to use the centralized config.
5. Update `.env.example` with the new variables.

---

### R-06: Rename `apps/cli/` to reflect actual contents (Priority: P2)

**Current state:** `apps/cli/` contains `session_logger.py` and `visualizer.py`, which are utility modules, not a CLI application.

**Target state:** Either create a real CLI entry point (e.g., `apps/cli/main.py` with argparse) or move utilities to `shared/debug/`.

**Steps:**
1. If a CLI is desired: create `apps/cli/main.py` with commands for starting the API server, running diagnostics, and viewing session logs.
2. If no CLI is planned: move `session_logger.py` to `shared/debug/session_logger.py` and `visualizer.py` to `shared/debug/visualizer.py`. Update imports in agent.py and server.py.
3. Run `lint-imports` and `pytest` to verify.

---

## 4.3 Refactor Sequencing

| Order | Item | Effort | Risk |
|-------|------|--------|------|
| 1 | R-01: Remove `sentence-transformers` from deps (P0-01) | 5 min | Low |
| 2 | R-02: Fix pre-existing test import paths (P0-02) | 30 min | Low |
| 3 | R-03: Wire audio/action/braille/face to agent (P0-03) | 2-3 hours | Medium |
| 4 | R-05: Centralize TTS config (P1-05) | 1 hour | Low |
| 5 | R-03: Extract system prompt to file (P2-08) | 30 min | Low |
| 6 | R-04: Clean dead infra packages (P2-06/07/09) | 30 min | Low |
| 7 | R-01: Organize test directory (P2-01) | 1 hour | Low |
| 8 | R-06: Rename/restructure apps/cli (P2-10) | 30 min | Low |

---

# Appendix: Feature Status Matrix

| Feature | Core Module | Agent Function Tool | REST Endpoint | Tests | Status |
|---------|------------|--------------------|--------------|----|--------|
| Object Detection + Depth | core/vision/spatial.py | `detect_obstacles`, `analyze_spatial_scene` | /health | Yes | Implemented |
| Visual Scene Description | core/vision/visual.py | `analyze_vision` | — | Yes | Implemented |
| Visual Question Answering | core/vqa/ (9 files) | `ask_visual_question` | /vqa/* | Yes | Implemented |
| OCR Text Reading | core/ocr/engine.py | `read_text` | — | Yes | Implemented |
| QR/AR Scanning | core/qr/ (5 files) | `scan_qr_code` | /qr/* | Yes | Implemented |
| Braille OCR | core/braille/ (5 files) | **Missing** | — | Yes | Core done, not wired |
| Face Detection | core/face/ (4 files) | **Missing** | /face/* | Partial | Core done, not wired |
| Sound Localization | core/audio/ (3 files) | **Missing** | /audio/health | Yes | Core done, not wired |
| Action Recognition | core/action/ (1 file) | **Missing** | /action/health | Yes | Core done, not wired |
| Memory / RAG | core/memory/ (14 files) | Inline in `ask_visual_question` | /memory/* | Yes | Implemented |
| Internet Search | infrastructure/llm/internet_search.py | `search_internet` | — | — | Implemented |
| TTS Streaming | infrastructure/speech/elevenlabs/ | Agent session config | — | Limited | Implemented |
| STT | infrastructure/speech/deepgram/ | Agent session config | — | Yes | Implemented |
| Continuous Processing | application/frame_processing/ | Proactive announcer | — | Yes | Implemented |
| Virtual Avatar (Tavus) | infrastructure/tavus/adapter.py | Entrypoint config | — | Broken | Optional, disabled |
| Cloud Sync | core/memory/cloud_sync.py | — | — | No | Stub |
| Voice Intent Router | core/speech/voice_router.py | — | — | Yes | Implemented, used in agent |
| Encryption | shared/encryption.py | — | — | Partial | Implemented |
| Startup Guards | shared/utils/startup_guards.py | — | /health | Yes | Implemented |

---

**End of Product Documentation Package**
