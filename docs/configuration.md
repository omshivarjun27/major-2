# Environment Variable Reference

> Comprehensive reference for all configuration variables used by the Voice & Vision Assistant.
> Total: 90 variables across 20 functional groups.

## Security Classifications

| Level | Description | Handling |
|-------|-------------|----------|
| SECRET | API keys, passwords, encryption keys | Via SecretProvider. Never log. Never commit. |
| INTERNAL | Non-sensitive operational config | Safe in env files. Not for end-user docs. |
| PUBLIC | Safe defaults, documented | Can appear in `.env.example`. |

---

## API Keys and Secrets (SECRET)

These credentials are routed through `SecretProvider` and must never appear in logs or version control.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LIVEKIT_API_KEY` | str | `""` | LiveKit WebRTC API key |
| `LIVEKIT_API_SECRET` | str | `""` | LiveKit WebRTC API secret |
| `DEEPGRAM_API_KEY` | str | `""` | Deepgram speech-to-text API key |
| `OLLAMA_API_KEY` | str | `""` | Ollama LLM API key |
| `ELEVEN_API_KEY` | str | `""` | ElevenLabs text-to-speech API key |
| `OLLAMA_VL_API_KEY` | str | `""` | Ollama vision-language model API key |
| `TAVUS_API_KEY` | str | `""` | Tavus virtual avatar API key |
| `MEMORY_ENCRYPTION_KEY` | str | `""` | Encryption key for FAISS index and face embeddings |
| `FACE_ENCRYPTION_KEY` | str | `""` | Encryption key for face data (defaults to MEMORY_ENCRYPTION_KEY) |

---

## Vision Provider (PUBLIC)

Controls which vision backend is active and how frames are analyzed.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VISION_PROVIDER` | str | `"ollama"` | Vision model backend. Currently only `ollama` is supported. |
| `OLLAMA_VL_MODEL_ID` | str | `"qwen3-vl:235b-instruct-cloud"` | Ollama vision-language model identifier |

---

## Tavus Avatar (PUBLIC)

Virtual avatar for video call presence. All optional.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_AVATAR` | bool | `false` | Enable Tavus virtual avatar integration |
| `TAVUS_REPLICA_ID` | str | `""` | Tavus replica (avatar appearance) identifier |
| `TAVUS_PERSONA_ID` | str | `""` | Tavus persona (behavior profile) identifier |
| `TAVUS_AVATAR_NAME` | str | `"ally-vision-avatar"` | Display name for the avatar instance |
| `TAVUS_ENABLED` | bool | `false` | Master toggle for Tavus integration |

---

## Spatial Perception (PUBLIC)

Object detection, depth estimation, and distance thresholds for obstacle awareness.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SPATIAL_PERCEPTION_ENABLED` | bool | `true` | Enable the spatial perception pipeline |
| `SPATIAL_USE_YOLO` | str | `"auto"` | YOLO detector mode: `auto`, `true`, or `false` |
| `YOLO_MODEL_PATH` | str | `"models/yolov8n.onnx"` | Path to YOLO ONNX model file |
| `YOLO_CONF_THRESHOLD` | float | `0.5` | Minimum detection confidence for YOLO |
| `SPATIAL_USE_MIDAS` | str | `"auto"` | MiDaS depth mode: `auto`, `true`, or `false` |
| `MIDAS_MODEL_PATH` | str | `"models/midas_v21_small_256.onnx"` | Path to MiDaS ONNX model file |
| `MIDAS_MODEL_TYPE` | str | `"MiDaS_small"` | MiDaS model variant |
| `ENABLE_SEGMENTATION` | bool | `false` | Enable edge-aware segmentation (disabled for performance) |
| `ENABLE_DEPTH` | bool | `false` | Enable per-pixel depth estimation (disabled for performance) |
| `CRITICAL_DISTANCE_M` | float | `1.0` | Distance threshold (meters) for CRITICAL priority |
| `NEAR_DISTANCE_M` | float | `2.0` | Distance threshold (meters) for NEAR_HAZARD priority |
| `FAR_DISTANCE_M` | float | `5.0` | Distance threshold (meters) for FAR_HAZARD priority |
| `LOW_LATENCY_WARNINGS` | bool | `true` | Skip LLM and use direct TTS for critical obstacles |

---

## Speech and VQA Bridge (PUBLIC)

Controls the STT-to-VQA-to-TTS pipeline and priority scene module.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_SPEECH_VQA` | bool | `true` | Enable speech-driven visual question answering |
| `ENABLE_PRIORITY_SCENE` | bool | `true` | Enable top-N hazard summary per frame |
| `PRIORITY_TOP_N` | int | `3` | Number of top hazards to announce per frame |
| `ENABLE_DEBUG_VISUALIZER` | bool | `true` | Enable CLI debug visualizer overlay |

---

## QR / AR Tag Scanning (PUBLIC)

QR code and AR marker detection with offline cache.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_QR_SCANNING` | bool | `true` | Master toggle for QR/AR scanning |
| `QR_CACHE_ENABLED` | bool | `true` | Cache previously scanned QR results locally |
| `QR_AUTO_DETECT` | bool | `true` | Automatically scan for QR codes in every frame |
| `QR_CACHE_TTL_SECONDS` | int | `86400` | Cache time-to-live in seconds (default: 24 hours) |
| `QR_CACHE_DIR` | str | `""` | Cache directory path. Empty string uses the default `qr_cache/` directory. |

---

## Latency Targets (PUBLIC)

SLA thresholds for the hot path. Values in milliseconds.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TARGET_STT_LATENCY_MS` | float | `100` | Target speech-to-text latency |
| `TARGET_VQA_LATENCY_MS` | float | `300` | Target visual Q&A latency |
| `TARGET_TTS_LATENCY_MS` | float | `100` | Target text-to-speech latency |
| `TARGET_TOTAL_LATENCY_MS` | float | `500` | Target end-to-end latency |

---

## Live Frame and Capture (PUBLIC)

Frame freshness, buffer sizing, and pipeline timeouts.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LIVE_FRAME_MAX_AGE_MS` | float | `500` | Maximum age of a frame before it's considered stale |
| `CAPTURE_CADENCE_MS` | float | `100` | Interval between frame captures |
| `FRAME_BUFFER_CAPACITY` | int | `30` | Maximum frames held in the ring buffer |
| `HOT_PATH_TIMEOUT_MS` | float | `500` | Maximum time for the full hot path |
| `PIPELINE_TIMEOUT_MS` | float | `300` | Maximum time for the perception pipeline |

---

## Worker Pool Concurrency (PUBLIC)

Thread/process pool sizes for each pipeline stage.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NUM_DETECT_WORKERS` | int | `2` | Object detection worker count |
| `NUM_DEPTH_WORKERS` | int | `1` | Depth estimation worker count |
| `NUM_SEGMENT_WORKERS` | int | `1` | Segmentation worker count |
| `NUM_OCR_WORKERS` | int | `1` | OCR worker count |
| `NUM_QR_WORKERS` | int | `1` | QR/AR scanning worker count |
| `NUM_EMBEDDING_WORKERS` | int | `1` | Embedding computation worker count |
| `NUM_FACE_WORKERS` | int | `1` | Face detection/recognition worker count |
| `NUM_AUDIO_WORKERS` | int | `1` | Audio processing worker count |
| `NUM_ACTION_WORKERS` | int | `1` | Action recognition worker count |

---

## Debounce and Deduplication (PUBLIC)

Prevents redundant announcements for the same obstacle.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DEBOUNCE_WINDOW_SECONDS` | float | `5.0` | Minimum interval between repeat announcements |
| `DISTANCE_DELTA_M` | float | `0.5` | Distance change required to re-announce an object |
| `CONFIDENCE_DELTA` | float | `0.15` | Confidence change required to re-announce an object |

---

## Watchdog (INTERNAL)

Stall detection for camera feed and worker threads.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CAMERA_STALL_THRESHOLD_MS` | float | `2000` | Camera feed stall timeout |
| `WORKER_STALL_THRESHOLD_MS` | float | `5000` | Worker thread stall timeout |

---

## Always-On / Proactive Processing (PUBLIC)

Controls continuous background perception and proactive announcements.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ALWAYS_ON` | bool | `true` | Keep the perception pipeline running continuously |
| `CONTINUOUS_PROCESSING` | bool | `true` | Process every captured frame (not just on user query) |
| `PROACTIVE_ANNOUNCE` | bool | `true` | Announce obstacles without user prompting |
| `PROACTIVE_CADENCE_S` | float | `2.0` | Minimum seconds between proactive announcements |
| `PROACTIVE_CRITICAL_ONLY` | bool | `false` | Only announce CRITICAL-priority obstacles proactively |

---

## Privacy and Consent (INTERNAL)

Controls for telemetry and memory consent enforcement.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MEMORY_TELEMETRY` | bool | `false` | Enable anonymized telemetry collection |
| `MEMORY_REQUIRE_CONSENT` | bool | `true` | Require explicit user consent before storing memories |

---

## Face Engine (PUBLIC)

Face detection, tracking, and recognition settings.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FACE_ENGINE_ENABLED` | bool | `true` | Enable face detection and tracking |
| `FACE_REGISTRATION_ENABLED` | bool | `false` | Allow new face identity registration |
| `FACE_CONSENT_REQUIRED` | bool | `true` | Require consent before processing face data |
| `FACE_DETECTOR_BACKEND` | str | `"auto"` | Detector backend: `auto`, `mtcnn`, `retinaface`, `haar`, or `mock` |
| `FACE_MIN_CONFIDENCE` | float | `0.5` | Minimum confidence for face detection |
| `FACE_MAX_TRACKED` | int | `20` | Maximum simultaneously tracked faces |
| `FACE_ENCRYPTION_ENABLED` | bool | `true` | Encrypt face embeddings at rest |

---

## Audio Engine (PUBLIC)

Sound source localization and audio event detection.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUDIO_ENGINE_ENABLED` | bool | `true` | Enable audio processing |
| `AUDIO_SSL_ENABLED` | bool | `true` | Enable sound source localization |
| `AUDIO_EVENT_DETECTION_ENABLED` | bool | `true` | Enable audio event detection (sirens, horns, etc.) |
| `AUDIO_SAMPLE_RATE` | int | `16000` | Audio sample rate in Hz |
| `AUDIO_MIN_ENERGY_DB` | float | `-40` | Minimum energy threshold for audio event detection |

---

## Action / Intent Recognition (PUBLIC)

CLIP-based action recognition from short video clips.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ACTION_ENGINE_ENABLED` | bool | `true` | Enable action/intent recognition |
| `ACTION_CLIP_LENGTH` | int | `16` | Number of frames per action clip |
| `ACTION_CLIP_STRIDE` | int | `4` | Frame stride between clip samples |
| `ACTION_MIN_CONFIDENCE` | float | `0.3` | Minimum confidence for action detection |

---

## Cloud Sync (PUBLIC)

Event synchronization and auto-summarization.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CLOUD_SYNC` | bool | `false` | Enable cloud event synchronization (env var name; stored as `CLOUD_SYNC_ENABLED` in CONFIG) |
| `CLOUD_SYNC_PROVIDER` | str | `"stub"` | Sync backend provider name |
| `MEMORY_EVENT_DETECTION` | bool | `true` | Detect and tag notable events in the memory stream |
| `MEMORY_AUTO_SUMMARIZE` | bool | `true` | Auto-generate summaries of stored events |

---

## Raw Media (INTERNAL)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RAW_MEDIA_SAVE` | bool | `false` | Save raw camera frames and audio to disk |

---

## Memory Engine (PUBLIC)

Defined in `core/memory/config.py`. Loaded via `MemoryConfig.from_env()`.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MEMORY_ENABLED` | bool | `false` | Enable the RAG memory engine (opt-in) |
| `MEMORY_RETENTION_DAYS` | int | `30` | Days before memories auto-expire |
| `MEMORY_MAX_VECTORS` | int | `5000` | Maximum vectors in the FAISS index |
| `MEMORY_INDEX_PATH` | str | `"./data/memory_index/"` | Directory for the FAISS index files |
| `MEMORY_ENCRYPTION` | bool | `false` | Encrypt memory index at rest |
| `MEMORY_ENCRYPTION_KEY_ENV` | str | `"MEMORY_ENCRYPTION_KEY"` | Env var name holding the encryption key |
| `MEMORY_SAVE_RAW` | bool | `false` | Save raw media alongside embeddings |
| `EMBEDDING_MODEL` | str | `"qwen3-embedding:4b"` | Text embedding model identifier |
| `IMAGE_EMBEDDING_ENABLED` | bool | `false` | Enable image embedding computation |
| `IMAGE_EMBEDDING_MODEL` | str | `"clip-ViT-B-32"` | Image embedding model identifier |
| `AUDIO_EMBEDDING_ENABLED` | bool | `false` | Enable audio embedding computation |
| `RAG_K` | int | `5` | Number of memories retrieved per RAG query |
| `MEMORY_SIMILARITY_THRESHOLD` | float | `0.1` | Minimum cosine similarity for retrieval |
| `EMBEDDING_BATCH_SIZE` | int | `8` | Batch size for embedding computation |
| `MEMORY_ASYNC_INDEXING` | bool | `true` | Index new memories asynchronously |
| `MEMORY_COMMIT_INTERVAL` | float | `5.0` | Seconds between index commits to disk |
| `MEMORY_LIGHT_MODE` | bool | `false` | Resource-constrained mode: text-only, reduced capacity |

---

## Docker / Container Detection (INTERNAL)

Used by `SecretProvider` to choose between `.env` file and OS environment.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DOCKER` | str | `""` | Set to `"true"` when running inside Docker |
| `CONTAINER` | str | `""` | Set to `"true"` when running in any container runtime |

---

## Notes

- Boolean variables accept `"true"` / `"false"` (case-insensitive). Some also accept `"1"` / `"0"`, `"yes"` / `"no"`, `"on"` / `"off"` in `core/memory/config.py`.
- Secret variables are resolved through the `SecretProvider` abstraction. In Docker, secrets come from OS environment variables. In local dev, they're read from a `.env` file.
- The `SECRETS` frozenset in `shared/config/settings.py` lists all variables classified as SECRET. These must have empty defaults and must never be logged.
- Run `validate_config()` at startup to surface warnings about unset secrets.
