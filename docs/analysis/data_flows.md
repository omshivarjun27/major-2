# Data Flow Analysis

## Overview

This document traces five primary data flows through the Voice & Vision Assistant,
identifying exact file paths, function signatures, data transformations, and error
handling gaps at each stage.

---

## Flow 1: Voice → STT → Intent → LLM → TTS → Audio

**Purpose**: User speaks a question; the system transcribes, routes, reasons, and
speaks back an answer.

### Pipeline

| # | Stage | File | Function / Class | Input | Output |
|---|-------|------|-------------------|-------|--------|
| 1 | Audio capture | LiveKit SDK (external) | WebRTC track → PCM frames | Microphone audio | Raw audio frames |
| 2 | Speech-to-text | `infrastructure/speech/` + LiveKit `deepgram` plugin | `deepgram.STT()` | PCM audio stream | Transcribed text (`str`) |
| 3 | Intent routing | `core/speech/voice_router.py` | `VoiceRouter.route(query)` | Transcribed text | `RouteResult(intent, handler, confidence, mode)` |
| 4 | Handler dispatch | `apps/realtime/agent.py` | `AllyVisionAgent` function tools (e.g., `look_at_camera`, `search_internet`) | `RouteResult` + optional camera frame | Handler-specific result (`str`) |
| 5 | LLM reasoning | `infrastructure/llm/ollama/handler.py` | `OllamaHandler.generate()` via OpenAI-compat API | Prompt + optional image | LLM text response |
| 6 | Text-to-speech | LiveKit `elevenlabs` plugin / local TTS | `elevenlabs.TTS()` | Answer text | Audio stream |
| 7 | Audio playback | LiveKit SDK (external) | WebRTC audio track | Audio stream | Speaker output |

### Data Transformations

1. **PCM → text**: Deepgram STT converts raw audio to transcript with timestamps and confidence.
2. **Text → RouteResult**: `VoiceRouter._detect_intent()` applies compiled regex patterns with precedence ordering. Confidence = `0.5 + (match_len / query_len) * 0.5 + precedence_bonus`. Filler words removed in `_preprocess_query()`.
3. **RouteResult → handler string**: `_select_handler()` maps `IntentType` enum to handler name (`"vqa"`, `"spatial"`, `"priority"`, `"qr"`, `"llm"`, `"command"`).
4. **Handler → LLM prompt**: Each handler constructs a domain-specific prompt (e.g., `PromptTemplates.SPATIAL` for spatial queries, `PromptTemplates.IDENTIFY` for object identification).
5. **LLM response → TTS**: Raw LLM text truncated to concise form (<12 words for critical alerts).

### Error Handling

- **STT failure**: Deepgram plugin handles reconnection internally; no explicit fallback STT in codebase.
- **Intent miss**: Falls back to `IntentType.GENERAL_CHAT` with `handler="llm"` (confidence 0.3).
- **LLM timeout**: `OllamaHandler` uses `asyncio.wait_for()` but timeout value is not always configured.
- **TTS failure**: System prompt specifies fallback to local TTS with `meta.tts_fallback=true`, but implementation relies on LiveKit plugin behavior.

### Gap Analysis

- ❌ No explicit fallback STT engine (VOSK mentioned in system prompt but not implemented).
- ❌ No TTS audio caching by text fingerprint (specified in system prompt, not implemented).
- ⚠️ Route confidence thresholds may produce ambiguous routing when multiple intents match similarly.

---

## Flow 2: Camera Frame → Vision/OCR → Explanation → Speech

**Purpose**: Camera captures a frame; the system detects objects, estimates depth,
builds a scene graph, reasons about it, and speaks the result.

### Pipeline

| # | Stage | File | Function / Class | Input | Output |
|---|-------|------|-------------------|-------|--------|
| 1 | Frame capture | `application/frame_processing/live_frame_manager.py` | `LiveFrameManager` → `TimestampedFrame` | WebRTC video track | `TimestampedFrame(frame, ts, frame_id)` |
| 2 | Freshness check | `application/frame_processing/freshness.py` | `is_frame_fresh(frame, max_age)` | `TimestampedFrame` | `bool` (stale frames rejected) |
| 3 | Object detection | `core/vqa/perception.py` | `PerceptionPipeline.run(image)` | numpy array / PIL Image | `PerceptionResult(detections, masks, depth_map, ...)` |
| 3a | Detection | `core/vqa/perception.py` | `MockObjectDetector.detect()` or `YOLODetector.detect()` | Image | `List[Detection]` |
| 3b | Segmentation | `core/vqa/perception.py` | `EdgeAwareSegmenter.segment()` or `MockSegmenter.segment()` | Image + detections | `List[SegmentationMask]` |
| 3c | Depth estimation | `core/vqa/perception.py` | `MiDaSDepthEstimator.estimate()` or `SimpleDepthEstimator.estimate()` | Image | `DepthMap` |
| 4 | Scene graph | `core/vqa/scene_graph.py` | `SceneGraphBuilder.build(perception)` | `PerceptionResult` | `SceneGraph(nodes, obstacles, summary)` |
| 5 | Spatial fusion | `core/vqa/spatial_fuser.py` | `SpatialFuser.fuse(perception)` | `PerceptionResult` | `FusedResult(obstacles, tracks, ...)` |
| 6 | Navigation format | `core/vqa/vqa_reasoner.py` | `MicroNavFormatter.format(fused, scene_graph)` | `FusedResult` + `SceneGraph` | Short TTS cue (`str`) |
| 7 | VQA reasoning | `core/vqa/vqa_reasoner.py` | `VQAReasoner` (via Ollama qwen3-vl) | Scene graph JSON + question | Natural language answer |
| 8 | Frame orchestration | `application/frame_processing/frame_orchestrator.py` | `FrameOrchestrator.process_frame()` | `TimestampedFrame` + worker functions | `FusedFrameResult` |
| 9 | TTS output | LiveKit `elevenlabs` plugin | `elevenlabs.TTS()` | Answer text | Audio stream |

### Data Transformations

1. **VideoFrame → numpy**: `_to_numpy()` in `perception.py` handles LiveKit VideoFrame, PIL Image, and raw numpy.
2. **numpy → Detection[]**: Detector returns `Detection(id, class_name, confidence, BoundingBox)`.
3. **Detection[] + Image → SegmentationMask[]**: Each mask has `detection_id`, binary `mask` array, `boundary_confidence`.
4. **Image → DepthMap**: Depth estimator returns `DepthMap(depth_array, min_depth, max_depth, is_metric)`.
5. **PerceptionResult → SceneGraph**: Builder calculates direction, priority, size category per detection using depth and bbox center. Infers spatial relations (left_of, near, in_front_of).
6. **PerceptionResult → FusedResult**: SpatialFuser applies temporal filtering (EMA smoothing), IOU-based tracking, confidence weighting.
7. **FusedResult → TTS string**: MicroNavFormatter produces concise phrases like `"2 objects. Chair 1.5m left. Step right."`.

### Error Handling

- ✅ `_to_numpy()` falls back to `np.zeros((480,640,3))` on any conversion error.
- ✅ `DepthMap.get_region_depth()` returns `(inf, inf, inf)` when depth_array is None.
- ✅ Invalid depth (>100 or inf) → estimated from y-position in `SceneGraphBuilder.build()`.
- ✅ `MiDaSDepthEstimator` falls back to `SimpleDepthEstimator` on load failure.
- ⚠️ `YOLODetector` silently falls through to `MockObjectDetector` — no runtime alert.

---

## Flow 3: QR Scan → Content Classification → Speech

**Purpose**: Camera frame is scanned for QR/barcode content; decoded data is
classified by type and spoken as a contextual message.

### Pipeline

| # | Stage | File | Function / Class | Input | Output |
|---|-------|------|-------------------|-------|--------|
| 1 | Intent detection | `core/speech/voice_router.py` | `VoiceRouter.route()` with `QR_PATTERNS` | Voice query (e.g., "scan QR") | `RouteResult(intent=QR_SCAN, handler="qr")` |
| 2 | Frame acquisition | `application/frame_processing/live_frame_manager.py` | `LiveFrameManager.get_latest()` | N/A | `TimestampedFrame` |
| 3 | QR detection | `core/qr/qr_scanner.py` | `QRScanner.scan(image)` | PIL Image | `List[QRDetection(raw_data, bbox, confidence, format_type)]` |
| 3a | Primary scan | `core/qr/qr_scanner.py` | `_scan_pyzbar()` or `_scan_cv2()` | PIL Image | `List[QRDetection]` |
| 3b | Preprocessing retry | `core/qr/qr_scanner.py` | `preprocess_for_qr()` → rescan | Contrast-stretched + threshold image | `List[QRDetection]` |
| 3c | Multi-scale retry | `core/qr/qr_scanner.py` | Scale at 75% and 50% → rescan | Resized + preprocessed images | `List[QRDetection]` |
| 4 | Content decode | `core/qr/qr_decoder.py` | `QRDecoder.decode(raw_data)` | Raw QR string | Classified content (URL, location, contact, etc.) |
| 5 | AR tag check | `core/qr/ar_tag_handler.py` | `ARTagHandler` | Frame | ArUco marker detections |
| 6 | Cache lookup | `core/qr/cache_manager.py` | `CacheManager.get(payload)` / `.put(payload, result)` | QR payload string | Cached result or None |
| 7 | Contextual message | `apps/realtime/agent.py` | QR handler in agent function tools | Classified QR content | Spoken message (e.g., "Bus stop 145 — Route 14 to Downtown") |
| 8 | TTS output | LiveKit plugin | `elevenlabs.TTS()` | Message text | Audio |

### Data Transformations

1. **PIL Image → QRDetection[]**: `pyzbar.decode()` returns decoded objects; mapped to `QRDetection(raw_data=utf8_string, bbox=(x,y,w,h), format_type=obj.type)`.
2. **Image preprocessing**: Grayscale → percentile contrast stretch (2nd-98th) → adaptive Gaussian threshold → morphological open (3×3 kernel).
3. **Raw data → classified content**: `QRDecoder` classifies payload as URL, location, transport, product, contact, WiFi, or plain text.
4. **Classified content → spoken message**: Agent transforms structured data into natural language contextual message.

### Error Handling

- ✅ Scanner returns `[]` (not exception) when no QR found.
- ✅ Multi-stage retry: raw → preprocessed → multi-scale (75%, 50%).
- ✅ Edge density filter (`QRScanner.edge_density()`) rejects low-density crops before expensive decode.
- ✅ `is_ready` property gates scan calls when no backend available.
- ⚠️ Cache TTL enforcement is file-based JSON — no in-memory expiry; stale reads possible on clock skew.
- ⚠️ No payload sanitization for malicious URLs (system prompt specifies "no automatic click-through" but implementation is in decoder, not scanner).

---

## Flow 4: Memory Store → RAG Retrieval → Response

**Purpose**: User's experiences are stored as vector-indexed memories; later
queries retrieve relevant memories and use LLM to synthesize answers.

### Pipeline — Ingestion

| # | Stage | File | Function / Class | Input | Output |
|---|-------|------|-------------------|-------|--------|
| 1 | Consent check | `core/memory/api_endpoints.py` | Consent middleware | Request | Allow/deny |
| 2 | Ingestion request | `core/memory/api_schema.py` | `MemoryStoreRequest` (Pydantic) | JSON body (transcript, scene_graph, image_base64, audio_base64) | Validated request |
| 3 | Summary generation | `core/memory/ingest.py` | `MemoryIngester.ingest()` | Request + LLM client | Summary text |
| 4 | Embedding | `core/memory/embeddings.py` | `OllamaEmbedder.embed_text()` | Summary text | `np.ndarray` (384-dim vector) |
| 5 | FAISS indexing | `core/memory/indexer.py` | `FAISSIndexer.add(id, embedding, metadata)` | Vector + `IndexMetadata` | Vector index position |
| 6 | Persistence | `core/memory/indexer.py` | `FAISSIndexer._save()` | Index + metadata | Disk files (`index.faiss`, `metadata.json`) |

### Pipeline — Query (RAG)

| # | Stage | File | Function / Class | Input | Output |
|---|-------|------|-------------------|-------|--------|
| 1 | Query request | `core/memory/api_schema.py` | `MemoryQueryRequest` (Pydantic) | JSON (query, mode, k, time_window_days) | Validated request |
| 2 | Query embedding | `core/memory/embeddings.py` | `OllamaEmbedder.embed_text()` | Query text | Query vector (384-dim) |
| 3 | Vector search | `core/memory/indexer.py` | `FAISSIndexer.search(query_vec, k)` | Query vector + k | `List[SearchResult(id, score, metadata)]` |
| 4 | Retrieval | `core/memory/retriever.py` | `MemoryRetriever.search()` | `MemorySearchRequest` | `MemorySearchResponse(results: List[MemoryHit])` |
| 5 | Context building | `core/memory/rag_reasoner.py` | `RAGReasoner._build_context(memories)` | `List[MemoryHit]` | Context string (formatted memories) |
| 6a | Template answer | `core/memory/rag_reasoner.py` | `RAGReasoner._try_template_answer()` | Query + memories | `(answer, confidence)` or `(None, 0)` |
| 6b | LLM reasoning | `core/memory/rag_reasoner.py` | `RAGReasoner._llm_reason()` | Prompt with context | `(answer, confidence, reasoning)` |
| 7 | Response | `core/memory/api_schema.py` | `MemoryQueryResponse` | Answer + citations + metrics | JSON response |

### LLM Backend

| Provider | Backend | File | Class | Notes |
|----------|---------|------|-------|-------|
| qwen3.5:cloud | Ollama cloud runtime | `core/memory/llm_client.py` | `OllamaClient` | Single provider, async HTTP calls |
| Stub | Stub fallback | `core/memory/llm_client.py` | `StubLLMClient` | All backends offline |

### Data Transformations

1. **Multimodal input → summary**: Ingester extracts text from transcript/scene_graph, generates 1-2 line summary.
2. **Summary → embedding**: Ollama `qwen3-embedding:4b` model produces 384-dim float32 vector.
3. **Embedding → FAISS index**: `IndexFlatL2` exact search; vectors stored contiguously.
4. **Query → top-k memories**: L2 distance search returns `k` closest vectors with metadata.
5. **Memories → context string**: Each memory formatted as `[Memory N] (timestamp): summary\n  Objects seen: ...`.
6. **Template matching**: Regex patterns for location/what/have queries produce direct answers from top memory.
7. **LLM reasoning**: `RAG_SYSTEM_PROMPT` constrains LLM to use ONLY provided context, cite timestamps.

### Error Handling

- ✅ `FAISSIndexer` uses `threading.RLock()` for thread safety.
- ✅ `StubLLMClient` ensures system never crashes on missing LLM.
- ✅ Eviction policy (`time` or `lru`) enforces `max_vectors` limit (default 5000).
- ✅ Fuzzy matching for common object name variations (keys→keychain, phone→smartphone).
- ⚠️ FAISS index is `IndexFlatL2` — O(n) scan; no approximate index for large datasets.
- ⚠️ No encryption-at-rest for FAISS index despite `_get_enc` import (import available but not wired in `add()`).
- ⚠️ `bare except:` in `_try_template_answer()` timestamp parsing (silent failure).

---

## Flow 5: Spatial Perception → Navigation Cue → TTS

**Purpose**: Real-time obstacle detection and distance estimation produce
concise, priority-sorted navigation warnings for the blind user.

### Pipeline

| # | Stage | File | Function / Class | Input | Output |
|---|-------|------|-------------------|-------|--------|
| 1 | Frame acquisition | `application/frame_processing/live_frame_manager.py` | `LiveFrameManager.get_latest()` | WebRTC video track | `TimestampedFrame` |
| 2 | Object detection | `core/vqa/perception.py` | `PerceptionPipeline.run()` → `detector.detect(image)` | numpy array | `List[Detection]` |
| 3 | Edge-aware segmentation | `core/vqa/perception.py` | `segmenter.segment(image, detections)` | Image + detections | `List[SegmentationMask]` |
| 4 | Depth estimation | `core/vqa/perception.py` | `depth_estimator.estimate(image)` | Image | `DepthMap(depth_array, min, max, is_metric)` |
| 5 | Perception assembly | `core/vqa/perception.py` | `PerceptionPipeline.run()` | Detections + masks + depth | `PerceptionResult` |
| 6 | Scene graph build | `core/vqa/scene_graph.py` | `SceneGraphBuilder.build(perception)` | `PerceptionResult` | `SceneGraph` with `ObstacleRecord[]` |
| 6a | Direction calc | `core/vqa/scene_graph.py` | `_calculate_direction(center_x)` | Pixel x-coordinate | `(Direction enum, angle_deg)` |
| 6b | Priority calc | `core/vqa/scene_graph.py` | `_calculate_priority(distance)` | Distance (meters) | `Priority enum` |
| 6c | Action generation | `core/vqa/scene_graph.py` | `_generate_action(direction, distance, priority)` | Direction + distance + priority | Action string (e.g., "stop, step right") |
| 7 | Temporal fusion | `core/vqa/spatial_fuser.py` | `SpatialFuser.fuse(perception)` | `PerceptionResult` | `FusedResult(obstacles: List[FusedObstacle])` |
| 7a | Track update | `core/vqa/spatial_fuser.py` | `TemporalFilter.update()` | Detections + depth_map | `List[TrackedObject]` with EMA smoothing |
| 7b | IOU matching | `core/vqa/spatial_fuser.py` | `_match_detections()` | Detections + existing tracks | Matched + unmatched lists |
| 8 | MicroNav format | `core/vqa/vqa_reasoner.py` | `MicroNavFormatter.format(fused_result)` | `FusedResult` | TTS cue (e.g., `"Stop! Chair very close slightly left."`) |
| 9 | Debounce | `apps/realtime/agent.py` | `UserData.should_debounce(cue, distance)` | Cue + distance | `bool` (suppress duplicate) |
| 10 | TTS output | LiveKit plugin | ElevenLabs / local TTS | Cue text | Audio stream |

### Priority Thresholds

| Distance | Priority | TTS Prefix | Action |
|----------|----------|------------|--------|
| < 1.0 m | `CRITICAL` | `"Stop!"` | `"stop and reassess"` or `"stop, step left/right"` |
| 1.0 – 2.0 m | `NEAR_HAZARD` | `"Caution,"` | `"step left/right"` |
| 2.0 – 5.0 m | `FAR_HAZARD` | (none) | `"be aware, step left/right"` |
| > 5.0 m | `SAFE` | (none) | `"safe to proceed"` |

### Data Transformations

1. **Frame → Detections**: YOLO/Mock returns `Detection(id, class_name, confidence, BoundingBox(x1,y1,x2,y2))`.
2. **Bbox + DepthMap → distance_m**: `depth_map.get_region_depth(bbox)` returns `(min, median, max)` within the bbox region.
3. **Pixel center_x → Direction**: `normalized_x = (cx - W/2) / (W/2)`, then `angle = normalized_x * 35°` (assuming 70° FOV), binned into 7 Direction categories.
4. **Detection → TrackedObject**: EMA with `alpha=0.7` on depth and confidence. Velocity estimated from bbox center displacement.
5. **FusedObstacle → TTS phrase**: `"[class] [distance] [direction]"` where distance is formatted as `"very close"`, `"half meter"`, `"1.5m"`, or `"3m"`.
6. **Safety prefix**: If any top-3 obstacle has `is_uncertain=True` (low confidence or high depth variance), prefix with `"Possible: "`.

### Error Handling

- ✅ `DepthMap.get_region_depth()` returns `(inf, inf, inf)` for null depth or empty regions.
- ✅ Invalid depth (>100m) estimated from y-position in scene graph builder.
- ✅ Stale tracks auto-pruned after 0.5s or 3 consecutive misses.
- ✅ Track count capped at `max_tracks=20` with eviction by miss count + confidence.
- ✅ Debounce window (7s default) prevents repetitive identical cues.
- ⚠️ FOV hardcoded at 70° — may not match actual camera hardware.
- ⚠️ `MicroNavFormatter._format_direction()` hardcodes 640px width assumption.
- ⚠️ No haptic feedback channel — all output is audio-only; in noisy environments, critical warnings may be missed.

---

## Cross-Cutting Concerns

### Latency Budget

| Target | Source |
|--------|--------|
| End-to-end per frame: ≤ 250 ms | System prompt |
| Detection + depth: ≤ 250 ms | System prompt |
| TTS first chunk: ≤ 300 ms | System prompt |
| Debounce window: 7 s | `agent.py` UserData default |
| Frame freshness: 500 ms | `FrameOrchestratorConfig.live_frame_max_age_ms` |

### Shared Data Types (canonical source: `shared/schemas/__init__.py`)

All five flows share these types:
- `BoundingBox`, `Detection`, `SegmentationMask`, `DepthMap`, `PerceptionResult`
- `ObstacleRecord`, `NavigationOutput`
- `Priority`, `Direction`, `SizeCategory`, `SpatialRelation` (enums)

### Common Error Patterns

1. **Graceful degradation**: Every pipeline stage has a mock/fallback implementation.
2. **Never crash**: `try/except` with fallback values throughout.
3. **Confidence gating**: Results below 0.3 are logged but not reported to user.
4. **Temporal smoothing**: EMA filtering prevents jitter in spatial outputs.


---

## GPU Acceleration Notes

### Hardware
- **GPU**: NVIDIA RTX 4060 (8GB VRAM)
- **CUDA**: Enabled for all local inference
- **ONNX Runtime**: CUDA Execution Provider for vision models (YOLO, MiDaS)
- **PyTorch CUDA**: Used for embedding inference and face detection

### GPU-Accelerated Pipelines
| Pipeline | GPU Usage | Model |
|----------|-----------|-------|
| Object Detection | ONNX Runtime CUDA EP | YOLO v8n |
| Depth Estimation | ONNX Runtime CUDA EP | MiDaS v2.1 small |
| Segmentation | ONNX Runtime CUDA EP | Edge-aware segmenter |
| Embedding | Torch CUDA (Ollama local) | qwen3-embedding:4b |
| OCR | PyTorch CUDA | EasyOCR |
| Face Detection | PyTorch CUDA | Face detector |

### Memory-Safe Batching
- WorkerPool respects VRAM limits (8GB budget)
- Embedding GPU batching with qwen3-embedding:4b
- Backpressure control prevents OOM on concurrent frame processing
- GPU-aware worker scaling: max concurrent GPU tasks limited by VRAM headroom

### Performance Expectations
- Reduced embedding latency via GPU batching
- Parallel frame processing across detection, depth, and segmentation
- GPU-aware worker scaling in PerceptionWorkerPool