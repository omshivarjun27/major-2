# Bootstrap & Run Guide

## Prerequisites

- Python 3.10+ (tested on 3.11)
- Git
- OS: Windows 10/11, Ubuntu 20.04+, or macOS 12+

## Quick Start

```bash
# 1. Clone
git clone https://github.com/codingaslu/Voice-Vision-Assistant-for-Blind.git
cd Voice-Vision-Assistant-for-Blind

# 2. Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env
# Edit .env with your API keys (LiveKit, Deepgram, ElevenLabs)

# 5. Run tests
python -m pytest tests/ nfr/tests/ -v --tb=short -q

# 6. Start the API server
uvicorn api_server:app --host 0.0.0.0 --port 8000

# 7. Start the LiveKit agent
python -m src.main
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LIVEKIT_URL` | Yes | — | LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | Yes | — | LiveKit API key |
| `LIVEKIT_API_SECRET` | Yes | — | LiveKit API secret |
| `DEEPGRAM_API_KEY` | Yes | — | Deepgram STT API key |
| `ELEVEN_API_KEY` | No | — | ElevenLabs TTS API key |
| `OLLAMA_VL_MODEL_ID` | No | `qwen3-vl:235b-instruct-cloud` | Vision-language model |
| `FACE_ENCRYPTION_ENABLED` | No | `true` | Encrypt face embeddings at rest |
| `DEBUG_ENDPOINTS_ENABLED` | No | `false` | Enable debug API endpoints |
| `DEBUG_AUTH_TOKEN` | No | — | Bearer token for debug endpoints |

## Running Tests

```bash
# Unit tests only
python -m pytest tests/unit/ -v --tb=short

# NFR (non-functional requirements) tests
python -m pytest nfr/tests/ -v --tb=short

# Full suite with coverage
python -m pytest tests/ nfr/tests/ --cov=. --cov-report=term-missing
```

## Docker

```bash
docker build -t voice-vision-assistant:latest .
docker run --env-file .env -p 8000:8000 voice-vision-assistant:latest
```
