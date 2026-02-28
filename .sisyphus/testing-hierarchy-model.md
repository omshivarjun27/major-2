# Testing Hierarchy Model — 8-Layer Testing Framework

Voice & Vision Assistant for Blind — 150-Task Quality Assurance

---

## Overview

The testing hierarchy enforces progressive validation across 8 layers, from isolated unit tests to autonomous agent behavior validation. Each layer has explicit triggers, gating rules, and rollback enforcement. The framework prevents regression, validates SLA compliance, and ensures architectural integrity throughout the 150-task development lifecycle.

---

## Layer 1: Unit Tests

**Purpose**: Isolated function tests validating single-module behavior.

**Trigger**: Every code change (pre-commit hook).

**Gating**: Must pass before merge to main.

**Current Status**: 840 tests across unit/, integration/, performance/, realtime/ directories.

**Coverage Requirements**:
- Minimum 80% overall coverage
- 100% coverage for critical path modules: shared/schemas, core/vision, core/memory
- Coverage verification: pytest --cov=shared,core --cov-fail-under=80

**Framework**: pytest + pytest-asyncio

**Scope**: Individual functions, async coroutines, exception handling, edge cases.

**Key Test Modules**:
- shared/schemas: type validation, field constraints, serialization
- core/vision: YOLO inference, MiDaS depth, segmentation logic
- core/memory: FAISS indexing, embedding generation, SQLite CRUD
- core/ocr: 3-tier fallback chain execution, character recognition
- core/braille: dot segmentation, classification accuracy
- core/face: detection accuracy, embedding generation, consent state transitions

**Failure Recovery**: Developer fixes test and re-runs locally before commit.

---

## Layer 2: Integration Tests

**Purpose**: Cross-module workflow validation; ensures modules communicate correctly.

**Trigger**: Changes spanning 2+ modules or touching shared dependencies.

**Gating**: Blocks Phase transitions; must pass before marking phase complete.

**Test Location**: tests/integration/

**Core Integration Flows** (8 total):

1. **Perception Pipeline** — Frame ingestion → YOLO detection → MiDaS depth → segmentation → scene graph construction. Validates end-to-end spatial reasoning without external models.

2. **RAG Query Path** — Text input → embedding generation → FAISS search → SQLite retrieval → ranking → response generation. Validates memory workflow with mock embedder.

3. **OCR Fallback Chain** — Image → EasyOCR → Tesseract → MSER heuristics. Validates graceful degradation when primary OCR fails.

4. **QR Scan → Cache** — QR detection → barcode decode → TTL cache lookup → expiration + refresh. Validates offline operation and cache consistency.

5. **Face Consent → Detection** — Consent state check → face detection enable/disable → embedding generation. Validates privacy-gated workflows.

6. **Speech Pipeline** — Text input → voice style selection → ElevenLabs API call → audio buffer → playback routing. Validates voice synthesis workflow with mock API.

7. **Frame Processing** — Live frame capture → freshness check → fusion with previous frames → debouncing → worker pool dispatch → result aggregation. Validates application-layer orchestration.

8. **API Health** — /health endpoint triggers canary checks for YOLO, MiDaS, FAISS, Deepgram, ElevenLabs. Validates dependency readiness without blocking.

**Assertion Coverage**:
- Module A output matches Module B input schema
- Error propagation across module boundaries
- State consistency after workflow completion
- Fallback paths execute on expected failures

**Failure Recovery**: Integration test failure blocks further Phase work until root cause fixed and test passing.

---

## Layer 3: System Tests

**Purpose**: End-to-end pipeline validation with real GPU inference.

**Trigger**: Phase completion checkpoints (Phase 1, 2, 3 completion gates).

**Gating**: Blocks Phase advancement; requires on-device validation.

**Hardware Requirement**: NVIDIA RTX 4060 or equivalent GPU.

**Test Duration**: ~15 minutes per full run.

**Three Primary Paths**:

### Audio Path
- User voice input → Deepgram STT → Intent extraction → LLM reasoning → ElevenLabs TTS → Audio output
- Validates latency: 100ms STT + 300ms reasoning + 100ms TTS ≤ 500ms total
- Tests: speech clarity recognition, accent robustness, response coherence

### Vision Path
- Camera frame capture → YOLO detection → MiDaS depth estimation → edge-aware segmentation → scene graph construction → spatial reasoning → navigation cue generation
- Validates latency: ≤300ms pipeline, ≤50ms per model inference
- Tests: object detection accuracy (mAP ≥ 0.45 on custom dataset), depth map consistency, spatial relationship correctness

### Memory Path
- User query text → qwen3-embedding:4b embedding generation → FAISS similarity search across 5K indexed vectors → SQLite retrieval → RAG context assembly → answer synthesis
- Validates retrieval precision, embedding quality, answer relevance
- Tests: recall@K ≥ 0.75, MRR ≥ 0.60, answer semantic match ≥ 0.80

**Concurrent Load Testing**: Up to 3 simultaneous requests to validate single-instance capacity.

**Failure Recovery**: System test failure requires investigation, code fix, and re-run before Phase advancement.

---

## Layer 4: Regression Tests

**Purpose**: Before/after comparison ensuring no capability loss.

**Trigger**: Every task completion; mandatory Phase gate.

**Gating**: BLOCKING — no task completes if regression detected.

**Baseline Metrics**:
- Test count: 840 minimum (must not decrease)
- Code coverage: 80% minimum (must not decrease)
- VRAM peak: ≤3.1GB on RTX 4060 (must not increase >10%)
- Hot path latency: ≤500ms (must not exceed)

**Regression Test Execution**:

```
1. Capture baseline metrics (pre-task)
   - pytest --collect-only --quiet | wc -l → baseline test count
   - pytest --cov=shared,core --cov-report=term-only → baseline coverage %
   - nvidia-smi -l 1 → baseline VRAM profile
   - Benchmark hot path end-to-end latency

2. Execute task implementation

3. Re-run full test suite (840 tests)

4. Capture post-task metrics

5. Compare:
   - If test_count_post < test_count_baseline → FAIL
   - If coverage_post < coverage_baseline → FAIL
   - If vram_peak_post > vram_baseline * 1.10 → FAIL
   - If hotpath_latency > 500ms → FAIL

6. If regression detected:
   - Revert code + documentation changes atomically
   - Log failure reason in .sisyphus/notepads/issues.md
   - Task marked REJECTED
```

**Artifact Preservation**: Regression test logs stored in .sisyphus/test-results/regression-{timestamp}.json.

**Failure Recovery**: Automatic rollback + manual investigation required.

---

## Layer 5: Canary Tests

**Purpose**: Lightweight smoke tests for critical paths before deployment.

**Trigger**: Pre-deployment validation; manual operator trigger.

**Gating**: Blocks deployment if any canary fails.

**Test Duration**: ~30 seconds total.

**6 Critical Path Canaries**:

1. **/health endpoint** — GET /health returns 200 OK with {"status": "healthy"} payload. Timeout: 5s.

2. **YOLO model load** — core/vision/spatial.py YOLODetector initializes, loads model weights, inference succeeds on 640x480 dummy image in <200ms. Timeout: 10s.

3. **MiDaS model load** — core/vision/spatial.py DepthEstimator initializes, loads model, depth inference succeeds on 640x480 dummy in <150ms. Timeout: 10s.

4. **FAISS index init** — core/memory/indexer.py FAISSIndexer loads index from disk, searches for 5 dummy vectors in <50ms. Timeout: 5s.

5. **Deepgram connection** — infrastructure/speech/deepgram_adapter.py authenticates with API key, performs credentials validation (no actual transcription). Timeout: 5s.

6. **ElevenLabs connection** — infrastructure/speech/elevenlabs_adapter.py authenticates with API key, validates available voices endpoint. Timeout: 5s.

**Parallel Execution**: All 6 canaries run in parallel; any failure → deployment blocked.

**Failure Details**: Each canary logs exception trace + timestamp to .sisyphus/canary-{timestamp}.log.

**Recovery Path**: Fix root cause (model download, API credentials, network), re-run canaries.

---

## Layer 6: Benchmark Tests

**Purpose**: Performance SLA validation and regression detection.

**Trigger**: Phase 4+ completion; after performance-affecting code changes.

**Gating**: Warnings on threshold miss; informational for Phase 4+.

**Benchmark Suites**:

### Hot Path Latency (500ms SLA)
- STT latency: ≤100ms (transcribe 10-second audio clip)
- VQA latency: ≤300ms (scene graph generation on 640x480 image)
- TTS latency: ≤100ms (synthesize 50-word prompt)
- Total: ≤500ms cumulative

### Vision Pipeline (300ms SLA)
- YOLO v8n inference: ≤200ms on 640x480 frame
- MiDaS depth: ≤80ms on 640x480 frame
- Segmentation: ≤50ms on detection outputs
- Total pipeline: ≤300ms

### FAISS Search (50ms SLA)
- Query embedding: 5-10 vectors from 5K index
- Search latency: ≤50ms per query
- Retrieval accuracy: recall@10 ≥ 0.75

### VRAM Profile (3.1GB peak on RTX 4060)
- Idle baseline: <500MB
- YOLO loaded: +200MB → 700MB total
- MiDaS loaded: +100MB → 800MB total
- FAISS index loaded: +1.5GB → 2.3GB total
- Embedder active: +800MB → 3.1GB total (peak)
- Degradation acceptable: <3.5GB sustained

### Load Testing (Concurrent Requests)
- 3 simultaneous API requests
- Latency degradation: <50% increase vs single request
- Error rate: 0% (no failures under load)
- Framework: custom timing harness + optional Locust

**Threshold Violations**:
- Hot path >550ms (10% margin): WARNING
- Single pipeline >350ms: WARNING
- VRAM >3.5GB sustained: FAIL
- Concurrency latency >50% increase: WARNING

**Framework**: Custom timing harness in tests/performance/ + pytest-benchmark for micro-benchmarks.

**Artifact Output**: benchmarks-{phase}-{timestamp}.json with all metrics + thresholds for historical trending.

---

## Layer 7: Accessibility Validation

**Purpose**: Blind user experience testing; validates sensory substitution quality.

**Trigger**: Changes to audio output, navigation cues, spatial descriptions, or voice routing.

**Gating**: Manual review required; blocks Phase completion if significant regression.

**Automated Accessibility Tests**:

1. **Audio Feedback Clarity** — TTS output detectability, speech rate validation (120-150 WPM), pause timing between spatial descriptions (min 200ms).

2. **Spatial Description Accuracy** — Scene graph spatial relationships (left/right/center/far/near) match actual object coordinates within ±10% error margin.

3. **Response Latency** — End-to-end latency from voice input to audio output ≤500ms under all conditions.

4. **Graceful Degradation** — If YOLO fails → fallback to generic object description. If TTS fails → retry with alternative voice. If memory query fails → generic response provided (not error).

5. **Navigation Cue Continuity** — Updates to spatial cues every 1-2 seconds during active navigation; no >2 second silent gaps during active session.

**Manual Testing Checklist**:
- [ ] Blind volunteer tester (external advisory group)
- [ ] Navigation in realistic environment (hallway, office, outdoor)
- [ ] Audio clarity and naturalness assessment
- [ ] Spatial description correctness validation
- [ ] Response coherence under stress (loud background noise, rapid movement)
- [ ] Session duration ≥30 minutes without fatigue

**Documentation**: Test results logged in .sisyphus/accessibility-{timestamp}.md with volunteer feedback transcript.

**Failure Recovery**: Accessibility regression requires design review + UX iteration before proceeding.

---

## Layer 8: Agent Validation

**Purpose**: Autonomous agent behavior testing; validates Memory.md and AGENTS.md structural integrity.

**Trigger**: Changes to Memory.md contract, AGENTS.md structure, or agent orchestration logic.

**Gating**: Informational; Phase transitions require sign-off.

**Validation Rules**:

### Memory.md Section Compliance
- Required sections present: Agent Context, Global Task Intelligence, Technical Debt, Risk Radar
- Each section has ≥3 subsections or tables
- All task IDs (e.g., "AR-1", "TD-001") properly formatted
- No circular task dependencies
- Task status values ∈ {pending, in_progress, completed, cancelled}

### AGENTS.md Template Compliance
- Sections 1-10 present in correct order
- All module paths valid (not placeholder stubs)
- Dependency flow matches declared 5-layer hierarchy
- No imports violating declared boundaries
- Risk Radar entries have Severity and Likelihood ∈ [1-5]
- Technology Decisions table includes "Why Selected" and "Alternatives Considered"

### Dependency Graph Validity
- Module import DAG is acyclic (verified by import-linter)
- Declared dependencies match actual imports
- No transitive circular dependencies across layers

### Documentation Drift Detection
- AGENTS.md module LOC counts ≤5% drift from actual
- Completed tasks section reflects actual completed work
- In-progress tasks sync with active branches
- Risk severity matches actual exploitability

**Agent Validation Script**:

```python
# Pseudocode
validate_memory_md_sections()  # Check required sections exist
validate_agents_md_structure()  # Verify 10-section format
validate_dependency_dag()      # Acyclic check via import-linter
validate_task_ids_consistency()  # All IDs well-formed
validate_coverage_tables()      # No missing modules
measure_documentation_drift()   # LOC and task sync
report_violations()             # JSON summary
```

**Threshold**: Documentation drift >5% on any metric → WARNING, >10% → FAILURE.

**Execution**: Automated as part of CI pipeline; reports logged to .sisyphus/agent-validation-{timestamp}.json.

---

## Execution Triggers Summary Table

| Layer | Trigger | Blocking? | Timeout | Artifact |
|-------|---------|-----------|---------|----------|
| 1: Unit | Every code change | Yes | 5 min | test-{timestamp}.log |
| 2: Integration | 2+ module changes | Yes (Phase gate) | 10 min | integration-{timestamp}.log |
| 3: System | Phase completion | Yes (Phase gate) | 15 min | system-{timestamp}.log |
| 4: Regression | Task completion | Yes (Task gate) | 10 min | regression-{timestamp}.json |
| 5: Canary | Pre-deployment | Yes | 30 sec | canary-{timestamp}.log |
| 6: Benchmark | Phase 4+ / perf change | No (warning) | 5 min | benchmarks-{timestamp}.json |
| 7: Accessibility | Audio/nav/voice changes | No (review gate) | N/A | accessibility-{timestamp}.md |
| 8: Agent | Memory/AGENTS/agent changes | No (sign-off) | 1 min | agent-validation-{timestamp}.json |

---

## Failure Severity Mapping

### Critical Failures (Block All Work)
- **Layer 1 Failure**: Unit test fails → Developer must fix before commit. No workarounds.
- **Layer 2 Failure**: Integration test fails → No Phase transition. Root cause analysis mandatory.
- **Layer 3 Failure**: System test fails → Phase blocked. Requires on-device investigation.
- **Layer 4 Failure**: Regression detected → Automatic code rollback + documentation rollback. Task marked REJECTED.

**Recovery**: Fix code, re-run layer, verify passing before task completion.

### High Failures (Block Deployment)
- **Layer 5 Failure**: Canary fails → Deployment blocked. Operational issue (credentials, network, model download).
- **Layer 6 Failure**: SLA exceeded significantly (>20% over threshold) → Performance investigation required before merge.

**Recovery**: Fix root cause, re-run canaries/benchmarks, retry deployment.

### Medium Failures (Require Review)
- **Layer 7 Failure**: Accessibility regression → UX review + design iteration required. Phase completion delayed.
- **Layer 8 Failure**: Documentation drift detected → AGENTS.md update required before task marking.

**Recovery**: Update documentation, re-validate, proceed with sign-off.

---

## Performance Regression Thresholds

### Latency Thresholds
| Metric | Yellow (Warning) | Red (Fail) | Notes |
|--------|------------------|-----------|-------|
| Hot path (500ms SLA) | >525ms | >550ms | 5% and 10% margins |
| YOLO inference | >220ms | >250ms | 300ms pipeline budget |
| MiDaS inference | >90ms | >120ms | 300ms pipeline budget |
| FAISS query | >60ms | >75ms | 50ms SLA + margin |
| TTS latency | >120ms | >150ms | 100ms SLA + margin |

### Resource Thresholds
| Metric | Yellow | Red | Notes |
|--------|--------|-----|-------|
| VRAM peak | >3.3GB | >3.5GB | 3.1GB baseline + margin |
| VRAM idle | >600MB | >800MB | Model overhead tracking |
| Test count change | -5% | -10% | Regression detection |
| Coverage change | -2% | -5% | Coverage floor |

### Quality Thresholds
| Metric | Yellow | Red | Notes |
|--------|--------|-----|-------|
| Test count decrease | ≥1 test removed | ≥5 tests removed | Failure if any removed |
| Coverage decrease | <80% | <75% | Minimum coverage gate |
| OCR accuracy (EasyOCR) | <90% | <85% | Character error rate |
| Detection mAP (YOLO) | <0.45 | <0.40 | Custom dataset baseline |

---

## Rollback Enforcement

### Automatic Rollback Triggers
1. **Regression Test Failure** → Test count decreased OR coverage decreased OR VRAM spike >10%
2. **System Test Failure** → End-to-end pipeline error detected
3. **Critical Layer Failure** → Layers 1-4 failures trigger rollback

### Rollback Procedure

```
1. Detect failure in test layer (e.g., test count 840 → 835)

2. Automatic actions:
   - git diff HEAD~1 HEAD → identify changed files
   - git revert HEAD --no-edit → atomically revert code changes
   - Revert task-related documentation edits in AGENTS.md/Memory.md
   - Document rollback reason in .sisyphus/notepads/issues.md

3. Log failure to rollback-{timestamp}.json:
   {
     "task_id": "...",
     "failure_layer": "Regression",
     "reason": "test_count_decreased",
     "tests_before": 840,
     "tests_after": 835,
     "reverted_files": [...],
     "timestamp": "2026-02-24T10:30:00Z"
   }

4. Notify developer:
   - Slack: "Task XYZ rolled back — {reason}. See .sisyphus/notepads/issues.md"
   - GitHub: Add comment to PR: "Rolled back due to {reason}"

5. Task status: REJECTED
   - Developer investigates root cause
   - Fixes and re-opens task
```

### Manual Rollback (Developer Override)
- Developer runs: `make rollback-task TASK_ID=xyz`
- Requires confirmation + reason entry
- Logs to .sisyphus/notepads/decisions.md with rationale

### Issue Documentation
All rollbacks documented in `.sisyphus/notepads/issues.md`:

```markdown
## Rollback: Task XYZ (2026-02-24)

**Reason**: Test count decreased from 840 → 835

**Failure Details**:
- Layer 4 (Regression) detected 5 test removal
- File: core/vision/spatial.py
- Tests affected: test_yolo_inference, test_midas_depth_batch, ...

**Root Cause**: (TBD by developer)

**Prevention**: (TBD by developer)

**Status**: Investigating
```

---

## Testing Philosophy

The 8-layer hierarchy reflects a progressive validation approach:

1. **Unit tests** catch logic errors immediately (developer feedback loop).
2. **Integration tests** catch module communication failures (architectural bugs).
3. **System tests** catch end-to-end failures (operational readiness).
4. **Regression tests** catch capability loss (quality floor enforcement).
5. **Canary tests** catch deployment blockers (operational safeguard).
6. **Benchmark tests** catch SLA violations (performance accountability).
7. **Accessibility tests** catch user experience regressions (mission alignment).
8. **Agent tests** catch documentation rot (architectural coherence).

**No layer can be skipped.** Each layer filters a different category of defects.

---

## Success Criteria

The testing framework succeeds when:

- ✅ All 840 unit tests passing consistently
- ✅ All 8 integration flows validated on task completion
- ✅ System tests validate all 3 primary paths (audio, vision, memory) end-to-end
- ✅ Zero regressions: test count, coverage, VRAM, latency maintained or improved
- ✅ Hot path latency ≤500ms sustained under 3-concurrent-request load
- ✅ VRAM peak ≤3.1GB on RTX 4060
- ✅ Canaries pass 100% of the time pre-deployment
- ✅ Accessibility tests pass with no user friction (external validation)
- ✅ Documentation drift <5% on all AGENTS.md metrics

---

**End of Document**
