# Workflow — Voice & Vision Assistant for Blind

> **Assumptions**: CI pipeline inferred from `.github/workflows/ci.yml`; runtime flow from `apps/realtime/AGENTS.md` and source code.

---

## Developer Workflow

```
1. Clone → python -m venv .venv → .venv/Scripts/activate
2. pip install -e ".[dev]"          # editable + dev extras
3. cp .env.example .env             # fill API keys
4. python -m apps.realtime.entrypoint download-files   # fetch ONNX models
5. uvicorn apps.api.server:app --host 0.0.0.0 --port 8000   # REST API
6. python -m apps.realtime.entrypoint dev               # LiveKit agent (dev mode)
7. Connect at agents-playground.livekit.io
```

**Lint & gate before pushing:**
```bash
ruff check . --fix && ruff format .
lint-imports                # architectural boundary enforcement
pytest tests/unit/ -q --timeout=60
```

---

## CI/CD Pipeline

```mermaid
flowchart TD
    PUSH["git push / PR\nmain or develop"] --> SS

    subgraph CI["GitHub Actions CI (.github/workflows/ci.yml)"]
        SS["secrets-scan\n• pytest test_secrets_scan.py\n• grep for real API keys in .env"]
        SS --> TEST

        TEST["test (matrix: py3.10/3.11/3.12)\n• install tesseract + libzbar0 + ffmpeg\n• pip install requirements*.txt\n• unit tests (60s timeout)\n• integration tests (120s)\n• full suite + coverage upload\n• NFR/performance tests (300s)\n• benchmark report artifact"]
        TEST --> LINT
        TEST --> SAST
        TEST --> DEPSCAN

        LINT["lint\n• ruff check --output-format=github\n• lint-imports (arch boundaries)"]
        SAST["sast\n• bandit SAST scan\n• fail on HIGH severity\n• upload bandit_report.json"]
        DEPSCAN["dependency-scan\n• pip-audit core + extras\n• fail on fixable CVEs\n• upload audit JSON reports"]

        LINT --> DOCKER
        SAST --> DOCKER
        DEPSCAN --> DOCKER

        DOCKER["docker (main branch only)\n• docker build (root Dockerfile)\n• smoke: import core\n• smoke: OCR backend check\n• smoke: GET /health == ok\n• upload image"]
    end

    DOCKER --> STAGING
    subgraph CD["Deployment"]
        STAGING["deploy-staging.yml\n• tagged release triggers\n• smoke tests on staging env"]
        STAGING --> PROD["deploy-production.yml\n• manual approval gate\n• canary deploy (deployments/canary/)"]
    end
```

---

## Runtime Request Lifecycle

### Voice Query → Spoken Response

```mermaid
sequenceDiagram
    participant U as User (mic)
    participant LK as LiveKit SFU
    participant AG as AllyVisionAgent
    participant TR as tool_router
    participant VC as vision_controller
    participant OL as Ollama API
    participant EL as ElevenLabs

    U->>LK: voice audio (WebRTC)
    LK->>AG: on_message(text)  [Deepgram STT ~100ms]
    AG->>AG: userdata.clear_perception_cache()
    AG->>TR: classify_query(text) → QueryType
    
    alt QueryType=VISUAL
        AG->>VC: analyze_vision(query)
        VC->>VC: capture_fresh_frame()
        VC->>VC: check_frame_freshness (<500ms)
        VC->>OL: streaming VLM request
        OL-->>VC: token stream (~300ms)
        VC-->>AG: response string
    else QueryType=SPATIAL
        AG->>VC: detect_obstacles()
        VC->>VC: capture_fresh_frame()
        VC->>VC: YOLO detect → segment → depth → fuse
        VC-->>AG: navigation cue (<200ms)
    else QueryType=SEARCH
        AG->>AG: voice_controller.search_internet()
        AG-->>AG: DuckDuckGo results (~5s timeout)
    else QueryType=QR_AR
        AG->>VC: capture_fresh_frame()
        AG->>AG: core/qr/ scan + decode + cache
    end

    AG->>EL: TTS request (~100ms)
    EL-->>LK: audio stream
    LK->>U: spoken response (WebRTC)
```

---

### Continuous Proactive Processing (always-on)

```mermaid
sequenceDiagram
    participant SM as session_manager
    participant SAMP as AdaptiveFrameSampler
    participant POOL as PerceptionWorkerPool
    participant AUD as AudioOutputManager
    participant U as User

    loop every PROACTIVE_CADENCE_S (default 2s)
        SM->>SAMP: next_frame_in_ms()
        SAMP-->>SM: adaptive cadence (100–1000ms)
        SM->>POOL: submit detect(frame)
        POOL-->>SM: ObstacleRecord list
        SM->>SM: Debouncer.should_announce()
        alt Priority=CRITICAL or changed scene
            SM->>AUD: speak_with_priority(cue, CRITICAL_HAZARD)
            AUD->>U: spoken warning (preempts other audio)
        end
    end
```

---

## Error Handling & Rollback

```mermaid
flowchart TD
    CALL["External service call\n(Deepgram / ElevenLabs / Ollama)"] --> CB

    CB{"Circuit Breaker\nopen?"}
    CB -- "No" --> EXEC["Execute with timeout\n(STT 2s / TTS 2s / LLM 10s)"]
    CB -- "Yes" --> FB

    EXEC --> RES{"Success?"}
    RES -- "Yes" --> OK["Return result"]
    RES -- "No" --> RETRY["RetryPolicy\nExponential backoff\n(base 0.5–1s, cap 5–30s)"]
    RETRY --> RETRIES{"Max retries\n(2–3) exceeded?"}
    RETRIES -- "No" --> EXEC
    RETRIES -- "Yes" --> FB

    FB["Fallback chain\nTTS: ElevenLabs→EdgeTTS→pyttsx3\nSTT: Deepgram→Whisper\nOCR: EasyOCR→Tesseract→MSER"]
    FB --> DEGRADE["DegradationCoordinator\n• notify user via TTS\n• throttle: 1 msg / 30s\n• update health registry"]
    DEGRADE --> LOG["Log at ERROR level\nStructured JSON + stack trace"]
```

**Rollback policy:**
- Container health probe fails → Docker restarts container automatically.
- Production deploy: canary under `deployments/canary/` before full rollout.
- No database migrations; SQLite/FAISS stored in `data/` volume (persistent).

---

## Build Artifacts & Caching

| Artifact | Location | Retention |
|----------|----------|-----------|
| Coverage XML | `coverage.xml` | Uploaded to Codecov |
| Benchmark report | `benchmark_report.json` | GitHub Actions artifact |
| Bandit SAST report | `bandit_report.json` | GitHub Actions artifact |
| pip-audit reports | `pip_audit_*.json` | GitHub Actions artifact |
| Docker image | Local daemon (main branch) | Tagged `voice-vision-assistant:latest` |
| pip cache | `~/.cache/pip` | Keyed on `requirements.txt` hash |
