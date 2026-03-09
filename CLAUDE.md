# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (editable with dev extras)
pip install -e ".[dev]"
# Or install from requirements
pip install -r requirements.txt
pip install -r requirements-extras.txt  # optional: OCR, Claude, GPU, avatar

# Download ML models (YOLO, MiDaS for spatial perception)
python scripts/download_models.py

# Validate environment configuration
python scripts/validate_env.py [--strict]

# Run tests
pytest                            # all tests
pytest tests/unit/ -v             # unit tests only
pytest tests/integration/ -v      # integration tests
pytest -k "test_spatial" -v       # run single test by keyword
pytest --cov=core --cov=application --cov=infrastructure --cov=shared --cov=apps --cov-report=term-missing

# Linting
ruff check .                      # lint with ruff
lint-imports                      # enforce architectural import boundaries
```

## Architecture

### 5-Layer Dependency Graph (enforced by import-linter)

```
apps/ → application/ → core/ → infrastructure/ → shared/
```

| Layer | Purpose | Key Modules |
|-------|---------|-------------|
| **shared/** | Canonical types, config, encryption, logging, utils | `schemas/`, `config/`, `utils/`, `logging/` |
| **infrastructure/** | External service adapters with resilience | `llm/`, `speech/`, `resilience/`, `monitoring/`, `tavus/` |
| **core/** | Business logic engines | `vision/`, `memory/`, `face/`, `audio/`, `braille/`, `ocr/`, `qr/`, `vqa/` |
| **application/** | Pipeline orchestration, frame processing | `pipelines/`, `frame_processing/`, `event_bus/`, `session_management/` |
| **apps/** | Entry points | `realtime/` (LiveKit agent), `api/` (FastAPI), `cli/` |

### Key Data Flows

**Voice Interaction Pipeline:**
```
User Speech → LiveKit → Deepgram STT → AllyVisionAgent
  → Tool Router (classify: VISUAL/SPATIAL/SEARCH/QR_AR/OCR/VQA/GENERAL)
    → Vision Controller (capture frame, run Ollama/spatial/VQA)
    → Voice Controller (search, QR scan)
  → LLM Response → ElevenLabs TTS → LiveKit → User Audio
```

**Spatial Perception Pipeline:**
```
Camera Frame → YOLODetector (ONNX) → EdgeAwareSegmenter → MiDaSDepthEstimator
  → SpatialFuser (distance, direction, priority) → NavigationOutput (TTS cue)
```

**Memory Pipeline (opt-in, MEMORY_ENABLED=false by default):**
```
Event → Text Embedding (Ollama) → FAISS Index + SQLite Metadata
  → RAG Retrieval → LLM Augmented Response
```

### Configuration

- **Environment variables**: `.env` file (see `.env.example`)
- **YAML configs**: `configs/config.yaml` (base), `configs/{environment}.yaml` (overrides)
- **Key env vars**: `LIVEKIT_URL/API_KEY/API_SECRET`, `DEEPGRAM_API_KEY`, `ELEVEN_API_KEY`, `OLLAMA_VL_API_KEY`, `SPATIAL_PERCEPTION_ENABLED`, `ENABLE_QR_SCANNING`, `MEMORY_ENABLED`

### Testing Conventions

- Unit tests: `tests/unit/test_<component>.py` — fast, isolated, mocked
- Integration tests: `tests/integration/` — cross-module, may require external services
- Performance tests: `tests/performance/` — NFR benchmarks
- Realtime tests: `tests/realtime/` — LiveKit pipeline tests
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`

### Resilience Patterns

- **Circuit Breaker**: 3-state (CLOSED→OPEN→HALF_OPEN) with configurable thresholds
- **Failover Chains**: STT (Deepgram→Whisper), TTS (ElevenLabs→Edge TTS)
- **Graceful Degradation**: Coordinated fallback ordering via `degradation_coordinator`

### Security & Privacy

- **PII Scrubbing**: Regex-based redaction in logging (emails, phones, API keys, SSNs)
- **Encryption**: Fernet AES-128-CBC with PBKDF2 key derivation (480,000 iterations)
- **Consent-Gated Features**: Face recognition and memory require explicit consent
- **Production Security**: HTTPS enforcement, rate limiting, circuit breakers enabled
