# Architecture Risk Assessment

## Overview

This document identifies architectural risks in the Voice & Vision Assistant,
categorized by severity and covering coupling, reliability, security, performance,
and maintainability concerns.

---

## 🔴 Critical Risks

### R1: Real API Keys Committed to Git

**Location**: `.env` (tracked in git)
**Details**: 7 real API keys found: LiveKit (URL, key, secret), Deepgram, ElevenLabs, Ollama, Tavus.
**Impact**: Credential leakage. Anyone with repository access has full API access.
**Mitigation**: Immediately rotate all keys. Add `.env` to `.gitignore`. Use secrets manager or CI environment variables.

### R2: Both Dockerfiles Run as Root

**Location**: `Dockerfile`, `deployments/docker/Dockerfile`
**Details**: Neither Dockerfile contains a `USER` instruction. Containers run as root.
**Impact**: Container escape vulnerability. Compromised process has full host access.
**Mitigation**: Add `RUN adduser --disabled-password appuser && USER appuser` after dependency installation.

### R3: No Input Sanitization on QR Payloads

**Location**: `core/qr/qr_scanner.py`, `core/qr/qr_decoder.py`
**Details**: System prompt specifies "no automatic click-through" for QR URLs, but scanner passes raw decoded data directly. No XSS/injection filtering on QR content before TTS output.
**Impact**: Malicious QR codes could inject harmful content into TTS output or trigger unintended actions.
**Mitigation**: Add payload sanitization layer in `QRDecoder` before content classification. Validate URL schemes, strip executable protocols.

---

## 🟠 High Risks

### R4: Single Points of Failure — External Services

**Location**: Multiple infrastructure adapters
**Details**:
- **Ollama cloud runtime** (qwen3.5:cloud): Required for all LLM reasoning (VQA, memory RAG). No local LLM fallback for inference.
- **Deepgram**: Sole STT provider. No backup STT (VOSK mentioned in system prompt but not implemented).
- **ElevenLabs**: Primary TTS. Fallback to local TTS is documented but relies on LiveKit plugin behavior, not explicit implementation.
**Impact**: Loss of any single service degrades or disables core functionality.
**Mitigation**: Implement explicit fallback STT (e.g., Whisper or VOSK). Add health-check probes for each service with circuit-breaker pattern.

### R5: FAISS Index — No Approximate Search

**Location**: `core/memory/indexer.py`
**Details**: Uses `IndexFlatL2` (exact brute-force search). `max_vectors=5000`.
**Impact**: O(n) search latency. At scale (>10K memories), search will exceed 250ms latency budget.
**Mitigation**: Migrate to `IndexIVFFlat` or `IndexHNSWFlat` for sub-linear search. Consider periodic index rebuild.

### R6: No Type Checker Configured

**Location**: `pyproject.toml` (absent mypy/pyright config)
**Details**: Heavy use of `Optional[Any]` and `Any` types throughout `UserData`, `FrameOrchestrator`, and `FusedFrameResult`. No static type enforcement.
**Impact**: Type errors caught only at runtime. Refactoring is high-risk. IDE support degraded.
**Mitigation**: Add `mypy` or `pyright` to CI. Start with `--warn-return-any` and gradually increase strictness.

### R7: In-Memory State Loss on Restart

**Location**: `apps/realtime/agent.py` (UserData), `core/vqa/spatial_fuser.py` (TrackedObject)
**Details**: All session state (`UserData`, tracked objects, debounce history, session logs) is stored in-memory. A process restart loses all context.
**Impact**: User's spatial context, conversation history, and tracking continuity lost on crash or deploy.
**Mitigation**: Persist critical session state to Redis or file-backed store. Implement session recovery on startup.

---

## 🟡 Medium Risks

### R8: Agent.py God Object

**Location**: `apps/realtime/agent.py` (1,900 lines)
**Details**: Single file contains: system prompt (272 lines), UserData dataclass (~30 fields), AllyVisionAgent class, all LiveKit function tools, spatial trigger logic, debounce logic, proactive mode, and session management.
**Impact**: Hard to test, modify, or review. High coupling between concerns. Single merge conflict bottleneck.
**Mitigation**: Extract into modules: `agent_prompts.py`, `agent_tools.py`, `agent_state.py`, `spatial_triggers.py`. Keep `agent.py` as thin orchestrator.

### R9: Hardcoded Camera Assumptions

**Location**: Multiple files
**Details**:
- FOV hardcoded at 70° (`SceneGraphBuilder.HORIZONTAL_FOV = 70.0`)
- Image width assumed 640px in `MicroNavFormatter._format_direction()`
- Default image size 640×480 in fallbacks
**Impact**: Navigation directions will be incorrect for cameras with different FOV. Distance calculations skewed.
**Mitigation**: Make FOV and resolution configurable via `config.yaml`. Pass actual camera metadata through the pipeline.

### R10: Duplicate Type Definitions

**Location**: `shared/schemas/__init__.py` vs `core/vqa/api_schema.py`
**Details**: Priority, Direction, BoundingBox, Detection, and ObstacleRecord are defined in both `shared/schemas` (dataclasses) and `core/vqa/api_schema.py` (Pydantic). Two parallel type hierarchies with slightly different names (`Priority` vs `PriorityLevel`, `Direction` vs `DirectionType`).
**Impact**: Serialization mismatches, confusion about canonical types, extra conversion code needed.
**Mitigation**: Use Pydantic models as the single source of truth, or generate API schemas from dataclasses via `pydantic.dataclasses`.

### R11: No Rate Limiting on API Endpoints

**Location**: `apps/api/server.py`
**Details**: FastAPI server exposes `/perception/frame`, `/vqa/ask`, `/memory/store`, `/memory/query`, etc. No rate limiting middleware.
**Impact**: Vulnerable to DoS. Heavy image processing + LLM calls are expensive.
**Mitigation**: Add `slowapi` or custom rate limiting middleware. Apply per-IP and per-endpoint limits.

### R12: Missing Encryption-at-Rest for FAISS Index

**Location**: `core/memory/indexer.py`
**Details**: `_get_enc` import exists for `shared.utils.encryption.get_encryption_manager`, but `FAISSIndexer.add()` and `_save()` do not actually encrypt stored data. `metadata.json` contains memory summaries in plaintext.
**Impact**: Memory summaries (potentially containing personal location/activity data) stored unencrypted on disk.
**Mitigation**: Wire encryption into `_save()` / `_load()`. Encrypt `metadata.json` and FAISS index file at rest.

### R13: No Graceful Shutdown

**Location**: `apps/realtime/agent.py`, `apps/api/server.py`
**Details**: No signal handler for SIGTERM/SIGINT. No cleanup of FAISS index, Tavus session, or tracked objects on shutdown.
**Impact**: Abrupt termination may corrupt FAISS index or leave dangling Tavus conversations.
**Mitigation**: Add `atexit` or signal handlers to flush FAISS, disconnect Tavus, and log final telemetry.

---

## 🟢 Low Risks

### R14: Test Import Errors (Stale Imports)

**Location**: `tests/unit/test_debug_endpoints.py`
**Details**: 13 test errors due to `import api_server` (stale module path; should be `from apps.api.server import app`).
**Impact**: 13 tests not running. Reduced coverage confidence.
**Mitigation**: Fix import to `from apps.api.server import app`.

### R15: Ruff Lint Backlog

**Location**: All Python files
**Details**: 3,674 lint issues (97.9% auto-fixable, mostly W293 whitespace warnings).
**Impact**: Noisy diffs. Developer friction. Pre-commit hooks may be disabled.
**Mitigation**: Run `ruff check . --fix && ruff format .` once. Enable pre-commit hook.

### R16: Bare `except:` Clauses

**Location**: `core/memory/rag_reasoner.py` (line 178, 238), various other files
**Details**: `except:` without specifying exception type catches KeyboardInterrupt and SystemExit.
**Impact**: May mask critical errors during development.
**Mitigation**: Replace with `except Exception:` at minimum.

### R17: Thread Safety of TemporalFilter

**Location**: `core/vqa/spatial_fuser.py`
**Details**: `TemporalFilter._tracks` dict mutated without locks. Safe only if called from a single asyncio event loop thread.
**Impact**: If `fuse()` is ever called from multiple threads (e.g., worker pool), race conditions on tracks.
**Mitigation**: Add `threading.Lock` or document single-thread constraint.

### R18: No Health Check for Embedding Service

**Location**: `core/memory/embeddings.py`
**Details**: `OllamaEmbedder` calls Ollama's embedding endpoint but has no startup health check or periodic liveness probe.
**Impact**: Silent failure if Ollama embedding model not loaded. Embeddings silently return zeros or error.
**Mitigation**: Add `is_ready()` method with probe on startup. Circuit-break on repeated failures.

---

## Risk Matrix Summary

| ID | Severity | Category | Component | Effort to Fix |
|----|----------|----------|-----------|---------------|
| R1 | 🔴 Critical | Security | `.env` | Low — rotate keys, add to .gitignore |
| R2 | 🔴 Critical | Security | Docker | Low — add USER instruction |
| R3 | 🔴 Critical | Security | QR Scanner | Medium — add sanitization layer |
| R4 | 🟠 High | Reliability | Infrastructure | High — implement fallback services |
| R5 | 🟠 High | Performance | Memory Engine | Medium — swap FAISS index type |
| R6 | 🟠 High | Maintainability | Build tooling | Medium — add mypy to CI |
| R7 | 🟠 High | Reliability | Agent state | High — add persistence layer |
| R8 | 🟡 Medium | Maintainability | Agent | Medium — extract modules |
| R9 | 🟡 Medium | Correctness | Perception | Low — make configurable |
| R10 | 🟡 Medium | Maintainability | Schemas | Medium — unify type definitions |
| R11 | 🟡 Medium | Security | API | Low — add rate limiting |
| R12 | 🟡 Medium | Security | Memory Engine | Medium — wire encryption |
| R13 | 🟡 Medium | Reliability | App lifecycle | Low — add signal handlers |
| R14 | 🟢 Low | Testing | Tests | Low — fix import path |
| R15 | 🟢 Low | Code Quality | All files | Low — auto-fix with ruff |
| R16 | 🟢 Low | Code Quality | Various | Low — specify exception types |
| R17 | 🟢 Low | Concurrency | Spatial Fuser | Low — add lock or document |
| R18 | 🟢 Low | Reliability | Embeddings | Low — add health check |

---

## Recommended Priority Order

1. **Immediate** (before next deploy): R1, R2
2. **Sprint 1**: R3, R4 (at least Deepgram STT fallback), R14, R15
3. **Sprint 2**: R5, R6, R8, R11
4. **Sprint 3**: R7, R9, R10, R12, R13
5. **Backlog**: R16, R17, R18


---

## GPU Infrastructure Notes

### GPU Hardware: NVIDIA RTX 4060 (8GB VRAM)

The system leverages local GPU acceleration for vision and embedding pipelines:

| Component | GPU Technology | VRAM Usage |
|-----------|--------------|------------|
| Object Detection (YOLO) | ONNX Runtime CUDA EP | ~200MB |
| Depth Estimation (MiDaS) | ONNX Runtime CUDA EP | ~100MB |
| Embedding (qwen3-embedding:4b) | Torch CUDA via Ollama | ~2GB |
| OCR (EasyOCR) | PyTorch CUDA | ~500MB |
| Face Detection | PyTorch CUDA | ~300MB |

### GPU Risk Considerations

- **VRAM Budget**: Total peak ~3.1GB of 8GB available. Safe headroom exists.
- **Backpressure**: WorkerPool must respect VRAM limits to prevent OOM.
- **Fallback**: All GPU models have CPU fallback paths (ONNX CPU EP, PyTorch CPU).
- **Concurrent Access**: ThreadPoolExecutor tasks share GPU; memory-safe batching required.
- **CUDA Availability**: System degrades gracefully to CPU if CUDA is unavailable.

### Cloud vs Local GPU Service Separation

| Service | Location | Protocol |
|---------|----------|----------|
| qwen3.5:cloud (LLM) | Cloud | Ollama cloud runtime, async HTTP |
| Deepgram (STT) | Cloud | WebSocket |
| ElevenLabs (TTS) | Cloud | HTTP/WebSocket |
| LiveKit (transport) | Cloud | WebRTC |
| Tavus (avatar) | Cloud | HTTP + WebSocket |
| DuckDuckGo (search) | Cloud | HTTP |
| qwen3-embedding:4b | Local GPU | Ollama local, HTTP |
| Vision models (YOLO, MiDaS) | Local GPU | ONNX Runtime CUDA EP |
| OCR models | Local GPU | PyTorch CUDA |
| Face detection | Local GPU | PyTorch CUDA |
| QR decoding | Local CPU | pyzbar/OpenCV |
| FAISS vector DB | Local CPU/GPU | In-process |