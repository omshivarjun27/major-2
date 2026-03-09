# Voice-Vision Assistant — Data Flow, Patterns & Implementation Details

## End-to-End Data Flow

### 1. Application Startup

```
entrypoint.py
  → load_dotenv()  (OPENAI_API_KEY defaults to "ollama")
  → configure_logging(level="INFO")  (JSON in prod, colored in dev)
  → cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    → entrypoint(ctx: JobContext)
      → session_manager setup (UserData creation)
      → AllyVisionAgent instantiation
      → ctx.connect() → LiveKit room join
      → agent.start(room)
```

### 2. User Voice Query Processing

```
[User speaks] → LiveKit WebRTC → Deepgram STT
  → AllyVisionAgent.on_message(text)
    → Flushes cached perception state (ensures fresh frame on next tool call)
    → LLM decides which tool to call
      ├── analyze_vision(query) → vision_controller.analyze_vision()
      │     → capture_fresh_frame() → VisualProcessor.capture_frame(room)
      │     → check_frame_freshness() (stale? return error)
      │     → Ollama streaming analysis (qwen3-vl model)
      │     → Stream chunks to TTS
      │
      ├── detect_obstacles(detail_level) → vision_controller.detect_obstacles()
      │     → capture_fresh_frame()
      │     → VisualProcessor.process_spatial(image)
      │       → SpatialProcessor.process_frame(image)
      │         → YOLODetector.detect() or MockObjectDetector.detect()
      │         → EdgeAwareSegmenter.segment()
      │         → MiDaSDepthEstimator.estimate_depth() or SimpleDepthEstimator
      │         → SpatialFuser.fuse() → ObstacleRecords
      │         → Generate NavigationOutput (short_cue + detailed)
      │     → Return spoken cue
      │
      ├── scan_qr_code(query) → voice_controller.scan_qr_code()
      │     → capture_fresh_frame()
      │     → QRScanner.scan(frame)
      │     → cache_manager (offline storage)
      │     → Contextual spoken message
      │
      ├── read_text(query) → vision_controller.read_text()
      │     → capture_fresh_frame()
      │     → OCR Engine (EasyOCR → Tesseract → MSER)
      │     → Return recognized text
      │
      ├── ask_visual_question(question) → vision_controller.ask_visual_question()
      │     → capture_fresh_frame()
      │     → VQA engine or Ollama fallback
      │     → Return answer
      │
      └── search_internet(query) → voice_controller.search_internet()
            → infrastructure/llm/internet_search.py
            → Return web results

    → LLM generates response using tool output
    → ElevenLabs TTS → LiveKit WebRTC → [User hears]
```

### 3. Frame Capture Lifecycle

```
VisualProcessor.capture_frame(room)
  ├── get_video_track(room) — check cached, then existing tracks, then wait
  ├── Persistent VideoStream (reused across calls, recreated on track change)
  ├── Pull single frame from stream
  ├── Tag with: frame_sequence++, epoch_ms, frame_id = "frm_00000001"
  └── Return PIL Image (or latest_frame fallback)

Frame Freshness Check:
  age = (now * 1000) - last_capture_epoch_ms
  fresh = age <= max_age_ms (default 500ms)
```

### 4. Spatial Perception Pipeline Detail

```
Input: PIL Image (resized to 240×180 for spatial)

Stage 1: Object Detection
  MockObjectDetector: 1 detection at image center (testing)
  YOLODetector (ONNX):
    → Letterbox resize to 640×640 (pad with 114)
    → HWC→NCHW, normalize 0-1, float32
    → ONNX inference → (1, 84, 8400) output
    → Transpose to (8400, 84): first 4 = cx,cy,w,h; next 80 = class scores
    → Confidence filter (≥ conf_threshold)
    → Greedy NMS (IoU > 0.45, max 25 detections)
    → Re-scale to original coordinates
    → Return List[Detection] (capped at MAX_DETECTIONS*5)

Stage 2: Edge-Aware Segmentation
  → Downscale image to 160×120 grayscale
  → Sobel gradient computation (OpenCV or numpy fallback)
  → For each detection (max 2):
    → Scale bbox to mask coordinates
    → Otsu thresholding within ROI
    → Find contours → edge pixels
    → Boundary confidence = 0.5 + variance_score + edge_score
  → Cache masks for reuse

Stage 3: Depth Estimation
  SimpleDepthEstimator: linear gradient fill (cached by dimensions)
  MiDaSDepthEstimator (ONNX):
    → Resize to 256×256
    → ImageNet normalization (mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])
    → ONNX inference → (1, 256, 256) inverse-depth
    → Resize back to original
    → Normalize to 0.5m - 10m range

Stage 4: Spatial Fusion
  For each detection:
    → Get depth at bbox center → distance_m
    → Calculate direction from center_x (8 directions, 70° FOV)
    → Assign priority (CRITICAL<1m, NEAR_HAZARD<2m, FAR_HAZARD<5m, SAFE)
    → Categorize size (SMALL/MEDIUM/LARGE/VERY_LARGE)
    → Generate action recommendation
  → Create ObstacleRecords

Stage 5: Navigation Output
  → Short TTS cue: "Person 1.2m ahead" 
  → Detailed description with all obstacles
  → Telemetry data
  → has_critical_obstacle flag
```

---

## Key Design Patterns

### 1. Resilience Pattern Stack
```
Circuit Breaker (CLOSED → OPEN after N failures → HALF_OPEN after timeout → CLOSED on success)
  └── Retry Policy (exponential backoff with jitter)
    └── Timeout Config (per-service configurable)
      └── Error Classifier (transient vs permanent → decides retry)
        └── Degradation Coordinator (graceful fallback ordering)
          └── Health Registry (component status tracking)
```

### 2. STT/TTS Failover Chains
```
STT: Deepgram (primary) → Whisper local (fallback)
TTS: ElevenLabs (primary) → Edge TTS free (fallback)
```

### 3. Tool Router Pattern
```
User query → classify_query(text) → QueryType
  → ToolRegistry.get_for_type(type) → ToolEntry
  → dispatch(tool_name, userdata) → DispatchResult
  → _failsafe_for_type(type) (on error)

Classification priority: QR/AR → OCR → Search → Spatial → Visual → General
```

### 4. Config Cascade
```
config.yaml (base defaults)
  → {environment}.yaml (overrides)
    → Environment variables (highest priority)
      → Runtime overrides (PERCEPTION_* prefix)
```

### 5. Consent-Gated Features
```
Face Recognition:
  → _load_face_consent() from data/face_consent.json
  → _is_face_consent_granted(identity_id)
  → API returns 403 if not consented
  → face_forget_all() → purges embeddings + revokes consent

Memory:
  → memory_consent_required config flag
  → Privacy controls module manages retention policies
```

### 6. Frame Freshness Enforcement
```
Every on_message():
  → Flush all cached perception/spatial state
  → Next tool call gets fresh camera frame
  → check_frame_freshness(max_age=500ms)
  → Stale frame? Return error message instead of stale data
```

---

## Security & Privacy

### PII Scrubbing (shared/logging/logging_config.py)
- Regex patterns for: API keys, Bearer tokens, emails, phone numbers, SSNs, credit cards, IPs (private), passwords
- Applied as logging filter — all log output scrubbed automatically

### Encryption (shared/utils/encryption.py)
- Fernet symmetric encryption (AES-128-CBC)
- PBKDF2 key derivation (480,000 iterations, SHA-256)
- Legacy mode: SHA-256 hash for backward compatibility
- Used for: FAISS indexes, face embeddings, memory metadata

### Production Security (configs/production.yaml)
- `enforce_https: true`, `require_auth: true`
- Rate limiting, DDoS protection
- Strict CORS, CSP headers
- Circuit breakers enabled

---

## Dependency Graph (Key Packages)

```
livekit-agents (real-time voice)
├── livekit-plugins-deepgram (STT)
├── livekit-plugins-elevenlabs (TTS)
├── livekit-plugins-openai (LLM interface)
└── livekit-plugins-silero (VAD)

onnxruntime (YOLO, MiDaS inference)
opencv-python (image processing, segmentation)
Pillow (image handling)
numpy (array operations)
faiss-cpu (vector similarity search)
sentence-transformers (text embeddings)
cryptography (Fernet encryption)
fastapi + uvicorn (REST API)
pydantic (data validation)
easyocr / pytesseract (OCR)
pyzbar (QR decoding)
httpx (async HTTP)
python-dotenv (.env loading)
PyYAML (config loading)
```

---

## Performance Optimization Techniques

1. **`__slots__`** on hot-path classes (MockObjectDetector, EdgeAwareSegmenter, SimpleDepthEstimator, VisualProcessor)
2. **Pre-allocated numpy arrays** — cached depth maps, mask buffers
3. **Aggressive image downscaling** — 480×360 for vision, 240×180 for spatial, 160×120 for segmentation
4. **Persistent VideoStream** — single stream reused across frame captures
5. **Rate limiting** — 300ms cooldown between spatial calls
6. **Cached masks** — segmentation reuses previous results when detection count matches
7. **Lazy initialization** — spatial processor created on first use
8. **GC after frame** — `gc.collect()` after each frame processing
9. **BILINEAR resize** — 2-3x faster than LANCZOS with acceptable quality
10. **Greedy NMS** — simple O(n²) NMS capped at 25 detections
