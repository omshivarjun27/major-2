# Voice-Vision Assistant — Detailed Module Reference

## Complete File Inventory with Key Classes & Functions

---

## shared/ — Foundation Layer

### shared/config/settings.py (587 lines)
**Key exports:** `CONFIG` dict, `VisionProvider` enum, helper functions
- `VisionProvider(Enum)` — Currently only `OLLAMA`
- `CONFIG` — Master configuration dict populated from env vars:
  - `vision.provider`, `vision.model_id`, `vision.base_url`, `vision.api_key`
  - `vision.vl_model_id`, `vision.vl_api_key` — Vision-language model
  - `spatial.*` — `enabled`, `use_yolo`, `yolo_model_path`, `enable_segmentation`, `enable_depth`, `midas_model_path`
  - `qr.*` — `enabled`, `cache_enabled`, `cache_dir`, `cache_max_age_hours`
  - `face.*` — `enabled`, `recognition_opt_in`, `embedding_model`, `similarity_threshold`
  - `audio.*` — `enabled`, `sr`, `chunk_length`, `detector`
  - `action.*` — `enabled`, `model`, `confidence_threshold`
  - `resilience.*` — timeouts, circuit_breakers, retry policies per service
- Helper functions: `get_config()`, `spatial_enabled()`, `face_enabled()`, `audio_enabled()`, `action_enabled()`, `qr_enabled()`

### shared/config/environment.py (491 lines)
- `Environment(Enum)` — DEVELOPMENT, STAGING, PRODUCTION, TEST
- `load_config(env=None)` → merges `config.yaml` + `{env}.yaml` + env vars
- `validate_config(config, env)` → `ConfigValidationResult` (errors, warnings)
- `config_diff(config_a, config_b)` → dict of differences
- `log_effective_config(config, redact_secrets=True)` → logs active settings

### shared/config/secret_provider.py (121 lines)
- `SecretProvider(ABC)` → `get_secret(key)` / `has_secret(key)` / `all_secrets()`
- `EnvironmentProvider` — reads from `os.environ`
- `EnvFileProvider` — parses `.env` files (handles comments, quotes)
- `create_secret_provider()` → auto-selects based on Docker detection
- `SECRET_KEYS` — set of known secret key names

### shared/schemas/__init__.py (389 lines)
**Enums:**
- `Priority` — CRITICAL (<1m), NEAR_HAZARD (1-2m), FAR_HAZARD (2-5m), SAFE (>5m)
- `Direction` — LEFT, SLIGHTLY_LEFT, CENTER, SLIGHTLY_RIGHT, RIGHT, FAR_LEFT, FAR_RIGHT, BEHIND
- `SizeCategory` — SMALL, MEDIUM, LARGE, VERY_LARGE
- `SpatialRelation` — LEFT_OF, RIGHT_OF, ABOVE, BELOW, IN_FRONT, BEHIND, NEXT_TO, ON_TOP, INSIDE
- `Verbosity` — BRIEF, NORMAL, DETAILED

**Dataclasses:**
- `BoundingBox(x1, y1, x2, y2)` — `from_xywh()`, `width/height/center/area`, `clamp()`
- `Detection(id, class_name, confidence, bbox)` — `to_dict()`
- `OCRWord(text, confidence, bbox)` / `OCRResult(words, text, confidence, engine)`
- `SegmentationMask(detection_id, mask, boundary_confidence, edge_pixels)`
- `DepthMap(depth_array, min_depth, max_depth, is_metric)` — `depth_at_point()`, `depth_in_bbox()`
- `PerceptionResult(detections, masks, depth_map, timestamp)`
- `ObstacleRecord(detection_id, class_name, distance_m, direction, priority, size, action, confidence, bbox)`
- `NavigationOutput(short_cue, detailed_description, telemetry, has_critical_obstacle)`

**ABCs:**
- `ObjectDetector` — `detect(image) → List[Detection]`, `is_ready() → bool`
- `Segmenter` — `segment(image, detections) → List[SegmentationMask]`
- `DepthEstimator` — `estimate(image) → DepthMap`

### shared/utils/encryption.py (213 lines)
- `EncryptionManager(key_source, legacy_mode=False)`
  - `encrypt(data: bytes) → bytes` / `decrypt(data: bytes) → bytes`
  - `save_encrypted_file(path, data)` / `load_encrypted_file(path) → bytes`
  - `encrypt_numpy(arr) → bytes` / `decrypt_numpy(data) → ndarray`
  - `encrypt_json(obj) → bytes` / `decrypt_json(data) → dict`
  - PBKDF2 key derivation with 480,000 iterations + random salt

### shared/utils/timing.py (191 lines)
- `TimingResult(name, start_time, end_time)` — `duration_ms` property
- `PipelineProfiler(enabled)`:
  - `start_request()` / `end_request()` — bracket request timing
  - `measure(name)` / `measure_async(name)` — context managers
  - `get_stats(name) → {count, avg_ms, min_ms, max_ms}`
  - `log_summary()` — formatted timing table
- `@measure(name)` decorator (auto-detects sync/async)
- `time_start()` / `time_end(start, label)` — inline helpers

### shared/utils/startup_guards.py (285 lines)
- `enforce_venv()` — exits with FATAL if not in venv
- `detect_device()` → "cuda" or "cpu"
- `scan_banned_modules(banned_list)` → list of detected modules
- `load_yaml_config(path)` → dict (with `PERCEPTION_*` env overrides)
- `run_startup_checks(config_path, skip_venv_check)` → info dict

### shared/utils/runtime_diagnostics.py (831 lines)
**TTS Diagnostics:**
- `TTSPreflightResult` — sample rate, codec, chunk config, readiness
- `TTSEventLog` — stream events with waveform stats
- `TTSDiagnostics` — preflight(), on_stream_start/end(), on_chunk_sent(), retry logic
- Audio utilities: `analyze_audio_chunk()`, `apply_soft_fade()`, `normalize_audio()`

**VQA Diagnostics:**
- `VQAPreflightResult` — frame/model/shape/warmup status with remediation commands
- `VQASkipCode(Enum)` — SKIP_NO_FRAME, SKIP_MODEL_LOAD, SKIP_SHAPE_MISMATCH, SKIP_TIMEOUT, SKIP_RESOURCE, SKIP_DEP_MISSING
- `VQADiagnostics.preflight()` — 5-step check sequence

**System:**
- `SystemStatus` — consolidated TTS+VQA status with JSON output
- `RuntimeDiagnostics` — orchestrator running all preflights

### shared/utils/vram_profiler.py (394 lines)
- `VRAMSnapshot(timestamp, allocated_mb, reserved_mb, peak_mb, label)`
- `VRAMProfile(name, start/end_allocated_mb, peak_allocated_mb, duration_ms)`
- `VRAMProfiler(enabled)`:
  - `track(name)` — context manager (resets peak, empties cache)
  - `register_component(name, idle_mb, active_mb, peak_mb)`
  - `get_top_consumers(n)`, `get_summary()`, `print_summary()`
- Helper functions: `is_cuda_available()`, `get_cuda_device_info()`, `get_current_vram_usage()`, `empty_cuda_cache()`

---

## core/ — Business Logic Layer (79 files)

### core/vision/spatial.py (1358 lines) — SPATIAL PERCEPTION
**Constants:** `MAX_DETECTIONS=2`, `MAX_MASK_SIZE=(160,120)`, `DEPTH_DOWNSCALE=4`

**Detectors:**
- `MockObjectDetector` — returns 1 detection at image center, `__slots__` optimized
- `YOLODetector(model_path, conf_threshold=0.5)`:
  - ONNX inference: letterbox resize to 640×640, NMS (IoU>0.45, top-25)
  - Ultralytics fallback via `YOLO.predict()`
  - 80 COCO class names

**Segmenter:**
- `EdgeAwareSegmenter`:
  - Downscales to 160×120, computes Sobel gradients
  - Otsu thresholding within bounding boxes
  - Boundary confidence = 0.5 + variance_score + edge_score (capped 0.95)
  - Cached masks for speed

**Depth Estimators:**
- `SimpleDepthEstimator(default_depth_range)` — vectorized linear gradient, cached
- `MiDaSDepthEstimator(model_path, model_type)`:
  - ONNX: resize to 256×256, ImageNet normalization, inverse-depth output
  - PyTorch hub fallback: `intel-isl/MiDaS`

**Fusion:**
- `SpatialFuser(image_width, image_height)`:
  - `CRITICAL_THRESHOLD=1.0m`, `NEAR_THRESHOLD=2.0m`, `FAR_THRESHOLD=5.0m`
  - Direction from center_x → 8 directions with angle calculation
  - Size categorization based on area percentage
  - Action recommendations per priority level

**Processor:**
- `SpatialProcessor` — full pipeline orchestration, `process_frame()` → `NavigationOutput`

### core/vision/visual.py (430 lines)
- `convert_video_frame_to_pil(frame)` — LiveKit VideoFrame → PIL (RGBA→RGB)
- `resize_image_for_processing(img, max_size)` — BILINEAR resize
- `VisualProcessor(enable_spatial)`:
  - `__slots__` with 13 attributes for memory efficiency
  - Auto-detects YOLO/MiDaS model files on disk
  - `capture_frame(room)` — persistent VideoStream, frame identity tagging
  - `process_spatial(image)` — rate-limited (300ms), returns cached if too soon
  - `get_quick_warning(image)` — low-latency hazard check
  - `get_spatial_context()` — text summary for LLM prompts

### core/vision/model_loader.py (439 lines)
- `QuantizationMode(Enum)` — NONE, INT8, FP16, DYNAMIC
- `ModelConfig(name, original_path, quantized_path, quantization_mode, accuracy_threshold, latency_budget_ms)`
- `ModelLoader.load_onnx_model(name, custom_path, force_quantized)` → (session, stats)
- `quantize_onnx_model(input_path, output_path, mode)` → `QuantizationResult`
- `BenchmarkResult` — original vs quantized comparison

### core/vision/model_download.py (110 lines)
- `ensure_yolo_model(dest)` — downloads YOLOv8n from GitHub, SHA-256 verified
- `ensure_midas_model(dest)` — downloads MiDaS v21 small from HuggingFace, SHA-256 verified
- Atomic download with temp file + checksum verification

### core/memory/ (20 files)
- `retriever.py` — `MemoryRetriever(indexer, text_embedder, config)`:
  - `search(request: MemorySearchRequest)` → `MemorySearchResponse`
  - `search_by_embedding(embedding, k, time_window_days, session_id)` → `List[SearchResult]`
  - `get_memory(memory_id)`, `get_session_memories(session_id)`, `get_recent_memories(hours)`
  - Score normalization, deduplication by summary
- Supporting modules: indexer, embeddings, config, ingest, rag_reasoner, privacy_controls, api_endpoints, cloud_sync, faiss_sync, sqlite_sync, sqlite_manager, maintenance, offline_queue, event_detection, llm_client, conflict_resolver, index_factory

### core/face/ (5 files)
- `face_detector.py`, `face_embeddings.py`, `face_tracker.py`, `face_social_cues.py`, `consent_audit.py`

### core/audio/ (4 files)
- `audio_event_detector.py`, `audio_fusion.py`, `enhanced_detector.py`, `ssl.py`

### core/braille/ (5 files)
- Pipeline: `braille_capture.py` → `braille_segmenter.py` → `braille_classifier.py` → `braille_ocr.py`
- `embossing_guidance.py` — embossing assistance

### core/ocr/engine.py
- 3-tier fallback: EasyOCR → Tesseract → MSER heuristic

### core/qr/ (5 files)
- `qr_scanner.py` → `qr_decoder.py` → `ar_tag_handler.py`
- `cache_manager.py` — offline caching with configurable max age
- `qr_api.py` — FastAPI router

### core/action/ (3 files)
- `action_recognizer.py`, `action_context.py`, `clip_recognizer.py`

---

## apps/ — Entry Points (15 files)

### apps/realtime/agent.py (289 lines)
**`AllyVisionAgent(Agent)`** — LiveKit agent coordinator:
- Inherits from `livekit.agents.Agent`
- `on_enter()` — agent startup
- `on_message(text)` — flushes cached perception for fresh context
- Tool functions (all `@function_tool`):
  - `search_internet(query)` — web search
  - `analyze_vision(query)` — Ollama vision analysis
  - `detect_obstacles(detail_level)` — YOLO-based detection
  - `analyze_spatial_scene(query)` — spatial + VQA
  - `ask_visual_question(question)` — VQA reasoning
  - `get_navigation_cue()` — quick nav from fresh frame
  - `scan_qr_code(query)` — QR/AR scanning
  - `read_text(query)` — OCR
- `entrypoint(ctx: JobContext)` — session lifecycle setup

### apps/realtime/tool_router.py (447 lines)
- `QueryType(Enum)` — VISUAL, SPATIAL, SEARCH, QR_AR, OCR, VQA, NAVIGATION, GENERAL
- Keyword pattern matching for classification (regex compiled once)
- `ToolRegistry` singleton — maps tool names to `ToolEntry` (handler + SLA)
- `dispatch(tool_name, userdata, **kwargs)` → `DispatchResult`
- `_failsafe_for_type(query_type)` — safe fallback messages

### apps/realtime/vision_controller.py (500 lines)
- `capture_fresh_frame(userdata)` — via VisualProcessor
- `check_frame_freshness(userdata, capture_ts)` — stale frame gate
- `heartbeat(userdata, component)` — watchdog heartbeat
- `run_ollama_analysis(userdata, analysis_llm, visual_ctx)` — streaming LLM
- `analyze_vision(userdata, query, llm_*params)` — full vision pipeline
- `detect_obstacles(userdata, detail_level)` — spatial detection
- `analyze_spatial_scene(userdata, query)` — spatial + VQA fallback
- `run_vqa_spatial(userdata, image, query)` — VQA engine for spatial
- `ask_visual_question(userdata, question)` — VQA reasoning
- `analyze_with_ollama(userdata, image, question)` — Ollama fallback
- `get_navigation_cue(userdata)` — quick nav
- `read_text(userdata, query)` — OCR pipeline

### apps/realtime/voice_controller.py (282 lines)
- `search_internet(userdata, query)` — web search via infrastructure
- `scan_qr_code(userdata, query)` — camera QR detection with spoken context
- `process_stream(chat_ctx, tools, userdata, *, llm_model, llm_base_url, llm_api_key)` — LLM stream routing

### apps/api/server.py (746 lines)
- FastAPI app with Swagger docs at `/docs`
- Route groups: `/health`, `/metrics`, `/face/*`, `/audio/*`, `/action/*`, `/memory/*`, `/qr/*`, `/vqa/*`
- Debug endpoints gated by `DEBUG_ENDPOINTS_ENABLED` + token auth
- `SessionLogger(max_events=1000)` singleton

---

## infrastructure/ — External Adapters (38 files)

### infrastructure/resilience/circuit_breaker.py (492 lines)
- `CircuitBreakerState(Enum)` — CLOSED, OPEN, HALF_OPEN
- `CircuitBreakerConfig(failure_threshold=3, reset_timeout_s=30, half_open_max_calls=1, success_threshold=1, excluded_exceptions)`
- `CircuitBreaker(service_name, config, on_state_change, metrics)`:
  - `call(func, *args, **kwargs)` — execute through breaker
  - `reset()` / `trip()` — manual control
  - `snapshot()` — non-blocking status for health endpoints
  - Async-safe via `asyncio.Lock`

### infrastructure/resilience/ (7 files total)
- `retry_policy.py` — exponential backoff retries
- `timeout_config.py` — per-service timeout settings
- `error_classifier.py` — retry decision logic
- `degradation_coordinator.py` — graceful degradation
- `health_registry.py` — component health tracking
- `livekit_monitor.py` — LiveKit connection monitoring

### infrastructure/speech/ (7 files)
- `deepgram/resilience.py` — Deepgram STT with circuit breaker
- `elevenlabs/tts_manager.py` — ElevenLabs TTS management
- `local/edge_tts_fallback.py` — Microsoft Edge TTS (free fallback)
- `local/whisper_stt.py` — Local Whisper STT (offline)
- `stt_failover.py` — STT failover: Deepgram → Whisper
- `tts_failover.py` — TTS failover: ElevenLabs → Edge TTS

### infrastructure/llm/ (5 files)
- `ollama/handler.py` — Ollama for vision + chat
- `internet_search.py` — Web search integration
- `config.py` — LLM configuration
- `siliconflow/` — Alternative provider support

### infrastructure/monitoring/ (3 files)
- `collector.py` — MetricsCollector
- `instrumentation.py` — Code instrumentation decorators
- `prometheus_metrics.py` — Prometheus text format export

### infrastructure/backup/ (3 files)
- `faiss_backup.py` / `sqlite_backup.py` — Data backup
- `scheduler.py` — Scheduled backups

### infrastructure/storage/adapter.py — Storage abstraction layer
### infrastructure/tavus/adapter.py — Tavus virtual avatar integration

---

## application/ — Orchestration Layer (23 files)

### application/frame_processing/ (5 files)
- `frame_orchestrator.py` — Coordinates frame → perception pipeline
- `freshness.py` — `is_frame_fresh()` validation
- `confidence_cascade.py` — Multi-model confidence scoring
- `live_frame_manager.py` — Real-time frame management
- `spatial_binding.py` — Binds spatial results to frames

### application/pipelines/ (11 files)
- `streaming_tts.py` — Streaming TTS pipeline
- `perception_pool.py` — Perception worker pool
- `perception_telemetry.py` — Perception metrics
- `frame_sampler.py` — Intelligent frame sampling
- `debouncer.py` — Response debouncing
- `cancellation.py` — Task cancellation
- `watchdog.py` — Pipeline health watchdog
- `worker_pool.py` — Generic async worker pool
- `pipeline_monitor.py` — Performance monitoring
- `audio_manager.py` — Audio pipeline management
- `integration.py` — Pipeline integration

### application/event_bus/bus.py — In-process event bus
### application/session_management/manager.py — Session lifecycle

---

## Root Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Build system, dependencies, tool configs (pytest, ruff, import-linter) |
| `requirements.txt` | Core Python dependencies |
| `Dockerfile` | Multi-stage build (python:3.11-slim, tesseract, ffmpeg) |
| `.env.example` | Environment variable template |
| `configs/config.yaml` | Base configuration defaults |
| `configs/development.yaml` | Dev overrides (relaxed, mocked) |
| `configs/production.yaml` | Production overrides (strict security) |
| `configs/staging.yaml` | Staging overrides |
| `.github/workflows/` | CI/CD pipelines |
