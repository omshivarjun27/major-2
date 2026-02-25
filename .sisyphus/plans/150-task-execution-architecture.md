# 150-Task Execution Architecture: Phase-Structured, Batch-Controlled Generation

## TL;DR

> **Quick Summary**: Replace the existing 150-task enumeration plan with a superior architecture that generates all 150 task definitions in phased batches, each validated for DAG integrity, governance compliance, and schema conformance. Hybrid execution: Sisyphus orchestrates within each phase batch; human review gates at phase boundaries.
>
> **Deliverables**:
> - `.sisyphus/task-schema.md` — Locked 16-field metadata schema with JSON Schema + markdown template
> - `.sisyphus/task-distribution.md` — Cluster-to-phase mapping resolving the 18-task arithmetic gap
> - `.sisyphus/phases/P0-tasks.md` through `.sisyphus/phases/P7-tasks.md` — 8 phase registry files (150 total task definitions)
> - `.sisyphus/dag.json` — Machine-readable global DAG (150 nodes, all edges, acyclic)
> - `.sisyphus/enumeration-validation-report.md` — Final validation sweep results
> - Updated `.sisyphus/change-control-protocol.md` Section 4 — Fixed version mapping alignment
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES — Wave 1 (3 parallel), Wave 2 (8 sequential with human gates), Wave Final (1)
> **Critical Path**: Schema Lock → P0 Batch → [human gate] → P1 Batch → ... → P7 Batch → [human gate] → Cross-Phase Edge Resolution → Global Validation

---

## Context

### Original Request
Design the complete 150-task execution architecture with phased, batch-controlled generation. Tasks generated in structured phase batches (10-20 per batch). After each batch, STOP and wait for user to type 'continue'. This replaces the existing `.sisyphus/plans/150-task-enumeration.md` entirely.

### Interview Summary
**Key Discussions**:
- User confirmed: REPLACE existing enumeration plan (not enhance)
- User confirmed: HYBRID execution model (Sisyphus within phases, human review at phase boundaries)
- Phase structure from master plan: P0=12, P1=25, P2=15, P3=20, P4=18, P5=20, P6=22, P7=18 (total=150)
- All outputs remain within `.sisyphus/` planning artifacts — no docs/tasks/, no code, no root file mutation
- 9 governance files are complete and define the structural framework
- 22 tasks already completed (treated as Phase -1 prerequisites, not numbered in T-001 to T-150)

**Research Findings**:
- Domain cluster allocations sum to 132 tasks vs 150 phase allocation — 18-task gap resolved via cross-cutting integration/stabilization tasks distributed across phases (2-3 per phase)
- Existing enumeration plan (632 lines) is structurally sound but lacks: per-task document mutation maps, risk isolation zone definitions, stabilization wave specifications, execution readiness criteria, forward reference resolution strategy
- Version mapping in change-control-protocol.md Section 4 uses incorrect task ranges (assumes 25-task phases)

### Metis Review
**Identified Gaps** (addressed):
- 18-task arithmetic gap between cluster estimates and phase allocations — resolved by distributing integration/stabilization tasks across phases
- Forward references in DAG — resolved via two-pass approach (first pass: backward refs only; second pass: cross-phase edge resolution task)
- 22 already-completed tasks — treated as Phase -1 prerequisites, referenced via `BASE-XXX` IDs in upstream dependencies but not numbered in T-001..T-150 range
- Planning-level vs implementation-level gate criteria — each phase batch encodes implementation gates as metadata; planning gates validated by the enumeration agent
- Writing agent output limits for 25-task phases — P1 split into sub-batches via session continuation
- No schema immutability enforcement after Wave 1 — addressed by making Task 1 explicitly lock schema with a checksum

### Oracle Consultation
**Strategic Recommendations** (incorporated):
- Phase boundary gates should validate BOTH planning-level criteria (DAG, schema, counts) AND encode implementation-level criteria as metadata within each batch for downstream execution
- 18-task gap: Distribute 18 integration/stabilization tasks as phase closeouts (2-3 per phase) assigned to existing clusters (CL-TQA, CL-OPS, CL-GOV, CL-APV, CL-INF). No new cluster created.
- Forward references: Two-pass approach — Task 13 resolves all cross-phase edges after all 8 phase batches complete
- Task granularity: P1 (25 tasks) uses session continuation (sub-batches of 12-13); all other phases generate in single pass
- Completed tasks: Phase -1 prerequisites with `BASE-XXX` identifiers, referenced but not numbered

---

## Work Objectives

### Core Objective
Produce a complete, DAG-validated, governance-compliant 150-task registry across 8 phase files with locked metadata schema, machine-readable dependency graph, and full document mutation mapping — structured for hybrid Sisyphus/human-gate execution.

### Concrete Deliverables
- `.sisyphus/task-schema.md` — locked 16-field metadata schema with JSON Schema definition and markdown template
- `.sisyphus/task-distribution.md` — cluster-to-phase mapping with 18-task gap resolution (integration/stabilization tasks distributed across existing clusters)
- `.sisyphus/phases/P0-tasks.md` — 12 task definitions for Foundation Hardening (CL-SEC, CRITICAL risk)
- `.sisyphus/phases/P1-tasks.md` — 25 task definitions for Core Completion (multi-cluster, HIGH risk)
- `.sisyphus/phases/P2-tasks.md` — 15 task definitions for Architecture Remediation (CL-APV, CRITICAL risk)
- `.sisyphus/phases/P3-tasks.md` — 20 task definitions for Resilience and Reliability (CL-INF, MEDIUM risk)
- `.sisyphus/phases/P4-tasks.md` — 18 task definitions for Performance and Validation (CL-VIS/CL-MEM/CL-TQA, HIGH risk)
- `.sisyphus/phases/P5-tasks.md` — 20 task definitions for Operational Readiness (CL-OPS/CL-INF, LOW risk)
- `.sisyphus/phases/P6-tasks.md` — 22 task definitions for Feature Evolution (CL-MEM/CL-AUD/CL-RSN, MEDIUM risk)
- `.sisyphus/phases/P7-tasks.md` — 18 task definitions for Hardening and Release (CL-TQA/CL-OPS/CL-GOV, HIGH risk)
- `.sisyphus/dag.json` — global DAG with 150 nodes, all intra- and cross-phase edges, validated acyclic
- `.sisyphus/enumeration-validation-report.md` — comprehensive validation results
- Updated `.sisyphus/change-control-protocol.md` Section 4 — corrected task-to-version mapping

### Definition of Done
- [ ] All 150 tasks enumerated with all 16 metadata fields populated (zero empty/placeholder fields)
- [ ] DAG is acyclic (topological sort succeeds on 150 nodes)
- [ ] No task has more than 5 upstream dependencies
- [ ] All task IDs are unique and contiguous (T-001 through T-150)
- [ ] All 14 domain clusters represented in at least 1 task
- [ ] Phase task counts match allocation: P0=12, P1=25, P2=15, P3=20, P4=18, P5=20, P6=22, P7=18
- [ ] Zero prohibited terms in any output file
- [ ] Every task has a non-empty doc_mutation_map
- [ ] Every task has risk_tier, governance_level, and regression_sensitivity populated
- [ ] Cross-phase edges resolved and validated in final pass
- [ ] Version mapping in change-control-protocol.md corrected

### Must Have
- Globally sequential task IDs (T-001 through T-150)
- All 16 metadata fields per task: task_id, slug, phase, cluster, objective, upstream_deps, downstream_impact, risk_tier, test_layers, doc_mutation_map, versioning_impact, governance_level, regression_sensitivity, parallelization_eligible, execution_environment, current_state
- DAG validation after each phase batch
- Traceability: every task maps to a stub (from 71), technical debt item (from TD register), risk item (from Risk Radar), governance gate, or new capability
- BASE-XXX references for 22 already-completed tasks
- Implementation-level gate criteria encoded as metadata per phase
- Integration/stabilization tasks distributed across existing clusters CL-TQA/CL-OPS/CL-GOV/CL-APV/CL-INF
- Stabilization checkpoints embedded at task 10, 20, 30, 50, 75, 100, 125, 150
- Human gate enforcement between every phase batch (STOP semantics)

### Must NOT Have (Guardrails)
- No code implementation or source file modification
- No docs/tasks/ folder creation or task folder materialization
- No root file mutation (except `.sisyphus/change-control-protocol.md` Section 4 fix)
- No task with more than 5 upstream dependencies
- No batch exceeding phase allocation by more than 2
- No standalone documentation-only tasks (docs are part of implementation tasks)
- No speculative tasks without architectural justification (every task traceable to stub/debt/risk/gate)
- No schema changes after Task 1 schema lock is completed
- No prohibited terms (robust, leverage, seamless, cutting-edge, synergy, etc.)
- No enumeration of all 150 tasks in a single batch
- No circular dependencies in DAG at any point during generation
- No forward references in upstream_deps (only backward references; downstream_impact may reference future phases)
- No tasks touching files outside the 5-layer hierarchy without explicit justification
- **No `docs/tasks/T-XXX/` folder creation** — task-template-blueprint.md defines 15-file task folders as an EXECUTION-TIME concern; this plan produces phase registry files (`.sisyphus/phases/P*-tasks.md`) as the sole output format during enumeration
- No modification of governance files except the explicit Section 4 fix in change-control-protocol.md
- No creation of research-only tasks (research is embedded in execution, not tracked separately)
- No stub-per-task inflation — related stubs MUST be grouped into coherent tasks

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision
- **Infrastructure exists**: N/A (documentation-only plan — no code being written)
- **Automated tests**: None (no code changes)
- **Framework**: Bash validation scripts (grep, wc, python/jq for JSON)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Schema Validation**: Bash (grep/python) — verify all 16 fields present per task definition
- **DAG Validation**: Bash (python) — parse dag.json, verify acyclicity via topological sort
- **ID Uniqueness**: Bash (grep/sort/uniq) — verify no duplicate task IDs
- **Count Validation**: Bash (grep/wc) — verify task counts per phase match allocation
- **Prohibited Terms**: Bash (grep) — verify zero prohibited terms in phase files
- **Cross-Reference**: Bash (grep) — verify all upstream_deps reference existing task IDs

---

## Execution Strategy

### Parallel Execution Waves

> Hybrid model: Sisyphus executes within each wave. Human gates between Wave 2 tasks.
> Wave 1: parallel foundation. Wave 2: sequential with STOP gates. Wave 3: two-pass resolution. Wave Final: validation.

```
Wave 1 (Foundation — 3 tasks, all parallel):
├── Task 1: Lock metadata schema + create phases directory [writing]
├── Task 2: Fix version mapping inconsistency in change-control-protocol.md [quick]
└── Task 3: Resolve 18-task arithmetic gap + create dag.json skeleton [quick]

Wave 2 (Phase Enumeration — 8 tasks, SEQUENTIAL with human gates):
├── Task 4:  Enumerate Phase 0: Foundation Hardening (12 tasks, T-001..T-012) [deep]
│   └── [HUMAN GATE: User reviews P0, types 'continue']
├── Task 5:  Enumerate Phase 1: Core Completion (25 tasks, T-013..T-037) [deep]
│   └── [HUMAN GATE: User reviews P1, types 'continue']
├── Task 6:  Enumerate Phase 2: Architecture Remediation (15 tasks, T-038..T-052) [deep]
│   └── [HUMAN GATE: User reviews P2, types 'continue']
├── Task 7:  Enumerate Phase 3: Resilience & Reliability (20 tasks, T-053..T-072) [deep]
│   └── [HUMAN GATE: User reviews P3, types 'continue']
├── Task 8:  Enumerate Phase 4: Performance & Validation (18 tasks, T-073..T-090) [deep]
│   └── [HUMAN GATE: User reviews P4, types 'continue']
├── Task 9:  Enumerate Phase 5: Operational Readiness (20 tasks, T-091..T-110) [deep]
│   └── [HUMAN GATE: User reviews P5, types 'continue']
├── Task 10: Enumerate Phase 6: Feature Evolution (22 tasks, T-111..T-132) [deep]
│   └── [HUMAN GATE: User reviews P6, types 'continue']
└── Task 11: Enumerate Phase 7: Hardening & Release (18 tasks, T-133..T-150) [deep]
    └── [HUMAN GATE: User reviews P7, types 'continue']

Wave 3 (Cross-Phase Resolution — 1 task):
└── Task 12: Resolve cross-phase DAG edges + stabilization checkpoint injection [deep]

Wave FINAL (Validation — 4 parallel):
├── Task F1: Task count audit across all phase files [quick]
├── Task F2: DAG integrity check (acyclicity, edge resolution, node count) [quick]
├── Task F3: Schema conformance audit (all 16 fields populated per task) [quick]
└── Task F4: Prohibited terms sweep + governance compliance check [quick]

Critical Path: T1-3 → T4 → [gate] → T5 → [gate] → ... → T11 → [gate] → T12 → F1-F4
Human Gates: 8 (one between each phase enumeration)
Parallel Speedup: Wave 1 (3x), Wave FINAL (4x)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|:-----|:-----------|:-------|:-----|
| 1 | — | 4-12 | 1 |
| 2 | — | 4 | 1 |
| 3 | — | 4 | 1 |
| 4 | 1, 2, 3 | 5 | 2 |
| 5 | 4 | 6 | 2 |
| 6 | 5 | 7 | 2 |
| 7 | 6 | 8 | 2 |
| 8 | 7 | 9 | 2 |
| 9 | 8 | 10 | 2 |
| 10 | 9 | 11 | 2 |
| 11 | 10 | 12 | 2 |
| 12 | 11 | F1-F4 | 3 |
| F1-F4 | 12 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 `writing`, T2 `quick`, T3 `quick`
- **Wave 2**: 8 tasks — all `deep` (sequential, complex enumeration requiring codebase awareness)
- **Wave 3**: 1 task — `deep` (cross-phase edge resolution)
- **Wave FINAL**: 4 tasks — all `quick` (validation only)

---

## TODOs

> Each orchestration task generates planning artifacts (phase files, DAG updates).
> Implementation + validation = ONE task. EVERY task has QA Scenarios.
> **CRITICAL**: Wave 2 tasks MUST pause after completion for human review before the next task starts.

- [x] 1. Lock Task Metadata Schema + Create Phases Directory

  **What to do**:
  - Create `.sisyphus/task-schema.md` defining the locked 16-field schema for all 150 task definitions
  - Fields: task_id, slug, phase, cluster, objective (1 paragraph), upstream_deps (list of T-XXX or BASE-XXX), downstream_impact (list of T-XXX or tag references), risk_tier (Low/Medium/High/Critical), test_layers (list from 8-layer model), doc_mutation_map (list of affected documents with section references), versioning_impact (patch/minor/major/none), governance_level (standard/elevated/critical), regression_sensitivity (low/medium/high), parallelization_eligible (yes/no with reason), execution_environment (Local GPU/Cloud/Hybrid), current_state (not_started/partial/blocked)
  - Include a JSON Schema definition for machine validation (parseable by python json.loads + jsonschema.validate)
  - Include a markdown template for human-readable phase files showing exact heading/field structure
  - Include a `phase_exit_criteria` metadata block template for encoding implementation gate criteria per phase
  - Include a `downstream_notes` field (non-DAG, free-text) for cross-phase impact annotations
  - Compute SHA-256 checksum of the locked schema; append to file as immutability anchor
  - Create `.sisyphus/phases/` directory (empty, ready for phase files)
  - Reference existing schemas from dependency-architecture.md and task-template-blueprint.md

  **Must NOT do**:
  - Do not enumerate any actual tasks
  - Do not create phase files yet (only the directory)
  - Do not modify existing governance files
  - Do not add fields beyond the 16 + phase_exit_criteria + downstream_notes

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Schema definition is a structured documentation task requiring precise field definitions and JSON Schema authoring
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed for schema creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4-12, F1-F4 (all phase batches need the locked schema)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `.sisyphus/dependency-architecture.md:20-34` — Existing JSON schema template for task dependency graphs (8-field model to extend to 16)
  - `.sisyphus/task-template-blueprint.md:28-42` — task.md required fields and section definitions

  **API/Type References**:
  - `.sisyphus/task-template-blueprint.md:60-68` — dependency-graph.json field definitions (upstream, downstream, files_read, etc.)
  - `.sisyphus/task-template-blueprint.md:70-77` — test-cases.json field definitions

  **External References**:
  - JSON Schema specification: https://json-schema.org/draft/2020-12/json-schema-core

  **WHY Each Reference Matters**:
  - dependency-architecture.md provides the base JSON structure that the new schema extends from 8 to 16+ fields
  - task-template-blueprint.md defines the existing field taxonomy that must be preserved for backward compatibility
  - governance-model.md Section 1 lists pre-flight check requirements that inform governance_level field values
  - testing-hierarchy-model.md trigger table (lines 340-349) defines the 8-layer names for the test_layers field enum

  **Acceptance Criteria**:
  - [ ] `.sisyphus/task-schema.md` exists with all 16 field definitions + phase_exit_criteria + downstream_notes
  - [ ] JSON Schema included and syntactically valid (python -c "import json; json.load(open('...'))" succeeds)
  - [ ] Markdown template included with exact heading structure for phase files
  - [ ] SHA-256 checksum appended at bottom of file
  - [ ] `.sisyphus/phases/` directory exists (empty)
  - [ ] Zero prohibited terms in schema file

  **QA Scenarios:**
  ```
  Scenario: Schema file contains all required fields
    Tool: Bash (grep)
    Preconditions: Task 1 completed, .sisyphus/task-schema.md exists
    Steps:
      1. grep -c 'task_id\|slug\|phase\|cluster\|objective\|upstream_deps\|downstream_impact\|risk_tier\|test_layers\|doc_mutation_map\|versioning_impact\|governance_level\|regression_sensitivity\|parallelization_eligible\|execution_environment\|current_state' .sisyphus/task-schema.md
      2. python -c "import json; json.load(open('.sisyphus/task-schema.md'.split('```json')[1].split('```')[0]))" (extract and validate JSON Schema block)
      3. ls -la .sisyphus/phases/
    Expected Result: >=16 field matches, JSON parses successfully, phases/ directory exists
    Failure Indicators: grep count < 16, python JSON parse error, phases/ missing
    Evidence: .sisyphus/evidence/task-1-schema-fields.txt

  Scenario: Schema has no prohibited terms
    Tool: Bash (grep)
    Preconditions: .sisyphus/task-schema.md exists
    Steps:
      1. grep -ni 'robust\|leverage\|seamless\|cutting-edge\|synergy' .sisyphus/task-schema.md
    Expected Result: 0 matches (exit code 1)
    Failure Indicators: Any match found
    Evidence: .sisyphus/evidence/task-1-prohibited-check.txt
  ```

  **Commit**: YES (groups with Tasks 2, 3)
  - Message: `docs(sisyphus): lock task metadata schema, fix version mapping, resolve arithmetic gap`
  - Files: `.sisyphus/task-schema.md`, `.sisyphus/phases/`

- [x] 2. Fix Version Mapping Inconsistency in change-control-protocol.md

  **What to do**:
  - Read `.sisyphus/change-control-protocol.md` Section 4 (Task-to-Version Mapping)
  - Rewrite the release grouping table to use actual phase task counts and correct task ID ranges:
    - P0: Tasks T-001 to T-012 (12 tasks) → Release 1.0.1-1.0.3
    - P1: Tasks T-013 to T-037 (25 tasks) → Release 1.1.0
    - P2: Tasks T-038 to T-052 (15 tasks) → Release 1.2.0
    - P3: Tasks T-053 to T-072 (20 tasks) → Release 1.3.0
    - P4: Tasks T-073 to T-090 (18 tasks) → Release 1.4.0
    - P5: Tasks T-091 to T-110 (20 tasks) → Release 1.5.0
    - P6: Tasks T-111 to T-132 (22 tasks) → Release 1.6.0 or 2.0.0
    - P7: Tasks T-133 to T-150 (18 tasks) → Release 2.0.0 or 2.1.0
  - Preserve all other sections and content in the file unchanged

  **Must NOT do**:
  - Do not rewrite sections other than Section 4
  - Do not modify version bump criteria in Section 3
  - Do not change the approval workflow in Section 8

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-section edit in an existing file, straightforward table replacement
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 4 (P0 enumeration needs correct version mapping as reference)
  - **Blocked By**: None

  **References**:
  - `.sisyphus/change-control-protocol.md:89-108` — Current Section 4 with incorrect task ranges assuming 25-task phases
  - `.sisyphus/150-task-master-plan.md:231-241` — Task Capacity Budget table with correct phase counts

  **Acceptance Criteria**:
  - [ ] Section 4 table reflects actual phase task counts (P0=12, P1=25, ..., P7=18)
  - [ ] Task ID ranges are contiguous and non-overlapping (T-001 to T-150)
  - [ ] Total across all phases = 150
  - [ ] No other sections modified

  **QA Scenarios:**
  ```
  Scenario: Version mapping table correctness
    Tool: Bash (grep)
    Preconditions: change-control-protocol.md updated
    Steps:
      1. grep 'T-001' .sisyphus/change-control-protocol.md
      2. grep 'T-150' .sisyphus/change-control-protocol.md
      3. grep -c 'Release' .sisyphus/change-control-protocol.md | head -1
    Expected Result: T-001 appears in P0 row, T-150 appears in P7 row, 8 release entries
    Evidence: .sisyphus/evidence/task-2-version-mapping.txt
  ```

  **Commit**: YES (groups with Tasks 1, 3)

- [x] 3. Resolve 18-Task Arithmetic Gap + Create DAG Skeleton

  **What to do**:
  - The 14 domain clusters sum to 132 estimated tasks. The 8 phases allocate 150. The gap of 18 tasks needs explicit resolution.
  - Create `.sisyphus/task-distribution.md` containing:
    - A cluster-to-phase mapping table showing how 132 cluster-estimated tasks distribute across phases
    - 18 integration/stabilization task slots distributed as phase closeouts (2-3 per phase):
      - P0: +2 (security integration smoke test, baseline metrics capture)
      - P1: +3 (stub replacement validation, cross-module integration test, architecture compliance check)
      - P2: +2 (god-file split validation, async conversion verification)
      - P3: +2 (circuit breaker integration test, failover orchestration validation)
      - P4: +2 (SLA validation under load, VRAM budget verification)
      - P5: +3 (monitoring stack integration, CD pipeline validation, runbook execution test)
      - P6: +2 (feature integration test, cloud sync validation)
      - P7: +2 (final regression suite, release artifact packaging)
    - These 18 tasks are assigned to existing clusters (CL-TQA, CL-OPS, CL-GOV, CL-APV, CL-INF) — NOT a new CL-INT cluster
    - Each of the 18 tasks must have specific artifacts and acceptance criteria (not filler)
  - Create `.sisyphus/dag.json` with empty but valid structure:
    ```json
    {
      "schema_version": "1.0",
      "total_tasks": 150,
      "phases": ["P0","P1","P2","P3","P4","P5","P6","P7"],
      "baseline_prerequisites": [],
      "nodes": [],
      "edges": []
    }
    ```
  - Include a `baseline_prerequisites` section in dag.json listing the 22 completed tasks as BASE-001 through BASE-022 with descriptions

  **Must NOT do**:
  - Do not enumerate actual task definitions (only distribution/allocation)
  - Do not modify 150-task-master-plan.md
  - Do not create a new CL-INT cluster (use existing clusters for integration tasks)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Arithmetic resolution and JSON skeleton creation, no complex analysis
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 4 (P0 enumeration needs distribution map and DAG skeleton)
  - **Blocked By**: None

  **References**:
  - `.sisyphus/150-task-master-plan.md:73-159` — 14 domain cluster definitions with estimated task counts (sum=132)
  - `.sisyphus/150-task-master-plan.md:231-241` — Task Capacity Budget (phase totals sum=150)
  - `AGENTS.md` Section 4 — completed/in-progress/pending/blocked task inventory (22 completed)
  - `.sisyphus/dependency-architecture.md:86-115` — DAG storage format template

  **Acceptance Criteria**:
  - [ ] `.sisyphus/task-distribution.md` exists with cluster-to-phase mapping
  - [ ] Distribution table sums to exactly 150 (132 cluster + 18 integration/stabilization)
  - [ ] `.sisyphus/dag.json` exists with valid JSON structure and `baseline_prerequisites` section
  - [ ] 22 baseline items listed as BASE-001 through BASE-022

  **QA Scenarios:**
  ```
  Scenario: Distribution sums correctly
    Tool: Bash (python)
    Preconditions: task-distribution.md and dag.json created
    Steps:
      1. python -c "import json; d=json.load(open('.sisyphus/dag.json')); print(f'Total: {d[\"total_tasks\"]}, Baseline: {len(d[\"baseline_prerequisites\"])}, Nodes: {len(d[\"nodes\"])}')
      2. grep -c 'BASE-' .sisyphus/dag.json
    Expected Result: Total: 150, Baseline: 22, Nodes: 0 (empty before phase enumeration), 22 BASE references
    Evidence: .sisyphus/evidence/task-3-distribution-validation.txt
  ```

  **Commit**: YES (groups with Tasks 1, 2)
  - Files: `.sisyphus/task-distribution.md`, `.sisyphus/dag.json`

- [x] 4. Enumerate Phase 0: Foundation Hardening (12 tasks, T-001 to T-012)

  **What to do**:
  - Create `.sisyphus/phases/P0-tasks.md` with exactly 12 task definitions following the locked schema from Task 1
  - Phase 0 focus: security remediation, secrets migration, Docker hardening, SAST baseline setup
  - Priority unlock task: T-001 MUST be Secrets Migration (migrating 7 API keys from plaintext `.env` to vault/KMS)
  - Include 2 integration/stabilization tasks (from 18-task gap): security integration smoke test + baseline metrics capture
  - All tasks are CL-SEC cluster, CRITICAL risk tier, governance_level=critical
  - Single-task isolation mandatory for all P0 tasks (parallelization_eligible=no)
  - Execution environment: mostly Cloud (secrets/API keys) with some Hybrid (Docker hardening)
  - Must reference actual codebase files: `.env`, `Dockerfile`, `deployments/docker/Dockerfile`, `shared/utils/encryption.py`, `shared/config/settings.py`, `.github/workflows/ci.yml`
  - Every task MUST have a populated `doc_mutation_map` listing affected AGENTS.md files, Memory.md sections, and changelog category
  - Include `phase_exit_criteria` block at bottom of file encoding the implementation gate from execution-order-strategy.md:
    - All 7 API keys rotated and stored in vault/KMS (zero plaintext in .env)
    - Docker containers running as non-root user
    - Zero critical security findings from SAST scan
    - Secrets management infrastructure verified operational
  - Update `.sisyphus/dag.json` by adding 12 nodes (T-001..T-012) and intra-phase edges
  - Validate DAG acyclicity after adding P0 nodes (run topological sort)
  - Mark already-completed items with `current_state: completed` if they overlap with P0 scope
  - `upstream_deps` may reference BASE-XXX items from the 22 completed prerequisites
  - `downstream_impact` may use `downstream_notes` field for cross-phase annotations (free text, not DAG edges)

  **Must NOT do**:
  - Do not exceed 14 tasks (12 allocated + 2 absolute max flex)
  - Do not create `docs/tasks/` folders — phase registry file is the sole output
  - Do not implement any security changes — task DEFINITIONS only
  - Do not modify existing governance files
  - Do not add forward references in `upstream_deps` (only backward references to T-001..T-012 range and BASE-XXX)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex task requiring deep understanding of 9 governance files, 5-layer architecture, security risk register, and technical debt items to produce accurate task definitions with correct dependency mapping
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction for documentation generation
    - `git-master`: No git operations needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2, first task)
  - **Blocks**: Task 5 (P1 depends on P0 being defined for DAG continuity)
  - **Blocked By**: Tasks 1, 2, 3 (schema, version mapping, distribution must be locked)

  **References**:

  **Pattern References**:
  - `.sisyphus/task-schema.md` (created in Task 1) — Locked metadata schema with field definitions and markdown template
  - `.sisyphus/task-distribution.md` (created in Task 3) — Cluster-to-phase mapping showing P0's 12-task allocation

  **Domain References** (what P0 tasks address):
  - `AGENTS.md` Section 7 — Security risks SR-1 (plaintext API keys), SR-2 (Docker root), SR-3 (no SAST), SR-4 (unencrypted consent)
  - `AGENTS.md` Section 8 — Technical debt TD-004 (7 API keys in .env), TD-005 (Docker non-root)
  - `.sisyphus/execution-order-strategy.md:40` — P0 risk classification (CRITICAL, single-task isolation)
  - `.sisyphus/execution-order-strategy.md:56-57` — Secrets Migration as priority unlock task
  - `.sisyphus/execution-order-strategy.md:113-118` — Phase 0→1 gate criteria (all 7 keys rotated, Docker non-root, zero critical SAST)
  - `.sisyphus/governance-model.md:19` — Tasks modifying shared/config/ carry system-wide blast radius

  **File References** (actual codebase files the tasks will target):
  - `.env` — 7 plaintext API keys (LIVEKIT_API_KEY, DEEPGRAM_API_KEY, OLLAMA_API_KEY, ELEVEN_API_KEY, OLLAMA_VL_API_KEY, TAVUS_API_KEY, LIVEKIT_API_SECRET)
  - `Dockerfile` and `deployments/docker/Dockerfile` — Docker non-root user migration
  - `shared/utils/encryption.py` — Encryption utilities for secrets management
  - `shared/config/settings.py` — Centralized configuration with 85+ env vars
  - `.github/workflows/ci.yml` — CI pipeline for SAST integration

  **WHY Each Reference Matters**:
  - AGENTS.md Section 7/8 provides the exact risk items and debt items that P0 tasks must remediate — each task should map 1:1 to a risk/debt item
  - Execution order strategy defines P0 as CRITICAL risk requiring single-task isolation — the agent must set parallelization_eligible=no for every task
  - Phase 0→1 gate criteria become the `phase_exit_criteria` metadata block — the agent must encode these verbatim
  - Actual file references ensure task definitions point to real paths, not hypothetical ones

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P0-tasks.md` contains exactly 12 task definitions (count: `grep -c '## T-' .sisyphus/phases/P0-tasks.md` = 12)
  - [ ] T-001 is Secrets Migration (grep 'T-001.*[Ss]ecret' P0-tasks.md returns match)
  - [ ] All tasks have all 16 metadata fields populated (grep for each field name returns 12 matches)
  - [ ] All tasks have `risk_tier: Critical` and `governance_level: critical`
  - [ ] All tasks have `parallelization_eligible: no`
  - [ ] All tasks have non-empty `doc_mutation_map`
  - [ ] `phase_exit_criteria` block present at bottom of file
  - [ ] DAG is acyclic after P0 nodes added (topological sort succeeds)
  - [ ] No upstream_deps reference task IDs > T-012 (no forward references)
  - [ ] Zero prohibited terms

  **QA Scenarios:**
  ```
  Scenario: P0 task count, ID range, and priority unlock
    Tool: Bash (grep)
    Preconditions: Task 4 completed, .sisyphus/phases/P0-tasks.md exists
    Steps:
      1. grep -c '## T-' .sisyphus/phases/P0-tasks.md
      2. grep -oP 'T-\d{3}' .sisyphus/phases/P0-tasks.md | sort -u | head -1
      3. grep -oP 'T-\d{3}' .sisyphus/phases/P0-tasks.md | sort -u | tail -1
      4. grep -i 'T-001.*secret\|secret.*T-001' .sisyphus/phases/P0-tasks.md | head -1
    Expected Result: count=12, first=T-001, last=T-012, T-001 contains 'secret'
    Failure Indicators: count != 12, first != T-001, last != T-012, T-001 not secrets-related
    Evidence: .sisyphus/evidence/task-4-p0-count-validation.txt

  Scenario: DAG acyclicity after P0 insertion
    Tool: Bash (python)
    Preconditions: dag.json updated with P0 nodes and edges
    Steps:
      1. python -c "
         import json, sys
         d = json.load(open('.sisyphus/dag.json'))
         nodes = {n['id'] for n in d['nodes']}
         edges = [(e['from'], e['to']) for e in d['edges']]
         in_deg = {n: 0 for n in nodes}
         adj = {n: [] for n in nodes}
         for f, t in edges:
           adj.setdefault(f, []).append(t)
           in_deg[t] = in_deg.get(t, 0) + 1
         q = [n for n in nodes if in_deg[n] == 0]
         s = []
         while q:
           n = q.pop(0); s.append(n)
           for m in adj.get(n, []):
             in_deg[m] -= 1
             if in_deg[m] == 0: q.append(m)
         print(f'Nodes: {len(nodes)}, Sorted: {len(s)}, Acyclic: {len(s)==len(nodes)}')
         sys.exit(0 if len(s)==len(nodes) else 1)
         "
    Expected Result: Nodes: 12, Sorted: 12, Acyclic: True
    Failure Indicators: Sorted < 12 (cycle detected), sys.exit(1)
    Evidence: .sisyphus/evidence/task-4-p0-dag-acyclicity.txt

  Scenario: No prohibited terms in P0
    Tool: Bash (grep)
    Steps:
      1. grep -ni 'robust\|leverage\|seamless\|cutting-edge\|synergy\|state-of-the-art\|innovative\|holistic\|paradigm\|next-generation' .sisyphus/phases/P0-tasks.md
    Expected Result: 0 matches (exit code 1)
    Evidence: .sisyphus/evidence/task-4-p0-prohibited.txt
  ```

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 0 Foundation Hardening (12 tasks T-001..T-012)`
  - Files: `.sisyphus/phases/P0-tasks.md`, `.sisyphus/dag.json`

- [ ] 5. Enumerate Phase 1: Core Completion (25 tasks, T-013 to T-037)

  **What to do**:
  - Create `.sisyphus/phases/P1-tasks.md` with exactly 25 task definitions following locked schema
  - Phase 1 focus: filling 71 stubs across 9 modules, implementing 5 placeholder module MVPs (reasoning, storage, monitoring, event_bus, session_mgmt)
  - Include 3 integration/stabilization tasks (from 18-task gap): stub replacement validation, cross-module integration test, architecture compliance check
  - Multiple clusters represented: CL-VIS, CL-MEM, CL-VQA, CL-OCR, CL-FACE, CL-AUD, CL-RSN, CL-APP, CL-INF
  - Risk tier: HIGH for most tasks, increased testing required
  - Each of the 5 placeholder modules MUST have at least 1 dedicated task
  - Group related stubs into coherent tasks (e.g., 'Fill 5 application/pipelines stubs' rather than 5 separate tasks)
  - Execution environment: varies by cluster (Local GPU for vision/face, Cloud for speech/LLM, Hybrid for VQA)
  - Must reference actual stub locations using `pass # stub`, `TODO`, or `...` patterns (NOT `NotImplementedError`)
  - Update `.sisyphus/dag.json` with P1 nodes (T-013..T-037) and edges (including edges from P0 tasks)
  - Validate DAG acyclicity after adding P1 nodes
  - Mark already-completed items with `current_state: completed` where P1 tasks overlap with the 22 completed items
  - Include `phase_exit_criteria` block encoding P1→P2 gate: stub count < 10, 5 placeholder modules have MVPs, test count >= 880, docs 100% coverage

  **Must NOT do**:
  - Do not exceed 27 tasks (25 allocated + 2 absolute max flex)
  - Do not create task folders — phase registry file only
  - Do not add forward references in `upstream_deps`
  - Do not create standalone documentation-only or research-only tasks

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Largest phase (25 tasks), requires mapping 71 stubs and 5 placeholder modules across 9 domain clusters with correct dependency chains
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Wave 2)
  - **Blocks**: Task 6 (P2 depends on P1)
  - **Blocked By**: Task 4 (P0 must be defined first)

  **References**:
  - `.sisyphus/150-task-master-plan.md:17-23` — Phase 1 definition (entry/exit criteria, challenges, allocation)
  - `.sisyphus/execution-order-strategy.md:41` — P1 risk classification (HIGH, increased testing)
  - `.sisyphus/execution-order-strategy.md:119-123` — P1→P2 gate criteria (stubs < 10, 5 MVPs, tests >= 880)
  - `AGENTS.md` Section 4 — Stub and Placeholder Inventory (71 stubs across 9 categories, 5 placeholders)
  - `AGENTS.md` Section 8 — TD-002 (71 stubs), TD-007 (5 empty modules)
  - `.sisyphus/150-task-master-plan.md:73-159` — 14 domain cluster definitions for multi-cluster task assignment
  - `.sisyphus/task-distribution.md` (created in Task 3) — Cluster-to-phase mapping showing P1's 25-task allocation

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P1-tasks.md` contains exactly 25 task definitions
  - [ ] All 5 placeholder modules (reasoning, storage, monitoring, event_bus, session_mgmt) have at least 1 dedicated task
  - [ ] All 16 metadata fields populated per task
  - [ ] DAG is acyclic after P1 nodes added (37 total nodes: 12 P0 + 25 P1)
  - [ ] No upstream_deps reference task IDs > T-037
  - [ ] Zero prohibited terms
  - [ ] `phase_exit_criteria` block present

  **QA Scenarios:**
  ```
  Scenario: P1 task count and placeholder module coverage
    Tool: Bash
    Steps:
      1. grep -c '## T-' .sisyphus/phases/P1-tasks.md
      2. grep -ci 'reasoning\|storage\|monitoring\|event.bus\|session' .sisyphus/phases/P1-tasks.md
      3. python -c "import json; d=json.load(open('.sisyphus/dag.json')); print(f'Nodes: {len(d[\"nodes\"])}')
    Expected Result: count=25, placeholder references >= 5, Nodes: 37
    Evidence: .sisyphus/evidence/task-5-p1-validation.txt

  Scenario: DAG acyclicity after P1
    Tool: Bash (python) — same acyclicity script as Task 4
    Expected Result: Nodes: 37, Sorted: 37, Acyclic: True
    Evidence: .sisyphus/evidence/task-5-p1-dag.txt
  ```

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 1 Core Completion (25 tasks T-013..T-037)`
  - Files: `.sisyphus/phases/P1-tasks.md`, `.sisyphus/dag.json`

- [ ] 6. Enumerate Phase 2: Architecture Remediation (15 tasks, T-038 to T-052)

  **What to do**:
  - Create `.sisyphus/phases/P2-tasks.md` with exactly 15 task definitions following locked schema
  - Phase 2 focus: agent.py god file split (1900 LOC into 4-5 domain controllers), OllamaEmbedder async conversion, shared/__init__.py cleanup
  - Include 2 integration/stabilization tasks: god-file split validation, async conversion verification
  - Clusters: CL-APV (primary — agent.py refactoring), CL-APP, CL-MEM
  - Risk tier: CRITICAL for agent.py refactoring (priority unlock task), HIGH for others
  - agent.py refactoring is THE priority unlock task for this phase (must be T-038 or earliest feasible)
  - Single-task isolation mandatory for agent.py refactoring tasks (parallelization_eligible=no)
  - Post-phase: no file exceeds 500 LOC, OllamaEmbedder fully async, import-linter passes
  - Update DAG, validate acyclicity
  - Include `phase_exit_criteria`: no file > 500 LOC, OllamaEmbedder async, import-linter clean, no circular deps

  **Must NOT do**:
  - Do not exceed 17 tasks
  - Do not create task folders

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: God file refactoring requires understanding 1900 LOC of real-time WebRTC logic, async patterns, and module boundary decisions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 7
  - **Blocked By**: Task 5

  **References**:
  - `.sisyphus/150-task-master-plan.md:25-31` — Phase 2 definition
  - `AGENTS.md` Section 8 — TD-001 (agent.py god file), TD-003 (sync OllamaEmbedder), TD-010 (shared re-exports)
  - `.sisyphus/execution-order-strategy.md:42,57-58,125-129` — P2 CRITICAL risk, agent.py as priority unlock, P2→P3 gate criteria
  - `apps/realtime/agent.py` — The 1900 LOC god file targeted for decomposition
  - `core/memory/embeddings.py` — OllamaEmbedder blocking call
  - `shared/__init__.py` — Re-export cleanup target

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P2-tasks.md` contains exactly 15 task definitions
  - [ ] agent.py refactoring is the priority unlock task
  - [ ] DAG is acyclic (52 total nodes)
  - [ ] Zero prohibited terms

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 2 Architecture Remediation (15 tasks T-038..T-052)`

- [ ] 7. Enumerate Phase 3: Resilience and Reliability (20 tasks, T-053 to T-072)

  **What to do**:
  - Create `.sisyphus/phases/P3-tasks.md` with exactly 20 task definitions following locked schema
  - Phase 3 focus: circuit breakers (Tenacity) for all 6 cloud services, local STT fallback (Whisper), local TTS fallback (Edge TTS/Coqui), retry logic with exponential backoff
  - Include 2 integration/stabilization tasks: circuit breaker integration test, failover orchestration validation
  - Clusters: CL-INF (primary), CL-AUD, CL-APP
  - Risk tier: MEDIUM (additive changes with lower breakage risk)
  - Priority unlock: Circuit Breaker Foundation pattern (must be early in phase)
  - All 6 cloud services (Deepgram, ElevenLabs, Ollama, LiveKit, Tavus, DuckDuckGo) MUST have dedicated circuit breaker tasks
  - Fallback STT and TTS must activate within 2 seconds of cloud failure
  - Update DAG, validate acyclicity
  - Include `phase_exit_criteria`: all 6 services have circuit breakers, STT fallback functional, TTS fallback functional, retry logic with backoff

  **Must NOT do**:
  - Do not exceed 22 tasks

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex dependency mapping across 6 cloud services with fallback chains
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 8
  - **Blocked By**: Task 6

  **References**:
  - `.sisyphus/150-task-master-plan.md:33-39` — Phase 3 definition
  - `AGENTS.md` Section 7 — DR-1 through DR-6 dependency risks (6 cloud services)
  - `AGENTS.md` Section 8 — TD-006 (no circuit breakers)
  - `.sisyphus/execution-order-strategy.md:43,58-59,131-136` — P3 MEDIUM risk, circuit breaker as priority unlock, P3→P4 gate criteria
  - `infrastructure/speech/deepgram/__init__.py` — Deepgram STT adapter module (needs circuit breaker)
  - `infrastructure/speech/elevenlabs/tts_manager.py` — ElevenLabs TTS adapter (needs circuit breaker)
  - `infrastructure/llm/ollama/handler.py` — Ollama LLM adapter (needs circuit breaker)

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P3-tasks.md` contains exactly 20 task definitions
  - [ ] All 6 cloud services have circuit breaker tasks (grep for each service name)
  - [ ] DAG is acyclic (72 total nodes)
  - [ ] Zero prohibited terms

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 3 Resilience (20 tasks T-053..T-072)`


- [ ] 8. Enumerate Phase 4: Performance and Validation (18 tasks, T-073 to T-090)

  **What to do**:
  - Create `.sisyphus/phases/P4-tasks.md` with exactly 18 task definitions following locked schema
  - Phase 4 focus: 500ms hot-path SLA validation under load, VRAM optimization via INT8 quantization, FAISS index scaling beyond 5K vectors, load testing with Locust at 10 concurrent users
  - Include 2 integration/stabilization tasks: SLA validation under concurrent load, VRAM budget verification
  - Clusters: CL-VIS (YOLO/MiDaS quantization), CL-MEM (FAISS scaling, embedding optimization), CL-TQA (load testing)
  - Risk tier: HIGH (behavioral changes and timing dependencies)
  - Execution environment: Local GPU (quantization, VRAM profiling), Hybrid (load testing)
  - Must reference performance targets: 300ms vision pipeline, 50ms FAISS query, 3.5GB VRAM ceiling
  - Locust load testing infrastructure MUST have a dedicated task
  - Update DAG (90 total nodes), validate acyclicity
  - Include `phase_exit_criteria`: load tests pass at 10 concurrent users, VRAM <= 3.5GB, CPU < 80%, no memory leaks in 1-hour test

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 9
  - **Blocked By**: Task 7

  **References**:
  - `.sisyphus/150-task-master-plan.md:41-47` — Phase 4 definition
  - `AGENTS.md` Section 7 — PR-1 through PR-4 performance risks
  - `AGENTS.md` Section 8 — TD-013 (no load/stress testing)
  - `.sisyphus/execution-order-strategy.md:44,137-142` — P4 HIGH risk, P4→5 gate criteria
  - `.sisyphus/testing-hierarchy-model.md:206-245` — Benchmark suites (hot path, vision pipeline, FAISS, VRAM, load)
  - `core/vision/spatial.py` — YOLO v8n and MiDaS inference targets for quantization
  - `core/memory/indexer.py` — FAISS indexer for scaling validation

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P4-tasks.md` contains exactly 18 task definitions
  - [ ] Locust load testing has a dedicated task
  - [ ] INT8 quantization has a dedicated task
  - [ ] DAG is acyclic (90 total nodes)

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 4 Performance (18 tasks T-073..T-090)`

- [ ] 9. Enumerate Phase 5: Operational Readiness (20 tasks, T-091 to T-110)

  **What to do**:
  - Create `.sisyphus/phases/P5-tasks.md` with exactly 20 task definitions following locked schema
  - Phase 5 focus: Prometheus/Grafana monitoring, automated CD pipeline, incident runbooks, backup/restore for FAISS indices and SQLite databases, alert threshold configuration
  - Include 3 integration/stabilization tasks: monitoring stack integration, CD pipeline validation, runbook execution test
  - Clusters: CL-OPS (primary), CL-INF
  - Risk tier: LOW (additive, non-critical changes)
  - Priority unlock: Monitoring Infrastructure (must be early in phase)
  - Execution environment: Cloud (monitoring/CD), Hybrid (backup/restore touches local FAISS/SQLite)
  - Must address OR-1 through OR-4 operational risks from AGENTS.md Section 7
  - Update DAG (110 total nodes), validate acyclicity
  - Include `phase_exit_criteria`: Prometheus live, Grafana dashboards, CD pipeline functional, runbooks documented, alerts configured

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 10
  - **Blocked By**: Task 8

  **References**:
  - `.sisyphus/150-task-master-plan.md:49-55` — Phase 5 definition
  - `AGENTS.md` Section 7 — OR-1 (no monitoring), OR-2 (no runbook), OR-3 (no CD), OR-4 (no backups)
  - `.sisyphus/execution-order-strategy.md:45,59,143-148` — P5 LOW risk, monitoring as priority unlock, P5→6 gate criteria
  - `infrastructure/monitoring/` — Stub monitoring directory
  - `data/` — FAISS indices and SQLite databases for backup

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P5-tasks.md` contains exactly 20 task definitions
  - [ ] Monitoring infrastructure is the priority unlock task
  - [ ] DAG is acyclic (110 total nodes)

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 5 Operations (20 tasks T-091..T-110)`

- [ ] 10. Enumerate Phase 6: Feature Evolution (22 tasks, T-111 to T-132)

  **What to do**:
  - Create `.sisyphus/phases/P6-tasks.md` with exactly 22 task definitions following locked schema
  - Phase 6 focus: multi-region cloud sync for user profiles and memory, CLIP-based action recognition integration, reasoning engine MVP providing contextual multi-frame summaries
  - Include 2 integration/stabilization tasks: feature integration test, cloud sync validation
  - Clusters: CL-MEM (cloud sync), CL-AUD (action recognition), CL-RSN (reasoning engine), CL-VQA (multi-frame reasoning)
  - Risk tier: MEDIUM (bounded by module boundaries)
  - Execution environment: Hybrid (cloud sync), Local GPU (CLIP, reasoning)
  - Must address state consistency challenges for distributed memory indices
  - Update DAG (132 total nodes), validate acyclicity
  - Include `phase_exit_criteria`: cloud sync operational, action recognition integrated, reasoning MVP functional, 24-hour smoke test passing

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 11
  - **Blocked By**: Task 9

  **References**:
  - `.sisyphus/150-task-master-plan.md:57-63` — Phase 6 definition
  - `.sisyphus/execution-order-strategy.md:46,149-153` — P6 MEDIUM risk, P6→7 gate criteria
  - `core/memory/cloud_sync.py` — In-progress cloud sync module
  - `core/action/action_recognizer.py` — In-progress action recognition
  - `core/reasoning/` — Empty placeholder module for reasoning engine

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P6-tasks.md` contains exactly 22 task definitions
  - [ ] No task exceeds module boundary (each task confined to 1-2 clusters)
  - [ ] DAG is acyclic (132 total nodes)

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 6 Feature Evolution (22 tasks T-111..T-132)`

- [ ] 11. Enumerate Phase 7: Hardening and Release (18 tasks, T-133 to T-150)

  **What to do**:
  - Create `.sisyphus/phases/P7-tasks.md` with exactly 18 task definitions following locked schema
  - Phase 7 focus: SAST/DAST scanning (Trivy/Snyk), canary deployment, full regression suite (1000+ tests), release artifact packaging, production readiness certification
  - Include 2 integration/stabilization tasks: final regression suite, release artifact packaging
  - Clusters: CL-TQA (regression/testing), CL-OPS (deployment/canary), CL-GOV (documentation/compliance)
  - Risk tier: HIGH (high visibility, low error margin)
  - T-150 MUST be the final release/deployment task (the capstone)
  - Execution environment: Hybrid (SAST local, DAST cloud, deployment cloud)
  - Update DAG (150 total nodes), validate acyclicity for the complete graph
  - Include `phase_exit_criteria` (Release Gate): SAST zero critical/high, DAST zero critical/high, dependency scan clean, canary deployment successful (10% traffic/2 hours), 1000+ tests passing, load test at 50 concurrent users

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 12
  - **Blocked By**: Task 10

  **References**:
  - `.sisyphus/150-task-master-plan.md:65-71` — Phase 7 definition
  - `.sisyphus/execution-order-strategy.md:47,155-162` — P7 HIGH risk, Release Gate criteria
  - `AGENTS.md` Section 7 — SR-3 (no SAST/DAST)
  - `.github/workflows/ci.yml` — CI pipeline for SAST integration
  - `deployments/` — Docker and Compose files for deployment

  **Acceptance Criteria**:
  - [ ] `.sisyphus/phases/P7-tasks.md` contains exactly 18 task definitions
  - [ ] T-150 is the final task (release/deployment capstone)
  - [ ] DAG is acyclic (150 total nodes — complete graph)
  - [ ] Zero prohibited terms

  **Commit**: YES
  - Message: `docs(sisyphus): enumerate Phase 7 Hardening (18 tasks T-133..T-150)`

- [ ] 12. Resolve Cross-Phase DAG Edges + Stabilization Checkpoint Injection

  **What to do**:
  - This is the second pass of the two-pass approach for DAG construction
  - Read ALL 8 phase files and the complete DAG
  - For each task's `downstream_notes` field, resolve any cross-phase references into actual DAG edges in dag.json
  - Add cross-phase edges where Phase N tasks unblock Phase N+1 tasks (e.g., T-012 secrets completion enables T-053 circuit breaker implementation)
  - Inject stabilization checkpoint markers at task boundaries: T-010, T-020, T-030, T-050, T-075, T-100, T-125, T-150
  - Verify the complete 150-node DAG is acyclic after all cross-phase edges are added
  - Verify no task has more than 5 upstream dependencies after edge resolution
  - Identify and document the critical path through the complete DAG
  - Add a `critical_path` field to dag.json listing the longest dependency chain
  - Verify all 14 domain clusters are represented across the 150 tasks
  - Verify contiguous task IDs (T-001 through T-150, no gaps, no duplicates)
  - Update all phase files with any corrected cross-references

  **Must NOT do**:
  - Do not add new tasks (150 is the ceiling)
  - Do not change task metadata (only DAG edges and checkpoint markers)
  - Do not modify governance files

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires reading all 8 phase files plus dag.json, understanding cross-phase dependency semantics, and performing graph-level analysis
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: F1-F4 (final validation needs complete DAG)
  - **Blocked By**: Task 11 (all phases must be enumerated)

  **References**:
  - `.sisyphus/phases/P0-tasks.md` through `.sisyphus/phases/P7-tasks.md` — All 8 phase files
  - `.sisyphus/dag.json` — Current DAG with intra-phase edges only
  - `.sisyphus/execution-order-strategy.md:51-62` — Dependency unlocking strategy (priority unlock tasks)
  - `.sisyphus/execution-order-strategy.md:84-105` — Stabilization checkpoint cycles (every 10, every phase, every 50)
  - `.sisyphus/dependency-architecture.md:36-43` — Circular dependency prevention rules and layer flow enforcement

  **Acceptance Criteria**:
  - [ ] dag.json has exactly 150 nodes
  - [ ] dag.json has cross-phase edges (not just intra-phase)
  - [ ] DAG is acyclic after all edges resolved (topological sort succeeds on 150 nodes)
  - [ ] No task has > 5 upstream dependencies
  - [ ] All 14 domain clusters represented (grep unique cluster values >= 14)
  - [ ] Task IDs T-001 through T-150 contiguous (150 unique IDs, no gaps)
  - [ ] Stabilization checkpoints present at T-010, T-020, T-030, T-050, T-075, T-100, T-125, T-150
  - [ ] `critical_path` field populated in dag.json
  - [ ] Zero upstream_deps reference non-existent task IDs

  **QA Scenarios:**
  ```
  Scenario: Complete DAG integrity
    Tool: Bash (python)
    Steps:
      1. python -c "
         import json, sys
         d = json.load(open('.sisyphus/dag.json'))
         nodes = {n['id'] for n in d['nodes']}
         edges = [(e['from'], e['to']) for e in d['edges']]
         # Verify 150 nodes
         assert len(nodes) == 150, f'Expected 150, got {len(nodes)}'
         # Verify contiguous IDs
         expected = {f'T-{i:03d}' for i in range(1, 151)}
         assert nodes == expected, f'Missing: {expected - nodes}'
         # Verify acyclicity (Kahn's algorithm)
         in_deg = {n: 0 for n in nodes}
         adj = {n: [] for n in nodes}
         for f, t in edges:
           adj.setdefault(f, []).append(t)
           in_deg[t] = in_deg.get(t, 0) + 1
         q = [n for n in nodes if in_deg[n] == 0]
         s = []
         while q:
           n = q.pop(0); s.append(n)
           for m in adj.get(n, []):
             in_deg[m] -= 1
             if in_deg[m] == 0: q.append(m)
         assert len(s) == 150, f'Cycle detected: sorted {len(s)}/150'
         # Verify max upstream <= 5
         for n in nodes:
           deps = [e for e in edges if e[1] == n]
           assert len(deps) <= 5, f'{n} has {len(deps)} upstream deps'
         # Verify cross-phase edges exist
         cross = [e for e in edges if d['nodes'][[x['id'] for x in d['nodes']].index(e[0])]['phase'] != d['nodes'][[x['id'] for x in d['nodes']].index(e[1])]['phase']]
         assert len(cross) > 0, 'No cross-phase edges found'
         print(f'PASS: 150 nodes, {len(edges)} edges, {len(cross)} cross-phase, acyclic, max_upstream<=5')
         "
    Expected Result: PASS with all assertions satisfied
    Evidence: .sisyphus/evidence/task-12-dag-integrity.txt

  Scenario: Cluster coverage
    Tool: Bash
    Steps:
      1. grep -ohP 'cluster: \S+' .sisyphus/phases/P*.md | sort -u | wc -l
    Expected Result: >= 14 unique clusters
    Evidence: .sisyphus/evidence/task-12-cluster-coverage.txt
  ```

  **Commit**: YES
  - Message: `docs(sisyphus): resolve cross-phase DAG edges and inject stabilization checkpoints`
  - Files: `.sisyphus/dag.json`, all `.sisyphus/phases/P*-tasks.md` (checkpoint annotations)

## Final Verification Wave

> 4 validation agents run in PARALLEL. ALL must PASS. Failure triggers re-enumeration of affected phase.

- [ ] F1. **Task Count Audit** — `quick`
  Grep all `.sisyphus/phases/P*.md` files. Count `## T-` headers. Assert exactly 150. Count per phase matches allocation (P0=12, P1=25, P2=15, P3=20, P4=18, P5=20, P6=22, P7=18).
  Output: `P0 [12] | P1 [25] | P2 [15] | P3 [20] | P4 [18] | P5 [20] | P6 [22] | P7 [18] | TOTAL [150] | VERDICT: PASS/FAIL`

- [ ] F2. **DAG Integrity Check** — `quick`
  Parse `.sisyphus/dag.json`. Run topological sort via python script. Verify acyclicity. Check no backward cross-phase edges in upstream_deps. Verify all task ID references resolve to existing nodes. Verify no task has >5 upstream deps.
  Output: `Nodes [150] | Edges [N] | Cycles [0] | Unresolved Refs [0] | Max Upstream [≤5] | VERDICT: PASS/FAIL`

- [ ] F3. **Schema Conformance Audit** — `quick`
  For each task in all 8 phase files, verify all 16 metadata fields are populated (not empty, not placeholder, not "TBD"). Cross-check task IDs in phase files match dag.json nodes. Verify BASE-XXX references are valid.
  Output: `Tasks [150] | Fields [16] | Complete [N/150] | BASE Refs [N valid] | VERDICT: PASS/FAIL`

- [ ] F4. **Prohibited Terms + Governance Sweep** — `quick`
  Grep all `.sisyphus/phases/P*.md` for prohibited terms list. Verify every task has non-empty doc_mutation_map. Verify every CRITICAL-risk task has governance_level=critical. Verify stabilization checkpoints present at task boundaries (T-010, T-020, T-030, T-050, T-075, T-100, T-125, T-150).
  Output: `Term Violations [0] | Empty Doc Maps [0] | Governance Mismatches [0] | Checkpoints [8/8] | VERDICT: PASS/FAIL`

---

## Commit Strategy

- **Wave 1**: `docs(sisyphus): lock task schema, fix version mapping, resolve arithmetic gap` — task-schema.md, task-distribution.md, change-control-protocol.md, dag.json, phases/
- **P0 Batch**: `docs(sisyphus): enumerate Phase 0 Foundation Hardening (12 tasks T-001..T-012)` — phases/P0-tasks.md, dag.json
- **P1 Batch**: `docs(sisyphus): enumerate Phase 1 Core Completion (25 tasks T-013..T-037)` — phases/P1-tasks.md, dag.json
- **P2 Batch**: `docs(sisyphus): enumerate Phase 2 Architecture Remediation (15 tasks T-038..T-052)` — phases/P2-tasks.md, dag.json
- **P3 Batch**: `docs(sisyphus): enumerate Phase 3 Resilience (20 tasks T-053..T-072)` — phases/P3-tasks.md, dag.json
- **P4 Batch**: `docs(sisyphus): enumerate Phase 4 Performance (18 tasks T-073..T-090)` — phases/P4-tasks.md, dag.json
- **P5 Batch**: `docs(sisyphus): enumerate Phase 5 Operations (20 tasks T-091..T-110)` — phases/P5-tasks.md, dag.json
- **P6 Batch**: `docs(sisyphus): enumerate Phase 6 Feature Evolution (22 tasks T-111..T-132)` — phases/P6-tasks.md, dag.json
- **P7 Batch**: `docs(sisyphus): enumerate Phase 7 Hardening (18 tasks T-133..T-150)` — phases/P7-tasks.md, dag.json
- **Cross-Phase**: `docs(sisyphus): resolve cross-phase DAG edges and inject stabilization checkpoints` — dag.json, all phase files
- **Final**: `docs(sisyphus): complete 150-task enumeration with full DAG validation` — enumeration-validation-report.md

---

## Success Criteria

### Verification Commands
```bash
# Task count per phase
grep -c '## T-' .sisyphus/phases/P0-tasks.md  # Expected: 12
grep -c '## T-' .sisyphus/phases/P1-tasks.md  # Expected: 25
grep -c '## T-' .sisyphus/phases/P2-tasks.md  # Expected: 15
grep -c '## T-' .sisyphus/phases/P3-tasks.md  # Expected: 20
grep -c '## T-' .sisyphus/phases/P4-tasks.md  # Expected: 18
grep -c '## T-' .sisyphus/phases/P5-tasks.md  # Expected: 20
grep -c '## T-' .sisyphus/phases/P6-tasks.md  # Expected: 22
grep -c '## T-' .sisyphus/phases/P7-tasks.md  # Expected: 18

# Total count
grep -c '## T-' .sisyphus/phases/P*-tasks.md | tail -1  # Expected: 150

# DAG validation
python -c "import json; d=json.load(open('.sisyphus/dag.json')); print(f'Nodes: {len(d[\"nodes\"])}, Edges: {len(d[\"edges\"])}')"  # Expected: Nodes: 150

# Prohibited terms
grep -rni 'robust\|leverage\|seamless\|cutting-edge\|synergy' .sisyphus/phases/  # Expected: no matches

# Schema conformance (spot check)
grep -c 'doc_mutation_map' .sisyphus/phases/P0-tasks.md  # Expected: 12 (one per task)
```

### Final Checklist
- [ ] All 150 tasks enumerated across 8 phase files
- [ ] DAG is acyclic with 150 nodes, all edges resolved
- [ ] All 14 clusters represented
- [ ] Version mapping fixed in change-control-protocol.md
- [ ] Zero prohibited terms across all phase files
- [ ] Schema locked in task-schema.md with checksum
- [ ] task-distribution.md resolves 18-task gap
- [ ] Stabilization checkpoints at 8 boundaries
- [ ] Cross-phase edges resolved in Task 12
- [ ] Enumeration validation report passes all checks
- [ ] Every task traceable to stub/debt/risk/gate/capability
