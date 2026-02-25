# Task Metadata Schema v1.0

**Status**: LOCKED  
**Applies to**: All 150 task definitions (T-001 through T-150)  
**Consumed by**: Phase files `.sisyphus/phases/P*-tasks.md`  
**Authority**: This file is the single source of truth for task structure. Phase enumeration tasks (Tasks 4 through 12) must conform exactly to this schema.

---

## Schema Purpose

Every task in the 150-task master plan carries a fixed set of 16 metadata fields. This document defines those fields, their types, allowed values, and constraints. Two additional metadata blocks (`phase_exit_criteria` and `downstream_notes`) appear at the phase-file level, not per-task.

The schema extends the original 8-field dependency model from `dependency-architecture.md` to cover governance, testing, versioning, and execution concerns that emerged during planning.

---

## Field Definitions

### 1. `task_id`
- **Type**: String
- **Format**: `T-XXX` where XXX is zero-padded (T-001 through T-150)
- **Constraints**: Unique across all 150 tasks. Must not overlap with the BASE-001 through BASE-022 range reserved for completed foundational work.
- **Purpose**: Primary key for DAG references, cross-phase linking, and progress tracking.

### 2. `slug`
- **Type**: String
- **Format**: Kebab-case, lowercase, max 50 characters
- **Examples**: `secrets-migration`, `yolo-quantization`, `faiss-backup-strategy`
- **Constraints**: Unique across all tasks. No underscores, no spaces, no uppercase.
- **Purpose**: Human-readable short name used in directory names and git branch references.

### 3. `phase`
- **Type**: String (enum)
- **Allowed values**: `P0`, `P1`, `P2`, `P3`, `P4`, `P5`, `P6`, `P7`
- **Constraints**: Must match the phase file where the task is defined.
- **Purpose**: Groups tasks into sequential execution stages. A task in phase N cannot depend on a task in phase N+1 or later.

### 4. `cluster`
- **Type**: String (enum)
- **Allowed values**: `CL-SEC`, `CL-VIS`, `CL-MEM`, `CL-VQA`, `CL-OCR`, `CL-FACE`, `CL-AUD`, `CL-RSN`, `CL-APP`, `CL-INF`, `CL-APV`, `CL-TQA`, `CL-OPS`, `CL-GOV`
- **Constraints**: Exactly one cluster per task. Cluster definitions are in `150-task-master-plan.md` Section 2.
- **Purpose**: Maps the task to its functional domain for context switching and expertise routing.

### 5. `objective`
- **Type**: String (free text, 1 paragraph)
- **Constraints**: Minimum 20 words, maximum 200 words. Must describe what the task achieves, not how.
- **Purpose**: Gives an executor enough context to understand the goal without reading auxiliary files.

### 6. `upstream_deps`
- **Type**: Array of strings
- **Format**: Each element is a `T-XXX` or `BASE-XXX` identifier
- **Constraints**: Backward references only. A task may reference tasks from earlier or same phases, never later phases. Empty array `[]` means no dependencies. The resulting graph must remain acyclic (DAG property).
- **Purpose**: Defines the execution prerequisites. A task is blocked until all upstream deps reach `completed` state.

### 7. `downstream_impact`
- **Type**: Array of strings
- **Format**: Each element is a `T-XXX` identifier or a tag (e.g., `#hot-path`, `#privacy`, `#vram`)
- **Constraints**: Informational, not enforced as hard blocks. Tags use `#` prefix.
- **Purpose**: Tracks which future tasks or concern areas are affected by this task's output.

### 8. `risk_tier`
- **Type**: String (enum)
- **Allowed values**: `Low`, `Medium`, `High`, `Critical`
- **Constraints**: Assessment must account for blast radius (local, module, layer, system) as defined in `dependency-architecture.md` Section 3.
- **Purpose**: Determines review depth, testing breadth, and rollback planning.

### 9. `test_layers`
- **Type**: Array of strings
- **Allowed values (8-layer model)**: `Unit`, `Integration`, `System`, `Regression`, `Canary`, `Benchmark`, `Accessibility`, `Agent`
- **Constraints**: At least one layer required. Order follows the hierarchy from the testing model (Unit first, Agent last).
- **Purpose**: Specifies which test layers must pass before the task is marked complete. See `testing-hierarchy-model.md` for trigger rules and timeouts per layer.

### 10. `doc_mutation_map`
- **Type**: Array of strings
- **Format**: `path/to/file.md#section-name` or just `path/to/file.md`
- **Constraints**: Must list every documentation file affected. Includes AGENTS.md files, Memory.md, PRD sections, and architecture docs.
- **Purpose**: Ensures documentation stays synchronized with code changes. Missed doc updates are treated as incomplete tasks.

### 11. `versioning_impact`
- **Type**: String (enum)
- **Allowed values**: `patch`, `minor`, `major`, `none`
- **Constraints**: Follows semantic versioning principles. Breaking API changes require `major`. New capabilities require `minor`. Bug fixes and refactors use `patch`. Internal-only changes with no user-facing effect use `none`.
- **Purpose**: Feeds into release planning and changelog generation.

### 12. `governance_level`
- **Type**: String (enum)
- **Allowed values**: `standard`, `elevated`, `critical`
- **Mapping**:
  - `standard`: Task passes the 4-point pre-flight check (DAG acyclic, no circular imports, files identified, test plan defined). Normal review.
  - `elevated`: Task modifies `shared/schemas/` or `shared/config/`, triggering system-wide blast radius analysis across all downstream layers. Extended review required.
  - `critical`: Task touches security boundaries (secrets, encryption, consent, Docker hardening) or Phase 0 foundational items. Cannot be deferred. Requires exhaustive impact analysis.
- **Purpose**: Controls the approval workflow depth. Derived from `governance-model.md` Section 1 pre-flight requirements.

### 13. `regression_sensitivity`
- **Type**: String (enum)
- **Allowed values**: `low`, `medium`, `high`
- **Mapping**:
  - `low`: Changes are isolated to a single file or utility function. Regression risk is minimal.
  - `medium`: Changes affect a module directory. Upstream dependency tests must be re-run.
  - `high`: Changes cross architectural layers. Full regression suite required, and any drop in test coverage or pass rate triggers immediate stop.
- **Purpose**: Determines the regression cascade prevention strategy per `dependency-architecture.md` Section 4.

### 14. `parallelization_eligible`
- **Type**: Object with two fields
  - `eligible`: Boolean (`yes` or `no`)
  - `reason`: String (free text, 1 sentence)
- **Constraints**: Tasks sharing write access to the same file cannot be parallelized. Tasks in the same phase with no mutual dependencies may run in parallel.
- **Purpose**: Enables the orchestrator to schedule concurrent execution where safe.

### 15. `execution_environment`
- **Type**: String (enum)
- **Allowed values**: `Local GPU`, `Cloud`, `Hybrid`
- **Mapping**:
  - `Local GPU`: Tasks touching inference models (YOLO v8n, MiDaS v2.1, FAISS embeddings, EasyOCR, Face Detection). Requires NVIDIA RTX 4060 with ONNX Runtime.
  - `Cloud`: Tasks touching external APIs (Deepgram, ElevenLabs, Ollama cloud endpoints, LiveKit).
  - `Hybrid`: Tasks spanning both local inference and cloud API integration.
- **Purpose**: Classifies runtime target for resource planning and CI environment selection. Defined in `task-template-blueprint.md` line 41.

### 16. `current_state`
- **Type**: String (enum)
- **Allowed values**: `not_started`, `partial`, `blocked`, `completed`
- **Constraints**: Initial value for all 150 tasks is `not_started`. Transitions follow: `not_started` -> `partial` -> `completed`, or `not_started` -> `blocked` -> `partial` -> `completed`. No backward transitions except from `blocked`.
- **Purpose**: Tracks execution progress. Only the orchestrator updates this field.

---

## Additional Phase-Level Metadata Blocks

These two blocks appear once per phase file, not per task.

### `phase_exit_criteria`
- **Location**: Bottom of each `P*-tasks.md` file
- **Type**: Ordered list of gate conditions
- **Purpose**: Defines what must be true before the orchestrator advances to the next phase. All tasks within the phase must reach `completed`. All specified test layers must pass. Documentation mutations must be verified.
- **Example**:
  1. All tasks in this phase have `current_state: completed`
  2. Zero failing tests across all `test_layers` specified by tasks in this phase
  3. Every entry in every task's `doc_mutation_map` has been verified as updated
  4. No unresolved `blocked` tasks remain
  5. Regression suite shows no coverage drop compared to phase entry baseline

### `downstream_notes`
- **Location**: Bottom of each `P*-tasks.md` file, after `phase_exit_criteria`
- **Type**: Free-text annotations (bulleted list)
- **Purpose**: Captures cross-phase impact observations that don't fit the formal DAG structure. These are informational warnings for future phase executors, not hard dependencies.
- **Example**:
  - P2 tasks that modify `shared/config/settings.py` will affect every cluster in P3 and beyond
  - Face consent logic in CL-FACE depends on encryption utilities from CL-SEC being finalized first
  - VRAM budget assumes P0 quantization tasks are complete before P3 vision tasks load models

---

## JSON Schema (Draft 2020-12)

The following schema validates a single task metadata object. Phase-level blocks (`phase_exit_criteria`, `downstream_notes`) are not included here since they exist outside the per-task structure.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://voice-vision-assistant.local/schemas/task-metadata-v1.0.json",
  "title": "Task Metadata Schema v1.0",
  "description": "Validates metadata for each of the 150 tasks in the Voice and Vision Assistant master plan.",
  "type": "object",
  "required": [
    "task_id",
    "slug",
    "phase",
    "cluster",
    "objective",
    "upstream_deps",
    "downstream_impact",
    "risk_tier",
    "test_layers",
    "doc_mutation_map",
    "versioning_impact",
    "governance_level",
    "regression_sensitivity",
    "parallelization_eligible",
    "execution_environment",
    "current_state"
  ],
  "additionalProperties": false,
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^T-(0[0-9]{2}|1[0-4][0-9]|150)$",
      "description": "Unique task identifier in T-XXX format, ranging from T-001 to T-150."
    },
    "slug": {
      "type": "string",
      "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
      "maxLength": 50,
      "description": "Kebab-case short name for directory and branch references."
    },
    "phase": {
      "type": "string",
      "enum": ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"],
      "description": "Sequential execution phase. Tasks cannot depend on later phases."
    },
    "cluster": {
      "type": "string",
      "enum": [
        "CL-SEC", "CL-VIS", "CL-MEM", "CL-VQA", "CL-OCR",
        "CL-FACE", "CL-AUD", "CL-RSN", "CL-APP", "CL-INF",
        "CL-APV", "CL-TQA", "CL-OPS", "CL-GOV"
      ],
      "description": "Domain cluster from the 14-cluster model defined in 150-task-master-plan.md."
    },
    "objective": {
      "type": "string",
      "minLength": 80,
      "maxLength": 1200,
      "description": "One-paragraph description of what the task achieves. Minimum 20 words."
    },
    "upstream_deps": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^(T-(0[0-9]{2}|1[0-4][0-9]|150)|BASE-(0[0-9]{2}|0[12][0-9]|022))$"
      },
      "description": "List of T-XXX or BASE-XXX identifiers that must complete before this task starts."
    },
    "downstream_impact": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^(T-(0[0-9]{2}|1[0-4][0-9]|150)|#[a-z][a-z0-9-]*)$"
      },
      "description": "List of T-XXX identifiers or hash-prefixed tags affected by this task."
    },
    "risk_tier": {
      "type": "string",
      "enum": ["Low", "Medium", "High", "Critical"],
      "description": "Risk assessment accounting for blast radius and failure impact."
    },
    "test_layers": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "Unit", "Integration", "System", "Regression",
          "Canary", "Benchmark", "Accessibility", "Agent"
        ]
      },
      "minItems": 1,
      "uniqueItems": true,
      "description": "Test layers from the 8-layer hierarchy that must pass for task completion."
    },
    "doc_mutation_map": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[a-zA-Z0-9_./-]+(#[a-zA-Z0-9_-]+)?$"
      },
      "description": "List of documentation files (with optional section anchors) that require updates."
    },
    "versioning_impact": {
      "type": "string",
      "enum": ["patch", "minor", "major", "none"],
      "description": "Semantic versioning impact of this task on the project release."
    },
    "governance_level": {
      "type": "string",
      "enum": ["standard", "elevated", "critical"],
      "description": "Approval workflow depth based on blast radius and security sensitivity."
    },
    "regression_sensitivity": {
      "type": "string",
      "enum": ["low", "medium", "high"],
      "description": "Determines scope of regression testing required after task completion."
    },
    "parallelization_eligible": {
      "type": "object",
      "required": ["eligible", "reason"],
      "additionalProperties": false,
      "properties": {
        "eligible": {
          "type": "string",
          "enum": ["yes", "no"],
          "description": "Whether this task can run concurrently with other same-phase tasks."
        },
        "reason": {
          "type": "string",
          "maxLength": 200,
          "description": "Brief justification for the parallelization decision."
        }
      },
      "description": "Parallelization eligibility with mandatory justification."
    },
    "execution_environment": {
      "type": "string",
      "enum": ["Local GPU", "Cloud", "Hybrid"],
      "description": "Runtime target classification for resource planning."
    },
    "current_state": {
      "type": "string",
      "enum": ["not_started", "partial", "blocked", "completed"],
      "description": "Current execution state. Initial value is not_started for all tasks."
    }
  }
}
```

---

## Markdown Template for Phase Files

Each task definition in a `P*-tasks.md` file must follow this exact structure. Copy this template and fill in the values.

```markdown
## T-XXX: slug-name-here

- **Phase**: P#
- **Cluster**: CL-XXX
- **Objective**: [1 paragraph, 20-200 words, describing what this task achieves]
- **Upstream Deps**: [`T-XXX`, `BASE-XXX`] or `[]`
- **Downstream Impact**: [`T-XXX`, `#tag`] or `[]`
- **Risk Tier**: Low | Medium | High | Critical
- **Test Layers**: [Unit, Integration, ...]
- **Doc Mutation Map**: [`path/to/file.md#section`, ...]
- **Versioning Impact**: patch | minor | major | none
- **Governance Level**: standard | elevated | critical
- **Regression Sensitivity**: low | medium | high
- **Parallelization Eligible**: yes/no, [reason]
- **Execution Environment**: Local GPU | Cloud | Hybrid
- **Current State**: not_started
```

### Phase File Footer Template

At the bottom of each `P*-tasks.md` file, include these two blocks:

```markdown
---

## Phase Exit Criteria

1. All tasks in this phase have `current_state: completed`
2. Zero failing tests across all `test_layers` specified by tasks in this phase
3. Every entry in every task's `doc_mutation_map` has been verified as updated
4. No unresolved `blocked` tasks remain
5. Regression suite shows no coverage drop compared to phase entry baseline
6. [Phase-specific criteria added here]

## Downstream Notes

- [Free-text cross-phase impact observations]
- [Warnings for future phase executors]
- [Non-DAG informational annotations]
```

---

## Validation Rules

These rules apply globally across all phase files:

1. **Uniqueness**: No two tasks share a `task_id` or `slug`.
2. **DAG integrity**: The union of all `upstream_deps` across all tasks must form an acyclic directed graph.
3. **Phase monotonicity**: If task A depends on task B, then A's phase number must be >= B's phase number.
4. **Completeness**: Every `T-XXX` referenced in any `upstream_deps` or `downstream_impact` field must exist as a defined task or fall within the BASE-001 to BASE-022 range.
5. **Cluster consistency**: A task's `cluster` must align with the module directories it primarily affects.
6. **Test layer minimum**: Every task specifies at least one test layer.
7. **State initialization**: All 150 tasks begin as `not_started`.
8. **Field count**: Exactly 16 fields per task. No more, no less.

---

## Schema Immutability Anchor

This schema is locked for the duration of the 150-task execution plan. Any proposed changes require a governance review with `critical` level approval. The SHA-256 checksum below covers all content above the checksum line.

<!-- SHA-256: 824e434ac4a8eb28c37381b0453fe37a136a606d8b00f4691361ec8fc003c365 -->
