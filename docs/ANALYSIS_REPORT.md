# Analysis Report — Voice-Vision Assistant for Blind (v2)

**Date:** 2026-02-11 (updated 2026-02-12)  
**Author:** Automated Agent (Claude Opus 4.6)  
**Scope:** Full codebase audit + continuous video processing integration + always-on mode.

---

## 0. Module Inventory (Full)

### Camera Capture & Frame Buffer
- `live_frame_manager.py` — Ring-buffer publisher-subscriber for TimestampedFrame ✅
- `frame_orchestrator.py` — Per-frame concurrent perception dispatch + fusion ✅
- `worker_pool.py` — Async worker pools (WorkerPool, WorkItem, WorkResult) ✅
- `freshness.py` — Freshness gate (rejects frames > LIVE_FRAME_MAX_AGE_MS) ✅
- `debouncer.py` — Spoken-cue dedup (distance-delta, scene-graph hash) ✅
- `watchdog.py` — Camera & worker health monitor with spoken alerts ✅

### Perception
- `vqa_engine/perception.py` — MockObjectDetector, SimpleDepthEstimator, EdgeAwareSegmenter
- `vqa_engine/scene_graph.py` — SceneGraphBuilder with frame_id/timestamp_ms
- `vqa_engine/spatial_fuser.py` — Multi-source spatial fusion
- `vqa_engine/orchestrator.py` — PerceptionOrchestrator concurrent runner
- `vqa_engine/vqa_reasoner.py` — Template + LLM VQA
- `vqa_engine/api_endpoints.py` — /perception/frame, /vqa/ask
- `src/tools/spatial.py` — Spatial perception tools
- `src/tools/visual.py` — Visual analysis tools

### OCR (needs hardening)
- `ocr_engine/__init__.py` — Pipeline: CLAHE+bilateral+deskew, EasyOCR/Tesseract backend. Missing: install fallback, user-facing errors.

### Braille — **NOT IMPLEMENTED**

### QR/AR
- `qr_engine/` — pyzbar QR, ArUco tags, JSON cache, FastAPI router

### Memory (RAG)
- `memory_engine/` — config, embeddings (sentence-transformers/CLIP), FAISS indexer, ingest, retriever, rag_reasoner, llm_client (Claude+Ollama+Stub), api_endpoints, maintenance

### LLM
- `memory_engine/llm_client.py` — ClaudeClient (claude-opus-4-6-20250610), OllamaClient (qwen3-vl)
- `src/tools/ollama_handler.py` — Primary VQA LLM handler

### STT/TTS
- `speech_vqa_bridge/` — Deepgram STT, ElevenLabs TTS, voice router, voice pipeline

### Debug/Observability
- `debug_tools/` — session_logger, visualizer

### Scripts/Docker — **NONE EXIST**

---

## Key Issues Found

1. **Braille engine missing** — Feature 7 completely unimplemented
2. **OCR fallback incomplete** — No install hints, no OpenCV-only heuristic fallback
3. **easyocr/pytesseract NOT in requirements.txt** — guaranteed ModuleNotFoundError
4. **MEMORY_ENABLED defaults to True** — violates privacy-first mandate (should be False)
5. **No dependency-check scripts** — No scripts/ directory at all
6. **No Dockerfile** — No containerisation
7. **No braille/OCR test fixtures** — Test coverage gaps
8. **Missing test modules** — No test_ocr_fallbacks, test_braille_*, test_rag_claude, test_debug_endpoints

## Implementation Plan (Phases)

1. ✅ Analysis Report (this file)
2. OCR Hardening — engine.py, fallback, requirements, install script
3. Braille Engine — capture, segmenter, classifier, OCR, embossing guidance
4. Memory/RAG + Claude — fix defaults, persistent consent, enhanced RAG
5. Debug Endpoints — /debug/braille_frame, /debug/ocr_install
6. Scripts & Packaging — check_deps, install_ocr, Dockerfile
7. Tests — unit + integration for all new modules
8. Docs — README, scenario_analysis.md, changed_files_list.txt

## Risk Assessment

- EasyOCR download (2GB+) — HIGH in CI; mitigate with mock fallback
- Tesseract binary missing — HIGH on Windows; provide choco/brew/apt hints
- Braille accuracy — HIGH; stub classifier, needs real training data
- Claude API key missing — MEDIUM; fallback to Ollama/stub

---

## 1. Architecture Map

### 1.1 Camera Capture & Frame Buffer
| Component | File | Role |
|-----------|------|------|
| `VisualProcessor` | `src/tools/visual.py` | Captures frames from LiveKit `rtc.VideoStream`, stores single `latest_frame` slot |
| `convert_video_frame_to_pil()` | `src/tools/visual.py` | Converts ARGB `VideoFrame` → RGB PIL Image |

### 1.2 Perception Pipeline
| Component | File | Role |
|-----------|------|------|
| `SpatialProcessor` | `src/tools/spatial.py` | DETECT → SEGMENT → DEPTH → FUSE → NAVIGATE |
| `PerceptionOrchestrator` | `vqa_engine/orchestrator.py` | Concurrent detection+segmentation+depth |
| `MockObjectDetector` | `vqa_engine/perception.py` | Mock detector (caches by image size) |
| `YOLODetector` | `vqa_engine/perception.py` | ONNX/ultralytics YOLO |
| `EdgeAwareSegmenter` | `vqa_engine/perception.py` | Edge-based segmentation |
| `MiDaSDepthEstimator` | `src/tools/spatial.py` | MiDaS depth estimation |

### 1.3 Scene Graph, OCR, QR
| Component | File |
|-----------|------|
| `SceneGraphBuilder` | `vqa_engine/scene_graph.py` |
| `OCRPipeline` | `ocr_engine/__init__.py` |
| `QRScanner` / `QRDecoder` | `qr_engine/qr_scanner.py`, `qr_engine/qr_decoder.py` |

### 1.4 Embeddings / RAG Memory
| Component | File |
|-----------|------|
| `TextEmbedder` | `memory_engine/embeddings.py` |
| `FAISSIndexer` | `memory_engine/indexer.py` |
| `MemoryIngester` / `MemoryRetriever` | `memory_engine/ingest.py`, `memory_engine/retriever.py` |
| `RAGReasoner` | `memory_engine/rag_reasoner.py` |

### 1.5 STT / TTS / LLM
| Component | File |
|-----------|------|
| `SpeechHandler` | `speech_vqa_bridge/speech_handler.py` |
| `TTSHandler` | `speech_vqa_bridge/tts_handler.py` |
| `OllamaHandler` | `src/tools/ollama_handler.py` |
| `VQAReasoner` | `vqa_engine/vqa_reasoner.py` |

---

## 2. Stale-Frame & Caching Issues

### 2.1 No Frame Timestamps
- `VisualProcessor.latest_frame` has **no timestamp or frame_id**.
- `SceneGraph.timestamp` uses second-precision string `"%Y-%m-%dT%H:%M:%S"`.
- `PerceptionResult.timestamp` is also a string — no epoch ms.

### 2.2 Stale-Frame Code Paths
- `VisualProcessor._last_nav_output` / `_last_obstacles` cached without expiry.
- `VisualProcessor.process_spatial()` rate-limited by `SPATIAL_COOLDOWN_MS=300` — returns stale cache.
- `MockObjectDetector._cached` keyed by `(width, height)` — identical output for same-size images.
- `EdgeAwareSegmenter._mask_cache`, `SimpleDepthEstimator._depth_array_cache` keyed by dimensions.
- `VQAReasoner._cache` has 5s TTL.

### 2.3 Global State
- `UserData` dataclass is mutable session state with cached perception fields.
- `api_endpoints.py` uses module-level globals for all pipeline instances.

---

## 3. Implementation Plan

### New Modules
| Module | Purpose |
|--------|---------|
| `live_frame_manager.py` | Continuous capture, ring buffer, pub-sub, frame_id + timestamp |
| `worker_pool.py` | Async worker pool with backpressure |
| `frame_orchestrator.py` | Per-frame fusion, timestamp validation, downstream routing |
| `watchdog.py` | Camera stall detection, worker health |
| `debouncer.py` | Output deduplication with scene-graph hashing |
| `freshness.py` | Timestamp validation helpers, stale-frame assertions |
| `tests/test_live_pipeline.py` | Comprehensive tests |

### Files to Modify
- `src/config.py` — new config keys
- `src/tools/visual.py` — frame_id/timestamp, LiveFrameManager integration
- `src/tools/spatial.py` — remove stale caches, accept frame_id
- `src/main.py` — integrate new infrastructure, freshness checks
- `vqa_engine/orchestrator.py` — frame_id tracking
- `vqa_engine/scene_graph.py` — frame_id, epoch_ms timestamp
- `vqa_engine/perception.py` — remove stale caches
- `shared/__init__.py` — TimestampedFrame, frame_id in PerceptionResult
- `api_server.py` — health/debug/consent endpoints

---

## 4. Continuous Video Processing — Gap Analysis & Fix (v2)

**Date:** 2026-02-12

### 4.1 Problem Statement

All six pipeline infrastructure modules (`live_frame_manager.py`, `worker_pool.py`,
`frame_orchestrator.py`, `watchdog.py`, `debouncer.py`, `freshness.py`) were implemented
and individually unit-tested (429 tests passing), but **none were wired into the actual
runtime**. The system only processed frames on-demand when a user asked a question via
speech — there was no continuous capture, no background consumer loop, and no proactive
hazard announcements.

### 4.2 Gaps Found

| # | Gap | Severity | Location |
|---|-----|----------|----------|
| 1 | `LiveFrameManager.start()` never called as background task | CRITICAL | `src/main.py` `entrypoint()` |
| 2 | `FrameOrchestrator` never instantiated in runtime | CRITICAL | `src/main.py` `entrypoint()` |
| 3 | No continuous consumer loop (subscriber → orchestrator) | CRITICAL | Missing entirely |
| 4 | No proactive TTS announcer (always-on hazard alerts) | HIGH | Missing entirely |
| 5 | No `ALWAYS_ON` / `CONTINUOUS_PROCESSING` config flags | MEDIUM | `src/config.py` |
| 6 | Missing `POST /debug/live_frames` endpoint | LOW | `api_server.py` |
| 7 | Missing `GET /debug/frame_rate` endpoint | LOW | `api_server.py` |
| 8 | No integration tests for continuous processing | MEDIUM | `tests/` |

### 4.3 Root Cause

The infrastructure modules were developed as standalone components with comprehensive
unit tests, but the **integration layer** — wiring them together in `entrypoint()` — was
never completed. The `entrypoint()` function initialised debouncer and watchdog but
stopped short of creating background tasks for continuous capture and processing.

### 4.4 Fix Summary

| File | Change |
|------|--------|
| `src/config.py` | Added 5 config keys: `ALWAYS_ON`, `CONTINUOUS_PROCESSING`, `PROACTIVE_ANNOUNCE`, `PROACTIVE_CADENCE_S`, `PROACTIVE_CRITICAL_ONLY`. Added `get_continuous_config()`. |
| `src/main.py` | Added imports for `FrameOrchestrator`, `get_continuous_config`, `get_worker_config`. Wired `_livekit_capture()` → `LiveFrameManager.start()` → subscriber → `_continuous_consumer()` → `FrameOrchestrator.process_frame()`. Added `_proactive_announcer()` for TTS hazard alerts. All launched as `asyncio.create_task()` after `agent_session.start()`. |
| `api_server.py` | Added `POST /debug/live_frames` (buffer state, subscriber info, capture stats) and `GET /debug/frame_rate` (FPS, latency, stale ratio). |
| `tests/test_continuous_processing.py` | 30+ tests across 10 test classes covering: continuous capture, freshness enforcement, producer-consumer flow, watchdog heartbeats, debouncer suppression, hot-path latency, worker pool, config flags, always-on mode, fused results. |

### 4.5 Architecture (Post-Fix)

```
LiveKit VideoStream
       │
       ▼
  _livekit_capture()         ─── capture_fn for LiveFrameManager
       │
       ▼
  LiveFrameManager.start()   ─── background task: cadence_ms loop
       │
       ├── on_frame → watchdog.heartbeat("camera")
       │
       ▼
  FrameSubscriber.get_frame() ─── consumer pulls from async queue
       │
       ▼
  _continuous_consumer()      ─── background task
       │
       ├── FrameOrchestrator.process_frame(frame)
       │   ├── freshness gate (reject if > 500ms)
       │   ├── detector_fn (YOLO / Mock)
       │   ├── depth_fn (MiDaS / Simple)
       │   └── fuse → FusedFrameResult
       │
       ├── watchdog.heartbeat("orchestrator")
       │
       └── _latest_fused["result"] = result
                    │
                    ▼
  _proactive_announcer()      ─── background task (if ALWAYS_ON)
       │
       ├── cadence: PROACTIVE_CADENCE_S (default 2s)
       ├── freshness check on result
       ├── debouncer.should_speak() gate
       └── agent_session.say(cue) → TTS output
```

### 4.6 Config Reference

| Key | Default | Env Var | Description |
|-----|---------|---------|-------------|
| `ALWAYS_ON` | `true` | `ALWAYS_ON` | Keep system running without user input |
| `CONTINUOUS_PROCESSING` | `true` | `CONTINUOUS_PROCESSING` | Enable background frame processing |
| `PROACTIVE_ANNOUNCE` | `true` | `PROACTIVE_ANNOUNCE` | Auto-announce hazards via TTS |
| `PROACTIVE_CADENCE_S` | `2.0` | `PROACTIVE_CADENCE_S` | Seconds between proactive announcements |
| `PROACTIVE_CRITICAL_ONLY` | `false` | `PROACTIVE_CRITICAL_ONLY` | Only announce critical hazards |

### 4.7 Test Coverage

New test file: `tests/test_continuous_processing.py`

| Test Class | Tests | Area |
|------------|-------|------|
| `TestContinuousCapture` | 4 | Capture loop, ring buffer wrap, clean stop, inject |
| `TestFreshnessInContinuousLoop` | 4 | Fresh/stale frame check, safe_output, orchestrator rejection |
| `TestProducerConsumerFlow` | 3 | End-to-end pipeline, backpressure, multiple subscribers |
| `TestWatchdogContinuousMode` | 3 | Heartbeat alive, stale detection, on_frame callback |
| `TestDebouncerInContinuousMode` | 3 | Suppression, different cue pass, window expiry |
| `TestHotPathLatency` | 2 | ≤500ms budget, telemetry recording |
| `TestWorkerPoolContinuous` | 2 | Submit/collect, error handling |
| `TestContinuousConfig` | 2 | Config keys presence, defaults |
| `TestAlwaysOn` | 2 | Run without consumers, idle suppression |
| `TestFusedFrameResult` | 2 | Freshness metadata, telemetry |
