---
title: "Monitoring Plan & KPIs"
version: 1.0.0
date: 2026-02-22T18:00:00Z
architecture_mode: hybrid_cloud_local_gpu
related_artifacts:
  - docs/analysis/hybrid_readiness.md
  - docs/analysis/component_inventory.json
  - docs/PRD/04_hld/HLD.md
  - docs/PRD/05_lld/LLD_systems.md
---

# Monitoring Plan & KPIs

## 1. Local Metrics

### 1.1 GPU Metrics

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **GPU VRAM allocated** | `torch.cuda.memory_allocated()` | Polled before/after inference tasks | Per-inference call |
| **GPU VRAM peak** | `torch.cuda.max_memory_allocated()` | Polled at pipeline checkpoint | Per-frame cycle |
| **GPU utilization %** | nvidia-smi polling or pynvml `nvmlDeviceGetUtilizationRates()` | Background polling (5s interval) | Time-series |
| **CUDA errors** | Exception handler in PerceptionWorkerPool | On-error capture | Per-occurrence |

**Instrumentation Points**:
- `PerceptionWorkerPool`: Wrap each GPU task submission with VRAM usage sampling
- `application/pipelines/pipeline_monitor.py`: Add GPU metrics to existing PipelineMonitor
- `/health` endpoint: Surface current VRAM usage in health response JSON

### 1.2 Frame Processing Metrics

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **Frame processing latency** | `PerceptionPipeline.run()` | Timer around full pipeline execution | Per-frame |
| **Detection latency** | `YOLODetector.detect()` | Timer in PerceptionWorkerPool task | Per-frame |
| **Depth estimation latency** | `MiDaSDepthEstimator.estimate()` | Timer in PerceptionWorkerPool task | Per-frame |
| **Frame drop rate** | `LiveFrameManager` | Ratio of dropped frames (deque overflow) to total received | Rolling 60s window |
| **Frame freshness violations** | `is_frame_fresh(max_age=500ms)` | Counter of rejected stale frames | Per-frame |
| **Detection count per frame** | `SceneGraphBuilder` | Count of Detection objects per frame | Per-frame |
| **Debounce suppression rate** | `Debouncer` | Ratio of suppressed to total cues | Rolling 60s window |

**Instrumentation Points**:
- `application/frame_processing/frame_orchestrator.py`: Timestamp entry/exit of `FrameOrchestrator.process()`
- `application/frame_processing/live_frame_manager.py`: Track deque overflow events
- `application/pipelines/debouncer.py`: Count suppressed vs. emitted cues

### 1.3 Worker Pool Metrics

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **Worker queue depth** | `PerceptionWorkerPool` / `WorkerPool` | `ThreadPoolExecutor._work_queue.qsize()` | Polled (5s interval) |
| **Active worker count** | `ThreadPoolExecutor._threads` | Length of active thread set | Polled (5s interval) |
| **Task completion rate** | Worker pool wrapper | Counter of completed tasks per second | Rolling 60s window |
| **Task failure rate** | Worker pool exception handler | Counter of failed tasks | Per-occurrence |

### 1.4 Memory System Metrics

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **FAISS query time** | `FAISSIndexer.search()` | Timer around search call | Per-query |
| **FAISS index size** | `FAISSIndexer` | `index.ntotal` property | Polled (60s interval) |
| **Embedding generation latency** | `OllamaEmbedder.embed_text()` | Timer around HTTP call to Ollama local | Per-call |
| **Memory store latency** | `MemoryIngester.ingest()` | End-to-end timer (embed + index + metadata) | Per-store operation |
| **RAG retrieval latency** | `MemoryRetriever.retrieve()` | Timer around embed + FAISS search + ranking | Per-query |

### 1.5 OCR Metrics

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **OCR success rate** | OCR Engine (3-tier fallback) | Track which tier succeeded per call | Per-call |
| **EasyOCR success rate** | `core/ocr/engine.py` | Counter of EasyOCR successes vs. fallback triggers | Per-call |
| **Tesseract fallback rate** | `core/ocr/engine.py` | Counter of Tesseract invocations | Per-call |
| **MSER heuristic fallback rate** | `core/ocr/engine.py` | Counter of MSER invocations (last resort) | Per-call |
| **OCR latency** | OCR Engine | Timer across entire fallback chain | Per-call |

---

## 2. Cloud Metrics

### 2.1 LLM Metrics (qwen3.5:cloud via Ollama Cloud Runtime)

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **LLM response time** | `OllamaHandler` / `OllamaClient` | `asyncio.wait_for()` elapsed time | Per-call |
| **LLM token count** | Response metadata | Parse usage from API response | Per-call |
| **LLM error rate** | Exception handler in OllamaHandler | Counter of non-2xx responses and timeouts | Per-call |
| **StubLLMClient activation count** | `StubLLMClient` | Counter of fallback invocations | Per-occurrence |

### 2.2 STT Metrics (Deepgram)

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **STT latency** | Deepgram WebSocket | Time from audio chunk send to transcript receive | Per-utterance |
| **STT transcript confidence** | Deepgram response | `confidence` field from response | Per-utterance |
| **STT connection drops** | WebSocket handler | Counter of WebSocket disconnects | Per-occurrence |
| **STT reconnect count** | Plugin-internal reconnect | Counter of reconnect attempts | Per-occurrence |

### 2.3 TTS Metrics (ElevenLabs)

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **TTS first audio chunk time** | `StreamingTTSCoordinator` | Time from text submission to first audio byte received | Per-utterance |
| **TTS total generation time** | `StreamingTTSCoordinator` | Time from submission to final audio chunk | Per-utterance |
| **TTS error rate** | ElevenLabs adapter | Counter of non-2xx responses and timeouts | Per-call |

### 2.4 Cross-Service Metrics

| Metric | Source | Collection Method | Granularity |
|--------|--------|-------------------|-------------|
| **Retry count per cloud service** | Cloud adapters (when BACKLOG-004 implemented) | Counter per service per retry attempt | Per-call |
| **Error rate per cloud service** | All cloud adapters | Ratio of failed to total calls (rolling 5m window) | Time-series |
| **Cloud API cost estimation** | Call counter × estimated cost per call | Computed from call counts | Hourly aggregate |
| **Circuit breaker state** | Circuit breaker (when BACKLOG-004 implemented) | State enum (CLOSED/OPEN/HALF_OPEN) per service | On-change |

---

## 3. System KPIs

### 3.1 Performance KPIs

| KPI | Target | Source | Measurement |
|-----|--------|--------|-------------|
| **End-to-end frame latency** | ≤ 250ms | System prompt specification | Timer from frame receipt to perception result |
| **TTS first audio chunk** | ≤ 300ms | System prompt specification | Timer from text submission to first audio byte |
| **Frame freshness window** | ≤ 500ms | FrameOrchestratorConfig | `is_frame_fresh(max_age=500ms)` check |
| **Debounce window** | 7 seconds | agent.py UserData configuration | Time between allowed duplicate navigation cues |
| **FAISS query time** | ≤ 50ms | Performance benchmark target | Timer around FAISSIndexer.search() |
| **Embedding generation time** | ≤ 200ms | OllamaEmbedder benchmark | Timer around embed_text() HTTP call |

### 3.2 Resource KPIs

| KPI | Target | Source | Measurement |
|-----|--------|--------|-------------|
| **GPU VRAM usage** | ≤ 6GB (75% of 8GB) | Safety threshold for RTX 4060 | `torch.cuda.memory_allocated()` peak |
| **FAISS index size** | ≤ 4,000 vectors (warning), ≤ 5,000 (hard limit) | IndexFlatL2 practical limit | `index.ntotal` |
| **Worker queue depth** | ≤ 10 pending tasks | Backpressure threshold | `ThreadPoolExecutor._work_queue.qsize()` |

### 3.3 Reliability KPIs

| KPI | Target | Source | Measurement |
|-----|--------|--------|-------------|
| **Uptime** | ≥ 99.5% | SLA target | Time with successful /health responses ÷ total time |
| **Detection confidence threshold** | ≥ 0.3 | SceneGraphBuilder configuration | Minimum confidence for included detections |
| **Cloud service availability** | ≥ 99% per service | Per-service error rate | 1 − (error_count ÷ total_calls) over 24h window |
| **Frame drop rate** | ≤ 5% | LiveFrameManager | Dropped ÷ total frames over rolling 60s |
| **Pipeline stall recovery time** | ≤ 15s | Watchdog recovery target | Time from stall detection to pipeline restart |

### 3.4 User Experience KPIs

| KPI | Target | Source | Measurement |
|-----|--------|--------|-------------|
| **Voice interaction round-trip** | ≤ 3s | End-to-end: STT → Intent → LLM → TTS | Timer from user speech end to first audio response |
| **Navigation cue delivery** | ≤ 500ms from detection | Spatial perception pipeline | Timer from YOLO detection to TTS cue dispatch |
| **OCR response time** | ≤ 2s | 3-tier fallback pipeline | Timer across entire OCR chain including fallbacks |

---

## 4. Observability Stack

### 4.1 Current Infrastructure

The system already includes foundational observability components:

| Component | Status | Description |
|-----------|--------|-------------|
| **PipelineMonitor** | ✅ Implemented | Background asyncio task collecting real-time processing metrics across perception and reasoning pipelines. Located at `application/pipelines/pipeline_monitor.py`. |
| **Watchdog** | ✅ Implemented | Background asyncio task monitoring pipeline health. Detects frame processing stalls (>10s) and triggers automatic pipeline restarts. Located at `application/pipelines/watchdog.py`. |
| **Structured JSON logging** | ✅ Implemented | Centralized logging via `shared.logging.logging_config.configure_logging()`. Structured telemetry events via `log_event()`. One logger per module using kebab-case names. |
| **Health endpoint** | ✅ Implemented | `/health` endpoint on FastAPI REST server (port 8000). Returns system health status. |
| **Debug endpoints** | ✅ Implemented | `/debug/perception`, `/debug/stale`, `/debug/camera`, `/debug/orchestrator`, `/debug/workers`, `/debug/frame-manager`, `/debug/frame-rate`, `/debug/watchdog` — protected by Bearer token. |
| **Response metadata** | ✅ Implemented | All API responses use `SuccessEnvelope` with `meta` block containing `gpu_used`, `cloud_calls`, `processing_time_ms`. |

### 4.2 Recommended Additions

#### Prometheus Metrics Export (Proposed)

Expose application metrics in Prometheus format via a `/metrics` endpoint on the FastAPI server.

**Key metrics to export**:
```
# GPU metrics
gpu_vram_allocated_bytes{device="cuda:0"}
gpu_vram_peak_bytes{device="cuda:0"}
gpu_utilization_percent{device="cuda:0"}

# Frame processing
frame_processing_duration_seconds (histogram)
frame_drop_total (counter)
frame_freshness_violations_total (counter)
detection_count_per_frame (histogram)

# Worker pools
worker_queue_depth{pool="perception"}
worker_queue_depth{pool="general"}
worker_tasks_completed_total{pool="perception"}
worker_tasks_failed_total{pool="perception"}

# Cloud services
cloud_request_duration_seconds{service="ollama_cloud"}
cloud_request_duration_seconds{service="deepgram"}
cloud_request_duration_seconds{service="elevenlabs"}
cloud_errors_total{service="ollama_cloud"}
cloud_errors_total{service="deepgram"}
cloud_errors_total{service="elevenlabs"}
cloud_retries_total{service="ollama_cloud"}

# Memory system
faiss_query_duration_seconds (histogram)
faiss_index_size_vectors (gauge)
embedding_generation_duration_seconds (histogram)

# OCR
ocr_success_total{tier="easyocr"}
ocr_success_total{tier="tesseract"}
ocr_success_total{tier="mser"}
ocr_failure_total (counter)
```

**Implementation**: Use `prometheus_client` Python library. Register metrics in PipelineMonitor and expose via `/metrics` endpoint.

#### Grafana Dashboards (Proposed)

| Dashboard | Panels | Refresh |
|-----------|--------|---------|
| **System Overview** | Uptime, GPU VRAM gauge, frame latency p50/p95/p99, active workers, FAISS index size | 10s |
| **Cloud Services** | Per-service latency histograms, error rates, retry counts, circuit breaker states | 10s |
| **Perception Pipeline** | Frame processing latency, detection counts, depth estimation latency, OCR tier distribution | 5s |
| **Memory System** | FAISS query time, index growth over time, embedding latency, RAG retrieval latency | 30s |
| **User Experience** | Voice round-trip time, navigation cue delivery time, TTS first chunk latency | 10s |

#### Log Aggregation (Proposed)

The existing structured JSON logging provides a solid foundation. Recommended enhancements:

1. **Log shipping**: Forward JSON logs to a centralized aggregator (Loki, Elasticsearch, or CloudWatch)
2. **Correlation IDs**: Add request/frame IDs to all log entries for end-to-end trace correlation
3. **Log levels**: Standardize log levels across modules — DEBUG for detailed traces, INFO for operational events, WARNING for degraded states, ERROR for failures
4. **Retention**: Configure 30-day retention for INFO+, 7-day for DEBUG

### 4.3 Health Check Enhancement (Proposed)

Extend the existing `/health` endpoint to return comprehensive system status:

```json
{
  "status": "healthy",
  "uptime_seconds": 86400,
  "gpu": {
    "available": true,
    "device": "NVIDIA RTX 4060",
    "vram_total_mb": 8192,
    "vram_allocated_mb": 3100,
    "vram_utilization_percent": 37.8
  },
  "services": {
    "ollama_local": {"status": "healthy", "latency_ms": 12},
    "ollama_cloud": {"status": "healthy", "latency_ms": 450},
    "deepgram": {"status": "healthy", "latency_ms": 85},
    "elevenlabs": {"status": "healthy", "latency_ms": 120},
    "livekit": {"status": "connected"}
  },
  "pipeline": {
    "frames_processed": 15234,
    "frames_dropped": 42,
    "last_frame_age_ms": 120,
    "watchdog_status": "active"
  },
  "memory": {
    "faiss_index_size": 1250,
    "faiss_max_size": 5000,
    "memory_enabled": false
  }
}
```
