# Voice-Vision Assistant for Blind — Codebase Architecture

## Project Overview

**Ally Vision Assistant** is a real-time AI-powered assistant for blind and visually impaired users that bridges visual gaps through voice interaction, scene understanding, obstacle detection, and micro-navigation. It uses LiveKit for real-time communication, Ollama vision models for scene analysis, YOLO/MiDaS for spatial perception, and a privacy-first memory engine.

---

## 5-Layer Architecture

The codebase enforces strict import boundaries via `import-linter`:

```
apps/ → application/ → core/ → infrastructure/ → shared/
```

| Layer | Purpose | Key Modules |
|-------|---------|-------------|
| **shared/** | Canonical types, config, encryption, logging, utils | `schemas/`, `config/`, `utils/`, `logging/` |
| **infrastructure/** | External service adapters, resilience, monitoring | `llm/`, `speech/`, `resilience/`, `monitoring/`, `storage/`, `tavus/`, `backup/` |
| **core/** | Business logic engines | `vision/`, `memory/`, `face/`, `audio/`, `braille/`, `ocr/`, `qr/`, `action/`, `speech/`, `reasoning/`, `vqa/` |
| **application/** | Pipeline orchestration, frame processing | `pipelines/`, `frame_processing/`, `event_bus/`, `session_management/` |
| **apps/** | Entry points — realtime agent, API server, CLI | `realtime/`, `api/`, `cli/` |

---

## Module Inventory (155+ Python files)

### shared/ (Foundation Layer)

#### `shared/config/`
- **`settings.py`** (587 lines) — Central `CONFIG` dict populated from env vars. Covers vision provider, spatial perception, QR scanning, face recognition, audio/action engines, resilience (timeouts, circuit breakers, retry policies), and feature toggles.
- **`environment.py`** (491 lines) — `Environment` enum (DEVELOPMENT/STAGING/PRODUCTION/TEST). Loads YAML configs from `configs/`, merges with env-var overrides, validates required keys, production rules. Provides `config_diff()` and `log_effective_config()`.
- **`secret_provider.py`** (121 lines) — `SecretProvider` ABC with `EnvironmentProvider` (os.environ) and `EnvFileProvider` (.env file). Auto-detects Docker vs local. Singleton `EncryptionManager`.

#### `shared/schemas/__init__.py` (389 lines) — Canonical Types
Core data structures used project-wide:
- **Enums**: `Priority` (CRITICAL/NEAR_HAZARD/FAR_HAZARD/SAFE), `Direction` (8 directions), `SizeCategory`, `SpatialRelation`, `Verbosity`
- **Dataclasses**: `BoundingBox` (with `from_xywh`, `center`, `area`, `clamp`), `Detection` (id, class_name, confidence, bbox), `OCRWord`, `OCRResult`, `SegmentationMask`, `DepthMap` (with `depth_at_point`, `depth_in_bbox`), `PerceptionResult`, `ObstacleRecord`, `NavigationOutput`
- **ABCs**: `ObjectDetector`, `Segmenter`, `DepthEstimator` — abstract pipeline stage interfaces

#### `shared/utils/`
- **`encryption.py`** (213 lines) — `EncryptionManager`: Fernet AES-128-CBC with PBKDF2 key derivation, legacy SHA-256 fallback. Methods for bytes, files, NumPy arrays, JSON.
- **`timing.py`** (191 lines) — `PipelineProfiler` with sync/async `measure()` context managers, `@measure` decorator, emoji-coded latency feedback (🟢<100ms, 🟡<500ms, 🟠<1s, 🔴>1s).
- **`startup_guards.py`** (285 lines) — Venv enforcement, CUDA/CPU detection, banned-module scanning, YAML config loading with `PERCEPTION_*` env-var overrides.
- **`runtime_diagnostics.py`** (831 lines) — `TTSDiagnostics` (preflight: sample rate/codec validation, chunk jitter monitoring, waveform analysis), `VQADiagnostics` (camera/model/shape/warmup/dependency checks with structured skip codes), `RuntimeDiagnostics` orchestrator emitting JSON `SYSTEM_STATUS`.
- **`vram_profiler.py`** (394 lines) — GPU VRAM profiling via PyTorch CUDA APIs: `VRAMProfiler.track()` context manager, top-N consumer analysis, component registration.
- **`helpers.py`** (22 lines) — `get_current_date_time()` utility.

#### `shared/logging/logging_config.py` (264 lines)
- `PIIScrubFilter` — regex-based redaction of emails, phone numbers, API keys, SSNs
- `StructuredJSONFormatter` / `HumanReadableFormatter`
- `configure_logging()` — configurable level, format, PII scrubbing

---

### core/ (Business Logic — 79 files)

#### `core/vision/` — Spatial Perception Pipeline

**`spatial.py`** (1358 lines) — The heart of spatial perception:
- **Pipeline**: `FRAME → DETECT → SEGMENT → DEPTH → FUSE → NAVIGATION`
- **Detectors**: `MockObjectDetector` (fast testing), `YOLODetector` (ONNX YOLOv8 with letterbox+NMS, or ultralytics fallback)
- **Segmentation**: `EdgeAwareSegmenter` — Sobel gradient + Otsu thresholding at 160×120, boundary confidence scoring
- **Depth**: `SimpleDepthEstimator` (gradient fill), `MiDaSDepthEstimator` (ONNX MiDaS v2.1 small 256×256, ImageNet normalization)
- **Fusion**: `SpatialFuser` — fuses detection+segmentation+depth → `ObstacleRecord` with distance, direction, priority, size category
- **Processor**: `SpatialProcessor` — orchestrates full pipeline, generates `NavigationOutput` with short TTS cue

**`visual.py`** (430 lines) — `VisualProcessor`:
- Persistent `rtc.VideoStream` for LiveKit frame capture
- Frame identity tracking (sequence ID + epoch_ms)
- Freshness validation (configurable `max_age_ms`)
- Rate-limited spatial processing (300ms cooldown)
- Combined `capture_and_analyze_spatial()` method

**`model_loader.py`** (439 lines) — INT8/FP16 quantization support:
- `ModelConfig` with original/quantized paths, accuracy threshold, latency budget
- `ModelLoader` with ONNX Runtime session management
- `quantize_onnx_model()` + `benchmark_quantization()` utilities

**`model_download.py`** (110 lines) — SHA-256 verified model downloads:
- `ensure_yolo_model()` → `models/yolov8n.onnx` from ultralytics GitHub
- `ensure_midas_model()` → `models/midas_v21_small_256.onnx` from HuggingFace

#### `core/memory/` — Privacy-First Memory Engine (20+ files)
- **`retriever.py`** (337 lines) — `MemoryRetriever`: FAISS vector search with text embedding, time/session filtering, deduplication, score normalization
- **`indexer.py`** — `FAISSIndexer`: FAISS index management with `SearchResult`
- **`embeddings.py`** — `TextEmbedder` with `create_embedders()` factory
- **`config.py`** — `MemoryConfig` with `get_memory_config()`
- **`ingest.py`** — Memory ingestion pipeline
- **`rag_reasoner.py`** — RAG pipeline for memory-augmented reasoning
- **`privacy_controls.py`** — Consent management, retention policies
- **`api_endpoints.py`** / **`api_schema.py`** — FastAPI memory endpoints
- **`cloud_sync.py`** / **`faiss_sync.py`** / **`sqlite_sync.py`** — Sync mechanisms
- **`sqlite_manager.py`** — SQLite metadata storage
- **`maintenance.py`** — Index maintenance and cleanup
- **`offline_queue.py`** — Offline operation support
- **`event_detection.py`** — Significant event identification
- **`llm_client.py`** — LLM client for memory processing

#### `core/face/` — Face Recognition (consent-gated)
- **`face_detector.py`** — Face detection engine
- **`face_embeddings.py`** — Face embedding generation and storage
- **`face_tracker.py`** — Multi-face tracking across frames
- **`face_social_cues.py`** — Social cue analysis (expressions, gaze)
- **`consent_audit.py`** — Consent audit trail

#### `core/audio/` — Audio Processing
- **`audio_event_detector.py`** — Audio event detection
- **`audio_fusion.py`** — Multi-modal audio fusion
- **`enhanced_detector.py`** — Enhanced audio detection
- **`ssl.py`** — Sound source localization

#### `core/braille/` — Braille Engine
- **`braille_capture.py`** — Camera frame capture for braille
- **`braille_segmenter.py`** — Dot pattern segmentation
- **`braille_classifier.py`** — Braille character classification
- **`braille_ocr.py`** — End-to-end braille text recognition
- **`embossing_guidance.py`** — Braille embossing assistance

#### `core/ocr/engine.py` — 3-Tier OCR Fallback
- EasyOCR → Tesseract → MSER heuristic

#### `core/qr/` — QR/AR Scanning
- **`qr_scanner.py`** — QR code scanner
- **`qr_decoder.py`** — Multi-format QR decoder
- **`ar_tag_handler.py`** — ArUco/AprilTag AR marker detection
- **`cache_manager.py`** — Offline QR data caching
- **`qr_api.py`** — QR scanning API endpoints

#### `core/action/` — Action Recognition
- **`action_recognizer.py`** — Activity recognition
- **`action_context.py`** — Contextual action understanding
- **`clip_recognizer.py`** — CLIP-based recognition

---

### application/ (Orchestration Layer — 23 files)

#### `application/frame_processing/`
- **`frame_orchestrator.py`** — Coordinates frame processing pipeline
- **`freshness.py`** — Frame freshness validation (`is_frame_fresh`)
- **`confidence_cascade.py`** — Multi-model confidence cascading
- **`live_frame_manager.py`** — Real-time frame management
- **`spatial_binding.py`** — Binds spatial results to frames

#### `application/pipelines/`
- **`streaming_tts.py`** — Streaming TTS pipeline
- **`perception_pool.py`** / **`perception_telemetry.py`** — Perception worker pool + telemetry
- **`frame_sampler.py`** — Intelligent frame sampling
- **`debouncer.py`** — Response debouncing
- **`cancellation.py`** — Task cancellation
- **`watchdog.py`** — Pipeline health watchdog
- **`worker_pool.py`** — Generic async worker pool
- **`pipeline_monitor.py`** — Pipeline performance monitoring
- **`audio_manager.py`** — Audio pipeline management
- **`integration.py`** — Pipeline integration utilities

#### `application/event_bus/bus.py` — In-process event bus
#### `application/session_management/manager.py` — Session lifecycle management

---

### infrastructure/ (External Service Adapters — 38 files)

#### `infrastructure/resilience/`
- **`circuit_breaker.py`** (492 lines) — Three-state circuit breaker (CLOSED→OPEN→HALF_OPEN) with configurable failure thresholds, reset timeouts, async-safe lock, event callbacks, metrics integration
- **`retry_policy.py`** — Configurable retry with exponential backoff
- **`timeout_config.py`** — Service-specific timeout configuration
- **`error_classifier.py`** — Error classification for retry decisions
- **`degradation_coordinator.py`** — Graceful degradation orchestration
- **`health_registry.py`** — Component health tracking
- **`livekit_monitor.py`** — LiveKit connection monitoring

#### `infrastructure/speech/`
- **`deepgram/resilience.py`** — Deepgram STT with resilience
- **`elevenlabs/tts_manager.py`** — ElevenLabs TTS management
- **`local/edge_tts_fallback.py`** — Edge TTS local fallback
- **`local/whisper_stt.py`** — Whisper STT local fallback
- **`stt_failover.py`** / **`tts_failover.py`** — STT/TTS failover chains

#### `infrastructure/llm/`
- **`ollama/handler.py`** — Ollama LLM handler
- **`internet_search.py`** — Web search integration
- **`config.py`** — LLM configuration
- **`siliconflow/`** — SiliconFlow provider support

#### `infrastructure/monitoring/`
- **`collector.py`** — Metrics collection
- **`instrumentation.py`** — Code instrumentation
- **`prometheus_metrics.py`** — Prometheus metrics export

#### `infrastructure/backup/`
- **`faiss_backup.py`** / **`sqlite_backup.py`** — Data backup
- **`scheduler.py`** — Backup scheduling

#### `infrastructure/storage/adapter.py` — Storage abstraction
#### `infrastructure/tavus/adapter.py` — Tavus virtual avatar integration

---

### apps/ (Entry Points — 15 files)

#### `apps/realtime/` — LiveKit Voice Agent
- **`agent.py`** (289 lines) — `AllyVisionAgent(Agent)`: LiveKit agent with `@function_tool` methods:
  - `search_internet()` — Web search
  - `analyze_vision()` — Scene analysis via Ollama
  - `detect_obstacles()` — Spatial obstacle detection (<200ms target)
  - `analyze_spatial_scene()` — Spatial+VQA analysis
  - `ask_visual_question()` — VQA reasoning (<500ms target)
  - `get_navigation_cue()` — Quick navigation
  - `scan_qr_code()` — QR/AR scanning
  - `read_text()` — OCR text reading
- **`entrypoint.py`** (79 lines) — App entry: loads .env, configures logging, suppresses Windows IPC errors, starts `cli.run_app()`
- **`vision_controller.py`** (500 lines) — Frame capture, freshness gates, Ollama streaming, obstacle detection, VQA spatial, OCR
- **`voice_controller.py`** (282 lines) — Internet search, QR scanning with contextual spoken messages, LLM stream processing
- **`tool_router.py`** (447 lines) — `QueryType` classification (VISUAL/SPATIAL/SEARCH/QR_AR/OCR/VQA/NAVIGATION/GENERAL), `ToolRegistry` singleton, `dispatch()` with failsafe fallbacks
- **`session_manager.py`** — Session lifecycle (T-038 extraction)
- **`user_data.py`** — `UserData` dataclass for session state
- **`prompts.py`** — `VISION_SYSTEM_PROMPT` and other agent prompts

#### `apps/api/server.py` (746 lines) — FastAPI REST Server
- Health endpoint (`/health`) with component status
- Face endpoints (`/face/*`) — consent-gated detection, forget-all
- Audio endpoints (`/audio/*`)
- Action endpoints (`/action/*`)
- QR endpoints (via `qr_api` router)
- Memory endpoints (`/memory/*`)
- VQA endpoints
- Prometheus metrics (`/metrics`)
- Debug endpoints (auth-gated): session logs, metrics, TTS diagnostics
- Session logger singleton

#### `apps/cli/`
- **`session_logger.py`** — Session event logging
- **`visualizer.py`** — CLI visualization utilities

---

## Configuration System

### Files
- `configs/config.yaml` — Base defaults (thresholds, latency, TTS, privacy)
- `configs/development.yaml` — Relaxed thresholds, mocked services, hot-reload
- `configs/production.yaml` — Strict security, HTTPS, rate limiting, circuit breakers
- `configs/staging.yaml` — Intermediate settings

### Key Environment Variables
| Variable | Purpose |
|----------|---------|
| `ENVIRONMENT` | Config profile (development/staging/production) |
| `LIVEKIT_URL/API_KEY/API_SECRET` | LiveKit connection |
| `DEEPGRAM_API_KEY` | Speech-to-text |
| `OLLAMA_API_KEY/VL_API_KEY/VL_MODEL_ID` | Ollama vision models |
| `ELEVEN_API_KEY` | ElevenLabs text-to-speech |
| `SPATIAL_PERCEPTION_ENABLED` | Enable spatial pipeline |
| `SPATIAL_USE_YOLO/SPATIAL_USE_MIDAS` | Enable real detectors |
| `ENABLE_QR_SCANNING/QR_CACHE_ENABLED` | QR scanning |
| `MEMORY_ENCRYPTION_KEY/FACE_ENCRYPTION_KEY` | Data encryption |
| `TAVUS_API_KEY/REPLICA_ID/PERSONA_ID` | Virtual avatar |

---

## Key Data Flow

### Voice Interaction Pipeline
```
User Speech → LiveKit → Deepgram STT → AllyVisionAgent
  → Tool Router (classify query type)
    → Vision Controller (capture frame, run Ollama/spatial/VQA)
    → Voice Controller (search, QR scan)
  → LLM Response → ElevenLabs TTS → LiveKit → User Audio
```

### Spatial Perception Pipeline
```
Camera Frame → YOLO Object Detection (ONNX Runtime)
  → Edge-Aware Segmentation (Sobel + Otsu)
  → MiDaS Depth Estimation (ONNX Runtime)
  → Spatial Fusion (distance, direction, priority)
  → Navigation Output (short TTS cue + detailed description)
```

### Memory Pipeline
```
User Interaction → Event Detection → Text Embedding (Ollama)
  → FAISS Indexing → SQLite Metadata
  → RAG Retrieval (on query) → LLM Augmented Response
```

---

## Build & Deploy

### Development
```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -e ".[dev,audio,ocr,avatar,gpu]"
cp .env.example .env  # Configure secrets
python apps/realtime/entrypoint.py dev
```

### Docker
```dockerfile
FROM python:3.11-slim
# Installs: tesseract-ocr, libzbar0, ffmpeg
# Non-root user, health check on port 8000
EXPOSE 8000 7880
CMD ["python", "apps/realtime/entrypoint.py", "start"]
```

### CI/CD (.github/workflows/)
- Linting (ruff), type checking (pyright), testing (pytest)
- Import boundary enforcement (import-linter)
- Docker build and push

---

## Performance Targets
| Operation | Target Latency |
|-----------|---------------|
| Frame capture | <100ms |
| Obstacle detection | <200ms |
| Scene analysis (Ollama) | <500ms |
| VQA reasoning | <500ms |
| Navigation cue | <200ms |
| TTS first chunk | <300ms |
| End-to-end voice response | <1000ms |
