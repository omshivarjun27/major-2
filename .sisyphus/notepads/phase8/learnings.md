## Phase 8: API Specification — Learnings

### Endpoint Sources (from component_inventory.json)
REST API Server (apps/api/server.py) — FastAPI 0.128+ on port 8000:
- /health, /config
- /qr/scan, /qr/cache, /qr/history, /qr/debug
- /face/consent, /face/embeddings
- /memory/store, /memory/search, /memory/query, /memory/consent
- /braille/read, /braille/debug
- /audio/health, /audio/ssl
- /debug/perception, /debug/stale, /debug/camera, /debug/orchestrator, /debug/workers, /debug/frame-manager, /debug/frame-rate, /debug/watchdog
- /session/create, /session/list
- /export/full, /import/full

Auth: Bearer token for debug endpoints only (DEBUG_AUTH_TOKEN)

LiveKit WebRTC Agent: WebSocket/WebRTC on port 8081 — NOT a REST endpoint, document as description only.

### Data Models for API
Key Pydantic models from data_model_inventory.json:
- MemoryStoreRequest, MemoryStoreResponse
- MemorySearchRequest, MemorySearchResponse, MemoryHit
- MemoryQueryRequest, MemoryQueryResponse, MemoryCitation
- MemoryConsentRequest, MemoryConsentResponse
- PerceptionFrameRequest, PerceptionFrameResponse
- VQAAskRequest, VQAAskResponse

### Cloud/GPU Boundaries
Cloud calls: qwen3.5:cloud (via Ollama cloud runtime), Deepgram (STT), ElevenLabs (TTS), Tavus (avatar), DuckDuckGo (search)
Local GPU: qwen3-embedding:4b (~2GB), YOLO v8n (~200MB), MiDaS v2.1 (~100MB), EasyOCR (~500MB), Face detection (~300MB)
FAISS: in-process, file-based persistence

### Constraints
- No OpenAI, no Claude, no Anthropic references
- Standard response envelope required
- Standard error contract required

# Phase 8 — API Specification Generation Learnings

## Date: 2026-02-22

### Files Generated
 `docs/PRD/06_api/openapi.yaml` — OpenAPI 3.0.3 spec with all 30 confirmed endpoints
 `docs/PRD/06_api/api_examples.json` — 10 example request/response payloads
 `docs/PRD/06_api/error_contracts.json` — ErrorEnvelope schema + 7 standard error codes
 `docs/PRD/06_api/metadata.json` — Phase metadata with architecture details

### Key Patterns & Conventions
 All responses use SuccessEnvelope with `status`, `data`, `meta` fields
 `meta` includes `gpu_used`, `cloud_calls`, `processing_time_ms` for every response
 Only `/memory/query` makes cloud calls (qwen3.5:cloud via Ollama cloud runtime)
 GPU-heavy endpoints: `/memory/store`, `/memory/search`, `/memory/query`, `/debug/perception`, `/braille/read`, `/face/embeddings`
 All debug/system/session/export endpoints are GPU-free
 QR scanning is CPU-only (pyzbar/OpenCV)

### Architecture Observations
 30 total REST endpoints on port 8000 via FastAPI
 LiveKit WebRTC agent on port 8081 is NOT part of REST API (WebSocket/WebRTC)
 Auth is Bearer token for debug endpoints only (DEBUG_AUTH_TOKEN env var)
 No user auth — single-user assistive device
 Memory system is opt-in (MEMORY_ENABLED=false default, requires explicit consent)
 OllamaEmbedder.embed_text() is synchronous/blocking (ISSUE-022)

### GPU VRAM Budget (RTX 4060, 8GB)
 qwen3-embedding:4b: ~2GB
 YOLO v8n: ~200MB
 MiDaS v2.1: ~100MB
 EasyOCR: ~500MB
 Face detection: ~300MB
 Peak usage: ~3.1GB (leaves headroom)

### Prohibited Terms Check
 Scanned all generated files for OpenAI, Claude, Anthropic — zero matches found

### Successful Approaches
 Reading component_inventory.json lines 18-30 provided authoritative endpoint list
 LLD_modules.md GPU annotations mapped directly to x-gpu-usage fields
 data_model_inventory.json Pydantic models mapped cleanly to OpenAPI schemas
 Error codes designed around actual failure modes: GPU VRAM limits, cloud timeouts, model loading