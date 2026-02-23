---
title: "Requirements Traceability Matrix"
version: 1.0.0
date: 2026-02-22T15:31:00Z
architecture_mode: hybrid_cloud_local_gpu
---

# Requirements Traceability Matrix

## 1. Introduction

The Requirements Traceability Matrix (RTM) is a management tool that ensures all functional requirements are tracked through the development lifecycle. It maps high-level requirements to their implementation modules, API interfaces, verification tests, monitoring metrics, and known issues or technical debt.

This matrix provides a holistic view of the system, allowing stakeholders to identify coverage gaps and ensure that every feature is properly documented, implemented, and verified.

### 1.1 Traceability Methodology

The traceability methodology employed in this system follows a forward-traceable approach:
1. **Requirements to Design**: Each Functional Requirement (FR) is mapped to one or more Low Level Design (LLD) modules.
2. **Design to Implementation**: Implementation is verified through API endpoints where applicable.
3. **Implementation to Verification**: Each component is exercised by one or more End-to-End (E2E) test cases.
4. **Verification to Operations**: Metrics and KPIs are defined to monitor the health and performance of the verified features in production.
5. **Continuous Improvement**: Gaps in traceability or identified implementation debts are captured in the prioritized backlog.

### 1.2 How to Read This Matrix

- **FR-ID**: The unique identifier for each functional requirement defined in the scope.
- **LLD Module(s)**: The low-level design modules responsible for implementing the requirement.
- **API Endpoint(s)**: The REST API routes associated with the feature.
- **E2E Test(s)**: The end-to-end test cases that verify the requirement's functionality.
- **Monitoring Metric(s)**: The key performance indicators and metrics collected during runtime.
- **Issue ID(s)**: Known bugs, security findings, or planned enhancements related to the requirement.
- **GAP**: Indicates a missing artifact or unlinked component that requires attention.

## 2. Functional Requirements Table

| FR-ID | Description | LLD Module(s) | API Endpoint(s) | E2E Test(s) | Monitoring Metric(s) | Issue ID(s) |
|:---|:---|:---|:---|:---|:---|:---|
| FR-001 | Real-time Voice Interaction | LiveKit WebRTC Agent, StreamingTTSCoordinator, VoiceRouter | GAP: No direct REST API (LiveKit WebRTC port 8081) | E2E-017, E2E-018, GAP: No E2E test for full voice flow | STT latency, TTS first audio chunk time, TTS total generation time | BACKLOG-004, BACKLOG-008, BACKLOG-023, BACKLOG-024 |
| FR-002 | Visual Question Answering (VQA) | FrameOrchestrator, PerceptionWorkerPool, PerceptionPipeline, SceneGraphBuilder, VQAReasoner, OllamaHandler | /debug/perception (via debug tag) | E2E-007, E2E-013 | Frame processing latency, Detection latency, Detection count per frame, LLM response time | BACKLOG-009, BACKLOG-026 |
| FR-003 | Spatial Obstacle Detection | PerceptionPipeline, SceneGraphBuilder, SpatialFuser, MicroNavFormatter, Debouncer | /debug/perception | E2E-007, E2E-013 | Depth estimation latency, Detection latency, Debounce suppression rate | BACKLOG-009, BACKLOG-017 |
| FR-004 | QR and AR Scanning | QRScanner, QRDecoder, CacheManager | /qr/scan, /qr/cache, /qr/history, /qr/debug | E2E-005, E2E-015, E2E-020 | GAP: No QR-specific metrics in monitoring plan | BACKLOG-003, BACKLOG-025 |
| FR-005 | Optical Character Recognition | OCRPipeline, PerceptionWorkerPool | GAP: Integrated into vision flow and WebRTC tools | GAP: No specific E2E test for general OCR | OCR success rate, OCR latency, EasyOCR success rate, Tesseract fallback rate, MSER heuristic fallback rate | GAP: No specific backlog item for OCR hardening |
| FR-006 | Braille OCR | BrailleOCR, PerceptionWorkerPool | /braille/read (inferred) | E2E-006 | GAP: No Braille-specific metrics in monitoring plan | GAP: No specific backlog item for Braille |
| FR-007 | Face Detection | FaceDetector, PerceptionWorkerPool | /face/consent, /face/embeddings | E2E-008 | GPU VRAM allocated (Face detector ~300MB) | GAP: No specific backlog item for Face |
| FR-008 | RAG-based Memory | MemoryIngester, OllamaEmbedder, FAISSIndexer, MemoryRetriever, RAGReasoner, LLMClient | /memory/store, /memory/search, /memory/query, /memory/consent | E2E-002, E2E-003, E2E-004, E2E-014, E2E-019 | FAISS query time, FAISS index size, Embedding generation latency, Memory store latency, RAG retrieval latency | BACKLOG-005, BACKLOG-012, BACKLOG-018, BACKLOG-022 |
| FR-009 | Internet Search | InternetSearch, LiveKit WebRTC Agent | GAP: Handled via WebRTC tool dispatch | GAP: No specific E2E test for internet search | LLM response time | GAP: No specific backlog item for search |
| FR-010 | Virtual Avatar | LiveKit WebRTC Agent (Tavus integration) | GAP: Configured via environment and WebRTC | GAP: No specific E2E test for avatar | GAP: No Tavus-specific metrics in monitoring plan | BACKLOG-013 |
| FR-011 | Audio Event Detection | GAP: Not explicitly listed in module specifications | /audio/health (indirect) | E2E-017 (indirect) | GAP: No audio event metrics in monitoring plan | GAP: No specific backlog item for audio events |
| FR-012 | REST API (System Management) | FastAPI REST Server | /health, /config, /export/full, /import/full, /debug/* | E2E-001, E2E-010, E2E-016, E2E-018 | GAP: No API-specific latency metrics in monitoring plan | BACKLOG-011 |
| FR-013 | Session Management | FastAPI REST Server, LiveKit WebRTC Agent | /session/create, /session/list, /export/full, /import/full | E2E-009, E2E-010 | GAP: No session metrics in monitoring plan | BACKLOG-007, BACKLOG-013 |
| FR-014 | Docker Deployment | GAP: Infrastructure concern (Dockerfile/Compose) | GAP: N/A | E2E-012 (GPU OOM recovery) | GPU utilization %, GPU VRAM peak | BACKLOG-002, BACKLOG-019 |
| FR-015 | CI/CD Pipeline | GAP: Infrastructure concern (.github/workflows) | GAP: N/A | GAP: CI executes all tests | Task failure rate | BACKLOG-006, BACKLOG-014, BACKLOG-015, BACKLOG-016, BACKLOG-020, BACKLOG-021 |

## 3. Detailed Traceability per Requirement

### FR-001: Real-time Voice Interaction
This requirement is the primary user interface, facilitating bi-directional communication.
- **Implementation**: Handled by the `LiveKit WebRTC Agent`, which orchestrates STT and TTS services. Intent classification is performed by `VoiceRouter`.
- **API**: Operates outside the REST API, using port 8081 for WebRTC signaling and media.
- **Verification**: Verified through component health checks (E2E-017, E2E-018) but lacks a full conversation flow test.
- **Metrics**: Heavily monitored for latency in the STT and TTS stages.

### FR-002: Visual Question Answering (VQA)
Provides high-level scene reasoning using multimodal cloud models.
- **Implementation**: Uses a cascade of local perception (YOLO, MiDaS) and cloud-based LLM reasoning (Ollama cloud). `VQAReasoner` synthesizes the scene graph into natural language.
- **API**: Exposed via `/debug/perception` for pipeline verification.
- **Verification**: Tested for processing speed (E2E-007) and concurrent load (E2E-013).
- **Metrics**: Performance is measured by end-to-end frame processing time and LLM response latency.

### FR-003: Spatial Obstacle Detection
Enables micro-navigation by identifying and tracking physical hazards.
- **Implementation**: Built upon `PerceptionPipeline` with specialized `SpatialFuser` for temporal tracking and `MicroNavFormatter` for cue generation.
- **API**: Verified through the perception debug endpoint.
- **Verification**: Shares test cases with VQA (E2E-007, E2E-013).
- **Metrics**: Focuses on depth estimation speed and the effectiveness of the `Debouncer` in preventing cue fatigue.

### FR-004: QR and AR Scanning
Decodes environmental markers for contextual information.
- **Implementation**: Utilizes `QRScanner` (OpenCV/pyzbar) and `QRDecoder` for payload classification. `CacheManager` provides offline persistence.
- **API**: Full lifecycle management through `/qr/*` endpoints.
- **Verification**: Comprehensive coverage with E2E-005 (scan), E2E-015 (TTL), and E2E-020 (cache).
- **Metrics**: Currently lacks specialized monitoring metrics in the primary plan.

### FR-005: Optical Character Recognition
General-purpose text recognition for reading labels and signs.
- **Implementation**: Features a 3-tier fallback engine (`OCRPipeline`) to ensure resilience across different lighting and focus conditions.
- **API**: Integrated into the vision agent; no standalone public endpoint documented.
- **Verification**: A significant testing gap exists for general-purpose OCR verification.
- **Metrics**: Tracked by success rate per tier and cumulative processing latency.

### FR-006: Braille OCR
Specialized engine for reading embossed Braille patterns.
- **Implementation**: A dedicated `BrailleOCR` module handles dot segmentation and grid-based classification.
- **API**: Accessible via the `/braille/read` endpoint for specialized capture.
- **Verification**: Explicitly tested by E2E-006.
- **Metrics**: No specialized Braille metrics defined in the current plan.

### FR-007: Face Detection
Identifies and tracks individuals to provide social context.
- **Implementation**: The `FaceDetector` generates identity embeddings using local GPU resources.
- **API**: Controlled via `/face/consent` and `/face/embeddings`.
- **Verification**: Privacy controls are verified by E2E-008.
- **Metrics**: Monitored via VRAM usage signatures (~300MB).

### FR-008: RAG-based Memory
Enables long-term persistence of visual and conversational experiences.
- **Implementation**: Combines `OllamaEmbedder`, `FAISSIndexer`, and `MemoryRetriever` for a privacy-first RAG pipeline.
- **API**: Comprehensive REST interface for storage, search, and consent management.
- **Verification**: Extensive testing across 5 E2E cases (E2E-002, 003, 004, 014, 019).
- **Metrics**: Deep telemetry on search performance and embedding generation.

### FR-009: Internet Search
Provides external knowledge grounding for user queries.
- **Implementation**: The `InternetSearch` module acts as a wrapper for DuckDuckGo, invoked as a tool by the vision agent.
- **API**: GAP: No REST endpoint; strictly agent-invoked.
- **Verification**: GAP: No automated E2E test currently exists.
- **Metrics**: Indirectly monitored via LLM response times when search results are included in the prompt context.

### FR-010: Virtual Avatar
Enhances social interaction through visual representation in video sessions.
- **Implementation**: Integrated via Tavus replicas within the `LiveKit WebRTC Agent`.
- **API**: Configurable through system environment variables.
- **Verification**: GAP: Testing is currently manual and lacks automated E2E coverage.
- **Metrics**: No specialized metrics are collected in the current monitoring plan.

### FR-011: Audio Event Detection
Classifies environmental sounds to alert the user of non-visual events.
- **Implementation**: Documented in system overviews but lacks detailed module specifications in LLD.
- **API**: Indirectly checked via `/audio/health`.
- **Verification**: Only verified via subsystem health checks (E2E-017).
- **Metrics**: GAP: No telemetry defined for sound classification performance.

### FR-012: REST API (System Management)
The administrative backbone for system control and diagnostics.
- **Implementation**: Built with FastAPI, providing a high-performance async interface.
- **API**: Over 30 endpoints covering health, configuration, and debugging.
- **Verification**: Core lifecycle verified by E2E-001, 010, 016, and 018.
- **Metrics**: GAP: General HTTP performance metrics are missing from the monitoring plan.

### FR-013: Session Management
Controls the lifecycle of user interactions and data persistence.
- **Implementation**: Orchestrated between the REST server and the WebRTC agent.
- **API**: Exposed via `/session/*` and `/export/*` endpoints.
- **Verification**: Tested by E2E-009 and E2E-010.
- **Metrics**: No session-specific metrics currently defined.

### FR-014: Docker Deployment
Ensures consistent system behavior across environments.
- **Implementation**: Provided via multi-stage Dockerfiles and Compose configurations for GPU acceleration.
- **API**: N/A (Infrastructure concern).
- **Verification**: Resilience to resource constraints tested by E2E-012.
- **Metrics**: Monitored via host-level GPU and memory utilization.

### FR-015: CI/CD Pipeline
Maintains code quality and deployment stability.
- **Implementation**: GitHub Actions workflows for testing, linting, and image building.
- **API**: N/A (Infrastructure concern).
- **Verification**: Validated by the successful execution of the test suite on every PR.
- **Metrics**: Tracked via task success/failure rates.

## 4. Gap Analysis

### 4.1 Documentation Gaps
- **Audio Event Detection (FR-011)**: This requirement lacks a detailed module specification in `LLD_modules.md`. While mentioned in the system overview, the internal methods and contracts are not documented.
- **REST API Metrics**: The `monitoring_plan.md` focuses heavily on domain-specific latencies but lacks general API performance metrics (e.g., request throughput, 5xx error rates, endpoint-specific latencies).

### 4.2 Testing Gaps
- **Voice Flow**: There is no dedicated E2E test case for the full bi-directional voice interaction flow (FR-001). Existing tests focus on component health rather than the conversational experience.
- **Internet Search (FR-009)**: No automated E2E verification exists for the internet search tool.
- **Virtual Avatar (FR-010)**: Verification of Tavus integration is currently manual.
- **General OCR (FR-005)**: While Braille OCR has a test, general text extraction lacks a formal E2E test case.

### 4.3 Monitoring Gaps
- **Specialized Metrics**: Features such as QR scanning, Braille reading, and Virtual Avatar integration lack specific telemetry points in the `monitoring_plan.md`.
- **Infrastructure Health**: Metrics for Docker container health and CI/CD pipeline performance are not integrated into the central monitoring system.

### 4.4 Implementation Debt
- **Security**: Backlog items BACKLOG-001, BACKLOG-002, BACKLOG-003, and BACKLOG-019 highlight critical security issues that impact the traceability of requirements to a secure baseline.
- **Reliability**: BACKLOG-004 identifies single points of failure for cloud services that jeopardize the reliability of FR-001, FR-002, and FR-008.

## 5. Glossary of Traceability Terms

- **RTM**: Requirements Traceability Matrix.
- **FR**: Functional Requirement.
- **LLD**: Low Level Design.
- **E2E**: End-to-End Test.
- **KPI**: Key Performance Indicator.
- **Backlog**: A prioritized list of work for the development team.
- **Gap**: A missing link between a requirement and its downstream artifacts.
- **RAG**: Retrieval-Augmented Generation.
- **VQA**: Visual Question Answering.
- **OCR**: Optical Character Recognition.
- **WebRTC**: Web Real-Time Communication.
- **FAISS**: Facebook AI Similarity Search.
- **STT**: Speech-to-Text.
- **TTS**: Text-to-Speech.
- **GPU**: Graphics Processing Unit.
- **VRAM**: Video Random Access Memory.
- **CI/CD**: Continuous Integration / Continuous Deployment.
- **PRD**: Product Requirements Document.

## 6. System Architecture Overview

The Voice & Vision Assistant follows a strict layered architecture as detailed in the technical documentation:
- **Interface Layer**: Contains the FastAPI REST Server and LiveKit WebRTC Agent.
- **Application Layer**: Handles use-case orchestration such as frame processing and TTS coordination.
- **Domain Layer**: Contains the core logic for perception, memory, and specialized OCR engines.
- **Infrastructure Layer**: Adapters for external services like Ollama, Deepgram, and ElevenLabs.
- **Shared Layer**: Cross-cutting utilities like logging, configuration, and shared schemas.

Tracing requirements across these layers ensures that high-level user features are correctly decomposed into manageable technical components.
