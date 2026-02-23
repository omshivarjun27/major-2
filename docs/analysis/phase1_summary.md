# Phase 1 Analysis — Repository Summary

_Generated: 2026-02-22 10:59:58 UTC_

## 1. Repository Size Summary

| Metric | Value |
|--------|-------|
| Total Files | 244 |
| Total Approx. LOC | 583,061 |
| Primary Language | python |

### Files by Language

| Language | Files | LOC |
|----------|-------|-----|
| python | 202 | 39,931 |
| markdown | 12 | 2,735 |
| other | 12 | 518,198 |
| json | 6 | 21,376 |
| yaml | 4 | 262 |
| shell | 3 | 245 |
| dockerfile | 2 | 71 |
| text | 2 | 95 |
| toml | 1 | 148 |

### Files by Top-Level Directory

| Directory | File Count |
|-----------|-----------|
| `tests/` | 85 |
| `core/` | 62 |
| `application/` | 20 |
| `shared/` | 17 |
| `infrastructure/` | 15 |
| `apps/` | 9 |
| `research/` | 8 |
| `scripts/` | 6 |
| `deployments/` | 2 |
| `models/` | 2 |
| `## Chat Customization Diagnostics.md/` | 1 |
| `.dockerignore/` | 1 |
| `.env/` | 1 |
| `.env.example/` | 1 |
| `.gitignore/` | 1 |
| `AGENTS.md/` | 1 |
| `docker-compose.test.yml/` | 1 |
| `Dockerfile/` | 1 |
| `identities.json/` | 1 |
| `MIGRATION_MAP.md/` | 1 |
| `pyproject.toml/` | 1 |
| `README.md/` | 1 |
| `requirements-extras.txt/` | 1 |
| `requirements.txt/` | 1 |
| `.github/` | 1 |
| `configs/` | 1 |
| `data/` | 1 |
| `reports/` | 1 |

## 2. Architectural Overview

This is a **Python monorepo** following a strict **layered architecture**:

```
shared/ → core/ → application/ → infrastructure/ → apps/
```

### Detected Layers

- `shared/` — present
- `core/` — present
- `application/` — present
- `infrastructure/` — present
- `apps/` — present

### Layer Responsibilities

| Layer | Purpose |
|-------|---------|
| `shared/` | Cross-cutting types, config, logging, utilities |
| `core/` | Domain logic: VQA perception, memory/RAG, OCR, Braille, face, speech |
| `application/` | Use-case orchestration, service layer |
| `infrastructure/` | External adapters (Ollama, Deepgram, ElevenLabs) |
| `apps/` | Entry points: FastAPI REST server, LiveKit WebRTC agent |

## 3. Observed Tech Stack

- **Python Version**: requires-python = ">=3.10"
- **Build System**: setuptools (`pyproject.toml`)
- **Test Framework**: pytest (async mode: auto)
- **Linter/Formatter**: ruff (`line-length=120`, Python 3.10 target)
- **Architecture Enforcement**: import-linter

### Key Frameworks & Libraries

- `ollama`
- `deepgram`
- `easyocr`
- `elevenlabs`
- `fastapi`
- `livekit`
- `numpy`
- `openai`
- `opencv`
- `pillow`
- `pydantic`
- `pytest`
- `ruff`
- `tesseract`
- `torch`
- `uvicorn`

### Dependencies (from requirements.txt)

```
livekit-agents[deepgram,elevenlabs,tavus]>=1.0.0
python-dotenv>=1.0.0
librosa>=0.10.0
numpy>=1.20.0
livekit-plugins-deepgram>=1.0.0
livekit-plugins-openai>=1.0.0
livekit-plugins-silero>=1.0.0
livekit-plugins-elevenlabs>=1.0.0
livekit-plugins-tavus>=1.0.0
livekit>=1.0.0
livekit-api>=1.0.0
langchain-community
duckduckgo-search
ollama
opencv-python
Pillow>=9.0.0
easyocr>=1.7.0
pytesseract>=0.3.10
pyzbar>=0.1.9
qrcode[pil]>=7.4
httpx>=0.26.0
onnxruntime>=1.15.0
scipy>=1.10.0
scikit-image>=0.21.0
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pytest>=7.0.0
pytest-asyncio>=0.23.0
faiss-cpu>=1.7.4
... and 9 more
```

## 4. Entry Points Summary

| Type | Path |
|------|------|
| Backend API | `apps/api/server.py` (FastAPI + uvicorn) |
| WebRTC Agent | `apps/realtime/agent.py` (LiveKit) |
| Docker (canonical) | `deployments/docker/Dockerfile` |
| CI Pipeline | `.github/workflows/ci.yml` |
| Compose (test) | `docker-compose.test.yml` |

## 5. Structural Red Flags

- ⚠️  Large file: `models/midas_v21_small_256.onnx` (65199 KB)
- ⚠️  Large file: `models/yolov8n.onnx` (12549 KB)
- ⚠️  Large file: `tests/generated_scenarios.json` (961 KB)

---
_End of Phase 1 Summary_