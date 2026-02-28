# Execution Order Strategy — Safe Task Sequencing and Parallelization

**Voice & Vision Assistant for Blind — 150-Task Orchestration Logic**

---

## 1. Safe Ordering Logic

Tasks follow a strict phase-based ordering model to ensure dependencies are satisfied and architectural integrity is maintained:

- **Phase Sequencing**: Tasks progress through Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 in strict order. Each phase must complete fully before the next phase begins.
- **Within-Phase Ordering**: Tasks within a single phase follow topological sort of their dependency DAG. A task executes only after all upstream dependencies are satisfied.
- **Independent Task Freedom**: If no dependency relationship exists between two tasks in the same phase, they may execute in any order or in parallel (subject to parallel task allowance rules below).
- **Cross-Phase Dependency Prohibition**: Cross-phase dependencies are strictly forbidden. If a Phase N task depends on a Phase M task where M > N, this indicates an architectural ordering error and must be corrected immediately.
- **Blocking Dependencies**: A task blocks all downstream tasks in its dependency chain until it completes successfully. Failed tasks halt all dependent tasks until the failure is resolved.

---

## 2. Parallel Task Allowance Rules

Task parallelization accelerates phase completion while preserving correctness and preventing resource contention:

**Eligibility Criteria for Parallel Execution**:
- **(a) File Independence**: Tasks modifying different files may run in parallel. Two tasks touching the same file must be serialized.
- **(b) Domain Clustering**: Tasks in different domain clusters (vision, memory, speech, face, audio, ocr, braille, qr, vqa, application, infrastructure, api, realtime, shared) may run in parallel unless they share upstream dependencies.
- **(c) Upstream Dependency Check**: Two tasks may run in parallel only if they have no shared upstream dependencies that would create a data-ordering risk.

**Parallelization Constraints**:
- **Maximum Parallel Tasks**: 3 concurrent tasks per phase. Exceeding this threshold causes context overload and increases defect likelihood.
- **File Conflict Detection**: Pre-execution analysis identifies all files touched by tasks in the current wave. Any file appearing in multiple tasks triggers automatic serialization of those tasks.
- **Module Conflict Guidelines**: Two tasks within the same core/ subdirectory (e.g., core/memory/) should be serialized unless architectural review explicitly certifies their independence.
- **Context Freshness**: After each task completes, re-evaluate remaining parallel tasks. Dependency graphs may shift as upstream tasks unblock new work.

---

## 3. Risk Classification Per Phase

Each phase carries inherent risk profiles that drive isolation, testing, and review requirements:

- **Phase 0 (Foundation Hardening)**: CRITICAL risk. Security changes, secrets migration, Docker hardening. Zero tolerance for defects. Single-task isolation mandatory.
- **Phase 1 (Core Completion)**: HIGH risk. Stub implementations, behavior changes, missing module completions. Increased testing required.
- **Phase 2 (Architecture Remediation)**: CRITICAL risk. God file refactoring, module splitting, structural changes. High regression potential.
- **Phase 3 (Resilience)**: MEDIUM risk. Circuit breakers, retry logic, graceful degradation. Additive changes with lower breakage risk.
- **Phase 4 (Performance)**: HIGH risk. Optimization, async conversion, resource tuning. Behavioral changes and timing dependencies.
- **Phase 5 (Operations)**: LOW risk. Monitoring infrastructure, logging, observability. Additive, non-critical changes.
- **Phase 6 (Features)**: MEDIUM risk. New functionality, expanded capabilities. Bounded by module boundaries.
- **Phase 7 (Hardening)**: HIGH risk. Release preparation, security scanning, production readiness. High visibility, low error margin.

---

## 4. Dependency Unlocking Strategy

Certain high-impact tasks serve as "unlock keys" that enable execution of many downstream tasks. Prioritizing unlock tasks accelerates the overall critical path:

**Priority Unlock Tasks**:
- **(a) Secrets Migration (Phase 0)**: Migrating 7 API keys from plaintext .env to vault/KMS unblocks all security-dependent tasks, cloud service circuit breakers, and compliance validations. Execute first within Phase 0.
- **(b) agent.py Refactoring (Phase 2)**: Splitting the 1900-line god file into 4-5 focused modules unblocks all realtime agent improvements, performance optimizations, and feature additions. Critical path milestone.
- **(c) Circuit Breaker Foundation (Phase 3)**: Implementing the foundational circuit breaker pattern unblocks per-service implementations for Deepgram, ElevenLabs, Ollama, LiveKit, and external APIs. Execute early in Phase 3.
- **(d) Monitoring Infrastructure (Phase 5)**: Establishing Prometheus/Grafana stack unblocks alerting, dashboard creation, SLA validation, and operational runbooks. Critical for production readiness.

**Unlock Execution Priority**: Within-phase ordering places unlock tasks immediately after all Phase N-1 dependencies are satisfied. Unlock tasks receive priority scheduling and should not be delayed by non-critical predecessor tasks.

---

## 5. High-Risk Task Isolation Method

Tasks classified as CRITICAL or HIGH risk must follow enhanced execution protocols to prevent regression and ensure quality:

**Isolation Requirements**:
- **(a) Single-Task Execution**: No parallel execution with other tasks. Dedicated execution window, no context switching.
- **(b) Pre/Post Regression Testing**: Execute full test suite before task start (baseline). Execute full test suite after task completion (validation). Compare results for any degradation.
- **(c) Explicit Rollback Plan**: Document step-by-step rollback procedure before starting task. Include git command sequence, file restoration steps, and database recovery if applicable.
- **(d) Architect Pre/Post Review**: Task requires architect sign-off before execution and comprehensive review immediately after completion. Review checklist: functional correctness, architectural compliance, no new technical debt, test coverage ≥85%.

**High-Risk Task Examples**:
- agent.py refactoring (Phase 2): 1900 LOC split into modules
- Secrets migration (Phase 0): API key relocation and vault setup
- OllamaEmbedder async conversion (Phase 4): Blocking call elimination
- Docker non-root hardening (Phase 0): Runtime user change
- FAISS index migration (Phase 1): Vector store restructuring

---

## 6. Stabilization Checkpoint Cycles

Periodic checkpoints ensure quality, prevent drift, and catch emerging issues early:

**Every 10 Tasks**:
- Execute full test suite: all 840+ test functions must pass
- Check documentation drift: verify AGENTS.md sections match codebase reality
- Update Memory.md metrics: LOC counts, stub inventory, technical debt register (Section 14)
- Verify module import compliance: import-linter validation

**Every Phase Boundary** (after Phase 0, 1, 2, etc.):
- Full regression test: all 840+ tests pass, no performance degradation >5%
- Documentation refresh: update AGENTS.md with phase completion notes, new technical debt items
- Update progress.md: mark completed tasks, adjust timeline if needed
- Changelog merge: consolidate git commits into human-readable phase summary
- Stakeholder communication: summary report on phase outcome, risks identified, next phase preview

**Every 50 Tasks** (major milestone):
- Comprehensive architecture review: verify 5-layer hierarchy compliance, identify new risks
- Performance benchmark run: measure hot path latency, VRAM usage, CPU utilization against targets
- Security scan: run SAST on code, DAST on APIs, dependency vulnerability check
- Technical debt assessment: review TD register, estimate remediation effort for new debt

---

## 7. Governance Review Gates

Phase transitions require explicit sign-off. Each gate defines concrete criteria that must be met before proceeding:

**Phase 0 → Phase 1 Gate** (Foundation Hardening Complete):
- All 7 API keys rotated and stored in vault/KMS (zero plaintext in .env)
- Docker containers running as non-root user confirmed
- Zero critical security issues from SAST scan
- Secrets management infrastructure verified operational

**Phase 1 → Phase 2 Gate** (Core Completion Verified):
- Stub count reduced below 10 items
- All 5 placeholder modules (storage, monitoring, event bus, session management, reasoning) have MVP implementations
- Test count ≥880 (baseline + 40 new tests)
- Documentation reflects 100% codebase coverage

**Phase 2 → Phase 3 Gate** (Architecture Remediation Complete):
- No file exceeds 500 lines of code (god file split confirmed)
- OllamaEmbedder async conversion complete (blocking calls eliminated)
- import-linter validation passes with zero violations
- Module boundaries enforced, no circular dependencies

**Phase 3 → Phase 4 Gate** (Resilience Baseline):
- All 6 cloud services (Deepgram, ElevenLabs, Ollama, LiveKit, Tavus, DuckDuckGo) have circuit breakers
- Fallback STT (Whisper local) functional and integrated
- Fallback TTS (Coqui or Edge TTS) functional and integrated
- Retry logic with exponential backoff implemented for all external calls

**Phase 4 → Phase 5 Gate** (Performance Validated):
- 500ms hot path SLA validated under concurrent load (load test ≥10 concurrent users)
- VRAM usage ≤3.5GB on RTX 4060 (headroom maintained for future features)
- CPU utilization <80% under peak load
- No memory leaks detected in 1-hour continuous operation test

**Phase 5 → Phase 6 Gate** (Operations Ready):
- Monitoring infrastructure live and collecting metrics (Prometheus scraping, Grafana dashboards)
- CD pipeline functional (automated deployment from main branch)
- Operational runbooks documented (incident response, degradation playbook, recovery procedures)
- Alert thresholds configured and tested

**Phase 6 → Phase 7 Gate** (Feature Completeness):
- All new features stable (24-hour smoke test passing)
- Test count ≥1000 (840 baseline + 160 new tests for new features)
- Performance regression <2% vs. Phase 5 baseline
- No critical or high technical debt introduced

**Phase 7 → Release Gate** (Production Readiness):
- SAST scan: zero critical and high findings
- DAST scan: zero critical and high findings
- Dependency vulnerability scan: zero critical and high findings
- Canary deployment successful (10% traffic for 2 hours, no errors)
- Full regression test suite passing (100% of 1000+ tests)
- Load test at 50 concurrent users, SLA maintained
- Runbooks executed and validated by operations team

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial release: 7 sections covering safe ordering, parallelization, risk classification, unlock strategy, isolation, checkpoints, and governance gates |

---

**End of Document**
