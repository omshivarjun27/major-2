# Summary — Voice & Vision Assistant for Blind

> **Assumptions** marked with ⚠️ throughout this document.

---

## Executive Summary

- **Real-time accessibility pipeline**: Blind user speaks → Deepgram STT (100ms) → Ollama VLM scene analysis (300ms) → ElevenLabs TTS (100ms) → spoken response; 500ms end-to-end SLA enforced.
- **5-layer monorepo** (`shared → core → application → infrastructure → apps`) with architectural boundaries enforced by import-linter on every CI run.
- **52 canonical data types** in `shared/schemas/__init__.py`; all layers must import from here — no redefinition.
- **8 production pipeline components** (`AudioOutputManager`, `PerceptionWorkerPool`, `AdaptiveFrameSampler`, `PipelineMonitor`, `CancellationScope`, `Debouncer`, `Watchdog`, `StreamingTTSCoordinator`) wired via `create_pipeline_components()` in `application/pipelines/integration.py`.
- **Privacy-first design**: RAG memory `MEMORY_ENABLED=false` by default; face embeddings AES-256 encrypted with consent gate; `PIIScrubFilter` active on all log handlers; GDPR erase endpoint always available.
- **Resilience**: Per-service circuit breakers, exponential-backoff retry policies, and 3-tier fallback chains for TTS, STT, and OCR; `DegradationCoordinator` notifies user via TTS on service failure.
- **429+ tests** across unit, integration, realtime, and performance suites; CI matrix Python 3.10/3.11/3.12; Bandit SAST + pip-audit CVE scan on every push.
- **Observability** ready: Prometheus scrape configs, Grafana dashboard provisioning, Loki log aggregation, and Alertmanager rules present under `deployments/`.

---

## Key Assumptions

| # | Assumption | Where to Verify |
|---|-----------|----------------|
| A1 | Ollama server runs locally at `http://localhost:11434` by default | `apps/realtime/agent.py:39`, `.env.example` |
| A2 | `ENABLE_SEGMENTATION` and `ENABLE_DEPTH` are `false` in production (disabled for latency) | `shared/config/settings.py:55–56` |
| A3 | `application/event_bus/` and `application/session_management/` are stubs (empty) | `application/event_bus/`, `application/session_management/` |
| A4 | No API authentication on public FastAPI endpoints (CORS/rate-limit absent) | `apps/api/server.py` (no middleware present) |
| A5 | `infrastructure/storage/` and `infrastructure/monitoring/` are stubs | `infrastructure/storage/`, `infrastructure/monitoring/` |
| A6 | Grafana dashboards are defined but not validated against real metric names | `deployments/grafana/dashboards/` |
| A7 | `core/reasoning/` is a placeholder/stub | `core/reasoning/` |
| A8 | `CLOUD_SYNC_ENABLED=false`; cloud sync provider is `"stub"` | `shared/config/settings.py:148–149` |

---

## Open Technical Questions

| ID | Question | File to Inspect |
|----|---------|----------------|
| OQ-1 | Does `apps/api/server.py` have any auth middleware or CORS headers? None visible in first 120 lines. | `apps/api/server.py:74–79` |
| OQ-2 | Is the `core/reasoning/` module intentionally empty or under construction? | `core/reasoning/` |
| OQ-3 | What is the actual metric name emitted at `/metrics`? Is Prometheus client (`prometheus-client`) installed? | `requirements.txt`, `apps/api/server.py` |
| OQ-4 | How is `LiveFrame` updated from WebRTC video track frames inside the LiveKit agent? | `application/frame_processing/live_frame_manager.py` |
| OQ-5 | Are Grafana dashboard JSON files complete and valid against the Prometheus metrics actually emitted? | `deployments/grafana/dashboards/` |
| OQ-6 | What happens to FAISS index on container restart — is `data/` a mounted volume or ephemeral? | `docker-compose.test.yml` (no volume defined), `deployments/compose/` |
| OQ-7 | `siliconflow/` adapter is listed as "Stub" — when will it become active? | `infrastructure/llm/siliconflow/` |
| OQ-8 | `application/event_bus/` stub — are there plans to wire it for inter-component events? | `application/event_bus/` |

---

## Prioritised TODO List

### Small (S) — < 1 day

- **S1** Add CORS middleware (`fastapi.middleware.cors.CORSMiddleware`) to `apps/api/server.py` — currently no CORS headers.
- **S2** Add `prometheus-client` to `requirements.txt` if not present; verify `/metrics` route exists on both services.
- **S3** Mount `data/` as a Docker volume in `docker-compose.test.yml` so FAISS/SQLite survive restarts.
- **S4** Add rate-limiting dependency (e.g., `slowapi`) to public API endpoints.

### Medium (M) — 1–5 days

- **M1** Replace `shared/config/settings.py` flat `CONFIG` dict with `pydantic-settings` `BaseSettings` for startup validation and type safety. (Noted in `shared/config/AGENTS.md`)
- **M2** Implement `application/event_bus/` for decoupled inter-component communication (replace direct function calls between pipeline components).
- **M3** Add `/metrics` endpoint to FastAPI server and agent using `prometheus-client` counters/histograms matching `deployments/prometheus/prometheus.yml` job targets.
- **M4** Write integration tests for `application/pipelines/` components (currently sparse in `tests/integration/`).
- **M5** Complete `infrastructure/storage/` adapter for external blob/KV storage (currently stub).

### Large (L) — 1+ week

- **L1** Implement `application/session_management/` for multi-session state persistence (enables resumable sessions across agent restarts).
- **L2** Activate and validate `core/reasoning/` as a central reasoning router (currently placeholder).
- **L3** Introduce horizontal scaling: extract `PerceptionWorkerPool` into a separate process/service with a message queue (Redis Streams) to allow multiple agent instances without lock contention.
- **L4** Complete `infrastructure/llm/siliconflow/` adapter as a hot-swap fallback for Ollama outages.

---

## Risk Analysis

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|-----------|
| Ollama single-point-of-failure (no remote fallback) | HIGH | MEDIUM | Circuit breaker exists; SiliconFlow stub needs completion (L4) |
| No API authentication on public endpoints | HIGH | HIGH | Add auth middleware immediately (S1 → M-security) |
| FAISS/SQLite lost on container restart (no volume) | MEDIUM | HIGH | Mount `data/` volume (S3) |
| `ENABLE_DEPTH=false` default limits navigation accuracy | MEDIUM | LOW | Accept for latency; note in user docs |
| Face encryption key (`FACE_ENCRYPTION_KEY`) not set = unencrypted | HIGH | MEDIUM | Startup guard should abort if key missing (`shared/utils/startup_guards.py`) |
| PII in debug ring buffer (SessionLogger) | LOW | LOW | Not persisted; clear on session end |
| FAISS unbounded index growth | LOW | MEDIUM | Add `maintenance.py` scheduled cleanup (already exists in `core/memory/maintenance.py`) |

---

## Scalability Forecast

| Dimension | Current State | Scaling Bottleneck | Recommendation |
|-----------|-------------|-------------------|----|
| Concurrent users | 1 (single LiveKit room per agent worker) | LiveKit agent is single-process | Run N agent workers behind LiveKit dispatcher |
| Ollama throughput | Sequential per-request | GPU VRAM / queue depth | Use Ollama's native load balancing or SiliconFlow fallback |
| FAISS index | In-process, single-node | ~1M vectors before latency degrades | Switch to Qdrant/Milvus for multi-user deployments |
| Camera frame rate | 100ms cadence (10 FPS) | PerceptionWorkerPool thread count | Increase `NUM_DETECT_WORKERS` or offload to GPU-accelerated worker |
| API throughput | Single uvicorn worker | Python GIL for CPU tasks | Use `gunicorn -k uvicorn.workers.UvicornWorker -w N` or async task queue |
