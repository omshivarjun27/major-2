---
title: "Low Level Design — System Architecture"
version: 1.0.0
date: 2026-02-22T14:37:47Z
architecture_mode: hybrid_cloud_local_gpu
related_artifacts:
  - docs/analysis/component_inventory.json
  - docs/analysis/data_flows.md
  - docs/PRD/04_hld/HLD.md
---

# 1. Module Breakdown by Layer

The system is organized into five functional layers, each with specific responsibilities and component sets as defined in the component inventory.

### Interface Layer
- **FastAPI REST Server** (apps/api/server.py): Provides 30+ endpoints for system configuration, memory management, and debugging. Implements Bearer token authentication for sensitive debug routes.
- **LiveKit WebRTC Agent** (apps/realtime/agent.py): Manages real-time audio and video streams. Acts as the primary interaction point for the voice-first assistant.

### Application Layer
- **FrameOrchestrator** (application/frame_processing/frame_orchestrator.py): Orchestrates per-frame fusion by collecting parallel worker results and validating timestamps.
- **LiveFrameManager** (application/frame_processing/live_frame_manager.py): Maintains an in-memory bounded deque for video frames to ensure low-latency access.
- **PerceptionWorkerPool** (application/pipelines/perception_pool.py): ThreadPoolExecutor dedicated to offloading CPU-bound inference tasks from the main event loop.
- **WorkerPool** (application/pipelines/worker_pool.py): Generic async task executor for parallel operations.
- **Debouncer** (application/pipelines/debouncer.py): Prevents redundant processing and audio feedback loops through time-based deduplication.
- **StreamingTTSCoordinator**: Manages sentence buffering for smooth, natural-sounding text-to-speech output.
- **Watchdog** (application/pipelines/watchdog.py): Background task that monitors pipeline health and triggers restarts upon detecting stalls.
- **PipelineMonitor** (application/pipelines/pipeline_monitor.py): Collects and reports metrics across the perception and reasoning pipelines.

### Domain Layer
- **VQA Engine**: Includes the PerceptionPipeline, SceneGraphBuilder, SpatialFuser, VQAReasoner, and MicroNavFormatter for visual understanding.
- **Memory Engine**: Comprises MemoryIngester, OllamaEmbedder, FAISSIndexer, MemoryRetriever, RAGReasoner, and LLMClient for persistent knowledge management.
- **OCR Engine**: A 3-tier fallback pipeline utilizing EasyOCR, Tesseract, and MSER heuristics.
- **QR/AR Engine**: Handles QR scanning, decoding, and caching via QRScanner, QRDecoder, and CacheManager.
- **Braille Engine**: Specialized OCR for braille text capture and classification.
- **Face Engine**: Responsible for face detection and embedding generation.
- **Speech Engine**: Manages intent routing via VoiceRouter and coordinates text-to-speech through TTSHandler.

### Local GPU Services
- **qwen3-embedding:4b**: Local embedding model (~2GB VRAM) running via Ollama.
- **YOLO v8n**: Object detection model (~200MB VRAM) running via ONNX Runtime CUDA EP.
- **MiDaS v2.1 small**: Depth estimation model (~100MB VRAM) running via ONNX Runtime CUDA EP.
- **EasyOCR**: Text recognition engine (~500MB VRAM) running via PyTorch CUDA.
- **Face detection**: Local identification model (~300MB VRAM) running via PyTorch CUDA.
- **FAISS IndexFlatL2**: In-process vector search engine.

### Cloud Integrations
- **OllamaHandler**: Connects to qwen3.5:cloud for high-level reasoning and VQA.
- **Deepgram Plugin**: Provides real-time speech-to-text via WebSockets.
- **ElevenLabs Plugin**: Delivers natural-sounding text-to-speech.
- **TavusAdapter**: Optional virtual avatar integration for video-based interactions.
- **InternetSearch**: DuckDuckGo search adapter for real-time information retrieval.
- **LiveKit**: WebRTC transport layer for audio and video.

### Storage
- **FAISS index** (data/memory_index/): Stores binary vector indexes and JSON metadata.
- **QR cache** (qr_cache/): File-based JSON storage with configurable TTL.
- **ONNX models** (models/): Local storage for pre-trained weights (YOLO, MiDaS).
- **Config** (configs/config.yaml): Central system configuration.
- **Session logs** (.runtime/logs/): Persistent storage for debugging and telemetry events.

# 2. Responsibility Matrix

| Component | Layer | Inputs | Outputs | Dependencies | GPU | Cloud |
|-----------|-------|--------|---------|--------------|-----|-------|
| FastAPI Server | Interface | HTTP requests | JSON responses | Core modules | No | No |
| LiveKit Agent | Interface | Audio/Video streams | Speech output | Core, Infrastructure | No | Yes |
| FrameOrchestrator | Application | TimestampedFrame | FusedFrameResult | PerceptionWorkerPool, SceneGraph | No | No |
| PerceptionWorkerPool | Application | Image arrays | Detection[], DepthMap, OCR text | YOLO, MiDaS, EasyOCR | Yes | No |
| WorkerPool | Application | Async tasks | Task results | ThreadPoolExecutor | No | No |
| Debouncer | Application | Navigation cues | Filtered cues | None | No | No |
| LiveFrameManager | Application | Video frames | TimestampedFrame | deque | No | No |
| StreamingTTSCoordinator | Application | Text sentences | Audio chunks | ElevenLabs | No | Yes |
| Watchdog | Application | Pipeline state | Restart signals | FrameOrchestrator | No | No |
| PipelineMonitor | Application | Pipeline events | Metrics | PerceptionWorkerPool | No | No |
| PerceptionPipeline | Domain | Image (numpy) | PerceptionResult | Detector, Segmenter, DepthEstimator | Yes | No |
| SceneGraphBuilder | Domain | PerceptionResult | SceneGraph | None | No | No |
| SpatialFuser | Domain | PerceptionResult | FusedResult | TemporalFilter | No | No |
| VQAReasoner | Domain | SceneGraph + question | Natural language answer | OllamaHandler | No | Yes |
| MicroNavFormatter | Domain | FusedResult | TTS cue string | None | No | No |
| MemoryIngester | Domain | MemoryStoreRequest | Memory ID | LLMClient, OllamaEmbedder | Yes | Yes |
| OllamaEmbedder | Domain | Text string | np.ndarray (384-dim) | Ollama local | Yes | No |
| FAISSIndexer | Domain | Vector + metadata | Index position | FAISS, threading.RLock | No | No |
| MemoryRetriever | Domain | Query vector + k | List[MemoryHit] | FAISSIndexer | No | No |
| RAGReasoner | Domain | Query + memories | Answer + citations | LLMClient | No | Yes |
| LLMClient | Domain | Prompt | LLM response | OllamaHandler | No | Yes |
| OCRPipeline | Domain | Image | OCR text | EasyOCR, Tesseract, MSER | Yes | No |
| QRScanner | Domain | Image | List[QRDetection] | pyzbar/OpenCV | No | No |
| QRDecoder | Domain | Raw QR data | Classified content | None | No | No |
| CacheManager | Domain | QR payload | Cached result | File I/O | No | No |
| BrailleOCR | Domain | Image | Braille text | Segmenter, Classifier | Yes | No |
| FaceDetector | Domain | Image | Face embeddings | PyTorch model | Yes | No |
| VoiceRouter | Domain | Transcribed text | RouteResult | Regex patterns | No | No |
| OllamaHandler | Infrastructure | Prompt + image | LLM text response | qwen3.5:cloud | No | Yes |
| Deepgram Plugin | Infrastructure | Audio stream | Transcribed text | Deepgram API | No | Yes |
| ElevenLabs Plugin | Infrastructure | Text | Audio stream | ElevenLabs API | No | Yes |
| TavusAdapter | Infrastructure | Audio/config | Avatar video | Tavus API | No | Yes |
| InternetSearch | Infrastructure | Query | Search results | DuckDuckGo | No | Yes |

# 3. Execution Model

The system utilizes a hybrid execution model that blends asyncio for I/O-bound tasks with ThreadPoolExecutors for CPU-bound ML inference.

- **ThreadPoolExecutor**: Both the PerceptionWorkerPool and the generic WorkerPool use thread pools to prevent heavy tasks (like detection, depth estimation, or OCR) from blocking the asyncio event loop.
- **PerceptionWorkerPool**: Dispatches parallel tasks for object detection, depth estimation, and OCR. It collects results using asyncio futures, ensuring that the main application remains responsive during inference.
- **Async HTTP Boundaries**: The OllamaHandler and other cloud adapters use httpx.AsyncClient with explicit timeouts managed via asyncio.wait_for(). Streaming services like Deepgram and ElevenLabs utilize WebSockets for low-latency communication.
- **Sync Gap Management**: A known issue (ISSUE-022) exists where OllamaEmbedder.embed_text() performs synchronous HTTP calls. Current mitigation involves offloading these calls to a thread pool where possible, with a planned transition to full async support.
- **Streaming TTS**: The StreamingTTSCoordinator buffers text at sentence boundaries before dispatching to ElevenLabs. This approach ensures natural prosody while maintaining a responsive user experience through audio chunk streaming.

# 4. GPU Utilization Strategy

The local GPU strategy focuses on maximizing throughput while remaining within the 8GB VRAM budget of the target NVIDIA RTX 4060 hardware.

- **VRAM Budget**: Current peak usage is approximately 3.1GB, leaving 60% headroom for system overhead and driver allocations.
- **Per-model Allocation**:
  - qwen3-embedding:4b: ~2GB
  - EasyOCR: ~500MB
  - Face Detection: ~300MB
  - YOLO v8n: ~200MB
  - MiDaS v2.1 small: ~100MB
- **Concurrent Execution**: Models are loaded on demand and pinned to VRAM. The PerceptionWorkerPool enables concurrent execution of detection and depth estimation to minimize per-frame latency.
- **Safety Mechanisms**: All GPU-accelerated modules include CPU fallback paths (ONNX CPU EP or PyTorch CPU mode). If a CUDA error occurs or VRAM is exhausted, the system automatically degrades to slower but reliable CPU inference.
- **Cloud Offloading**: General-purpose LLM tasks are routed to the cloud to preserve local VRAM for time-critical vision and embedding tasks.
