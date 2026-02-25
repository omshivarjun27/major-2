# Phase 2: Architecture Remediation

> **Phase Focus**: God file decomposition (agent.py 1900 LOC to 4-5 modules), OllamaEmbedder async conversion, shared/__init__.py cleanup.
> **Task Count**: 15 (T-038 through T-052)
> **Risk Classification**: CRITICAL for agent.py decomposition, HIGH for async conversion and integration.
> **Priority Unlock**: T-038 Agent Session Manager Extract

---

## T-038: agent-session-manager-extract

- **Phase**: P2
- **Cluster**: CL-APV
- **Objective**: Extract session lifecycle management from agent.py into `apps/realtime/session_manager.py`. This module handles WebRTC session creation, teardown, and reconnection logic. The extraction isolates session state from the monolithic agent, giving each lifecycle phase a clear boundary. All session-related callbacks, timeout handlers, and participant tracking move into the new module. The agent coordinator will import and delegate to the session manager rather than embedding this logic inline. Backward compatibility with existing LiveKit session flows must be preserved throughout the extraction.
- **Upstream Deps**: [`BASE-015`]
- **Downstream Impact**: [`T-039`, `T-040`, `T-041`, `T-042`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`apps/realtime/AGENTS.md`, `AGENTS.md#technical-debt`, `docs/architecture.md#agent-modules`]
- **Versioning Impact**: minor
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, priority unlock task and first extraction from agent.py
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-039: agent-vision-controller-extract

- **Phase**: P2
- **Cluster**: CL-APV
- **Objective**: Extract vision processing logic from agent.py into `apps/realtime/vision_controller.py`. This module owns frame capture orchestration, model dispatch (YOLO, MiDaS, segmentation), and result aggregation for the real-time pipeline. The vision controller interfaces with `core/vision/` engines and `application/frame_processing/` components. It must support both synchronous single-frame analysis and streaming multi-frame workflows. All vision-related function routing, frame caching, and model selection logic currently embedded in agent.py moves here.
- **Upstream Deps**: [`T-038`]
- **Downstream Impact**: [`T-041`, `T-042`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`apps/realtime/AGENTS.md`, `docs/vision.md#controller`]
- **Versioning Impact**: minor
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on session manager extraction completing first
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-040: agent-voice-controller-extract

- **Phase**: P2
- **Cluster**: CL-APV
- **Objective**: Extract voice interaction logic from agent.py into `apps/realtime/voice_controller.py`. This module manages STT routing to Deepgram, TTS dispatch to ElevenLabs, and conversation state tracking. It owns the audio pipeline callbacks, silence detection handlers, and speech segmentation logic. The voice controller coordinates with `core/speech/` for voice routing and `infrastructure/speech/` for provider adapters. All voice-related state machines and audio buffer management currently inlined in agent.py move to this dedicated module.
- **Upstream Deps**: [`T-038`]
- **Downstream Impact**: [`T-041`, `T-042`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`apps/realtime/AGENTS.md`, `docs/speech.md#controller`]
- **Versioning Impact**: minor
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on session manager extraction completing first
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-041: agent-tool-router-extract

- **Phase**: P2
- **Cluster**: CL-APV
- **Objective**: Extract function routing and tool dispatch from agent.py into `apps/realtime/tool_router.py`. This module classifies incoming query types (visual, search, QR/AR, general) and maps them to the appropriate capability handler. It owns the intent classification logic, tool registration table, and response aggregation for multi-tool queries. The tool router depends on vision_controller and voice_controller being extracted first, since it dispatches work to both. All function-call definitions, parameter validation, and tool error handling currently scattered through agent.py consolidate here.
- **Upstream Deps**: [`T-039`, `T-040`]
- **Downstream Impact**: [`T-042`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`apps/realtime/AGENTS.md`, `docs/architecture.md#tool-routing`]
- **Versioning Impact**: minor
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, must follow both controller extractions
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-042: agent-coordinator-slim

- **Phase**: P2
- **Cluster**: CL-APV
- **Objective**: Slim agent.py down to a pure coordinator role under 500 lines of code. The coordinator imports session_manager, vision_controller, voice_controller, and tool_router, then wires their dependencies at initialization. It retains only the top-level LiveKit agent entrypoint, plugin registration, and cross-module error propagation. All 28 REST endpoints must remain functional through the coordinator's delegation layer. Backward compatibility with the existing `apps.realtime.entrypoint` launcher is mandatory. No business logic should remain in agent.py after this task.
- **Upstream Deps**: [`T-041`]
- **Downstream Impact**: [`T-043`, `T-048`, `T-051`]
- **Risk Tier**: Critical
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`apps/realtime/AGENTS.md`, `AGENTS.md#technical-debt`, `docs/architecture.md#agent-coordinator`]
- **Versioning Impact**: major
- **Governance Level**: critical
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final step in the agent decomposition chain
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-043: agent-split-test-suite

- **Phase**: P2
- **Cluster**: CL-APV
- **Objective**: Create a comprehensive test suite for the decomposed agent modules. Write unit tests for session_manager, vision_controller, voice_controller, and tool_router as isolated units. Write integration tests verifying all 28 REST endpoints still return correct responses through the coordinator delegation layer. Add WebRTC session lifecycle tests confirming creation, reconnection, and teardown paths work end-to-end. Target a minimum of 60 new test functions covering the 4 extracted modules and the slimmed coordinator.
- **Upstream Deps**: [`T-042`]
- **Downstream Impact**: [`T-049`, `T-051`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `tests/unit/apps/realtime/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, requires all extracted modules to exist
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-044: ollama-embedder-async

- **Phase**: P2
- **Cluster**: CL-MEM
- **Objective**: Convert OllamaEmbedder from synchronous to asynchronous execution. Replace blocking HTTP calls with aiohttp, add connection pooling for reuse across concurrent embedding requests, and implement proper async context management for cleanup. The current synchronous implementation blocks the event loop for approximately 150ms per call (PR-2), which is unacceptable in a real-time pipeline. After conversion, embedding calls must yield control to the event loop during network I/O. Add retry logic with exponential backoff for transient Ollama server errors. Preserve the existing embedding interface contract so callers don't need modification.
- **Upstream Deps**: [`T-020`]
- **Downstream Impact**: [`T-045`, `T-046`, `T-052`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `AGENTS.md#performance-risks`, `AGENTS.md#technical-debt`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, no file overlap with agent decomposition tasks
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-045: llm-client-async

- **Phase**: P2
- **Cluster**: CL-MEM
- **Objective**: Convert LLM client calls to async across the Ollama adapter and SiliconFlow adapter in `infrastructure/llm/`. Ensure that reasoning calls, completion requests, and streaming responses all use async patterns consistently. Update `core/memory/llm_client.py` if it wraps infrastructure adapters synchronously. Add connection pooling and timeout configuration per provider. This closes the remaining synchronous LLM call paths that T-044 doesn't cover, giving the entire LLM interaction layer non-blocking behavior.
- **Upstream Deps**: [`T-044`]
- **Downstream Impact**: [`T-046`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/llm/AGENTS.md`, `core/memory/AGENTS.md`, `docs/architecture.md#llm-async`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, operates on infrastructure/llm/ files independent of agent tasks
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-046: async-audit-sweep

- **Phase**: P2
- **Cluster**: CL-MEM
- **Objective**: Audit all remaining synchronous blocking calls across `core/` and `application/` layers. Search for `requests.get`, `requests.post`, `urllib`, synchronous `subprocess` calls, and any `time.sleep` usage that blocks the event loop in async contexts. Flag each finding with file path, line number, and blocking duration estimate. Convert any blocking calls found in hot-path code (detection pipeline, frame processing, RAG queries) to async equivalents. Produce a final audit report confirming zero blocking calls remain in latency-sensitive code paths.
- **Upstream Deps**: [`T-044`, `T-045`]
- **Downstream Impact**: [`T-050`, `T-052`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/AGENTS.md`, `application/AGENTS.md`, `docs/performance.md#async-audit`]
- **Versioning Impact**: patch
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, must follow both async conversion tasks to avoid rework
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-047: shared-init-cleanup

- **Phase**: P2
- **Cluster**: CL-APP
- **Objective**: Clean up `shared/__init__.py` to remove unnecessary re-exports and reduce coupling between the shared layer and its consumers. Audit every symbol exported from `shared/__init__.py`, identify which ones are actually imported by other modules, and remove dead exports. Organize remaining imports by functional group (config, logging, schemas, utils). Update all downstream import sites that relied on the convenience re-exports to import directly from submodules. This addresses TD-010 and makes the shared module's public API explicit rather than a grab bag of transitive imports.
- **Upstream Deps**: [`BASE-001`]
- **Downstream Impact**: [`T-048`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`shared/AGENTS.md`, `AGENTS.md#technical-debt`, `docs/architecture.md#shared-layer`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, operates on shared/ files with no overlap to agent or memory tasks
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-048: import-boundary-enforcement

- **Phase**: P2
- **Cluster**: CL-APP
- **Objective**: Verify and enforce all 5-layer import boundaries after the agent split and shared cleanup are complete. Run `lint-imports` and fix any violations introduced by the new module structure in `apps/realtime/`. Update `pyproject.toml` import-linter contracts if the new modules (session_manager, vision_controller, voice_controller, tool_router) need explicit boundary definitions. Confirm that no circular dependencies exist between the extracted agent modules. Validate that shared/ still imports only from the standard library, core/ only from shared/, and so on up the hierarchy.
- **Upstream Deps**: [`T-042`, `T-047`]
- **Downstream Impact**: [`T-050`, `T-051`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, Regression]
- **Doc Mutation Map**: [`pyproject.toml`, `AGENTS.md#architectural-risks`, `docs/architecture.md#import-boundaries`]
- **Versioning Impact**: patch
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, must wait for both agent slim-down and shared cleanup
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-049: agent-architecture-documentation

- **Phase**: P2
- **Cluster**: CL-GOV
- **Objective**: Document the new decomposed agent module architecture. Write clear descriptions of each module's responsibility: session_manager (lifecycle), vision_controller (perception dispatch), voice_controller (audio pipeline), tool_router (capability routing), and the coordinator (wiring and delegation). Update `apps/realtime/AGENTS.md` with the module map, data flow diagrams, and interface contracts. Add a migration guide explaining how the monolithic agent.py was split, so future contributors understand the module boundaries.
- **Upstream Deps**: [`T-043`]
- **Downstream Impact**: [`T-050`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`apps/realtime/AGENTS.md`, `docs/architecture.md#realtime-agent`, `AGENTS.md#repository-structure`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, documentation work with no code file overlap
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-050: p2-tech-debt-reassessment

- **Phase**: P2
- **Cluster**: CL-GOV
- **Objective**: Reassess the technical debt register after all P2 changes are complete. Mark TD-001 (agent.py god file) as resolved if agent.py is under 500 LOC. Mark TD-003 (OllamaEmbedder sync blocking) as resolved if async conversion is verified. Mark TD-010 (shared/__init__.py re-exports) as resolved if cleanup is confirmed. Identify any new debt introduced during the refactoring and add it to the register with severity and fix-effort estimates. Update AGENTS.md Section 8 with the revised debt table.
- **Upstream Deps**: [`T-046`, `T-048`, `T-049`]
- **Downstream Impact**: []
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`AGENTS.md#technical-debt`, `AGENTS.md#architectural-risks`, `docs/tech-debt.md`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, documentation reassessment with no code file overlap
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-051: p2-god-file-split-validation

- **Phase**: P2
- **Cluster**: CL-APV
- **Objective**: Validate the agent.py decomposition meets all acceptance criteria. Confirm no single file in `apps/realtime/` exceeds 500 lines of code. Run the full test suite and verify all 28 REST endpoints return correct responses. Execute WebRTC session lifecycle tests confirming creation, reconnection, and teardown. Run `lint-imports` and confirm zero violations. Measure startup time regression (must not exceed 2x baseline). This is the first integration closeout task for Phase 2, covering the god file split chain.
- **Upstream Deps**: [`T-043`, `T-048`]
- **Downstream Impact**: [`T-052`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System, Regression]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, requires both test suite and boundary enforcement to be complete
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-052: p2-async-conversion-verification

- **Phase**: P2
- **Cluster**: CL-TQA
- **Objective**: Verify all blocking calls have been eliminated from latency-sensitive code paths. Run the async audit tool produced by T-046 as a regression check. Confirm OllamaEmbedder operates non-blocking by measuring event loop latency before and after embedding calls (target: < 5ms loop block). Profile the hot path end-to-end and verify that no synchronous HTTP calls remain in the detection, frame processing, or RAG query pipelines. Produce a final performance comparison report against the P0 baseline metrics from T-012. This is the second integration closeout task for Phase 2.
- **Upstream Deps**: [`T-046`, `T-051`]
- **Downstream Impact**: []
- **Risk Tier**: High
- **Test Layers**: [Integration, Benchmark, Regression]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `docs/baselines/p2_metrics.json`, `AGENTS.md#performance-assumptions`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final verification task depends on all prior work
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Zero failing tests across all `test_layers` specified by tasks in this phase
3. Every entry in every task's `doc_mutation_map` has been verified as updated
4. No unresolved `blocked` tasks remain
5. Regression suite shows no coverage drop compared to phase entry baseline
6. No file exceeds 500 lines of code (god file split confirmed)
7. OllamaEmbedder async conversion complete (blocking calls eliminated)
8. import-linter validation passes with zero violations
9. Module boundaries enforced, no circular dependencies

## Downstream Notes

- P3 circuit breakers depend on clean async patterns from T-044/T-045
- P4 performance work assumes agent.py is decomposed for targeted profiling
- P6 feature additions to the agent will target individual controller modules, not the monolith
- The event loop latency improvement from async conversion sets the baseline for P4 hot-path SLA validation
