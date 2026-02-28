# 150-Task Master Plan: Structural Architecture

This document defines the structural architecture for organizing and executing the next 150 tasks for the Voice & Vision Assistant for Blind. It establishes the containers, clusters, and workflows necessary to move from the current 62% beta status to a production-ready, resilient, and high-performance accessibility platform.

## Section 1: Macro Phases

The project progression is organized into eight sequential macro phases, each with specific entry and exit criteria to ensure architectural integrity and security before moving to higher-complexity features.

### Phase 0: Foundation Hardening
* **Focus**: Security remediation and technical debt baseline.
* **Entry Criteria**: Project exists in current 62% beta state with identified security gaps in `.env` and Docker configurations.
* **Exit Criteria**: All 7 plaintext API keys rotated and moved to a secured secret management flow; Docker non-root migration complete; zero critical security findings in SAST scans.
* **Technical Challenges**: Ensuring a smooth transition for local developers when moving from plaintext `.env` to encrypted or vaulted secrets.
* **Resource Allocation**: High focus on DevOps and Security specialists.
* **Estimated Task Count**: 12 tasks.

### Phase 1: Core Completion
* **Focus**: Filling functional gaps and architectural placeholders.
* **Entry Criteria**: Phase 0 security hardening complete and validated.
* **Exit Criteria**: 71 stubs across 9 modules addressed with functional logic; empty placeholder modules (reasoning, storage, monitoring, event_bus, session_mgmt) containing MVP implementations; global stub count < 10.
* **Technical Challenges**: Maintaining interface consistency across 5 new module implementations while avoiding circular imports.
* **Resource Allocation**: Balanced between Core Vision and Application Layer developers.
* **Estimated Task Count**: 25 tasks.

### Phase 2: Architecture Remediation
* **Focus**: Decoupling the god file and eliminating synchronous bottlenecks.
* **Entry Criteria**: Phase 1 core stubs filled and placeholders operational.
* **Exit Criteria**: `apps/realtime/agent.py` refactored into domain-specific controllers (no file > 500 LOC); `OllamaEmbedder` fully asynchronous with non-blocking event loop integration; circular dependencies eliminated via `shared/__init__.py` cleanup.
* **Technical Challenges**: Refactoring 1,900 LOC of real-time logic without breaking the WebRTC stream or increasing latency.
* **Resource Allocation**: Senior Backend/Architect focus.
* **Estimated Task Count**: 15 tasks.

### Phase 3: Resilience & Reliability
* **Focus**: Hardening external dependencies and implementing fallbacks.
* **Entry Criteria**: Phase 2 architecture remediation complete.
* **Exit Criteria**: Circuit breakers (Tenacity) implemented for all 6 cloud services (Deepgram, ElevenLabs, Ollama, LiveKit, Tavus, DuckDuckGo); functional local fallbacks for STT (Whisper) and TTS (Edge TTS) that activate within 2 seconds of cloud failure.
* **Technical Challenges**: Orchestrating uninterrupted fallback transitions during active voice sessions without user-perceivable lag.
* **Resource Allocation**: Infrastructure and Reliability Engineers.
* **Estimated Task Count**: 20 tasks.

### Phase 4: Performance & Validation
* **Focus**: Meeting the 500ms hot-path SLA under real-world conditions.
* **Entry Criteria**: Phase 3 resilience patterns operational and tested.
* **Exit Criteria**: Load tests (Locust) passing at target concurrency of 10 simultaneous users on RTX 4060; VRAM optimization via INT8 quantization complete; FAISS index scaling validated beyond 5,000 vectors within 50ms query latency.
* **Technical Challenges**: Balancing model precision loss during quantization against the critical 300ms vision processing budget.
* **Resource Allocation**: AI/ML Engineers and Performance Specialists.
* **Estimated Task Count**: 18 tasks.

### Phase 5: Operational Readiness
* **Focus**: Building the "run" side of the platform.
* **Entry Criteria**: Phase 4 performance targets met and documented.
* **Exit Criteria**: Prometheus/Grafana monitoring live with alerting thresholds for 5XX errors and latency spikes; automated CD pipeline functional for staging/production; documented incident runbooks and validated backup/restore procedures for FAISS and SQLite.
* **Technical Challenges**: Implementing real-time telemetry that doesn't add significant overhead to the hot-path processing loop.
* **Resource Allocation**: DevOps and SRE focus.
* **Estimated Task Count**: 20 tasks.

### Phase 6: Feature Evolution
* **Focus**: Moving beyond basic perception to high-level reasoning and sync.
* **Entry Criteria**: Phase 5 operational infrastructure stable and monitored.
* **Exit Criteria**: Multi-region cloud sync operational for user profiles and memory; advanced CLIP-based action recognition integrated; reasoning engine MVP providing contextual summaries across multiple frames.
* **Technical Challenges**: Managing state consistency across distributed memory indices in a hybrid local/cloud environment.
* **Resource Allocation**: Full-stack and AI researchers.
* **Estimated Task Count**: 22 tasks.

### Phase 7: Hardening & Release
* **Focus**: Final production validation and deployment.
* **Entry Criteria**: Phase 6 features stable and integrated into the main pipeline.
* **Exit Criteria**: Full regression suite (840+ tests) passing in CI with 90%+ coverage; automated SAST/DAST (Trivy/Snyk) scans clean; successful canary deployment to target hardware with zero rollback triggers.
* **Technical Challenges**: Coordinating final release artifacts across multiple entrypoints (REST API, WebRTC Agent, CLI).
* **Resource Allocation**: QA, Release Engineering, and Product Management.
* **Estimated Task Count**: 18 tasks.

## Section 2: Domain Clusters

Tasks are categorized into 14 domain clusters based on module boundaries and risk profiles. This clustering allows for focused context switching and specialized expertise application.

### CL-SEC: Security & Secrets
* **Functional Scope**: Encryption utilities, secret injection, non-root Docker hardening, PII scrubbing verification.
* **Key Dependencies**: `shared/utils/`, `.env`, `Dockerfile`.
* **Risk Profile**: CRITICAL — Errors here lead to data breaches or service exposure.
* **Est. Tasks**: 12.

### CL-VIS: Core Vision
* **Functional Scope**: YOLO detection, MiDaS depth, edge-aware segmentation, spatial fusion logic.
* **Key Dependencies**: `core/vision/`, ONNX Runtime, GPU drivers.
* **Risk Profile**: MEDIUM — Performance regressions impact the core user value proposition.
* **Est. Tasks**: 8.

### CL-MEM: Core Memory
* **Functional Scope**: FAISS indexing, RAG retrieval, cloud synchronization, embedding generation.
* **Key Dependencies**: `core/memory/`, SQLite, Ollama.
* **Risk Profile**: HIGH — Data corruption or slow retrieval breaks the context-aware reasoning.
* **Est. Tasks**: 14.

### CL-VQA: Core VQA
* **Functional Scope**: Scene graph construction, multimodal perception orchestration, visual reasoning.
* **Key Dependencies**: `core/vqa/`, Qwen-VL.
* **Risk Profile**: MEDIUM — Logic errors lead to incorrect or hallucinated descriptions.
* **Est. Tasks**: 6.

### CL-OCR: Core OCR & Braille
* **Functional Scope**: 3-tier OCR fallback (EasyOCR, Tesseract, MSER), Braille segmentation and classification.
* **Key Dependencies**: `core/ocr/`, `core/braille/`.
* **Risk Profile**: LOW — Failures are usually local to the specific scan intent.
* **Est. Tasks**: 4.

### CL-FACE: Core Face
* **Functional Scope**: Face detection, tracking, person identification, consent-gated memory linking.
* **Key Dependencies**: `core/face/`.
* **Risk Profile**: MEDIUM — High privacy sensitivity requires careful implementation of consent logic.
* **Est. Tasks**: 6.

### CL-AUD: Audio & Action
* **Functional Scope**: Audio event detection, sound source localization, CLIP-based action recognition.
* **Key Dependencies**: `core/audio/`, `core/action/`.
* **Risk Profile**: MEDIUM — Environmental noise can lead to high false-positive rates.
* **Est. Tasks**: 8.

### CL-RSN: Core Reasoning
* **Functional Scope**: Advanced context-aware reasoning, multi-frame summary generation.
* **Key Dependencies**: `core/reasoning/` (placeholder).
* **Risk Profile**: HIGH — This is a new module with no existing base implementation.
* **Est. Tasks**: 8.

### CL-APP: Application Layer
* **Functional Scope**: Frame processing pipelines, debouncers, watchdog timers, event bus implementation.
* **Key Dependencies**: `application/`.
* **Risk Profile**: HIGH — 16 stubs in the core orchestrator impact system stability.
* **Est. Tasks**: 12.

### CL-INF: Infrastructure
* **Functional Scope**: Service adapters (STT, TTS, LLM), storage abstractions, monitoring instrumentation.
* **Key Dependencies**: `infrastructure/`.
* **Risk Profile**: HIGH — Cloud dependency failures must be handled gracefully here.
* **Est. Tasks**: 10.

### CL-APV: Apps & API
* **Functional Scope**: FastAPI server, LiveKit agent implementation, CLI debug tools.
* **Key Dependencies**: `apps/`.
* **Risk Profile**: CRITICAL — Contains the 1,900 LOC god file that coordinates all components.
* **Est. Tasks**: 12.

### CL-TQA: Testing & QA
* **Functional Scope**: Unit, integration, performance, and real-time pipeline tests.
* **Key Dependencies**: `tests/`.
* **Risk Profile**: HIGH — Insufficient testing masks regressions in high-complexity vision code.
* **Est. Tasks**: 14.

### CL-OPS: DevOps & Deployment
* **Functional Scope**: CI/CD pipelines, Docker multi-stage builds, environment validation scripts.
* **Key Dependencies**: `.github/`, `deployments/`, `scripts/`.
* **Risk Profile**: HIGH — Deployment failures block the release cycle and validation.
* **Est. Tasks**: 10.

### CL-GOV: Docs & Governance
* **Functional Scope**: Technical documentation, memory privacy policies, progress tracking.
* **Key Dependencies**: `docs/`, `AGENTS.md`.
* **Risk Profile**: LOW — Essential for long-term maintenance but non-functional.
* **Est. Tasks**: 8.

## Section 3: Lifecycle Waves

Execution follows a repeating four-wave cycle within each phase. This ensures that no code is written without analysis and no feature is finished without documentation.

1. **Research Wave (Analysis)**
   * **Activities**: Deep dive into existing module stubs; evaluation of library options (e.g., Tenacity for retries, Locust for load testing).
   * **Artifacts**: Research Logs, Architecture Decision Records (ADRs), benchmarking reports.

2. **Implementation Wave (Creation)**
   * **Activities**: Writing of modular, type-hinted Python 3.10+ code; concurrent creation of unit tests.
   * **Artifacts**: New feature code, updated configuration schemas, unit test suites.

3. **Hardening Wave (Verification)**
   * **Activities**: Execution of regression test suites; performance validation against the 300ms pipeline budget.
   * **Artifacts**: Test results, performance profiles, security scan reports, bug fix commits.

4. **Documentation Wave (Completion)**
   * **Activities**: Updating module-specific `AGENTS.md`; updating the memory engine documentation; finalizing changelogs.
   * **Artifacts**: Updated AGENTS.md files, Memory.md updates, technical debt register updates.

## Section 4: Scaling Strategy

To manage a high volume of tasks without compromising quality, the following rules apply to task granularity and execution:

### Task Granularity Rules
* **Atomic Scope**: Each task must modify exactly one logical component (e.g., one class, one service adapter).
* **LOC Limit**: No single implementation task should exceed 200 lines of changed code, excluding tests.
* **Self-Contained Verification**: Every task must include its own verification step (test or diagnostic run).

### Parallelization & Serialization
* **Sequential Critical Path**: Security hardening (Phase 0) and Agent refactoring (Phase 2) are strictly serialized.
* **Parallel Domain Tracks**: Core Vision, OCR, and Face modules can be developed in parallel once Phase 1 stubs are defined.
* **Dependency Gating**: Infrastructure stubs must be filled (Phase 1) before resilience patterns (Phase 3) are applied.

### Concurrency Controls
* **Branching Strategy**: Use short-lived feature branches targeting specific domain clusters.
* **Merge Criteria**: Mandatory passing of CI (Lint, Test, Import Linter) and peer review for any change in HIGH or CRITICAL risk clusters.

### Checkpoint Strategy
* **Integrity Validation**: Every 10 completed tasks, a full system integrity check is performed, including `import-linter` verification and `lsp_diagnostics` across all changed files.
* **VRAM Monitoring**: Peak VRAM usage must be logged after every major vision or memory change to ensure we stay within the 8GB target (current peak 3.1GB).

## Section 5: Risk-Adjusted Ordering

Execution priority is determined by the intersection of severity and architectural impact.

1. **The Critical Path (P0)**:
   * **Rationale**: Blocks security compliance and maintainability.
   * **Mitigation Path**: Rotate all keys immediately, then refactor the agent to enable concurrent development.
   * **Key Tasks**: Secrets migration, `agent.py` decoupling, async `OllamaEmbedder`.

2. **High-Risk Remediation (P1)**:
   * **Rationale**: High probability of system-wide failure if stubs remain unaddressed.
   * **Mitigation Path**: Fill stubs with MVP logic first, then iterate for performance.
   * **Key Tasks**: Application layer stubs, monitoring/storage placeholders, FAISS scaling.

3. **Medium-Risk Evolution (P2)**:
   * **Rationale**: Essential for the 500ms SLA and high-fidelity feedback.
   * **Mitigation Path**: Use research waves to validate model quantization before full implementation.
   * **Key Tasks**: Action recognition, reasoning engines, cloud fallbacks, VRAM optimization.

4. **Low-Risk Polish (P3)**:
   * **Rationale**: Improves developer experience and long-term sustainability.
   * **Mitigation Path**: Documentation and cleanup tasks are batched to minimize context switching.
   * **Key Tasks**: Env-var documentation, Braille refinements, code cleanup.

## Section 6: Task Capacity Budget

The following table summarizes the distribution of the 150 tasks across the macro phases, ensuring a balanced workload and clear roadmap.

| Phase ID | Phase Name | Task Count | Primary Focus |
|:---------|:-----------|:-----------|:--------------|
| P0 | Foundation Hardening | 12 | Security & Secrets |
| P1 | Core Completion | 25 | Stubs & Placeholders |
| P2 | Architecture Remediation | 15 | God File & Async |
| P3 | Resilience & Reliability | 20 | Circuit Breakers & Fallbacks |
| P4 | Performance & Validation | 18 | SLA & VRAM Optimization |
| P5 | Operational Readiness | 20 | Monitoring & Backups |
| P6 | Feature Evolution | 22 | Cloud Sync & Reasoning |
| P7 | Hardening & Release | 18 | Regression & Deployment |
| **Total**| | **150** | |

### Burn-up Projection
The plan assumes a steady throughput of 10-15 tasks per week, resulting in a 10-15 week completion timeline for the full 150-task backlog. High-risk phases (P1, P2, P3) are expected to have a slower velocity due to complex refactoring requirements.

---
*End of Master Plan*
