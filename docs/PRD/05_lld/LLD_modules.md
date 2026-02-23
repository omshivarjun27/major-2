---
title: "Low Level Design — Module Specifications"
version: 1.0.0
date: 2026-02-22T14:37:47Z
architecture_mode: hybrid_cloud_local_gpu
---

# Module Specifications

### FastAPI REST Server
- **Layer**: Interface
- **File**: apps/api/server.py
- **Description**: Primary HTTP interface for configuration, data management, and system debugging.
- **Public Interfaces**: 30+ endpoints including `/health`, `/memory/*`, `/qr/*`, and `/debug/*`.
- **Internal Methods**: `app.startup()`, `app.shutdown()`, `verify_token()`.
- **Input Contracts**: JSON payloads (MemoryStoreRequest, MemoryQueryRequest, PerceptionFrameRequest).
- **Output Contracts**: JSON responses (MemoryStoreResponse, PerceptionFrameResponse).
- **Error Handling**: Standard HTTP 4xx/5xx responses; Pydantic validation error mapping.
- **Retry Strategy**: N/A (Server-side).
- **GPU Required**: No
- **Blocking or Async**: Async

### LiveKit WebRTC Agent
- **Layer**: Interface
- **File**: apps/realtime/agent.py
- **Description**: Real-time voice/vision agent handling WebRTC streams and tool dispatch.
- **Public Interfaces**: LiveKit job context entry point; function tools (`look_at_camera`, `search_internet`).
- **Internal Methods**: `entrypoint()`, `AllyVisionAgent.__init__()`, `on_speech_recognized()`.
- **Input Contracts**: Audio/Video WebRTC tracks; transcript strings from STT.
- **Output Contracts**: Audio WebRTC tracks (speech).
- **Error Handling**: Graceful session termination; tool-level try/except with speech feedback.
- **Retry Strategy**: WebRTC-level automatic reconnection.
- **GPU Required**: No
- **Blocking or Async**: Async

### FrameOrchestrator
- **Layer**: Application
- **File**: application/frame_processing/frame_orchestrator.py
- **Description**: Coordinates per-frame perception, fusion, and scene graph generation.
- **Public Interfaces**: `process_frame(frame)`.
- **Internal Methods**: `_dispatch_workers()`, `_assemble_results()`, `_build_scene_graph()`.
- **Input Contracts**: `TimestampedFrame`.
- **Output Contracts**: `FusedFrameResult`.
- **Error Handling**: Skips stale frames; uses default/empty results for failed worker tasks.
- **Retry Strategy**: N/A (Internal pipeline).
- **GPU Required**: No
- **Blocking or Async**: Async (orchestrates ThreadPool tasks)

### PerceptionWorkerPool
- **Layer**: Application
- **File**: application/pipelines/perception_pool.py
- **Description**: Dedicated thread pool for executing vision and text inference tasks.
- **Public Interfaces**: `submit_task(func, *args)`.
- **Internal Methods**: `__init__()`, `shutdown()`.
- **Input Contracts**: Image arrays, task functions.
- **Output Contracts**: Task-specific results (List[Detection], DepthMap, etc.).
- **Error Handling**: Captures worker exceptions; returns `PerceptionError` markers.
- **Retry Strategy**: N/A (Task-level).
- **GPU Required**: Yes (indirectly through workers; ~3.1GB total)
- **Blocking or Async**: ThreadPool

### WorkerPool
- **Layer**: Application
- **File**: application/pipelines/worker_pool.py
- **Description**: General-purpose thread pool for offloading non-vision CPU-bound tasks.
- **Public Interfaces**: `run_in_thread(coro)`.
- **Internal Methods**: `_execute()`.
- **Input Contracts**: Callables or coroutines.
- **Output Contracts**: Task return values.
- **Error Handling**: Logs failures; propagates exceptions to callers.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: ThreadPool

### LiveFrameManager
- **Layer**: Application
- **File**: application/frame_processing/live_frame_manager.py
- **Description**: Buffer management for live video frames with freshness control.
- **Public Interfaces**: `push_frame(frame)`, `get_latest()`.
- **Internal Methods**: `_evict_stale()`.
- **Input Contracts**: WebRTC `VideoFrame`.
- **Output Contracts**: `TimestampedFrame`.
- **Error Handling**: Drops frames if deque is full (maxlen enforced).
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync (thread-safe deque)

### Debouncer
- **Layer**: Application
- **File**: application/pipelines/debouncer.py
- **Description**: Suppresses redundant navigation cues and repetitive responses.
- **Public Interfaces**: `should_emit(cue_id, content)`.
- **Internal Methods**: `_cleanup_old_keys()`.
- **Input Contracts**: Cue identifier, text content.
- **Output Contracts**: Boolean (emit/suppress).
- **Error Handling**: N/A (Memory-based).
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync

### StreamingTTSCoordinator
- **Layer**: Application
- **File**: application/pipelines/tts_coordinator.py (inferred from inventory/HLD)
- **Description**: Buffers sentences and manages concurrent TTS synthesis requests.
- **Public Interfaces**: `speak(text)`.
- **Internal Methods**: `_split_sentences()`, `_dispatch_tts()`.
- **Input Contracts**: Response text (str).
- **Output Contracts**: Audio chunk stream.
- **Error Handling**: Falls back to local TTS on cloud failure.
- **Retry Strategy**: None documented.
- **GPU Required**: No
- **Blocking or Async**: Async

### Watchdog
- **Layer**: Application
- **File**: application/pipelines/watchdog.py
- **Description**: Monitors system health and pipeline activity to prevent stalls.
- **Public Interfaces**: `heartbeat(module_id)`, `start()`.
- **Internal Methods**: `_check_stalls()`, `_trigger_recovery()`.
- **Input Contracts**: Heartbeat signals.
- **Output Contracts**: Health status; restart triggers.
- **Error Handling**: Self-healing via process/task restart.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Async

### PipelineMonitor
- **Layer**: Application
- **File**: application/pipelines/pipeline_monitor.py
- **Description**: Metrics collector for latency, VRAM (proposed), and success rates.
- **Public Interfaces**: `log_latency(module, value)`, `get_report()`.
- **Internal Methods**: `_aggregate_stats()`.
- **Input Contracts**: Floating point latency values.
- **Output Contracts**: Metric reports (Dict).
- **Error Handling**: Logs failures to report metrics.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Async

### PerceptionPipeline
- **Layer**: Domain
- **File**: core/vqa/perception.py
- **Description**: Orchestrates YOLO detection, MiDaS depth, and segmentation.
- **Public Interfaces**: `run(image)`.
- **Internal Methods**: `_to_numpy()`, `_run_inference_parallel()`.
- **Input Contracts**: Image (numpy/PIL).
- **Output Contracts**: `PerceptionResult`.
- **Error Handling**: Graceful degradation to Mock/Simple estimators.
- **Retry Strategy**: N/A.
- **GPU Required**: Yes (~800MB for vision models)
- **Blocking or Async**: Sync (run inside thread pool)

### SceneGraphBuilder
- **Layer**: Domain
- **File**: core/vqa/scene_graph.py
- **Description**: Constructs a graph of spatial relationships between detected objects.
- **Public Interfaces**: `build(perception_result)`.
- **Internal Methods**: `_calculate_direction()`, `_calculate_priority()`, `_infer_relations()`.
- **Input Contracts**: `PerceptionResult`.
- **Output Contracts**: `SceneGraph`.
- **Error Handling**: Estimates missing depth from Y-position.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync

### SpatialFuser
- **Layer**: Domain
- **File**: core/vqa/spatial_fuser.py
- **Description**: Temporal filtering and obstacle tracking using EMA smoothing.
- **Public Interfaces**: `fuse(perception_result)`.
- **Internal Methods**: `_match_detections()`, `_update_tracks()`.
- **Input Contracts**: `PerceptionResult`.
- **Output Contracts**: `FusedResult`.
- **Error Handling**: Evicts stale tracks; handles unmatched detections as new tracks.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync

### VQAReasoner
- **Layer**: Domain
- **File**: core/vqa/vqa_reasoner.py
- **Description**: Reasons about the scene graph to answer natural language questions.
- **Public Interfaces**: `ask(question, scene_graph)`.
- **Internal Methods**: `_build_vqa_prompt()`.
- **Input Contracts**: Question string, `SceneGraph`.
- **Output Contracts**: Natural language answer.
- **Error Handling**: Returns `StubLLMClient` response on reasoning failure.
- **Retry Strategy**: None documented.
- **GPU Required**: No
- **Blocking or Async**: Async (via OllamaHandler)

### MicroNavFormatter
- **Layer**: Domain
- **File**: core/vqa/vqa_reasoner.py
- **Description**: Formats fused obstacle data into concise navigation cues.
- **Public Interfaces**: `format(fused_result)`.
- **Internal Methods**: `_format_direction()`, `_format_distance()`.
- **Input Contracts**: `FusedResult`.
- **Output Contracts**: TTS-ready cue string (e.g., "Chair 1.5m left").
- **Error Handling**: Prefixes uncertain results with "Possible:".
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync

### MemoryIngester
- **Layer**: Domain
- **File**: core/memory/ingest.py
- **Description**: Processes multimodal input for storage in the vector memory.
- **Public Interfaces**: `ingest(request)`.
- **Internal Methods**: `_generate_summary()`, `_store_vector()`.
- **Input Contracts**: `MemoryStoreRequest`.
- **Output Contracts**: Memory ID.
- **Error Handling**: Checks user consent before ingestion.
- **Retry Strategy**: N/A.
- **GPU Required**: Yes (for embedding)
- **Blocking or Async**: Async

### OllamaEmbedder
- **Layer**: Domain
- **File**: core/memory/embeddings.py
- **Description**: Generates 384-dimensional text embeddings using local qwen3-embedding:4b.
- **Public Interfaces**: `embed_text(text)`.
- **Internal Methods**: `_call_ollama_api()`.
- **Input Contracts**: Text string.
- **Output Contracts**: `np.ndarray` (384-dim).
- **Error Handling**: ISSUE-022: Sync HTTP calls may block; needs run_in_executor.
- **Retry Strategy**: None documented.
- **GPU Required**: Yes (~2GB VRAM)
- **Blocking or Async**: Sync (blocking HTTP)

### FAISSIndexer
- **Layer**: Domain
- **File**: core/memory/indexer.py
- **Description**: Local vector database using FAISS IndexFlatL2.
- **Public Interfaces**: `add(id, vector, metadata)`, `search(query_vector, k)`.
- **Internal Methods**: `_save()`, `_load()`.
- **Input Contracts**: ID string, numpy vector, `IndexMetadata`.
- **Output Contracts**: Search result list with scores.
- **Error Handling**: Thread-safe access via `threading.RLock()`.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync (blocks during disk I/O)

### MemoryRetriever
- **Layer**: Domain
- **File**: core/memory/retriever.py
- **Description**: High-level retrieval logic for the RAG system.
- **Public Interfaces**: `search(query_request)`.
- **Internal Methods**: `_filter_by_time()`.
- **Input Contracts**: `MemorySearchRequest`.
- **Output Contracts**: `MemorySearchResponse`.
- **Error Handling**: Returns empty results if index is unavailable.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Async

### RAGReasoner
- **Layer**: Domain
- **File**: core/memory/rag_reasoner.py
- **Description**: Synthesizes retrieved memories into natural language answers.
- **Public Interfaces**: `reason(query, memories)`.
- **Internal Methods**: `_build_context()`, `_try_template_answer()`.
- **Input Contracts**: Query string, list of `MemoryHit`.
- **Output Contracts**: Answer + citations.
- **Error Handling**: Uses `RAG_SYSTEM_PROMPT` to constrain LLM to provided context.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Async (via LLMClient)

### LLMClient
- **Layer**: Domain
- **File**: core/memory/llm_client.py
- **Description**: Unified client for cloud-based LLM reasoning.
- **Public Interfaces**: `generate(prompt)`.
- **Internal Methods**: `_call_api()`.
- **Input Contracts**: Prompt string.
- **Output Contracts**: `LLMResponse`.
- **Error Handling**: Falls back to `StubLLMClient` on API failure.
- **Retry Strategy**: None documented.
- **GPU Required**: No
- **Blocking or Async**: Async

### OCRPipeline
- **Layer**: Domain
- **File**: core/ocr/engine.py
- **Description**: Tiered OCR engine with GPU-accelerated and CPU-only backends.
- **Public Interfaces**: `read(image)`.
- **Internal Methods**: `_try_easyocr()`, `_try_tesseract()`, `_try_mser()`.
- **Input Contracts**: Image array.
- **Output Contracts**: OCR text result.
- **Error Handling**: Fallback cascade: EasyOCR -> Tesseract -> MSER -> Error.
- **Retry Strategy**: N/A.
- **GPU Required**: Yes (~500MB for EasyOCR)
- **Blocking or Async**: Sync (run inside thread pool)

### QRScanner
- **Layer**: Domain
- **File**: core/qr/qr_scanner.py
- **Description**: Detects and decodes QR codes from camera frames.
- **Public Interfaces**: `scan(image)`.
- **Internal Methods**: `_scan_pyzbar()`, `_scan_cv2()`, `preprocess_for_qr()`.
- **Input Contracts**: Image (PIL).
- **Output Contracts**: List of `QRDetection`.
- **Error Handling**: Multi-stage retry with preprocessing and scaling.
- **Retry Strategy**: Internal 3-stage retry (Raw, Preprocessed, Multi-scale).
- **GPU Required**: No
- **Blocking or Async**: Sync

### QRDecoder
- **Layer**: Domain
- **File**: core/qr/qr_decoder.py
- **Description**: Classifies and interprets raw QR payload data.
- **Public Interfaces**: `decode(raw_data)`.
- **Internal Methods**: `_classify_payload()`.
- **Input Contracts**: Raw QR string.
- **Output Contracts**: Structured classified content.
- **Error Handling**: Returns "Plain Text" classification for unknown formats.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync

### CacheManager
- **Layer**: Domain
- **File**: core/qr/cache_manager.py
- **Description**: Offline-first file-based cache for QR scan results.
- **Public Interfaces**: `get(payload)`, `put(payload, result)`.
- **Internal Methods**: `_load_cache()`, `_save_cache()`.
- **Input Contracts**: Payload string, result dictionary.
- **Output Contracts**: Cached result or None.
- **Error Handling**: Configurable TTL (default 86400s).
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync

### BrailleOCR
- **Layer**: Domain
- **File**: core/braille/braille_ocr.py (inferred from inventory/README)
- **Description**: Specialized OCR for converting braille dot patterns to text.
- **Public Interfaces**: `read(image)`.
- **Internal Methods**: `_segment_dots()`, `_classify_grid()`.
- **Input Contracts**: Image array.
- **Output Contracts**: Translated text.
- **Error Handling**: Checks brightness/contrast before processing.
- **Retry Strategy**: N/A.
- **GPU Required**: Yes (for classification)
- **Blocking or Async**: Sync (run inside thread pool)

### FaceDetector
- **Layer**: Domain
- **File**: core/face/face_detector.py (inferred from inventory/README)
- **Description**: Detects faces and generates embeddings for identity tracking.
- **Public Interfaces**: `detect(image)`.
- **Internal Methods**: `_generate_embeddings()`.
- **Input Contracts**: Image array.
- **Output Contracts**: Face bounding boxes and embeddings.
- **Error Handling**: Checks user consent (data/face_consent.json).
- **Retry Strategy**: N/A.
- **GPU Required**: Yes (~300MB VRAM)
- **Blocking or Async**: Sync (run inside thread pool)

### VoiceRouter
- **Layer**: Domain
- **File**: core/speech/voice_router.py
- **Description**: Regex-based intent classifier for voice commands.
- **Public Interfaces**: `route(query)`.
- **Internal Methods**: `_detect_intent()`, `_preprocess_query()`.
- **Input Contracts**: Transcribed text.
- **Output Contracts**: `RouteResult`.
- **Error Handling**: Falls back to IntentType.GENERAL_CHAT on mismatch.
- **Retry Strategy**: N/A.
- **GPU Required**: No
- **Blocking or Async**: Sync

### OllamaHandler
- **Layer**: Infrastructure
- **File**: infrastructure/llm/ollama/handler.py
- **Description**: Adapter for local and cloud-based vision/language models.
- **Public Interfaces**: `generate(prompt, image)`.
- **Internal Methods**: `_call_openai_api()`.
- **Input Contracts**: Prompt string, optional image.
- **Output Contracts**: LLM text response.
- **Error Handling**: Uses `asyncio.wait_for()` for timeout management.
- **Retry Strategy**: None implemented.
- **GPU Required**: No (Cloud integration)
- **Blocking or Async**: Async

### InternetSearch
- **Layer**: Infrastructure
- **File**: infrastructure/llm/internet_search.py
- **Description**: Web search adapter using the DuckDuckGo engine.
- **Public Interfaces**: `search(query)`.
- **Internal Methods**: `_parse_results()`.
- **Input Contracts**: Query string.
- **Output Contracts**: List of search result snippets.
- **Error Handling**: Gracefully returns "Search unavailable" on failure.
- **Retry Strategy**: None documented.
- **GPU Required**: No
- **Blocking or Async**: Async
