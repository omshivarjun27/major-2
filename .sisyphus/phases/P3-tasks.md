# Phase 3: Resilience & Reliability

> **Phase Focus**: Circuit breakers for all 6 cloud services, local STT/TTS fallbacks, retry with exponential backoff, graceful degradation modes, health check endpoints.
> **Task Count**: 20 (T-053 through T-072)
> **Risk Classification**: HIGH for fallback implementations and failover orchestration, MEDIUM for per-service circuit breakers.
> **Priority Unlock**: T-053 Circuit Breaker Foundation

---

## T-053: circuit-breaker-foundation

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Implement the foundational circuit breaker pattern using Tenacity library. Create a reusable `CircuitBreaker` class in `infrastructure/resilience/circuit_breaker.py` with configurable failure thresholds, reset timeouts, half-open state probing, and event callbacks. The base implementation must support three states (closed, open, half-open) with configurable transition rules. Expose a decorator `@with_circuit_breaker(service_name)` for easy wrapping of external calls. Include metrics hooks for monitoring integration in Phase 5.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-054`, `T-055`, `T-056`, `T-057`, `T-058`, `T-059`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `docs/architecture.md#resilience`, `AGENTS.md#dependency-risks`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, priority unlock task for Phase 3
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-054: circuit-breaker-deepgram

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Wrap all Deepgram STT API calls with the circuit breaker pattern from T-053. Configure failure threshold at 3 consecutive failures, reset timeout at 30 seconds. Add health check probe that sends a minimal audio sample to verify Deepgram availability during half-open state. Log all state transitions for operational visibility. When circuit opens, emit an event that triggers the local STT fallback (T-060).
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-060`, `T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/speech/deepgram/AGENTS.md`, `AGENTS.md#dependency-risks`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, independent from other per-service circuit breakers after T-053
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-055: circuit-breaker-elevenlabs

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Wrap all ElevenLabs TTS API calls with the circuit breaker pattern. Configure failure threshold at 3 consecutive failures, reset timeout at 30 seconds. Add health check probe that requests a minimal TTS synthesis to verify ElevenLabs availability during half-open state. When circuit opens, emit an event that triggers the local TTS fallback (T-061).
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-061`, `T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/speech/elevenlabs/AGENTS.md`, `AGENTS.md#dependency-risks`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, independent from other per-service circuit breakers
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-056: circuit-breaker-ollama

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Wrap all Ollama LLM and embedding API calls with the circuit breaker pattern. Configure failure threshold at 5 consecutive failures (higher tolerance since Ollama is local), reset timeout at 15 seconds. Add health check probe using the `/api/tags` endpoint. Separate circuit breakers for reasoning calls vs embedding calls since they have different latency profiles and failure modes.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/llm/AGENTS.md`, `core/memory/AGENTS.md`, `AGENTS.md#dependency-risks`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent from other per-service circuit breakers
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-057: circuit-breaker-livekit

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Wrap LiveKit WebRTC connection management with the circuit breaker pattern. Configure failure threshold at 2 consecutive failures (low tolerance for real-time streaming), reset timeout at 60 seconds. Add reconnection logic with exponential backoff for session recovery. Handle mid-session failures gracefully by buffering audio and attempting reconnection before dropping the session.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`apps/realtime/AGENTS.md`, `AGENTS.md#dependency-risks`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, independent from other per-service circuit breakers
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-058: circuit-breaker-tavus

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Wrap Tavus virtual avatar API calls with the circuit breaker pattern. Configure failure threshold at 3 consecutive failures, reset timeout at 45 seconds. Since Tavus is optional (ENABLE_AVATAR=false by default), the circuit breaker should degrade gracefully to audio-only mode when the circuit opens. No local fallback needed, as avatar is a non-critical feature.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/tavus/AGENTS.md`, `AGENTS.md#dependency-risks`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, independent from other per-service circuit breakers
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-059: circuit-breaker-duckduckgo

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Wrap DuckDuckGo search API calls with the circuit breaker pattern. Configure failure threshold at 3 consecutive failures, reset timeout at 30 seconds. When circuit opens, return a helpful message to the user ("Internet search is temporarily unavailable") rather than failing silently. Cache recent search results for 1 hour as a partial fallback during outages.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Low
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/llm/AGENTS.md`, `AGENTS.md#dependency-risks`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: yes, independent from other per-service circuit breakers
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-060: fallback-stt-whisper

- **Phase**: P3
- **Cluster**: CL-APP
- **Objective**: Implement local Whisper-based STT fallback that activates when the Deepgram circuit breaker opens. Download and configure whisper-tiny or whisper-base model for edge deployment within VRAM budget. Create `core/speech/whisper_fallback.py` implementing the same STT interface as the Deepgram adapter. The fallback must activate within 2 seconds of circuit breaker trigger. Add VRAM management to load/unload the Whisper model dynamically to avoid persistent memory consumption when not in use.
- **Upstream Deps**: [`T-054`]
- **Downstream Impact**: [`T-065`, `T-071`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`core/speech/AGENTS.md`, `infrastructure/speech/AGENTS.md`, `AGENTS.md#dependency-risks`, `docs/architecture.md#fallbacks`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on Deepgram circuit breaker being complete
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-061: fallback-tts-edge

- **Phase**: P3
- **Cluster**: CL-APP
- **Objective**: Implement local TTS fallback using Edge TTS (or Coqui TTS) that activates when the ElevenLabs circuit breaker opens. Create `core/speech/edge_tts_fallback.py` implementing the same TTS interface as the ElevenLabs adapter. The fallback must activate within 2 seconds of circuit breaker trigger. Prioritize Edge TTS for its zero-GPU-cost execution; fall back to Coqui TTS if Edge TTS is unavailable. Voice quality will be lower but response time must remain under 500ms.
- **Upstream Deps**: [`T-055`]
- **Downstream Impact**: [`T-065`, `T-071`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`core/speech/AGENTS.md`, `infrastructure/speech/AGENTS.md`, `AGENTS.md#dependency-risks`, `docs/architecture.md#fallbacks`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on ElevenLabs circuit breaker being complete
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-062: retry-exponential-backoff

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Implement a reusable retry mechanism with exponential backoff and jitter for all external API calls. Create `infrastructure/resilience/retry_policy.py` using Tenacity with configurable parameters: max retries (default 3), base delay (default 1s), max delay (default 30s), jitter factor (default 0.5). Integrate with the circuit breaker so retries occur within closed/half-open states but not when the circuit is open. Add per-service retry configuration overrides in `shared/config/settings.py`.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-063`, `T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `shared/config/AGENTS.md`, `docs/architecture.md#retry-policy`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent utility module
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-063: retry-integration-all-services

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Apply the retry policy from T-062 to all 6 cloud service adapters (Deepgram, ElevenLabs, Ollama, LiveKit, Tavus, DuckDuckGo). Configure per-service retry parameters: real-time services (Deepgram, LiveKit) get max 2 retries with 500ms base delay; batch services (Ollama embedding, DuckDuckGo) get max 3 retries with 1s base delay; optional services (Tavus) get max 1 retry. Verify retry attempts are logged with service name, attempt number, and delay duration.
- **Upstream Deps**: [`T-062`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/speech/AGENTS.md`, `infrastructure/llm/AGENTS.md`, `infrastructure/tavus/AGENTS.md`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs retry policy module complete
- **Execution Environment**: Cloud
- **Current State**: not_started

---

## T-064: timeout-configuration

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Add explicit timeout configuration for all external API calls. Create a centralized timeout registry in `shared/config/settings.py` with per-service values: Deepgram STT (5s), ElevenLabs TTS (10s), Ollama reasoning (30s), Ollama embedding (15s), LiveKit connection (10s), LiveKit heartbeat (5s), Tavus (15s), DuckDuckGo (10s). Ensure timeouts trigger the retry mechanism before opening the circuit breaker. Add TIMEOUT_MULTIPLIER env var for testing environments.
- **Upstream Deps**: [`T-062`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`shared/config/AGENTS.md`, `AGENTS.md#performance-assumptions`, `docs/configuration.md#timeouts`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent configuration task
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-065: fallback-orchestrator

- **Phase**: P3
- **Cluster**: CL-APP
- **Objective**: Create a fallback orchestration layer in `application/pipelines/fallback_orchestrator.py` that coordinates failover between primary cloud services and local fallbacks. The orchestrator monitors circuit breaker states for Deepgram and ElevenLabs, and when either opens, transparently reroutes requests to the local Whisper or Edge TTS fallback. Handle mid-conversation failover without dropping the active voice session. Log all failover events with timestamps, service names, and recovery times.
- **Upstream Deps**: [`T-060`, `T-061`]
- **Downstream Impact**: [`T-066`, `T-071`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`application/pipelines/AGENTS.md`, `docs/architecture.md#fallback-orchestration`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, requires both fallback implementations
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-066: graceful-degradation-modes

- **Phase**: P3
- **Cluster**: CL-APP
- **Objective**: Define and implement 4 degradation modes for the system: FULL (all services online), DEGRADED-SPEECH (local STT/TTS active, cloud vision available), DEGRADED-VISION (cloud speech available, local vision only), MINIMAL (all local, no cloud). Create `application/pipelines/degradation_manager.py` that tracks current system mode based on circuit breaker states. Expose current mode via the REST API (`/health/mode` endpoint) and announce mode changes to the user via TTS.
- **Upstream Deps**: [`T-065`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`application/pipelines/AGENTS.md`, `apps/api/AGENTS.md`, `docs/architecture.md#degradation-modes`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs fallback orchestrator
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-067: health-check-endpoints

- **Phase**: P3
- **Cluster**: CL-APV
- **Objective**: Implement health check endpoints for all external services. Create `/health/services` endpoint returning per-service status (healthy, degraded, unavailable) based on circuit breaker states. Create `/health/ready` endpoint for Kubernetes-style readiness probes. Create `/health/live` endpoint for liveness probes. Each endpoint must respond within 100ms without triggering actual service calls (use cached circuit breaker state). Add aggregate health score (0-100) computed from individual service states.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`apps/api/AGENTS.md`, `AGENTS.md#operational-risks`, `docs/api.md#health-endpoints`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, only needs foundation circuit breaker
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-068: connection-pool-management

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Implement connection pool management for HTTP-based external services. Create shared aiohttp ClientSession pools in `infrastructure/resilience/connection_pool.py` with configurable limits per service: Deepgram (5 connections), ElevenLabs (3 connections), Ollama (10 connections, local with higher throughput), DuckDuckGo (3 connections), Tavus (2 connections). Ensure pools are properly initialized at startup and cleaned up at shutdown. Monitor pool utilization and log warnings when pools are near capacity.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `docs/architecture.md#connection-management`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, infrastructure utility
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-069: error-classification-framework

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Create an error classification framework that categorizes external service errors into: transient (retry), permanent (fail fast), rate-limit (backoff), and auth (alert). Implement `infrastructure/resilience/error_classifier.py` that examines HTTP status codes, exception types, and response bodies to classify errors. Map classification to circuit breaker behavior: transient errors increment failure count, permanent errors open circuit immediately, rate-limit errors trigger extended backoff, auth errors trigger alert without circuit change.
- **Upstream Deps**: [`T-053`]
- **Downstream Impact**: [`T-071`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`infrastructure/AGENTS.md`, `docs/architecture.md#error-handling`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, classification module independent
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-070: resilience-test-suite

- **Phase**: P3
- **Cluster**: CL-TQA
- **Objective**: Create a comprehensive test suite for all resilience components. Write chaos-style tests that simulate each cloud service failure mode: timeout, connection refused, 500 error, rate limit (429), auth failure (401/403). Verify circuit breaker state transitions (closed to open to half-open to closed) for each service. Test fallback activation timing (must be < 2 seconds). Test retry logic under various failure patterns. Test degradation mode transitions. Target minimum 40 new test functions covering the full resilience stack.
- **Upstream Deps**: [`T-063`, `T-065`, `T-066`]
- **Downstream Impact**: [`T-071`, `T-072`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, System, Regression]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `tests/unit/infrastructure/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs all resilience components implemented
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-071: p3-circuit-breaker-integration-test

- **Phase**: P3
- **Cluster**: CL-INF
- **Objective**: Integration closeout task. Trigger deliberate failures for Deepgram, ElevenLabs, and Ollama services and verify that: (1) circuit breakers open within the configured failure threshold, (2) fallback services activate within 2 seconds, (3) health endpoints reflect degraded state, (4) retry logic respects circuit breaker state, (5) graceful degradation mode transitions correctly. Produce a test report documenting pass/fail for each service's full failure-recovery cycle.
- **Upstream Deps**: [`T-070`]
- **Downstream Impact**: [`T-072`]
- **Risk Tier**: High
- **Test Layers**: [Integration, System, Regression]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final integration validation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-072: p3-failover-orchestration-validation

- **Phase**: P3
- **Cluster**: CL-APV
- **Objective**: Integration closeout task. Execute an end-to-end failover test: start a voice session, mid-conversation trigger Deepgram failure, verify Whisper fallback activates transparently, then trigger ElevenLabs failure, verify Edge TTS fallback activates. Measure total disruption time (target: < 2 seconds per failover). Verify the user receives a TTS notification of degraded mode. Test recovery: restore cloud services and verify the system returns to FULL mode within 60 seconds. Produce a performance comparison report: cloud vs fallback latency, quality metrics.
- **Upstream Deps**: [`T-071`]
- **Downstream Impact**: []
- **Risk Tier**: High
- **Test Layers**: [Integration, System, Regression]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `docs/baselines/p3_failover_metrics.json`, `AGENTS.md#performance-assumptions`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final phase validation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Zero failing tests across all `test_layers` specified by tasks in this phase
3. Every entry in every task's `doc_mutation_map` has been verified as updated
4. No unresolved `blocked` tasks remain
5. Regression suite shows no coverage drop compared to phase entry baseline
6. All 6 cloud services (Deepgram, ElevenLabs, Ollama, LiveKit, Tavus, DuckDuckGo) have circuit breakers
7. Fallback STT (Whisper local) functional and integrated
8. Fallback TTS (Edge TTS or Coqui) functional and integrated
9. Retry logic with exponential backoff implemented for all external calls
10. Graceful degradation modes defined and testable

## Downstream Notes

- P4 performance work assumes circuit breakers are in place, avoiding cascading failures during load tests
- P4 VRAM budget must account for Whisper model loading during fallback scenarios
- P5 monitoring infrastructure will consume the metrics hooks from the circuit breaker foundation (T-053)
- P5 alert thresholds will reference circuit breaker state transitions and fallback activation events
- P7 release gate requires all circuit breakers passing chaos testing
