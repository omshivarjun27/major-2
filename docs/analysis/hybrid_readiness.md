# Hybrid Architecture Readiness Assessment

**Date**: 2026-02-22
**Architecture**: Hybrid Cloud + Local GPU
**Cloud LLM**: qwen3.5:cloud (Ollama cloud runtime)
**Local Embedding**: qwen3-embedding:4b (RTX 4060, CUDA)

## Executive Summary

The system implements a functional hybrid architecture with clear separation between cloud services (LLM reasoning, STT, TTS, transport) and local GPU workloads (vision, embedding, OCR, face detection). The local GPU pipeline is well-designed with ~3.1GB peak VRAM usage against 8GB available, providing comfortable headroom. However, the cloud side lacks resilience — no retry/backoff, no circuit breakers, and no fallback providers — making the system fragile under cloud service disruption. Production readiness is blocked by 4 critical security issues and 6 high-severity architectural flaws.

## Dimension Scores

| Dimension | Score (0-10) | Rationale |
|-----------|-------------|-----------|
| Reliability | 5/10 | SPOFs for Deepgram/ElevenLabs/Ollama cloud with no documented retry or circuit breaker. Graceful degradation exists for local components (MiDaS→Simple, YOLO→Mock) but cloud failures are unhandled. No graceful shutdown. In-memory state lost on restart. |
| Scalability | 5/10 | FAISS O(n) IndexFlatL2 limits memory search to ~5K vectors. 1,900-line god object is a development bottleneck. WorkerPool and PerceptionWorkerPool provide some parallelism. No horizontal scaling story. |
| GPU Efficiency | 7/10 | RTX 4060 (8GB) with ~3.1GB peak usage provides 60% headroom. ONNX Runtime CUDA EP for vision models is efficient. All GPU models have CPU fallback paths. However, OllamaEmbedder is synchronous (blocks event loop), no explicit batch control for embedding, and no GPU memory monitoring. |
| Cloud Efficiency | 4/10 | No retry/backoff for any cloud service. No circuit breaker pattern. OllamaEmbedder is synchronous blocking. Single provider for STT (Deepgram), TTS (ElevenLabs), and LLM (qwen3.5:cloud). No TTS caching despite specification. DuckDuckGo search has no error handling documented. |
| Maintainability | 4/10 | No type checker (mypy/pyright). 3,674 lint issues. 1,900-line god object. Duplicate type definitions (shared/schemas vs core/vqa/api_schema). 76.7% format non-compliance. FusedFrameResult uses Any for 7/13 fields. |
| **Overall** | **5/10** | Functional core with well-designed GPU pipeline, but production readiness blocked by security issues, cloud resilience gaps, and significant maintainability debt. |

## Cloud Dependency Resilience

### Current State

| Cloud Service | Retry/Backoff | Circuit Breaker | Fallback | Health Check |
|---------------|--------------|-----------------|----------|-------------|
| Deepgram (STT) | None documented | None | None (VOSK mentioned but not implemented) | Plugin-internal reconnect only |
| ElevenLabs (TTS) | None documented | None | System prompt mentions local TTS, but relies on LiveKit plugin behavior | None |
| Ollama cloud (LLM) | None documented | None | `StubLLMClient` returns static fallback | None |
| LiveKit (transport) | WebRTC built-in reconnect | None | None (core transport) | None |
| DuckDuckGo (search) | None documented | None | None | None |

### Assessment

Cloud resilience is **weak**. The system has no explicit retry with exponential backoff for any cloud service. The `OllamaHandler` uses `asyncio.wait_for()` with timeouts, but timeout values are not always configured. The only documented fallback is `StubLLMClient` which returns a static "I don't have enough context" response when all LLM backends are offline.

**Risk**: A 30-second Deepgram outage results in complete voice input loss. An ElevenLabs outage results in no audio output. An Ollama cloud outage disables all reasoning.

## Local GPU Memory Management

### VRAM Budget (RTX 4060 — 8GB)

| Component | Technology | Est. VRAM | Status |
|-----------|-----------|-----------|--------|
| Object Detection (YOLO v8n) | ONNX Runtime CUDA EP | ~200MB | Active when SPATIAL_USE_YOLO=true |
| Depth Estimation (MiDaS v2.1 small) | ONNX Runtime CUDA EP | ~100MB | Active when SPATIAL_USE_MIDAS=true |
| Embedding (qwen3-embedding:4b) | Torch CUDA via Ollama local | ~2,000MB | Always active |
| OCR (EasyOCR) | PyTorch CUDA | ~500MB | Active when OCR backend detected |
| Face Detection | PyTorch CUDA | ~300MB | Active when ENABLE_FACE=true |
| **Peak Total** | | **~3,100MB** | **38.75% of 8GB** |

### Assessment

GPU memory management is **adequate for single-user operation**. The ~3.1GB peak usage leaves ~4.9GB headroom, sufficient for CUDA context overhead and driver allocations. Key observations:

- **Positive**: All GPU models have CPU fallback paths. ONNX Runtime CUDA EP is memory-efficient for inference.
- **Gap**: No explicit VRAM monitoring or backpressure at the GPU level. `WorkerPool` provides task-level backpressure but doesn't check GPU memory availability before scheduling GPU work.
- **Gap**: No GPU memory budget enforcement — if all components load simultaneously, the total is well within bounds, but there's no guard against a rogue model loading.
- **Risk**: Adding a local LLM fallback (for cloud outage resilience) would need ~2-4GB additional VRAM, potentially exceeding the budget.

## Embedding Batching Strategy

### Current State

`OllamaEmbedder.embed_text()` is a **synchronous, single-item** method:
- Makes one HTTP call per text string to the Ollama local embedding endpoint
- No batch API support (`/api/embeddings` accepts a single prompt)
- No client-side batching or request queuing
- **Synchronous**: blocks the calling thread (and the asyncio event loop if called from async context)

### Assessment

Embedding batching is **not implemented**. Each memory ingestion or RAG query triggers a blocking HTTP call to the local Ollama service. The `qwen3-embedding:4b` model loads into GPU memory (~2GB) and processes one request at a time.

**Impact**: During burst memory ingestion (e.g., storing multiple memories in sequence), each embedding call blocks for ~50-200ms. In async context, this stalls the entire event loop, affecting real-time perception, voice processing, and navigation cues.

**Recommendation**: Wrap `embed_text()` in `run_in_executor()` for immediate non-blocking behavior. Long-term, implement client-side batching with a request queue and configurable batch size.

## Async Boundary Correctness

### Current State

| Component | Async? | Correct? | Notes |
|-----------|--------|----------|-------|
| `OllamaHandler` (LLM) | Yes | ✅ | Uses `httpx.AsyncClient`, `asyncio.wait_for()` |
| `OllamaEmbedder` (embedding) | **No** | ❌ | Synchronous HTTP calls block event loop (ISSUE-022) |
| `OllamaClient` (memory LLM) | Yes | ✅ | Async HTTP via Ollama cloud runtime |
| Deepgram STT | Yes | ✅ | WebSocket-based, handled by LiveKit plugin |
| ElevenLabs TTS | Yes | ✅ | HTTP/WebSocket, handled by LiveKit plugin |
| `YOLODetector.detect()` | No | ⚠️ | CPU-bound, should use `run_in_executor()` |
| `MiDaSDepthEstimator.estimate()` | No | ⚠️ | CPU-bound, should use `run_in_executor()` |
| `PerceptionWorkerPool` | Thread pool | ✅ | Uses `ThreadPoolExecutor` for CPU-bound inference |
| `FAISSIndexer` | No | ⚠️ | Uses `threading.RLock()` — safe for threads but blocks event loop |

### Assessment

Async boundaries are **mostly correct** with one critical violation: `OllamaEmbedder` is synchronous but called from async contexts. The `PerceptionWorkerPool` correctly offloads CPU-bound work (detection, depth, segmentation) to a thread pool. The `OllamaHandler` is properly async. However, `FAISSIndexer` operations (which hold an RLock) should also be offloaded to avoid event loop blocking during disk I/O.

## Queue Backpressure Handling

### Current Mechanisms

| Component | Mechanism | Bounded? | Backpressure Action |
|-----------|----------|----------|---------------------|
| `LiveFrameManager` | `collections.deque(maxlen=N)` | ✅ Yes | Old frames dropped silently |
| `Debouncer` | Time-based deduplication (7s window) | ✅ Yes | Duplicate cues suppressed |
| `WorkerPool` | `ThreadPoolExecutor` | ✅ Yes | Task queue bounded by worker count |
| `PerceptionWorkerPool` | `ThreadPoolExecutor` | ✅ Yes | Task queue bounded by worker count |
| `TemporalFilter` | `max_tracks=20` with eviction | ✅ Yes | Lowest-confidence tracks evicted |
| `Frame freshness` | `is_frame_fresh(max_age=500ms)` | ✅ Yes | Stale frames rejected |

### Assessment

Queue backpressure is **well-implemented for the local pipeline**. The frame processing path has multiple layers of backpressure: LiveFrameManager drops old frames, freshness check rejects stale frames, Debouncer suppresses duplicate cues, and TemporalFilter caps track count. This prevents unbounded growth in the perception pipeline.

**Gap**: No backpressure on cloud API calls. If the Ollama cloud endpoint is slow, requests queue up without bound. No queue depth monitoring or shedding for memory ingestion requests.

## Fault Isolation (Cloud vs Local)

### Cloud Service Failure Scenarios

| Failure | Impact | Isolation | Recovery |
|---------|--------|-----------|----------|
| Ollama cloud (LLM) down | No VQA reasoning, no RAG answers | ❌ Not isolated — `StubLLMClient` returns static response | Manual restart or wait for recovery |
| Deepgram (STT) down | Complete voice input loss | ❌ Not isolated — no fallback STT | Manual restart or wait for recovery |
| ElevenLabs (TTS) down | No audio output | ⚠️ Partial — LiveKit may fall back to local TTS | Undocumented automatic behavior |
| LiveKit (transport) down | Total system failure | ❌ Not isolated — core transport | No recovery possible without transport |
| DuckDuckGo (search) down | No internet search answers | ✅ Isolated — only affects search intent | Graceful — returns "search unavailable" |

### Local GPU Failure Scenarios

| Failure | Impact | Isolation | Recovery |
|---------|--------|-----------|----------|
| CUDA unavailable | All models fall back to CPU | ✅ Well-isolated — graceful degradation | Automatic CPU fallback |
| YOLO model missing | Falls back to MockObjectDetector | ⚠️ Silent fallback (ISSUE-026) | Automatic but unannounced |
| MiDaS model missing | Falls back to SimpleDepthEstimator | ✅ Logged fallback | Automatic with warning |
| Ollama local (embedding) down | Memory system degraded | ⚠️ No health check (ISSUE-018) | Silent failure — garbage vectors |
| GPU OOM | Process crash | ❌ Not isolated — no OOM handler | Manual restart required |

### Assessment

Fault isolation is **asymmetric**: local GPU failures are well-handled with graceful degradation to CPU/mock implementations, but cloud service failures are poorly isolated. The local pipeline follows the "never crash" design philosophy effectively. The cloud side lacks circuit breakers, health probes, and explicit fallback implementations.

## Key Risks

1. **Deepgram SPOF**: Complete voice input loss with no fallback STT. For a blind user, this is total system failure since voice is the only input method.
2. **Synchronous embedding blocking event loop**: `OllamaEmbedder.embed_text()` blocks the asyncio event loop for 50-200ms per call, stalling real-time perception and voice processing during memory operations.
3. **No cloud retry/backoff**: Transient cloud failures (network blips, rate limiting) cause immediate failure rather than graceful retry, despite being the most common failure mode for HTTP APIs.
4. **GPU OOM with no handler**: If VRAM budget is exceeded (e.g., by adding local LLM fallback), the process crashes with no graceful degradation or recovery mechanism.
5. **Silent GPU degradation**: YOLO→Mock fallback produces synthetic detection data without alerting the user, potentially providing misleading navigation cues to a blind person.

## Recommendations

1. **Implement circuit breaker pattern for all cloud services** — Add retry with exponential backoff (3 retries, 1s/2s/4s) for Deepgram, ElevenLabs, and Ollama cloud calls. Use a circuit breaker that opens after 3 consecutive failures and probes for recovery every 30 seconds. Effort: M (2-4 hours per service).

2. **Convert OllamaEmbedder to async** — Wrap `embed_text()` in `asyncio.get_event_loop().run_in_executor()` as an immediate fix. Long-term, rewrite using `httpx.AsyncClient` with batch support. Effort: S (1-2 hours for run_in_executor, M for full async rewrite).

3. **Implement Whisper-based local STT fallback** — Use `faster-whisper` with CPU mode (~500MB RAM, no GPU needed) as fallback when Deepgram is unreachable. Wire into LiveKit STT plugin interface. Effort: L (1-3 days including LiveKit integration).

4. **Add GPU memory monitoring** — Implement a lightweight VRAM usage check using `torch.cuda.memory_allocated()` before scheduling GPU work. Add backpressure when usage exceeds 75% of total VRAM (6GB threshold). Surface in `/health` endpoint. Effort: S (1-2 hours).

5. **Annotate detector degradation in navigation output** — When `MockObjectDetector` is active, prefix navigation cues with "Simulated: " or disable spatial navigation entirely. Add `is_mock` flag to detector and check in `MicroNavFormatter`. Effort: S (1-2 hours).

6. **Add cloud service health dashboard to /health endpoint** — Return structured JSON with liveness status for each cloud service: Ollama cloud, Deepgram, ElevenLabs, LiveKit, and local services: Ollama embedding, YOLO, MiDaS. Effort: M (2-4 hours).

7. **Implement TTS audio caching** — Cache ElevenLabs responses by text fingerprint (SHA-256) in an LRU cache (max 100 entries). This reduces latency for repeated navigation cues and reduces cloud API costs by an estimated 20-40%. Effort: M (2-4 hours).
