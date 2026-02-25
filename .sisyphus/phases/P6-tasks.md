# Phase 6: Feature Evolution

> **Phase Focus**: Multi-region cloud sync for user profiles and memory, CLIP-based action recognition, reasoning engine MVP, multi-frame VQA reasoning.
> **Task Count**: 22 (T-111 through T-132)
> **Risk Classification**: HIGH for cloud sync architecture, conflict resolution, and integration closeouts; MEDIUM for reasoning modules and action recognition.
> **Priority Unlock**: T-111 Cloud Sync Architecture, T-117 CLIP Action Recognition, T-120 Reasoning Engine Foundation

---

## T-111: cloud-sync-architecture

- **Phase**: P6
- **Cluster**: CL-MEM
- **Objective**: Design and implement the cloud synchronization architecture for FAISS indices and SQLite user data. Create `core/memory/cloud_sync.py` with bidirectional sync protocol: local-to-cloud push, cloud-to-local pull, conflict detection using vector timestamps. Support eventual consistency model with configurable sync intervals (default: 5 minutes). Define data partitioning strategy: per-user indices for privacy isolation. Target sync completion under 2 seconds for incremental changes.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-112`, `T-113`, `T-131`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `docs/architecture.md#cloud-sync`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, foundational architecture
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-112: cloud-sync-faiss

- **Phase**: P6
- **Cluster**: CL-MEM
- **Objective**: Implement FAISS index synchronization between local and cloud storage. Support incremental sync: track added/removed vectors since last sync via change log. Implement merge strategy for concurrent modifications on different devices. Handle index format differences between GPU and CPU FAISS indices. Add checksum verification after each sync to detect corruption. Support S3-compatible and Azure Blob storage backends.
- **Upstream Deps**: [`T-111`]
- **Downstream Impact**: [`T-114`, `T-131`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `infrastructure/AGENTS.md`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, depends on sync architecture
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-113: cloud-sync-sqlite

- **Phase**: P6
- **Cluster**: CL-MEM
- **Objective**: Implement SQLite database synchronization for user profiles, consent records, and memory metadata. Use CRDT-inspired conflict resolution for concurrent writes. Implement WAL-based change capture for efficient incremental sync. Handle schema migrations gracefully during sync (version negotiation between local and cloud). Preserve data privacy: encrypt user data at rest and in transit during sync operations.
- **Upstream Deps**: [`T-111`]
- **Downstream Impact**: [`T-114`, `T-131`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `shared/utils/AGENTS.md`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: yes, independent from FAISS sync
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-114: cloud-sync-conflict-resolution

- **Phase**: P6
- **Cluster**: CL-MEM
- **Objective**: Implement comprehensive conflict resolution for cloud sync scenarios. Handle: simultaneous edits to same user profile (last-writer-wins with merge option), concurrent FAISS index modifications (union merge for additions, tombstone for deletions), network partition recovery (full resync with change replay). Create `core/memory/conflict_resolver.py` with pluggable resolution strategies. Log all conflicts with before/after state for audit trail. Target resolution time under 500ms per conflict.
- **Upstream Deps**: [`T-112`, `T-113`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `docs/architecture.md#conflict-resolution`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, needs both sync implementations
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-115: cloud-sync-privacy-controls

- **Phase**: P6
- **Cluster**: CL-MEM
- **Objective**: Add privacy controls to cloud sync. Implement user-level sync consent (opt-in per data category: memory, preferences, face embeddings). Add data residency configuration (restrict sync to specific regions). Implement right-to-erasure: cascade deletion across all synced locations within 24 hours. Add sync audit log showing what data was transferred, when, and where. Integrate with existing consent management from Phase 1.
- **Upstream Deps**: [`T-114`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `shared/config/AGENTS.md`, `docs/privacy.md`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs conflict resolution
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-116: cloud-sync-offline-queue

- **Phase**: P6
- **Cluster**: CL-MEM
- **Objective**: Implement offline operation queue for cloud sync. When network is unavailable, queue all local changes in a persistent write-ahead log. On reconnection, replay queued changes in order with conflict detection. Implement queue compaction to merge redundant operations (e.g., multiple edits to same record). Set maximum queue size (1000 operations) with oldest-first eviction. Monitor queue depth as a Prometheus metric.
- **Upstream Deps**: [`T-111`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/memory/AGENTS.md`, `docs/architecture.md#offline-queue`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, queue independent of FAISS/SQLite specifics
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-117: clip-action-recognition-model

- **Phase**: P6
- **Cluster**: CL-AUD
- **Objective**: Integrate CLIP-based action recognition for video clip analysis. Create `core/action/clip_recognizer.py` using OpenAI CLIP model to classify actions from short video segments (1-3 seconds). Define action vocabulary of 50 common indoor activities (walking, sitting, reaching, pointing, eating, etc.). Implement frame sampling strategy: extract 4 evenly-spaced frames per clip. Target classification latency under 200ms per clip. Support both zero-shot (text prompts) and fine-tuned classification modes.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-118`, `T-119`, `T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, Benchmark]
- **Doc Mutation Map**: [`core/action/AGENTS.md`, `docs/architecture.md#action-recognition`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent module
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-118: action-context-integration

- **Phase**: P6
- **Cluster**: CL-AUD
- **Objective**: Integrate action recognition results into the scene understanding pipeline. Combine detected actions with spatial perception (who is doing what, where) and memory context (has this person done this before). Create `core/action/action_context.py` that produces enriched action descriptions: "Person near the door is reaching for the handle" rather than just "reaching detected". Integrate with the VQA pipeline for action-aware question answering.
- **Upstream Deps**: [`T-117`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/action/AGENTS.md`, `core/vqa/AGENTS.md`]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs CLIP model
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-119: audio-event-detection

- **Phase**: P6
- **Cluster**: CL-AUD
- **Objective**: Implement audio event detection for environmental sound awareness. Create `core/audio/event_detector.py` that classifies ambient sounds: doorbell, knock, alarm, phone ring, glass breaking, dog barking, baby crying, appliance beeps. Use a lightweight audio classification model (YAMNet or AudioSet-based). Process audio in 1-second windows with 500ms overlap. Emit events with confidence scores and timestamp. Priority-sort events for TTS announcement (safety-critical first).
- **Upstream Deps**: []
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/audio/AGENTS.md`, `docs/architecture.md#audio-events`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent audio subsystem
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-120: reasoning-engine-foundation

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Build the reasoning engine MVP foundation. Create `core/reasoning/engine.py` with a multi-step reasoning pipeline: (1) perception aggregation (combine vision, audio, memory inputs), (2) context enrichment (add temporal history, user preferences), (3) inference (generate conclusions using LLM), (4) response formatting (adapt for TTS delivery). Implement the reasoning chain as a composable pipeline with pluggable stages. Target end-to-end reasoning completion under 300ms for cached contexts.
- **Upstream Deps**: []
- **Downstream Impact**: [`T-121`, `T-122`, `T-123`, `T-124`, `T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/reasoning/AGENTS.md`, `docs/architecture.md#reasoning-engine`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, foundational module
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-121: temporal-reasoning

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Add temporal reasoning capability to the reasoning engine. Implement a sliding window memory that tracks the last 30 seconds of perception results. Enable the engine to answer temporal questions: "Is anyone still near the door?", "Did the object move?", "How long has the alarm been ringing?". Create `core/reasoning/temporal.py` with event timeline tracking, change detection, and duration estimation. Use frame_id correlation to maintain temporal consistency.
- **Upstream Deps**: [`T-120`]
- **Downstream Impact**: [`T-124`, `T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/reasoning/AGENTS.md`, `docs/reasoning.md#temporal`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, depends on foundation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-122: spatial-reasoning

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Add spatial reasoning capability using the scene graph from VQA and depth maps from vision. Enable the engine to answer spatial questions: "What's between me and the table?", "Is the path to the door clear?", "How far is the nearest chair?". Create `core/reasoning/spatial.py` that constructs a 3D mental model from 2D detections + depth, supporting spatial relation queries (LEFT_OF, RIGHT_OF, BLOCKING, BEHIND, ABOVE, BELOW).
- **Upstream Deps**: [`T-120`]
- **Downstream Impact**: [`T-124`, `T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/reasoning/AGENTS.md`, `docs/reasoning.md#spatial`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent from temporal reasoning
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-123: causal-reasoning

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Add causal reasoning capability to infer cause-effect relationships from observations. Enable the engine to provide explanations: "The alarm is ringing because the door was opened", "That person might be leaving because they picked up their bag". Create `core/reasoning/causal.py` with a rule-based inference engine for common indoor scenarios, augmented by LLM for novel situations. Maintain a cause-effect knowledge graph of 100+ common indoor relationships.
- **Upstream Deps**: [`T-120`]
- **Downstream Impact**: [`T-124`, `T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/reasoning/AGENTS.md`, `docs/reasoning.md#causal`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes, independent reasoning module
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-124: reasoning-integration

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Integrate temporal, spatial, and causal reasoning modules into the unified reasoning engine. Create a reasoning orchestrator that selects appropriate reasoning modules based on query type and available context. Implement a confidence scoring system that combines evidence from multiple reasoning paths. Add explanation generation: each reasoning output includes a human-readable chain of evidence. Test with 20 representative indoor scenarios covering all reasoning types.
- **Upstream Deps**: [`T-121`, `T-122`, `T-123`]
- **Downstream Impact**: [`T-125`, `T-131`]
- **Risk Tier**: High
- **Test Layers**: [Unit, Integration, System]
- **Doc Mutation Map**: [`core/reasoning/AGENTS.md`, `docs/reasoning.md#integration`]
- **Versioning Impact**: minor
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, needs all reasoning modules
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-125: multi-frame-vqa

- **Phase**: P6
- **Cluster**: CL-VQA
- **Objective**: Extend VQA to support multi-frame reasoning. Instead of answering questions based on a single frame, accumulate context from the last 5 frames (2.5 seconds at 2fps). Enable answers that incorporate motion and change: "The person is walking toward you", "The door just opened". Create `core/vqa/multi_frame.py` with frame buffer management, change detection between consecutive frames, and multi-frame prompt construction for the VLM.
- **Upstream Deps**: [`T-124`]
- **Downstream Impact**: [`T-126`, `T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vqa/AGENTS.md`, `docs/vqa.md#multi-frame`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs reasoning integration
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-126: proactive-scene-narration

- **Phase**: P6
- **Cluster**: CL-VQA
- **Objective**: Implement proactive scene narration that automatically describes significant scene changes without waiting for user queries. Detect when major changes occur (new person enters, obstacle appears in path, environmental hazard detected) and generate TTS notifications. Implement a narration debouncer (minimum 5 seconds between notifications) to avoid overwhelming the user. Allow user to configure narration verbosity (minimal, normal, detailed) via voice command.
- **Upstream Deps**: [`T-125`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [`core/vqa/AGENTS.md`, `application/pipelines/AGENTS.md`, `docs/features.md#proactive-narration`]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no, needs multi-frame VQA
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-127: reasoning-test-suite

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Create comprehensive tests for all reasoning capabilities. Design 60 test scenarios covering: 15 temporal reasoning (motion tracking, duration estimation, event sequencing), 15 spatial reasoning (path finding, relation queries, distance estimation), 15 causal reasoning (cause-effect inference, prediction, explanation), 15 integrated reasoning (multi-modal, multi-frame, context-dependent). Each test includes input data, expected reasoning output, and confidence threshold.
- **Upstream Deps**: [`T-124`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, Regression]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `core/reasoning/AGENTS.md`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs reasoning integration
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-128: cloud-sync-test-suite

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Create comprehensive tests for cloud sync functionality. Test scenarios: normal sync (add/update/delete), conflict resolution (simultaneous edits, merge strategies), offline queue (queue operations, replay on reconnect, compaction), privacy controls (consent enforcement, data residency, right-to-erasure), performance (sync time < 2s for incremental, < 30s for full). Target 40 test functions covering all sync paths.
- **Upstream Deps**: [`T-115`, `T-116`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, Regression]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `core/memory/AGENTS.md`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs all sync components
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-129: action-recognition-test-suite

- **Phase**: P6
- **Cluster**: CL-RSN
- **Objective**: Create tests for action recognition and audio event detection. Test CLIP action classification accuracy on 50 sample video clips (target > 80% accuracy on top-3 predictions). Test audio event detection on 30 sample audio clips (target > 85% accuracy). Test integration of action context with scene understanding. Test priority sorting of audio events. Target 25 test functions.
- **Upstream Deps**: [`T-118`, `T-119`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration, Benchmark]
- **Doc Mutation Map**: [`tests/AGENTS.md`, `core/action/AGENTS.md`, `core/audio/AGENTS.md`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs action + audio modules
- **Execution Environment**: Local GPU
- **Current State**: not_started

---

## T-130: p6-feature-documentation

- **Phase**: P6
- **Cluster**: CL-GOV
- **Objective**: Document all Phase 6 features: cloud sync architecture and configuration, action recognition capabilities and vocabulary, reasoning engine architecture and reasoning types, multi-frame VQA and proactive narration, audio event detection configuration. Update AGENTS.md with new module descriptions. Create user-facing feature documentation explaining new capabilities. Add configuration guides for cloud sync and action recognition.
- **Upstream Deps**: [`T-126`, `T-127`]
- **Downstream Impact**: [`T-131`]
- **Risk Tier**: Low
- **Test Layers**: [Unit]
- **Doc Mutation Map**: [`docs/`, `AGENTS.md#documentation-coverage`, `core/reasoning/AGENTS.md`, `core/action/AGENTS.md`]
- **Versioning Impact**: none
- **Governance Level**: standard
- **Regression Sensitivity**: low
- **Parallelization Eligible**: no, needs features complete
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## T-131: p6-feature-integration-test

- **Phase**: P6
- **Cluster**: CL-TQA
- **Objective**: Integration closeout. Verify cloud sync + reasoning engine + audio event detection compose without regression. Run end-to-end scenarios: (1) user asks spatial question while action is detected, verify combined answer, (2) cloud sync completes while reasoning query is in progress, verify no interference, (3) audio event triggers proactive narration during active conversation, verify priority handling. Run full regression suite to confirm no degradation from P5 baseline.
- **Upstream Deps**: [`T-128`, `T-129`, `T-130`]
- **Downstream Impact**: [`T-132`]
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

## T-132: p6-cloud-sync-validation

- **Phase**: P6
- **Cluster**: CL-INF
- **Objective**: Integration closeout. Validate bidirectional FAISS/SQLite sync under realistic conditions. Test: (1) incremental sync completes under 2 seconds, (2) full resync completes under 30 seconds, (3) conflict resolution produces correct results for 10 conflict scenarios, (4) offline queue replays correctly after 100-operation accumulation, (5) privacy controls enforce consent correctly across sync boundaries. Produce a sync performance and correctness report.
- **Upstream Deps**: [`T-131`]
- **Downstream Impact**: []
- **Risk Tier**: High
- **Test Layers**: [Integration, System, Regression]
- **Doc Mutation Map**: [`tests/integration/AGENTS.md`, `docs/baselines/p6_sync_metrics.json`, `AGENTS.md#documentation-coverage`]
- **Versioning Impact**: none
- **Governance Level**: elevated
- **Regression Sensitivity**: high
- **Parallelization Eligible**: no, final phase validation
- **Execution Environment**: Hybrid
- **Current State**: not_started

---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Cloud sync operational: bidirectional FAISS/SQLite sync with conflict resolution
3. Action recognition integrated: CLIP-based classification with context enrichment
4. Reasoning engine MVP: temporal, spatial, and causal reasoning functional
5. Multi-frame VQA: answers incorporate motion and change from frame buffer
6. Audio event detection: 8+ ambient sound categories classified in real-time
7. Proactive narration: automatic scene change notifications with debouncing
8. 24-hour smoke test passing (all new features stable under continuous operation)
9. Test count >= 1000 (baseline + new feature tests)
10. Performance regression < 2% vs Phase 5 baseline

## Downstream Notes

- P7 security scanning must cover cloud sync data paths for encryption compliance
- P7 load test at 50 users must include cloud sync traffic
- P7 release notes must document all P6 features as new capabilities
- Reasoning engine architecture decisions set the foundation for future enhancement
