---
title: "Scope, Constraints & Assumptions — Voice & Vision Assistant for Blind"
section: 02
related_artifacts:
  - docs/analysis/component_inventory.json
  - docs/analysis/data_flows.md
  - docs/analysis/architecture_risks.md
  - docs/analysis/hybrid_readiness.md
---

# 02 Scope, Constraints & Assumptions

## 1. In Scope

The system includes the following features and capabilities as confirmed by technical artifacts:

1.  **Real-time Voice Interaction**: Bi-directional voice communication over LiveKit WebRTC.
2.  **Visual Question Answering (VQA)**: Multimodal scene analysis using qwen3.5:cloud and spatial perception fusion.
3.  **Spatial Obstacle Detection**: Real-time identification of hazards with micro-navigation audio cues.
4.  **QR and AR Scanning**: Detection and decoding of QR codes and ArUco markers using pyzbar and OpenCV.
5.  **Optical Character Recognition**: Text extraction with a 3-tier fallback (EasyOCR, Tesseract, MSER).
6.  **Braille OCR**: Specialized pipeline for translating physical Braille dots to digital text.
7.  **Face Detection**: Embedding generation and matching, subject to user consent.
8.  **RAG-based Memory**: Persistent storage and retrieval of past visual/audio experiences.
9.  **Internet Search**: External knowledge retrieval via DuckDuckGo.
10. **Virtual Avatar**: Integration with Tavus for optional visual representation.
11. **Audio Event Detection**: Environmental sound classification.
12. **REST API**: Over 30 endpoints for system management, debugging, and data export.
13. **Session Management**: Full lifecycle control including data import/export.
14. **Docker Deployment**: Containerized environment with local GPU support.
15. **CI/CD Pipeline**: Automated testing and linting via GitHub Actions.

## 2. Out of Scope

The following items are explicitly excluded from the current system requirements:

1.  **Visual User Interface**: No web or mobile frontend exists; the design is exclusively voice-first.
2.  **Multi-user Concurrency**: The system is designed as a single-user assistive device.
3.  **Horizontal Scaling**: No mechanisms for load balancing or multi-node distribution are present.
4.  **Offline LLM Fallback**: High-level reasoning requires an active connection to qwen3.5:cloud.
5.  **Real-time Video Output**: System output is restricted to audio streams; video tracks are ingest-only.
6.  **GPS/Location Services**: Geographic positioning is not integrated into the core pipeline.
7.  **Haptic Feedback**: All navigation cues and alerts are delivered via audio.
8.  **Multi-language TTS**: Voice synthesis is limited to default ElevenLabs configurations.

## 3. Constraints

1.  **GPU VRAM Limit**: Local inference is capped by the 8GB VRAM of the target NVIDIA RTX 4060.
2.  **Cloud Dependency**: STT, TTS, and LLM reasoning require stable internet connectivity.
3.  **Network Latency**: End-to-end performance is sensitive to WebSocket and HTTP response times.
4.  **Single-user Design**: Lack of multi-tenant isolation restricts deployment to individual devices.
5.  **FAISS Scaling**: Vector search is bounded at 5,000 records to maintain latency targets.
6.  **Runtime Environment**: Requires Python ≥ 3.10 and the CUDA toolkit for GPU acceleration.
7.  **Camera Specifications**: Hardware is assumed to provide a ~70° FOV; deviations may skew spatial accuracy.
8.  **Privacy Settings**: Memory features are disabled by default (MEMORY_ENABLED=false) and require explicit opt-in.

## 4. Assumptions

1.  **Hardware Availability**: An NVIDIA GPU with CUDA support is present for local inference tasks.
2.  **Ollama Services**: Local Ollama (embedding) and cloud Ollama (LLM) runpoints are available and provisioned.
3.  **LiveKit Infrastructure**: A LiveKit server is accessible with valid API credentials.
4.  **Cloud Provisioning**: API keys for Deepgram, ElevenLabs, and Tavus are valid and active.
5.  **Camera Performance**: The connected camera provides at least 640×480 resolution at a functional frame rate.
6.  **Model Assets**: YOLO and MiDaS ONNX weights are correctly placed in the `models/` directory.
7.  **Graceful Degradation**: CPU fallback is acceptable and functional when GPU acceleration is unavailable.
8.  **User Consent**: Features involving face embeddings and long-term memory require intentional user activation.
