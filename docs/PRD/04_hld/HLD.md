---
title: "High Level Design — Voice & Vision Assistant for Blind"
version: 1.0.0
date: 2026-02-22T14:25:35Z
architecture_mode: hybrid_cloud_local_gpu
related_artifacts:
  - docs/analysis/component_inventory.json
  - docs/analysis/data_flows.md
  - docs/analysis/hybrid_readiness.md
  - docs/PRD/01_overview.md
---

# 1. System Architecture Overview

The Voice & Vision Assistant is a 5-layer monorepo following a strict hierarchical dependency model: `shared → core → application → infrastructure → apps`. This structure ensures modularity and clean boundaries, which are enforced at build time by an import-linter.

The system features two primary entry points:
1. **FastAPI REST Server (Port 8000)**: Provides over 30 endpoints for system configuration, memory management, QR scanning, and debugging.
2. **LiveKit WebRTC Agent (Port 8081)**: Handles real-time, low-latency audio and video streams for direct user interaction.

The system utilizes a hybrid cloud and local GPU execution model. Heavy reasoning and speech processing are offloaded to cloud providers, while low-latency perception and privacy-sensitive embeddings run locally on NVIDIA RTX 4060 hardware. The assistant is designed as a voice-first, single-user device with no visual frontend.

# 2. Architectural Principles

- **Separation of Concerns**: Each of the 5 layers has a distinct responsibility. `shared/` contains common types and must never import from other layers. `core/` contains domain logic but cannot import from application or infrastructure layers.
- **Async Boundaries**: The system prioritizes non-blocking operations. The `OllamaHandler` uses async HTTP clients, while the `PerceptionWorkerPool` offloads heavy ML inference to a dedicated `ThreadPoolExecutor` to keep the main event loop responsive. A known gap exists in the synchronous `OllamaEmbedder`, which is targeted for future optimization.
- **GPU-Aware Compute**: Local inference targets an RTX 4060 with 8GB VRAM. Current usage peaks at approximately 3.1GB, providing significant headroom. All GPU-accelerated models include CPU fallback paths for reliability.
- **Cloud Isolation**: The infrastructure layer encapsulates all external dependencies like Deepgram, ElevenLabs, and Ollama cloud. Domain logic never interacts directly with cloud APIs, allowing for easier mocking and potential provider swaps.
- **Never Crash Philosophy**: Pipeline stages are designed for graceful degradation. If a model fails to load or a cloud service is unreachable, the system uses mock detectors, heuristic estimators, or static stub responses to maintain basic functionality.

# 3. Layer Breakdown

| Layer | Components | Responsibility |
|-------|-----------|----------------|
| **USERS** | Blind/VI user, REST API consumers | Interact via voice+camera (LiveKit) or HTTP |
| **INTERFACE LAYER** | LiveKit WebRTC Agent (8081), FastAPI REST Server (8000) | Transport, protocol handling, session management |
| **APPLICATION LAYER** | FrameOrchestrator, WorkerPool, PerceptionWorkerPool, Debouncer, LiveFrameManager, StreamingTTSCoordinator, Watchdog, PipelineMonitor | Frame processing orchestration, parallel task execution, health monitoring, TTS coordination |
| **DOMAIN LAYER** | VQA Engine (PerceptionPipeline, SceneGraphBuilder, SpatialFuser, VQAReasoner, MicroNavFormatter), Memory Engine (MemoryIngester, OllamaEmbedder, FAISSIndexer, MemoryRetriever, RAGReasoner, LLMClient), OCR Engine (3-tier fallback), QR/AR Engine (scanner, decoder, cache), Braille Engine, Face Engine, Speech Engine (VoiceRouter, TTSHandler) | Core business logic — perception, reasoning, memory, text recognition |
| **LOCAL GPU SERVICES** | qwen3-embedding:4b (~2GB VRAM), YOLO v8n (~200MB), MiDaS v2.1 (~100MB), EasyOCR (~500MB), Face detection (~300MB), FAISS (in-process), pyzbar (CPU) | On-device inference and vector search |
| **CLOUD SERVICES** | qwen3.5:cloud (LLM), Deepgram (STT), ElevenLabs (TTS), LiveKit (WebRTC), Tavus (avatar, optional), DuckDuckGo (search) | Remote inference, speech processing, transport |
| **STORAGE** | FAISS index (data/memory_index/), QR cache (qr_cache/), ONNX models (models/), config.yaml (configs/) | Persistence for vectors, caches, model weights, configuration |

# 4. Hybrid Execution Strategy

The system balances performance and latency by splitting workloads between local hardware and cloud services.

**Cloud Services Usage:**
- **Reasoning**: LLM tasks for VQA, RAG, and general chat use `qwen3.5:cloud` via an async Ollama cloud runtime.
- **Speech**: Deepgram provides real-time STT via WebSockets, while ElevenLabs handles high-quality TTS.
- **Transport & Search**: LiveKit manages real-time WebRTC streams. Internet lookups use DuckDuckGo. Optional avatar rendering is provided by Tavus.

**Local GPU Services Usage:**
- **Vision**: YOLO v8n for object detection and MiDaS v2.1 for depth estimation run via ONNX Runtime with CUDA acceleration.
- **Text & Identity**: EasyOCR and face detection use PyTorch with CUDA. `qwen3-embedding:4b` generates text embeddings for the memory system.
- **Data & CPU**: QR decoding uses pyzbar on the CPU. Vector similarity searches are performed in-process using FAISS.

**Fallback Logic:**
The system maintains a "never crash" guarantee through local fallbacks. ONNX and PyTorch models revert to CPU execution if CUDA is unavailable. If specific model files are missing, the system swaps in mock detectors or heuristic-based estimators. When cloud services are unreachable, the `StubLLMClient` provides static responses to prevent pipeline stalls.

# 5. Data Flow Summary

The system orchestrates five primary end-to-end data flows.

| # | Flow | Stages | Key Components |
|---|------|--------|----------------|
| 1 | Voice → STT → Intent → LLM → TTS → Audio | 7 | Deepgram, VoiceRouter (6 intents), qwen3.5:cloud, ElevenLabs |
| 2 | Camera → Perception → Scene Graph → VQA → Speech | 9 | YOLO, MiDaS, SceneGraphBuilder, SpatialFuser, VQAReasoner |
| 3 | QR Scan → Classify → Speech | 8 | pyzbar/OpenCV, QRDecoder, CacheManager (3-level retry) |
| 4 | Memory Store → RAG Retrieval → Response | 13 (6 ingest + 7 query) | qwen3-embedding:4b, FAISS, qwen3.5:cloud |
| 5 | Spatial Perception → Navigation Cue → TTS | 10 | YOLO, MiDaS, SpatialFuser (EMA smoothing), MicroNavFormatter, Debouncer |

**Latency Budgets:**
- **Per Frame Perception**: ≤ 250ms
- **Detection + Depth**: ≤ 250ms
- **TTS First Chunk**: ≤ 300ms
- **Frame Freshness**: 500ms
- **Debounce Window**: 7s

# 6. Scalability Strategy

The system scales through specialized worker pools. The `PerceptionWorkerPool` uses a `ThreadPoolExecutor` to parallelize GPU-heavy inference tasks like detection and depth estimation. General tasks are handled by a standard `WorkerPool`. The `FrameOrchestrator` manages per-frame fusion, while the `LiveFrameManager` uses a bounded deque to drop stale frames under heavy load.

**GPU Memory Guardrails:**
With a peak VRAM usage of ~3.1GB on an 8GB RTX 4060, the system maintains 60% headroom. This prevents OOM errors during concurrent processing. However, the system currently lacks active VRAM monitoring or backpressure based on GPU usage.

**Limitations:**
- FAISS uses an `IndexFlatL2` structure, which is O(n) and limited to approximately 5,000 vectors.
- The architecture is single-process and does not support horizontal scaling.
- The `agent.py` file is a 1,900-line god object that presents a development bottleneck.
- There is no current rate limiting on cloud API calls or incoming REST requests.

# 7. Reliability Strategy

The system prioritizes local reliability through its "never crash" philosophy and graceful degradation. Local failures are well-isolated, automatically falling back to CPU or mock implementations.

**Cloud Resilience Gaps**:
Currently, the system lacks explicit retry or backoff logic for cloud APIs like Deepgram or ElevenLabs. An outage in these services can lead to a total loss of voice interaction. The `StubLLMClient` is the only active cloud fallback, returning a static message if the LLM provider is offline.

**Recommendations for Improvement**:
- Implement exponential backoff (3 retries) for all cloud calls.
- Add circuit breakers to each cloud service that open after 3 consecutive failures.
- Integrate a local STT fallback (like Whisper) to maintain basic voice control during network outages.

# 8. Observability Overview

The system includes dedicated background tasks for health and performance monitoring.
- **PipelineMonitor**: Collects and reports real-time processing metrics.
- **Watchdog**: Specifically monitors pipeline health to detect stalls and trigger automatic restarts.

**Observability Gaps**:
The system does not yet separate metrics for cloud versus local latency, nor does it monitor `torch.cuda` memory allocations. Future enhancements should include surfacing VRAM usage in the `/health` endpoint and tracking individual cloud service error rates separately from local inference performance.
