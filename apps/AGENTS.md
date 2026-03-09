# apps/AGENTS.md
Application entrypoints: the only layer allowed to import from all other project layers.
**Services**: FastAPI REST (port 8000) and LiveKit WebRTC Agent (port 8081).

## WHERE TO LOOK
- `api/server.py` (745 LOC): FastAPI application hosting 28+ endpoints.
- `realtime/agent.py` (288 LOC): LiveKit agent coordinator with 8 `@function_tool` wrappers.
- `realtime/entrypoint.py`: LiveKit worker launcher and signal handler.
- `realtime/session_manager.py` (775 LOC): Session lifecycle orchestrator (connect, init, diagnostics, avatar).
- `cli/`: Re-exports debug tools from `shared/debug/`.

## FASTAPI ENDPOINTS
| Group | Gate | Routes |
|-------|------|--------|
| **Core** | Always | `GET /health` |
| **VQA** | `vqa_enabled()` | `/vqa/*` (ask, perception) |
| **Memory** | `memory_enabled()` | `/memory/*` (store, search, query, consent) |
| **QR/AR** | `qr_enabled()` | `/qr/*` (scan, cache, history) |
| **Face** | `face_enabled()` | `/face/*` (health, consent, forget) |
| **Debug** | `DEBUG_ENDPOINTS_ENABLED` | `/debug/*` (requires `require_debug_auth`) |
| **GDPR** | Always | `/export/data`, `/export/erase` |

## LIVEKIT AGENT TOOLS
The agent exposes the following function tools to the LLM:
- `search_internet`: Web search (SLA: none).
- `analyze_vision`: Visual description (SLA: <500ms).
- `detect_obstacles`: Spatial hazard detection (SLA: <200ms).
- `analyze_spatial_scene`: Full spatial perception scan.
- `get_navigation_cue`: Priority-sorted micro-navigation output.
- `scan_qr_code`: QR/AR tag scanning.
- `read_text`: OCR text extraction from camera frame.

## KEY CONVENTIONS
- **Fresh-Context Rule**: `userdata.clear_perception_cache()` is called on **every new user query** to ensure vision is never stale.
- **UserData Session State**: All per-session state (watchdog, debouncer, logger) is stored in the `UserData` dataclass.
- **Optional Imports**: All heavy modules (torch, FAISS) are wrapped in try/except with `_*_AVAILABLE` flags to allow the system to start even if dependencies are missing.
- **Debug Auth**: Debug endpoints require the `require_debug_auth` dependency. Set `DEBUG_AUTH_TOKEN` in `.env`.
