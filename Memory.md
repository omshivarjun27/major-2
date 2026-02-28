<!--
Location: /Memory.md
Scope: Entire Codebase
Owner: Autonomous Agents
Update Policy: Mandatory on Every Structural or Behavioral Change
-->

# Persistent Architectural & Operational Memory

This file is the persistent memory layer for all agents operating on the Voice & Vision Assistant for Blind codebase. It records architecture, data models, APIs, configuration, dependencies, performance, security posture, decisions, research, changes, and open issues. Agents MUST read this file before any structural work and MUST update it after completing changes.

## Section 1: Purpose & Scope

This document serves as the authoritative record for the Voice & Vision Assistant for Blind project. It ensures continuity across autonomous operations and maintains a shared state for architectural integrity.

- **Location**: `/Memory.md` (ROOT ONLY)
- **Scope**: Entire Codebase
- **Owner**: Autonomous Agents
- **Update Policy**: Mandatory on Every Structural or Behavioral Change
- **Purpose**: Persistent context for all agents, recording the system's evolution and current state.

## Section 2: System Identity Snapshot

| Property | Value |
| :--- | :--- |
| Project Name | Voice & Vision Assistant for Blind |
| Architecture | Modular Monolith (5-layer strict hierarchy) |
| Language | Python 3.10+ |
| Framework Stack | FastAPI + LiveKit Agents + ONNX Runtime |
| Runtime | Hybrid Cloud + Local GPU |
| Hardware Target | NVIDIA RTX 4060 (8GB VRAM) |
| Peak VRAM | ~3.1GB |
| LOC | 48,096 across 201 files in 47 directories |
| Tests | 840 functions across 61 test files |
| Contributors | 2 (Muhammed Aslam A: 14 commits, omshivarjun: 5 commits) |
| Total Commits | 21 |
| Current Phase | Beta |
| Completion | 63% |
| Architecture Maturity | 3/5 |
| Documentation Health | 78/100 |
| Technical Debt | Medium-High (71 stubs, 15 registered debt items) |
| Entry Points | FastAPI REST (port 8000, 28 endpoints), LiveKit WebRTC (port 8081) |

## Section 3: Architectural Memory

### 3.1 Layer Hierarchy

The system enforces a strict 5-layer dependency flow. Each layer may only import from layers below it.

```
shared -> core -> application -> infrastructure -> apps
```

| Layer | LOC | May Import From | Forbidden Imports | Enforcement |
| :--- | :--- | :--- | :--- | :--- |
| shared | 4,012 | stdlib only | core, application, infrastructure, apps | import-linter |
| core | 17,414 | shared | application, infrastructure, apps | import-linter |
| application | 4,507 | shared, core | infrastructure, apps | import-linter |
| infrastructure | 978 | shared | apps (partial enforcement) | import-linter |
| apps | 3,406 | shared, core, application, infrastructure | None (top layer) | import-linter |

### 3.2 Module Registry

| Module | Path | Status | Stub Count | Key Classes |
| :--- | :--- | :--- | :--- | :--- |
| Vision/Spatial | core/vision/ | Complete (95%) | 4 | SpatialPerceptionEngine, YOLODetector, MiDaSDepthEstimator |
| VQA | core/vqa/ | Complete (90%) | 1 | PerceptionOrchestrator, SceneGraphBuilder, VQAReasoner |
| Memory | core/memory/ | In Progress (75%) | 7 | FAISSIndexer, RAGReasoner, OllamaEmbedder, MemoryIngester |
| OCR | core/ocr/ | Complete (95%) | 0 | OCREngine (3-tier fallback) |
| Braille | core/braille/ | Complete (95%) | 0 | BrailleOCR, BrailleSegmenter, BrailleClassifier |
| QR/AR | core/qr/ | Complete (90%) | 4 | QRScanner, ARHandler, QRCache |
| Face | core/face/ | In Progress (80%) | 3 | FaceDetector, FaceTracker, FaceEmbeddingStore |
| Speech | core/speech/ | Complete (85%) | 0 | VoiceRouter, TTSBridge |
| Audio | core/audio/ | In Progress (70%) | 1 | AudioEventDetector, SoundSourceLocalizer |
| Action | core/action/ | In Progress (60%) | 1 | ActionRecognizer |
| Reasoning | core/reasoning/ | Empty Placeholder | 0 | None |

### 3.3 Service Boundaries

The system exposes two primary entry points:
1. **FastAPI REST API (port 8000)**: 28 endpoints for management, state queries, and GDPR-compliant data export.
2. **LiveKit WebRTC Agent (port 8081)**: Real-time multimodal voice and vision interaction.

### 3.4 Data Flow Paths

- **Audio Path**: User Voice -> Deepgram STT -> Intent Router -> Core Engine -> LLM -> ElevenLabs TTS -> Audio Output.
- **Vision Path**: User Camera -> Frame Sampler -> Detect, Depth, Segment -> Scene Graph -> Navigation Cue.

### 3.5 External Integrations

| Provider | Service | Type | Fallback |
| :--- | :--- | :--- | :--- |
| Deepgram | STT | Cloud | None (SPOF) |
| ElevenLabs | TTS | Cloud | None (SPOF) |
| Ollama | LLM (Qwen-VL) | Cloud | None |
| LiveKit | WebRTC | Cloud | None |
| Tavus | Avatar | Cloud (optional) | Disabled by default |
| DuckDuckGo | Search | Cloud | None |
| YOLO v8n | Detection | Local GPU (~200MB VRAM) | MockObjectDetector |
| MiDaS v2.1 | Depth | Local GPU (~100MB VRAM) | SimpleDepthEstimator |
| qwen3-embedding:4b | Embeddings | Local GPU (~2GB VRAM) | None |
| EasyOCR | OCR | Local GPU (~500MB VRAM) | Tesseract -> MSER |
| FAISS | Vector Search | Local CPU | None |

### 3.6 Known Architectural Anti-Patterns

1. **God File**: `apps/realtime/agent.py`. 1,900 LOC file violates single responsibility (TD-001, P0).
2. **Empty Placeholder Modules** (5): core/reasoning, infrastructure/storage, infrastructure/monitoring, application/event_bus, and application/session_mgmt.
3. **Synchronous Blocking**: OllamaEmbedder.embed_text() blocks the event loop, roughly 150ms per call (TD-003, P0).
4. **Over-exported shared/__init__.py**: 319 LOC re-exporting too many symbols (TD-010, P2).


### Section 4: Data Memory

#### 4.1 Core Data Models (shared/schemas/__init__.py)

**Enums (4)**:
| Enum | Values | Purpose |
|------|--------|---------|
| Priority | CRITICAL, NEAR_HAZARD, FAR_HAZARD, SAFE | Obstacle priority based on distance thresholds |
| Direction | FAR_LEFT, LEFT, SLIGHTLY_LEFT, CENTER, SLIGHTLY_RIGHT, RIGHT, FAR_RIGHT | Relative direction from user center of view |
| SizeCategory | SMALL (<5%), MEDIUM (5-25%), LARGE (>25%) | Object size relative to frame |
| SpatialRelation | LEFT_OF, RIGHT_OF, ABOVE, BELOW, IN_FRONT_OF, BEHIND, NEAR, BLOCKING | Relationships between detected objects |

**Dataclasses (7)**:
| Model | Fields | Purpose |
|-------|--------|---------|
| BoundingBox | x1, y1, x2, y2 | Pixel-coordinate bounding box with utility methods (center, area, clamp, from_xywh) |
| Detection | id, class_name, confidence, bbox | Single object detection result |
| SegmentationMask | detection_id, mask, boundary_confidence, edge_pixels | Edge-aware segmentation mask for a detection |
| DepthMap | depth_array, min_depth, max_depth, is_metric | Depth estimation result with get_region_depth(bbox) returning (min, median, max) |
| PerceptionResult | detections, masks, depth_map, image_size, latency_ms, timestamp, frame_id | Combined perception pipeline output |
| ObstacleRecord | id, class_name, bbox, centroid_px, distance_m, direction, direction_deg, mask_confidence, detection_confidence, priority, size_category, action_recommendation | Fused spatial obstacle data (detection + segmentation + depth) |
| NavigationOutput | short_cue, verbose_description, telemetry, has_critical | Navigation cue output in multiple formats |

**Abstract Base Classes (3)**:
| ABC | Abstract Methods | Purpose |
|-----|-----------------|---------|
| ObjectDetector | detect(image), is_ready() | Contract for object detection implementations |
| Segmenter | segment(image, detections) | Contract for segmentation implementations |
| DepthEstimator | estimate(image) | Contract for depth estimation implementations |

#### 4.2 Domain-Specific Models
Note that additional models exist within each core module (face identities, memory records, QR cache entries, braille cells, etc.) but the shared schemas above form the canonical pipeline contract. Total model count across the codebase: 52 (22 dataclasses, 20 Pydantic, 10 enums, 3 ABCs).

### Section 5: API Memory

#### 5.1 REST API Endpoints (FastAPI, port 8000)

**System Health (4 endpoints)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /health | None | System health with all engine statuses |
| GET | /health/camera | None | Camera feed health and frame age |
| GET | /health/orchestrator | None | Orchestrator pipeline status |
| GET | /health/workers | None | Worker pool queue sizes and stats |

**QR/AR Scanning (4 endpoints, gated by ENABLE_QR_SCANNING)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /qr/scan | None | Submit frame for QR/AR code scanning |
| GET | /qr/cache | None | View cached QR scan results |
| GET | /qr/history | None | Scan history with timestamps |
| GET | /qr/debug | None | QR engine debug info |

**VQA (registered via core.vqa.api_endpoints)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| Various | /vqa/* | None | Visual question answering endpoints |

**Memory Engine (registered via core.memory.api_endpoints)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| Various | /memory/* | None | Memory ingestion, retrieval, and management |
| DELETE | /memory/delete_all | None | Delete all stored memories (irreversible) |

**Face Engine (5 endpoints, gated by FACE_ENGINE_ENABLED)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /face/health | None | Face engine component health |
| POST | /face/consent | None | Record face consent for identity |
| GET | /face/consent/log | None | View face consent audit trail |
| POST | /face/detect | None | Consent-gated face detection (returns 403 if no consent) |
| DELETE | /face/forget_all | None | Delete all face data and revoke consent |

**Audio Engine (2 endpoints, gated by AUDIO_ENGINE_ENABLED)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /audio/health | None | Audio engine health (SSL, event detector, fuser) |
| GET | /debug/ssl_frame | Bearer token | SSL configuration and status |

**Action Engine (1 endpoint, gated by ACTION_ENGINE_ENABLED)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /action/health | None | Action recognizer health |

**Braille (2 endpoints)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /braille/read | None | Submit frame for braille reading |
| GET | /debug/braille_frame | Bearer token | Braille segmentation pipeline status |

**Debug Endpoints (8 endpoints, all require Bearer token via DEBUG_AUTH_TOKEN)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | /debug/metrics | Bearer token | Perception and TTS aggregate metrics |
| POST | /debug/perception_frame | Bearer token | Debug perception overlay |
| GET | /logs/sessions | Bearer token | List debug sessions |
| GET | /logs/session/{session_id} | Bearer token | Retrieve session events |
| POST | /logs/session | Bearer token | Create new debug session |
| POST | /debug/stale_check | Bearer token | Scan for stale-frame usage points |
| POST | /debug/live_frames | Bearer token | LiveFrameManager state |
| GET | /debug/frame_rate | Bearer token | Frame rate and latency stats |
| GET | /debug/watchdog_status | Bearer token | Watchdog stall detection history |
| GET | /debug/dependency_status | Bearer token | Optional dependency availability |
| GET | /debug/ocr_install | Bearer token | OCR backend installation status |

**GDPR Compliance (2 endpoints)**:
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /export/data | None | Export all user data (GDPR Art. 20 - Data Portability) |
| DELETE | /export/erase | None | Erase all user data (GDPR Art. 17 - Right to Erasure) |

#### 5.2 WebRTC Interface (LiveKit, port 8081)
The LiveKit agent handles real-time multimodal interaction. It is not a REST API but a WebRTC-based agent that processes audio and video streams. Connection is via LiveKit playground or compatible WebRTC clients.

### Section 6: Configuration Memory

#### 6.1 Feature Flags (7)
| Flag | Default | Purpose |
|------|---------|---------|
| SPATIAL_PERCEPTION_ENABLED | true | Enable/disable spatial perception pipeline |
| ENABLE_QR_SCANNING | true | Enable/disable QR/AR tag scanning |
| FACE_ENGINE_ENABLED | true | Enable/disable face detection and tracking |
| AUDIO_ENGINE_ENABLED | true | Enable/disable audio event detection |
| ACTION_ENGINE_ENABLED | true | Enable/disable action/intent recognition |
| CLOUD_SYNC_ENABLED | false | Enable/disable memory cloud synchronization |
| TAVUS_ENABLED | false | Enable/disable Tavus virtual avatar |

#### 6.2 Environment Variables by Category

**Vision Provider (3)**:
VISION_PROVIDER (ollama), OLLAMA_VL_API_KEY, OLLAMA_VL_MODEL_ID (qwen3-vl:235b-instruct-cloud)

**Tavus Avatar (5)**:
ENABLE_AVATAR (false), TAVUS_API_KEY, TAVUS_REPLICA_ID, TAVUS_PERSONA_ID, TAVUS_AVATAR_NAME (ally-vision-avatar)

**Spatial Perception (10)**:
SPATIAL_PERCEPTION_ENABLED (true), SPATIAL_USE_YOLO (auto), YOLO_MODEL_PATH, YOLO_CONF_THRESHOLD (0.5), SPATIAL_USE_MIDAS (auto), MIDAS_MODEL_PATH, MIDAS_MODEL_TYPE (MiDaS_small), ENABLE_SEGMENTATION (false), ENABLE_DEPTH (false), LOW_LATENCY_WARNINGS (true)

**Distance Thresholds (3)**:
CRITICAL_DISTANCE_M (1.0), NEAR_DISTANCE_M (2.0), FAR_DISTANCE_M (5.0)

**Latency Targets (4)**:
TARGET_STT_LATENCY_MS (100), TARGET_VQA_LATENCY_MS (300), TARGET_TTS_LATENCY_MS (100), TARGET_TOTAL_LATENCY_MS (500)

**Live Frame & Capture (5)**:
LIVE_FRAME_MAX_AGE_MS (500), CAPTURE_CADENCE_MS (100), FRAME_BUFFER_CAPACITY (30), HOT_PATH_TIMEOUT_MS (500), PIPELINE_TIMEOUT_MS (300)

**Worker Pool Concurrency (6)**:
NUM_DETECT_WORKERS (2), NUM_DEPTH_WORKERS (1), NUM_SEGMENT_WORKERS (1), NUM_OCR_WORKERS (1), NUM_QR_WORKERS (1), NUM_EMBEDDING_WORKERS (1)

**Debounce & Deduplication (3)**:
DEBOUNCE_WINDOW_SECONDS (5.0), DISTANCE_DELTA_M (0.5), CONFIDENCE_DELTA (0.15)

**Watchdog (2)**:
CAMERA_STALL_THRESHOLD_MS (2000), WORKER_STALL_THRESHOLD_MS (5000)

**Continuous Processing (5)**:
ALWAYS_ON (true), CONTINUOUS_PROCESSING (true), PROACTIVE_ANNOUNCE (true), PROACTIVE_CADENCE_S (2.0), PROACTIVE_CRITICAL_ONLY (false)

**Privacy & Consent (2)**:
MEMORY_TELEMETRY (false), MEMORY_REQUIRE_CONSENT (true)

**Face Engine (7)**:
FACE_ENGINE_ENABLED (true), FACE_REGISTRATION_ENABLED (false), FACE_CONSENT_REQUIRED (true), FACE_DETECTOR_BACKEND (auto), FACE_MIN_CONFIDENCE (0.5), FACE_MAX_TRACKED (20), FACE_ENCRYPTION_ENABLED (true)

**Audio Engine (5)**:
AUDIO_ENGINE_ENABLED (true), AUDIO_SSL_ENABLED (true), AUDIO_EVENT_DETECTION_ENABLED (true), AUDIO_SAMPLE_RATE (16000), AUDIO_MIN_ENERGY_DB (-40)

**Action Engine (4)**:
ACTION_ENGINE_ENABLED (true), ACTION_CLIP_LENGTH (16), ACTION_CLIP_STRIDE (4), ACTION_MIN_CONFIDENCE (0.3)

**Cloud Sync (4)**:
CLOUD_SYNC_ENABLED (false), CLOUD_SYNC_PROVIDER (stub), MEMORY_EVENT_DETECTION (true), MEMORY_AUTO_SUMMARIZE (true)

**QR/AR (4)**:
ENABLE_QR_SCANNING (true), QR_CACHE_ENABLED (true), QR_AUTO_DETECT (true), QR_CACHE_TTL_SECONDS (86400)

**Debug & Auth (2)**:
DEBUG_ENDPOINTS_ENABLED (false), DEBUG_AUTH_TOKEN

**Miscellaneous (3)**:
RAW_MEDIA_SAVE (false), MAX_TOKENS (500), TEMPERATURE (0.7)

#### 6.3 Configuration Access Patterns
All configuration is centralized in `shared/config/settings.py` via a single `CONFIG` dictionary. Access is provided through typed helper functions: `get_config()`, `get_spatial_config()`, `get_face_config()`, `get_audio_config()`, `get_worker_config()`, `get_qr_config()`, etc. Direct `os.environ.get()` calls within `settings.py` only. Other modules use the accessor functions.
## Section 7: Dependency Memory

#### 7.1 Core Dependencies (requirements.txt)
| Package | Version Constraint | Purpose | Risk |
|---------|-------------------|---------|------|
| livekit-agents[deepgram,elevenlabs,tavus] | >=1.0.0 | Real-time WebRTC agent framework with STT/TTS plugins | Cloud dependency |
| livekit | >=1.0.0 | LiveKit SDK | Cloud dependency |
| livekit-api | >=1.0.0 | LiveKit server API | Cloud dependency |
| livekit-plugins-deepgram | >=1.0.0 | Deepgram STT integration | Cloud SPOF |
| livekit-plugins-openai | >=1.0.0 | LLM integration plugin | Cloud dependency |
| livekit-plugins-silero | >=1.0.0 | Voice activity detection | Local |
| livekit-plugins-elevenlabs | >=1.0.0 | ElevenLabs TTS integration | Cloud SPOF |
| livekit-plugins-tavus | >=1.0.0 | Tavus avatar integration | Cloud (optional) |
| python-dotenv | >=1.0.0 | Environment variable loading | None |
| librosa | >=0.10.0 | Audio analysis | None |
| numpy | >=1.20.0 | Numerical computing | None |
| langchain-community | latest | LangChain community integrations | None |
| duckduckgo-search | latest | Internet search | Cloud |
| ollama | latest | Ollama LLM client | Cloud |
| opencv-python | latest | Computer vision | None |
| Pillow | >=9.0.0 | Image processing | None |
| easyocr | >=1.7.0 | OCR (primary backend) | GPU |
| pytesseract | >=0.3.10 | OCR (secondary backend) | External binary |
| pyzbar | >=0.1.9 | QR code decoding | External DLL on Windows |
| qrcode[pil] | >=7.4 | QR code generation (tests) | None |
| httpx | >=0.26.0 | Async HTTP client | None |
| onnxruntime | >=1.15.0 | ML model inference | GPU (optional) |
| scipy | >=1.10.0 | Scientific computing | None |
| scikit-image | >=0.21.0 | Image processing | None |
| fastapi | >=0.109.0 | REST API framework | None |
| uvicorn | >=0.27.0 | ASGI server | None |
| pydantic | >=2.5.0 | Data validation | None |
| pytest | >=7.0.0 | Testing framework | Dev only |
| pytest-asyncio | >=0.23.0 | Async test support | Dev only |
| faiss-cpu | >=1.7.4 | Vector similarity search | None |
| sentence-transformers | >=2.2.0 | Text embeddings | GPU |
| cryptography | >=41.0.0 | Encryption | None |
|
#### 7.2 Dependency Risk Summary
- Total packages: ~32 core + optional extras
- Cloud SPOFs: Deepgram (STT), ElevenLabs (TTS) — no fallback providers
- GPU dependencies: EasyOCR, sentence-transformers, onnxruntime
- External binaries: Tesseract (system install), zbar DLL (Windows)
- Supply chain size: 32 direct packages, contributor bus factor of 2

## Section 8: Performance Memory

#### 8.1 Latency Budget (Hot Path SLA: 500ms)
| Stage | Target | Budget | Validated |
|-------|--------|--------|-----------|
| STT (Deepgram) | 100ms | 20% of budget | Not under load |
| VQA Pipeline | 300ms | 60% of budget | Not under load |
| TTS (ElevenLabs) | 100ms | 20% of budget | Not under load |
| Total Hot Path | 500ms | 100% | Not validated under concurrent load |

#### 8.2 Pipeline Latency Targets
| Component | Target | Current Status |
|-----------|--------|----------------|
| Pipeline total | 300ms | Enforced via PIPELINE_TIMEOUT_MS |
| Hot path timeout | 500ms | Enforced via HOT_PATH_TIMEOUT_MS |
| Frame max age | 500ms | Enforced via LIVE_FRAME_MAX_AGE_MS |
| Debounce window | 5.0s | Deduplication of repeat detections |
| Camera stall threshold | 2000ms | Watchdog trigger for camera feed |
| Worker stall threshold | 5000ms | Watchdog trigger for stuck workers |

#### 8.3 VRAM Budget (RTX 4060, 8GB)
| Model | VRAM Usage | Status |
|-------|-----------|--------|
| YOLO v8n | ~200MB | Active when model file present |
| MiDaS v2.1 | ~100MB | Active when model file present |
| qwen3-embedding:4b | ~2.0GB | Managed by Ollama runtime |
| EasyOCR | ~500MB | Loaded on first use |
| Face Detection | ~300MB | Active when FACE_ENGINE_ENABLED |
| **Total Peak** | **~3.1GB** | 39% of 8GB budget |
| Available headroom | ~4.9GB | Limited room for model upgrades |

#### 8.4 Known Performance Issues
1. **OllamaEmbedder sync blocking** (TD-003, P0): embed_text() blocks the event loop for ~150ms per call. Must be migrated to async.
2. **500ms SLA unvalidated** (PR-1): The hot path SLA has never been tested under concurrent load. FAISS search degrades beyond 1M vectors.
3. **SQLite single-writer lock** (TD-009, P2): Concurrent RAG writes are serialized by SQLite's lock, creating a bottleneck under load.
4. **No load testing**: No Locust or equivalent load testing infrastructure exists (TD-013, P0).

## Section 9: Security Memory

#### 9.1 Current Security Posture
- **Overall Rating**: Fragile (5/10)
- **Critical Gaps**: Secrets management, Docker root execution, missing SAST/DAST

#### 9.2 Secrets Inventory (CRITICAL — 7 API keys in plaintext .env)
| Secret | Storage | Risk |
|--------|---------|------|
| LIVEKIT_API_KEY | .env plaintext | Critical |
| LIVEKIT_API_SECRET | .env plaintext | Critical |
| DEEPGRAM_API_KEY | .env plaintext | Critical |
| OLLAMA_VL_API_KEY | .env plaintext | Critical |
| ELEVEN_API_KEY | .env plaintext | Critical |
| TAVUS_API_KEY | .env plaintext | Critical |
| DEBUG_AUTH_TOKEN | .env plaintext | High |

**Mitigation Plan**: Migrate to HashiCorp Vault, AWS KMS, or equivalent secrets management. Current state: no migration started.

#### 9.3 Privacy Controls
| Control | Status | Implementation |
|---------|--------|----------------|
| Memory opt-in | Active | MEMORY_ENABLED defaults to false |
| Face consent | Active | /face/consent API with file-backed persistence |
| PII scrubbing | Active | shared/logging/pii_scrubber.py filters logs |
| FAISS encryption | Available | cryptography package, FACE_ENCRYPTION_ENABLED=true by default |
| GDPR data export | Active | POST /export/data (Art. 20) |
| GDPR data erasure | Active | DELETE /export/erase (Art. 17) |
| Raw media storage | Disabled | RAW_MEDIA_SAVE defaults to false |
| Consent audit trail | Active | /face/consent/log endpoint |

#### 9.4 Known Security Vulnerabilities
1. **SR-1** (Critical): 7 API keys stored in plaintext .env file — no secrets management
2. **SR-2** (High): Docker containers run as root — missing USER directive
3. **SR-3** (High): No SAST/DAST scanning in CI pipeline
4. **SR-4** (Medium): Face consent state stored as local JSON file without encryption
5. **No circuit breakers**: Cloud service failures cascade without protection
6. **No rate limiting**: API endpoints have no rate limiting beyond feature flags

#### 9.5 Authentication & Authorization
- Debug endpoints gated by DEBUG_AUTH_TOKEN (Bearer token in Authorization header)
- Debug endpoints disabled by default (DEBUG_ENDPOINTS_ENABLED=false)
- Face detection endpoints gated by consent check (returns 403 without consent)
- No user authentication system — single-user design
- No role-based access control


### Section 10: Decision Memory

#### 10.1 Architectural Decision Records

**ADR-001: Modular Monolith over Microservices**
- Date: 2025-04-15 (project inception)
- Status: Accepted
- Context: The system requires sub-500ms end-to-end latency for real-time accessibility. Vision models share GPU memory and need low-latency data transfer.
- Decision: Use a modular monolith with strict 5-layer hierarchy enforced by import-linter.
- Consequences: Latency optimized for single-instance deployment. Horizontal scaling is blocked by GPU affinity and monolith design. Acceptable tradeoff for the target hardware (single RTX 4060).

**ADR-002: Hybrid Cloud + Local GPU Architecture**
- Date: 2025-04-15
- Status: Accepted
- Context: Some capabilities (STT, TTS, VLM reasoning) require cloud-scale models, while safety-critical perception must run locally with deterministic latency.
- Decision: Cloud for Qwen-VL, Deepgram, ElevenLabs, LiveKit. Local GPU for YOLO, MiDaS, EasyOCR, FAISS, Face Detection.
- Consequences: Dual dependency model. Cloud failures affect speech but not spatial perception. Six cloud services create SPOF risks without circuit breakers.

**ADR-003: FAISS + SQLite Hybrid Memory**
- Date: 2025-05-01
- Status: Accepted
- Context: RAG memory requires fast semantic search and reliable structured storage.
- Decision: FAISS IndexFlatL2 for vector similarity search, SQLite WAL mode for structured data. Row IDs synchronized across both.
- Consequences: High-speed retrieval for up to 5,000 vectors. Single-writer SQLite lock limits concurrent writes. FAISS search degrades beyond 1M vectors.

**ADR-004: Privacy-First Memory Design**
- Date: 2025-05-01
- Status: Accepted
- Context: Users are blind/visually impaired — storing personal data (faces, conversations) requires explicit consent.
- Decision: MEMORY_ENABLED defaults to false. Face recognition requires explicit consent via API. PII scrubbing on all logs. No raw media storage by default. GDPR Art. 17 and Art. 20 endpoints.
- Consequences: Reduced functionality by default but strong privacy posture. Consent state stored as local JSON (not encrypted — known vulnerability SR-4).

**ADR-005: 3-Tier OCR Fallback**
- Date: 2025-08-01
- Status: Accepted
- Context: Single OCR backend fails on various text types. EasyOCR is accurate but slow; Tesseract is fast but struggles with tilted text; MSER is a last-resort heuristic.
- Decision: EasyOCR (primary) → Tesseract (secondary) → MSER heuristic (tertiary) → helpful error message.
- Consequences: Robust text reading across diverse scenarios. Auto-probe at startup detects available backends. Install scripts provided per OS.

**ADR-006: Embedding Model Migration to qwen3-embedding:4b**
- Date: 2026-02-15
- Status: Accepted
- Context: all-MiniLM-L6-v2 had limited multilingual support and lower retrieval quality.
- Decision: Migrate to qwen3-embedding:4b (384 dimensions) via Ollama for better RAG retrieval quality.
- Consequences: ~2GB VRAM for embedding model. Improved retrieval accuracy. OllamaEmbedder currently blocks event loop synchronously (TD-003).

**ADR-007: 5-Layer Architecture Migration**
- Date: 2026-02-15
- Status: Accepted
- Context: Original flat structure caused circular imports and made the codebase difficult to navigate.
- Decision: Migrate to shared → core → application → infrastructure → apps hierarchy with import-linter enforcement.
- Consequences: Clean dependency flow. All 201 files reorganized. Import boundaries enforced in CI. Some modules are placeholder shells (5 empty modules).

### Section 11: Research Memory

#### 11.1 Technology Evaluations
| Technology | Task | Why Selected | Alternatives Rejected | Rejection Reason |
|-----------|------|-------------|----------------------|------------------|
| YOLO v8n | Object Detection | Best speed/accuracy for edge | SSD, Faster R-CNN | Poor latency or excessive VRAM |
| MiDaS v2.1 | Depth Estimation | Robust monocular depth | AdaBins, ZoeDepth | Too computationally heavy for 300ms budget |
| Qwen-VL | Visual Reasoning | Superior accessibility descriptions | LLaVA, CogVLM | Lower accuracy for accessibility-specific tasks |
| qwen3-embedding:4b | Text Embeddings | Optimized RAG retrieval | BERT, Sentence-Transformers | Lower retrieval quality |
| FAISS | Vector Storage | Fastest similarity search | ChromaDB, Pinecone | Network latency, external cloud dependency |
| EasyOCR | General OCR | High accuracy on natural scenes | PaddleOCR | Larger footprint |
| Deepgram | STT | Lowest latency real-time speech | Whisper (local) | GPU reserved for vision, latency concerns |
| ElevenLabs | TTS | Most natural conversational voice | Coqui TTS, Edge TTS | Quality gap for accessibility use case |
| LiveKit | WebRTC | Production-grade streaming | WebSockets, Kurento | Insufficient production robustness |
| ONNX Runtime | Inference | Universal execution provider | TensorRT, OpenVINO | Hardware-specific, less portable |

#### 11.2 Performance Benchmarks
| Model | Inference Time | Hardware | Notes |
|-------|---------------|----------|-------|
| YOLO v8n (ONNX) | ~30ms | RTX 4060 | Object detection per frame |
| MiDaS v2.1 (ONNX) | ~50ms | RTX 4060 | Depth map per frame |
| qwen3-embedding:4b | ~150ms | RTX 4060 via Ollama | Per embedding call (sync, blocking) |
| EasyOCR | ~2-5s | RTX 4060 | Full page OCR |
| FAISS IndexFlatL2 | <50ms | CPU | For up to 5,000 vectors |

#### 11.3 Future Evolution Paths
- Circuit breakers: Exponential backoff for all 6 cloud dependencies using Tenacity
- Local STT fallback: Whisper as fallback when Deepgram is unavailable
- Local TTS fallback: Edge TTS as fallback when ElevenLabs is unavailable
- Model quantization: INT8 quantization of YOLO and MiDaS to halve VRAM usage
- Cloud sync: Global user profile and memory synchronization across regions

### Section 12: Thinking Log

#### 12.1 Architectural Reasoning (append-only)

**2025-04-15 — Project Inception**
Chose monolith over microservices because inter-process communication latency would violate the 500ms hot path SLA. Local GPU processing requires shared memory access for YOLO, MiDaS, and segmentation to avoid redundant data transfers. The 5-layer hierarchy was designed to prevent architectural drift while keeping the deployment surface minimal.

**2025-05-01 — Memory Engine Design**
FAISS + SQLite hybrid chosen after evaluating ChromaDB (too heavy for single-user deployment) and pure SQLite FTS5 (insufficient semantic search quality). The ID synchronization between FAISS row indices and SQLite rowids is a known fragility point but acceptable for the current scale (<5,000 vectors).

**2025-08-01 — OCR Resilience Strategy**
Single-backend OCR kept failing on edge cases (tilted text, low contrast, handwriting). The 3-tier fallback was designed to maximize coverage: EasyOCR handles most cases, Tesseract catches clean printed text fast, and MSER provides a heuristic last resort. Auto-probe at startup prevents hard crashes when backends are missing.

**2026-02-15 — Architecture Migration Sprint**
The flat file structure had become unmaintainable with 200+ files. The 5-layer migration took 2 commits and reorganized every file. import-linter was added to CI to prevent regression. Five modules were created as empty placeholders to mark future work areas (reasoning, storage, monitoring, event bus, session management).

**2026-02-23 — Documentation Sprint**
Created 50 AGENTS.md files across the repository using a 9-section template. This provides directory-level intelligence for autonomous agents. The root AGENTS.md uses a 10-section enterprise format. Documentation health score improved from ~60 to 78/100.

**2026-02-24 — Memory.md Creation**
This file was created to serve as persistent architectural memory across agent sessions. The 18-section structure captures system identity, architecture, data, APIs, config, dependencies, performance, security, decisions, research, reasoning, changes, compression, issues, and governance. The goal is to eliminate context loss between autonomous work sessions.

### Section 13: Change Tracking

#### 13.1 Git History Summary
| Commit | Date | Author | Description |
|--------|------|--------|-------------|
| a14f7ba | 2025-04-15 | omshivarjun | Add images directory |
| d2da14b | 2025-04-15 | omshivarjun | Initial commit |
| 3d9fcae–1d9be44 | 2025-04-16 to 2025-05-15 | omshivarjun | Update files (7 commits) |
| 5ecbecc | 2025-05-16 | omshivarjun | Avatar added |
| 25c7b01–b834521 | 2025-05-17 to 2025-05-18 | Muhammed Aslam A | Update files (2 commits) |
| 2cf6def–4a189e4 | 2025-05-19 | Muhammed Aslam A | Update README.md (2 commits, v1.0.0 tag) |
| c2b71b4 | 2026-02-15 | Muhammed Aslam A | refactor: complete Phase 1-4 migration to Clean Architecture |
| 4b6e6e3 | 2026-02-15 | Muhammed Aslam A | feat: replace all-MiniLM-L6-v2 with qwen3-embedding:4b |
| 723bfc7 | 2026-02-22 | Muhammed Aslam A | Initial commit from workspace |
| 0ce7d8a | 2026-02-23 | Muhammed Aslam A | docs: add hierarchical AGENTS.md knowledge base |
| 885c8b8 | 2026-02-23 | Muhammed Aslam A | docs: restructure and update master documentation index |

#### 13.2 Development Timeline
- **2025-04-15**: Project inception, initial commit
- **2025-04-16 to 2025-05-18**: Rapid feature development (13 commits)
- **2025-05-19**: v1.0.0 tag, README updates
- **2025-05-20 to 2026-02-14**: 9-month dormancy (zero commits)
- **2026-02-15**: Architecture migration sprint — 5-layer Clean Architecture + embedding model migration (2 commits)
- **2026-02-22**: Workspace reinitialisation
- **2026-02-23**: Documentation sprint — 50 AGENTS.md files, docs-index restructure (2 commits)
- **2026-02-24**: Memory.md creation (this document)

#### 13.3 Recent Changes (Last 7 Days)
| Date | Change | Impact |
|------|--------|--------|
| 2026-02-23 | 50 AGENTS.md files created across all directories | Documentation health 60 → 78 |
| 2026-02-23 | docs-index.md restructured with risk map | Improved navigation |
| 2026-02-23 | progress.md updated to 63% completion | Status tracking |
| 2026-02-24 | Memory.md created (this file) | Persistent agent memory |

### Section 14: Context Compression

#### 14.1 Twenty-Line Summary
Voice & Vision Assistant for Blind is a real-time accessibility platform providing sensory substitution for blind and visually impaired users. Built as a Python 3.10+ modular monolith with a strict 5-layer hierarchy (shared → core → application → infrastructure → apps) enforced by import-linter. The system runs on hybrid Cloud + Local GPU architecture targeting an NVIDIA RTX 4060 with ~3.1GB peak VRAM usage. Core capabilities include YOLO v8n object detection, MiDaS v2.1 depth estimation, 3-tier OCR fallback (EasyOCR → Tesseract → MSER), braille reading, QR/AR scanning, face detection with consent gating, and privacy-first RAG memory using FAISS + SQLite. Cloud services include Deepgram (STT), ElevenLabs (TTS), Qwen-VL via Ollama (reasoning), and LiveKit (WebRTC streaming). The system exposes 28 REST endpoints on port 8000 and a LiveKit WebRTC agent on port 8081. The codebase contains 48,096 LOC across 201 files, with 840 test functions and 50 AGENTS.md documentation files. Current phase is Beta at 63% completion with architecture maturity 3/5. Technical debt includes a 1,900-LOC god file (agent.py), 71 stub implementations, and 5 empty placeholder modules. Critical security gaps: 7 API keys in plaintext .env, Docker running as root, no circuit breakers for cloud services. The 500ms hot path SLA has not been validated under concurrent load. Privacy controls are strong: memory opt-in, face consent, PII scrubbing, GDPR export/erasure. Two contributors have made 21 commits since April 2025, with a 9-month dormancy between May 2025 and February 2026.

#### 14.2 Ten-Line Summary
Voice & Vision Assistant for Blind: Python 3.10+ modular monolith (5-layer, import-linter enforced) for real-time accessibility. Hybrid Cloud (Deepgram STT, ElevenLabs TTS, Qwen-VL, LiveKit WebRTC) + Local GPU (YOLO, MiDaS, EasyOCR, FAISS) on RTX 4060 (~3.1GB VRAM). 48,096 LOC, 201 files, 840 tests, 28 REST endpoints, 50 AGENTS.md files. Core engines: vision, VQA, memory (FAISS+SQLite RAG), OCR (3-tier fallback), braille, QR/AR, face (call-gated), speech, audio, action. Beta phase at 63% completion, architecture maturity 3/5. Critical debt: agent.py god file (1,900 LOC), 71 stubs, 5 empty modules. Security gaps: 7 plaintext API keys, Docker root, no circuit breakers. Privacy-first: memory opt-in, face consent, PII scrubbing, GDPR Art. 17/20. Hot path SLA (500ms) unvalidated under load. Two contributors, 21 commits, 9-month dormancy gap.

#### 14.3 Five-Line Summary
Voice & Vision Assistant for Blind: Python modular monolith (5-layer) for real-time accessibility on RTX 4060. Hybrid Cloud (Deepgram, ElevenLabs, Qwen-VL, LiveKit) + Local GPU (YOLO, MiDaS, EasyOCR, FAISS). 48K LOC, 840 tests, 28 endpoints, Beta at 63%. Critical issues: 1,900-LOC god file, 71 stubs, 7 plaintext API keys, no circuit breakers. Privacy-first with consent gating and GDPR compliance.

#### 14.4 One-Line Summary
Real-time accessibility monolith (Python, 48K LOC, 63% complete) using hybrid cloud+GPU for vision, speech, and memory with privacy-first design but critical gaps in secrets management and operational resilience.

### Section 15: Open Issues

#### 15.1 Critical (P0) — 4 Issues
| ID | Issue | Impact | Owner | Blocked By |
|----|-------|--------|-------|------------|
| OI-001 | 7 API keys in plaintext .env (SR-1) | Security breach risk | DevOps | Vault/KMS selection |
| OI-002 | agent.py god file 1,900 LOC (TD-001) | Unmaintainable, regression-prone | Core team | Refactoring plan |
| OI-003 | OllamaEmbedder blocks event loop (TD-003) | Latency spikes during RAG ingestion | Core team | None |
| OI-004 | No load testing for 500ms SLA (TD-013) | SLA unvalidated, production risk | QA | Locust setup |

#### 15.2 High (P1) — 6 Issues
| ID | Issue | Impact | Owner | Blocked By |
|----|-------|--------|-------|------------|
| OI-005 | Docker runs as root (SR-2) | Container escape risk | DevOps | None |
| OI-006 | No circuit breakers for cloud services (TD-006) | Cascading failures | Core team | Tenacity integration |
| OI-007 | No SAST/DAST scanning (SR-3) | Undetected vulnerabilities | DevOps | Tool selection |
| OI-008 | 71 stub implementations (TD-002) | Incomplete functionality | All teams | Prioritized backlog |
| OI-009 | 5 empty placeholder modules (TD-007) | Architecture gaps | Core team | Design decisions |
| OI-010 | No monitoring infrastructure (OR-1) | Blind to production issues | DevOps | Prometheus setup |

#### 15.3 Medium (P2) — 5 Issues
| ID | Issue | Impact | Owner | Blocked By |
|----|-------|--------|-------|------------|
| OI-011 | SQLite single-writer lock (TD-009) | Write contention under load | Core team | DB migration plan |
| OI-012 | shared/__init__.py over-exports (TD-010) | Import bloat, coupling | Core team | None |
| OI-013 | Face consent stored unencrypted (SR-4) | Privacy risk | Core team | None |
| OI-014 | 85+ env vars poorly documented (TD-012) | Misconfiguration risk | Docs team | None |
| OI-015 | Duplicate encryption.py files (TD-014) | Code duplication | Core team | None |


### Section 16: Agent Update Contract

#### 16.1 Mandatory Update Triggers
Any agent that performs one of the following actions MUST update this Memory.md file:

| Trigger | Sections to Update |
|---------|-------------------|
| New file or module created | Section 3 (Architecture), Section 2 (LOC counts) |
| API endpoint added/removed | Section 5 (API Memory) |
| Data model added/changed | Section 4 (Data Memory) |
| Dependency added/removed | Section 7 (Dependency Memory) |
| Configuration variable added | Section 6 (Configuration Memory) |
| Security posture changed | Section 9 (Security Memory) |
| Performance characteristic changed | Section 8 (Performance Memory) |
| Architectural decision made | Section 10 (Decision Memory) |
| Technology evaluated | Section 11 (Research Memory) |
| Bug fixed or feature completed | Section 13 (Change Tracking) |
| Issue resolved or discovered | Section 15 (Open Issues) |
| Any structural change | Section 12 (Thinking Log), Section 14 (Context Compression) |

#### 16.2 Update Rules
1. **Never delete history** — append new entries, do not remove old ones
2. **Never overwrite** — use append operations only
3. **Timestamp all entries** — format: YYYY-MM-DD
4. **Cross-reference** — link related changes across sections (e.g., "See ADR-008" or "Resolves OI-003")
5. **Update compression summaries** — when significant changes accumulate, update Section 14

#### 16.3 Pre-Work Checklist
Before starting any structural work, agents MUST:
1. Read this Memory.md file completely
2. Read the relevant AGENTS.md for the target directory
3. Check Section 15 (Open Issues) for related blockers
4. Check Section 10 (Decision Memory) for relevant architectural decisions
5. Verify current state against Section 2 (System Identity Snapshot)

#### 16.4 Post-Work Checklist
After completing any structural work, agents MUST:
1. Update all triggered sections (see 16.1)
2. Append reasoning to Section 12 (Thinking Log)
3. Update Section 13.3 (Recent Changes)
4. Verify no prohibited terms were introduced
5. Update Section 2 metrics if LOC, test count, or file count changed

### Section 17: Prompt Template

#### 17.1 Memory.md Update Prompt
When an agent needs to update this file, use the following prompt structure:

```
## Memory.md Update

### Change Description
[One-line description of what changed]

### Triggered Sections
[List sections that need updating per Section 16.1]

### Updates
[For each triggered section, provide the content to append]

### Verification
- [ ] No prohibited terms (Claude, Anthropic, OpenAI)
- [ ] No placeholder text (TBD, TODO, coming soon)
- [ ] Append-only (no deletions or overwrites)
- [ ] Timestamps included
- [ ] Cross-references added where applicable
```

#### 17.2 Context Loading Prompt
When an agent needs to load project context, use:

```
## Context Load Request

Read the following files in order:
1. /Memory.md — Section 14 (Context Compression) for quick overview
2. /Memory.md — Section 2 (System Identity) for current metrics
3. /Memory.md — Section 15 (Open Issues) for known blockers
4. /AGENTS.md — Root architecture document
5. /[target-directory]/AGENTS.md — Local module intelligence

Then proceed with the task, referencing Memory.md sections as needed.
```

### Section 18: Versioning

#### 18.1 Document Version
| Field | Value |
|-------|-------|
| Version | 1.0.0 |
| Created | 2026-02-24 |
| Last Updated | 2026-02-24 |
| Schema Version | 1.0 |
| Sections | 18 |
| Total Updates | 1 (initial creation) |

#### 18.2 Version History
| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-02-24 | Autonomous Agent (Atlas Orchestrator) | Initial creation with all 18 sections populated from codebase analysis |

#### 18.3 Schema Evolution Rules
- Minor version bump (1.0.x): Content updates within existing sections
- Minor version bump (1.x.0): New subsections added to existing sections
- Major version bump (x.0.0): New sections added or section structure changed
- All version changes must be recorded in Section 18.2

---

*End of Memory.md — Persistent Architectural & Operational Memory*
*Voice & Vision Assistant for Blind — Version 1.0.0*