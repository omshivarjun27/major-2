---
title: "Product Overview — Voice & Vision Assistant for Blind"
section: 01
related_artifacts:
  - docs/analysis/component_inventory.json
  - docs/analysis/data_flows.md
---

# 01 Product Overview

## 1. Problem Statement

The Voice & Vision Assistant addresses the critical accessibility needs of blind and visually impaired users who require real-time audio descriptions of their environment to navigate and interact with the world independently. The system is designed with a voice-first interface, eliminating the need for a visual frontend. Users interact primarily through LiveKit WebRTC audio/video streams or a REST API, receiving immediate spoken feedback about obstacles, text, objects, and spatial context.

## 2. System Capabilities

Confirmed capabilities include:

- **Voice Q&A with Intent Routing**: A VoiceRouter handles 6 primary intent types including visual description, identification, spatial awareness, and general chat.
- **Spatial Obstacle Detection**: Real-time obstacle identification and micro-navigation using YOLO and depth estimation, providing priority-based TTS cues (Critical <1m, Near Hazard 1-2m, Far Hazard 2-5m).
- **QR/AR Scanning**: Decoding of QR codes and ArUco markers with a 3-level retry mechanism and offline cache, supporting classification of URLs, locations, and transport data.
- **OCR with 3-Tier Fallback**: Robust text recognition using EasyOCR, Tesseract, and MSER heuristics.
- **Braille OCR**: A specialized pipeline for capturing, segmenting, and classifying Grade 1 Braille.
- **Face Detection**: Consent-gated face detection and embedding storage.
- **RAG Memory**: A privacy-first, consent-gated memory system using FAISS and local embeddings (qwen3-embedding:4b).
- **Internet Search**: Real-time information lookup via DuckDuckGo.
- **Virtual Avatar**: Optional visual representation via Tavus (disabled by default).
- **Audio Event Detection**: Recognition of environmental audio cues.
- **Session Management**: Full support for session export/import and persistence.

## 3. User Types

- **Primary**: Blind / Visually Impaired individuals who interact with the system via voice and camera streams over LiveKit WebRTC.
- **Secondary**: Developers and integrators who consume the REST API for testing, debugging, and secondary application integration.

## 4. Operational Modes

- **Real-time Mode**: Powered by the LiveKit WebRTC Agent on port 8081, handling low-latency audio/video processing and voice synthesis.
- **REST API Mode**: Powered by a FastAPI server on port 8000, offering over 30 endpoints for QR scanning, memory management, and system debugging.

## 5. Hybrid Execution Model

| Concern | Location | Technology |
|---------|----------|-----------|
| LLM reasoning (VQA, RAG, chat) | Cloud | qwen3.5:cloud via Ollama cloud runtime (async HTTP) |
| Speech-to-text | Cloud | Deepgram (WebSocket) |
| Text-to-speech | Cloud | ElevenLabs (HTTP/WebSocket) |
| Real-time transport | Cloud | LiveKit (WebRTC) |
| Virtual avatar | Cloud | Tavus (HTTP + WebSocket) |
| Web search | Cloud | DuckDuckGo (HTTP) |
| Text embedding | Local GPU | qwen3-embedding:4b, Ollama local, RTX 4060 CUDA |
| Object detection | Local GPU | YOLO v8n, ONNX Runtime CUDA EP |
| Depth estimation | Local GPU | MiDaS v2.1 small, ONNX Runtime CUDA EP |
| OCR | Local GPU | EasyOCR, PyTorch CUDA |
| Face detection | Local GPU | PyTorch CUDA |
| QR decoding | Local CPU | pyzbar/OpenCV |
| Vector search | Local CPU/GPU | FAISS (in-process) |

## 6. High-Level Architecture Summary

The system is organized as a 5-layer monorepo: `shared → core → application → infrastructure → apps`.
- **apps/**: Entry points for the FastAPI REST server (8000) and LiveKit WebRTC Agent (8081).
- **application/**: Orchestrates the perception pipeline, worker pools, and frame management.
- **core/**: Implements domain-specific logic for VQA, OCR, Braille, and spatial perception.
- **infrastructure/**: Contains adapters for external cloud services and local ML runtimes.
- **shared/**: Provides common schemas, configuration, and logging utilities.

Strict import boundaries are enforced by an import-linter to maintain architectural integrity.

## 7. Performance Intent

- **End-to-end Latency**: ≤ 250ms per frame for perception.
- **Detection + Depth**: ≤ 250ms processing time.
- **TTS Responsiveness**: First audio chunk delivered within ≤ 300ms.
- **Frame Freshness**: 500ms threshold to prevent processing of stale data.
- **GPU Resource Management**: RTX 4060 target with a ~3.1GB peak VRAM budget and a 7/10 efficiency score.
