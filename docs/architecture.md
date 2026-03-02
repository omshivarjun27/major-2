# Architecture Documentation

**Version**: 1.0.0 | **Date**: 2026-03-02

---

## System Overview

Voice & Vision Assistant is a real-time accessibility assistant for blind and low-vision users.
It combines speech recognition, computer vision, NLP, and audio synthesis into a single
voice-first experience accessible over WebRTC or REST.

---

## Layer Architecture

The codebase follows a strict five-layer architecture enforced by `import-linter`:

```
┌──────────────────────────────────────┐
│              apps/                    │  Entrypoints (API, realtime agent, CLI)
├──────────────────────────────────────┤
│          application/                 │  Use-case orchestration
├──────────────────────────────────────┤
│   core/          infrastructure/      │  Domain engines | External adapters
├──────────────────────────────────────┤
│              shared/                  │  Schemas, config, logging, utils
└──────────────────────────────────────┘
```

**Import rule**: each layer may only import from layers below it.

| Layer | May import | May NOT import |
|-------|-----------|----------------|
| `apps/` | all layers | — |
| `application/` | `core/`, `shared/` | `infrastructure/`, `apps/` |
| `core/` | `shared/` | `application/`, `infrastructure/`, `apps/` |
| `infrastructure/` | `shared/` | `core/`, `application/`, `apps/` |
| `shared/` | stdlib only | any project layer |

---

## Core Modules

| Module | Purpose | Key Class |
|--------|---------|-----------|
| `core/vqa/` | Visual Q&A — image description | `VQAEngine` |
| `core/vision/` | Spatial perception, YOLO, MiDaS depth | `SpatialPerceptionPipeline` |
| `core/memory/` | RAG memory — FAISS + Ollama embeddings | `MemoryIngester`, `MemoryRetriever` |
| `core/ocr/` | 3-tier OCR (EasyOCR → Tesseract → MSER) | `OCREngine` |
| `core/braille/` | Braille capture → segment → classify | `BrailleOCR` |
| `core/face/` | Face detection, tracking, recognition | `FaceDetector`, `FaceTracker` |
| `core/speech/` | TTS bridge, STT handler, voice router | `TTSHandler`, `VoiceRouter` |
| `core/audio/` | Audio event detection, sound localisation | `AudioEventDetector` |
| `core/qr/` | QR/AR scanning, offline TTL cache | `QRScanner` |
| `core/action/` | CLIP-based action recognition | `ActionRecognizer` |
| `core/reasoning/` | Query classification and reasoning engine | `ReasoningEngine` |

---

## Hot Path (≤ 500 ms)

```
User voice → STT (Deepgram, ≤100ms)
           → VoiceRouter (intent classification, ~5ms)
           → VQA / Spatial / QR / Search (≤300ms)
           → TTS (ElevenLabs / Edge, ≤100ms)
           → Audio output
```

---

## Infrastructure Adapters

| Adapter | External Service | Purpose |
|---------|-----------------|---------|
| `infrastructure/speech/deepgram.py` | Deepgram | Real-time STT |
| `infrastructure/speech/elevenlabs.py` | ElevenLabs | Neural TTS |
| `infrastructure/llm/ollama.py` | Ollama | LLM + VL inference |
| `infrastructure/tavus/` | Tavus | Virtual avatar in video calls |
| `infrastructure/resilience/circuit_breaker.py` | — | Circuit breaker pattern |

---

## Shared Schemas (canonical types)

All cross-layer data exchange uses types from `shared/schemas/`:

| Type | Purpose |
|------|---------|
| `Detection` | Object detection result (id, class, confidence, bbox) |
| `DepthMap` | Per-pixel depth array with `get_region_depth()` |
| `PerceptionResult` | Full pipeline output (detections + masks + depth) |
| `ObstacleRecord` | Fused obstacle: distance_m, direction, priority |
| `NavigationOutput` | TTS-ready navigation cue |
| `Priority` | Enum: CRITICAL / NEAR_HAZARD / FAR_HAZARD / SAFE |
| `Direction` | Enum: FAR_LEFT … FAR_RIGHT |

---

## Feature Flags

All optional features are controlled by `shared/config/settings.py`:

| Flag | Default | Feature |
|------|---------|---------|
| `spatial_enabled()` | true | Obstacle detection |
| `qr_enabled()` | true | QR/AR scanning |
| `face_enabled()` | false | Face recognition |
| `audio_enabled()` | false | Audio event detection |
| `action_enabled()` | false | Action recognition |
| `tavus_enabled()` | false | Virtual avatar |
| `cloud_sync_enabled()` | false | Cloud event sync |

---

## Deployment Architecture

```
┌─────────────────────────────────────┐
│          Docker Container           │
│  ┌─────────────┐  ┌──────────────┐  │
│  │  FastAPI    │  │  LiveKit     │  │
│  │  :8000      │  │  Agent :8081 │  │
│  └─────────────┘  └──────────────┘  │
│         │                │          │
│  ┌──────┴────────────────┴───────┐  │
│  │     Application Layer         │  │
│  │  (orchestration, pipelines)   │  │
│  └───────────────────────────────┘  │
│         │                           │
│  ┌──────┴───────────────────────┐   │
│  │     Core Engines             │   │
│  │  VQA / Vision / Speech / QR  │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
         │                 │
    Deepgram STT     ElevenLabs TTS
    Ollama VL        LiveKit WebRTC
```
