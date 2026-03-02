# Architecture — Voice & Vision Assistant for Blind

> **Assumptions**: Inferred from source code; no runtime profiling performed.
> All file references are relative to the repository root.

## One-Line Summary

Real-time, privacy-first accessibility assistant that fuses WebRTC audio, computer vision, and LLM reasoning into sub-500ms spoken responses for blind users.

---

## System Context Diagram

```mermaid
flowchart TB
    subgraph Users["External Users"]
        BU([Blind User\nmic + camera])
        SU([Sighted User\nvideo call])
    end

    subgraph System["Voice & Vision Assistant"]
        API["FastAPI REST\nport 8000"]
        AGENT["LiveKit Agent\nport 8081"]
    end

    subgraph ExtAPIs["External APIs"]
        LK["LiveKit\nWebRTC SFU"]
        DG["Deepgram\nSTT (100ms SLA)"]
        EL["ElevenLabs\nTTS (100ms SLA)"]
        OL["Ollama\nLocal LLM / VLM"]
        DDG["DuckDuckGo\nWeb Search"]
        TAV["Tavus\nVirtual Avatar (opt)"]
    end

    subgraph Obs["Observability"]
        PROM["Prometheus\n:9090"]
        GRAF["Grafana\n:3000"]
        LOKI["Loki\nLogs"]
    end

    BU -- "WebRTC audio/video" --> LK
    LK -- "livekit-agents SDK" --> AGENT
    AGENT -- "REST" --> API
    AGENT -- "HTTP/gRPC" --> DG
    AGENT -- "HTTP/gRPC" --> EL
    AGENT -- "HTTP (Ollama API)" --> OL
    AGENT -- "HTTPS" --> DDG
    AGENT -- "REST + WS" --> TAV
    SU -- "WebRTC" --> LK

    API -- "metrics" --> PROM
    AGENT -- "metrics" --> PROM
    PROM --> GRAF
    AGENT -- "structured JSON" --> LOKI
```

---

## Component / Container Diagram

```mermaid
flowchart LR
    subgraph apps["apps/ — Entrypoints"]
        API["api/server.py\nFastAPI 50+ endpoints\nport 8000"]
        RT["realtime/agent.py\nAllyVisionAgent\nCoordinator (288 LOC)"]
        SM["realtime/session_manager.py\n739 LOC — session lifecycle"]
        VC["realtime/vision_controller.py\n499 LOC — frame/VQA/spatial"]
        VOC["realtime/voice_controller.py\n281 LOC — search/QR"]
        TR["realtime/tool_router.py\n446 LOC — QueryType dispatch"]
    end

    subgraph app["application/ — Orchestration"]
        PIPE["pipelines/integration.py\nPipelineComponents factory"]
        FP["frame_processing/\nFrameOrchestrator\nFreshness/ConfidenceCascade"]
        PM["PipelineMonitor\nSLO tracking"]
        AUDIO["AudioOutputManager\n5-level priority queue"]
        CANCEL["CancellationScope\nQuery-level cancellation"]
        SAMP["AdaptiveFrameSampler\n100–1000ms cadence"]
        POOL["PerceptionWorkerPool\nThreadPoolExecutor"]
        DEB["Debouncer 5s window"]
        WD["Watchdog\nstall detection"]
    end

    subgraph core["core/ — Domain Engines"]
        VQA["vqa/\norchestrator + perception\n+ scene_graph + reasoner"]
        VIS["vision/spatial.py\nYOLO+MiDaS ONNX\nObjectDetector/DepthEstimator"]
        MEM["memory/\nFAISS + SQLite RAG\nprivacy-first opt-in"]
        OCR["ocr/\n3-tier: EasyOCR→Tesseract→MSER"]
        BR["braille/\nBrailleOCR pipeline"]
        QR["qr/\nQRScanner+ARTagHandler\n+CacheManager"]
        FACE["face/\nRetinaFace/MTCNN\nconsent-gated"]
        SPEECH["speech/\nVoiceAskPipeline\nVoiceRouter"]
        AUD["audio/\nSoundSourceLocalizer\nAudioEventDetector"]
        ACT["action/\nActionRecognizer\nClipBuffer 16-frame"]
    end

    subgraph infra["infrastructure/ — Adapters"]
        OLLAMA["llm/ollama/\nOllamaHandler\nLRU cache 64 entries"]
        SEARCH["llm/internet_search.py\nInternetSearch (DuckDuckGo)"]
        EMBED["llm/embeddings/\nBaseEmbedder (Ollama)"]
        STT["speech/deepgram/\nSTT via LiveKit plugins"]
        TTS["speech/elevenlabs/\nTTSManager 3-tier chain"]
        TAVUS["tavus/adapter.py\nTavusAdapter (default off)"]
        RES["resilience/\nCircuitBreaker\nRetryPolicy\nDegradationCoordinator"]
    end

    subgraph shared["shared/ — Cross-cutting"]
        SCH["schemas/__init__.py\n52 types: Detection, BoundingBox\nObstacleRecord, NavigationOutput…"]
        CFG["config/settings.py\n85+ env vars, 7 feature flags\nget_spatial/qr/face/audio_config()"]
        LOG["logging/\nPII scrub, structured JSON"]
        ENC["utils/\nencryption, timing, startup guards"]
    end

    RT --> SM
    RT --> VC
    RT --> VOC
    RT --> TR
    API --> core
    SM --> PIPE
    VC --> VIS
    VC --> VQA
    VC --> OCR
    VOC --> QR
    VOC --> SEARCH
    PIPE --> AUDIO & CANCEL & SAMP & POOL & DEB & WD & PM
    FP --> VIS
    VQA --> OLLAMA
    MEM --> EMBED
    SPEECH --> TTS
    infra --> shared
    core --> shared
    app --> core
    app --> shared
```

---

## Deployment Topology

```mermaid
flowchart TB
    subgraph Container["Docker Container (python:3.11-slim)"]
        direction LR
        API_P["uvicorn :8000\nFastAPI REST"]
        AGT_P["livekit-agents worker :8081\nAllyVisionAgent"]
        HC["HEALTHCHECK\nGET /health every 30s"]
    end

    subgraph Models["Local Models (models/)"]
        YOLO["yolov8n.onnx\n(auto-download)"]
        MIDAS["midas_v21_small_256.onnx\n(auto-download)"]
    end

    subgraph Storage["Persistent Storage"]
        DB["data/\nSQLite + FAISS index\nQR cache"]
    end

    subgraph Cloud["External Cloud Services"]
        LK_SFU["LiveKit SFU\nWebRTC"]
        DG_API["Deepgram API\nSTT"]
        EL_API["ElevenLabs API\nTTS"]
        OL_API["Ollama API\nqwen3.5:397b-cloud"]
    end

    subgraph Obs2["Observability Stack"]
        PROM2["Prometheus :9090"]
        GRAF2["Grafana :3000"]
        LOKI2["Loki :3100"]
        ALERT["Alertmanager :9093"]
    end

    Container -- "HTTP" --> Cloud
    Container --> Models
    Container --> Storage
    Container -- "metrics scrape" --> PROM2
    PROM2 --> GRAF2
    PROM2 --> ALERT
    Container -- "log push" --> LOKI2
```

---

## Communication Patterns

| From | To | Protocol | Sync/Async | SLA |
|------|----|----------|-----------|-----|
| LiveKit SFU | Agent | WebRTC / livekit-agents SDK | Async stream | — |
| Agent | Deepgram | gRPC via LiveKit plugin | Async | 100ms |
| Agent | ElevenLabs | HTTPS chunked | Async stream | 100ms |
| Agent | Ollama | HTTP REST (OpenAI-compat) | Async SSE | 300ms |
| Agent | DuckDuckGo | HTTPS | Async | 5s timeout |
| Agent | Tavus | REST + WebSocket | Async | 5s timeout |
| API | Core engines | In-process function calls | Async | — |
| Prometheus | API/Agent | HTTP scrape /metrics | Pull, 10s | — |

---

## Security & Auth

- **Secrets**: 9 secrets (LiveKit, Deepgram, ElevenLabs, Ollama, Tavus keys) never logged; `PIIScrubFilter` active in all handlers.  (`shared/config/settings.py:251–263`)
- **Face data**: AES-256 encrypted at rest (`FACE_ENCRYPTION_ENABLED=true` default); consent required before any storage. (`shared/config/settings.py:122–127`)
- **Memory/RAG**: `MEMORY_ENABLED=false` by default; requires explicit consent endpoint `/memory/consent`. (`core/memory/privacy_controls.py`)
- **Debug endpoints**: Gated by `DEBUG_ENDPOINTS_ENABLED` + `DEBUG_AUTH_TOKEN` Bearer check. (`apps/api/server.py:46–70`)
- **Docker**: Non-root `appuser`, no build tools in runtime image. (`deployments/docker/Dockerfile:58–79`)
- **CI**: Bandit SAST scan + pip-audit CVE scan on every push. (`ci.yml:143–271`)

---

## Observability

- **Metrics**: Prometheus scrapes `/metrics` on api:8000 and agent:8081 every 10s; Grafana dashboards + Alertmanager rules. (`deployments/prometheus/prometheus.yml`)
- **Logging**: Structured JSON via `configure_logging()`; `PIIScrubFilter` redacts emails, IPs, face IDs, API keys. (`shared/logging/logging_config.py`)
- **Health**: `GET /health` returns JSON `{status: ok}`; Docker HEALTHCHECK every 30s. (`deployments/docker/Dockerfile:82–83`)
- **SLO tracking**: `PipelineMonitor` tracks per-stage latency (STT 100ms, VQA 300ms, TTS 100ms, total 500ms). (`application/pipelines/pipeline_monitor.py`)
- **Session debug**: `SessionLogger` ring buffer captures per-turn state for offline inspection. (`shared/debug/`)

---

## Failure Modes & Resilience

- **Circuit breakers**: Per-service (Deepgram, ElevenLabs, Ollama, LiveKit, Tavus, DuckDuckGo); 3 failures → open; 30–60s reset. (`infrastructure/resilience/circuit_breaker.py`)
- **Retry policies**: Exponential backoff with cap; Deepgram/ElevenLabs max 2 retries, Ollama max 3. (`infrastructure/resilience/retry_policy.py`)
- **TTS fallback chain**: ElevenLabs → local Edge TTS (en-US-AriaNeural) → pyttsx3. (`infrastructure/speech/tts_failover.py`)
- **STT fallback**: Deepgram → local Whisper (configurable model size). (`infrastructure/speech/stt_failover.py`)
- **OCR fallback**: EasyOCR → Tesseract → MSER heuristic. (`core/ocr/`)
- **Graceful degradation**: `DegradationCoordinator` announces degraded state via TTS at most every 30s. (`infrastructure/resilience/degradation_coordinator.py`)
- **Pipeline never crashes**: All engine methods return error strings; `try/except` at every boundary.

---

## Recommended Next Engineering Tasks

1. **S** — Add CORS middleware and rate-limiting to `apps/api/server.py` (currently missing, noted in `apps/api/AGENTS.md`).
2. **M** — Replace `shared/config/settings.py` flat dict with `pydantic-settings` `BaseSettings` for type-safe validation (noted in `shared/config/AGENTS.md`).
3. **L** — Implement `application/event_bus/` and `application/session_management/` stubs into real production modules for decoupled inter-component communication.
