# Dependency Architecture for Voice & Vision Assistant

This document defines the structural management of the task dependency graph for the 150-task master plan. It ensures the integrity of the modular monolith architecture while maintaining the 5-layer hierarchy (shared, core, application, infrastructure, apps).

## Section 1: Task Dependency Graph Structure

Each task in the 150-item roadmap is governed by an 8-dimensional dependency matrix. This matrix prevents architectural drift and ensures that vision and audio processing pipelines maintain their performance SLAs.

1. **Upstream Code Dependencies**: Lists specific modules or functions that must be stable before the task begins. For example, a task in `core/vqa` cannot start until the `core/vision/spatial.py` module is finalized.
2. **Downstream Impact Map**: Identifies components that require re-validation or potential refactoring following the task completion.
3. **Document Dependencies**: Tracks which `AGENTS.md` or `Memory.md` files require updates. Every task affecting the 3-tier OCR fallback must update the documentation in `core/ocr/AGENTS.md`.
4. **JSON Contract Dependencies**: Ensures compliance with established data schemas such as `api_examples.json` or `LLD_data_models.json`.
5. **Test Dependencies**: Defines the test suite baseline. A task in `core/memory` must pass `tests/unit/core/memory/` and `tests/integration/rag_pipeline/`.
6. **Performance Dependencies**: Evaluates the impact on the 500ms hot path and 300ms vision pipeline. Tasks adding new inference logic must not exceed the allotted VRAM or latency budgets.
7. **Accessibility Dependencies**: Monitors changes to the blind user experience, specifically focusing on audio feedback clarity and spatial description accuracy.
8. **Agent Memory Dependencies**: Updates specific sections of the project memory as defined in the Section 16 contract of the master plan.

### JSON Schema Template for Task Dependency Graphs

```json
{
  "task_id": "T-XXX",
  "upstream": ["T-YYY"],
  "downstream": ["T-ZZZ"],
  "files_read": ["core/vision/spatial.py", "shared/config/settings.py"],
  "files_modified": ["core/vqa/scene_graph.py"],
  "docs_updated": ["core/vqa/AGENTS.md", "docs/architecture.md"],
  "json_contracts": ["LLD_data_models.json"],
  "tests_required": ["tests/unit/core/vqa/test_scene_graph.py"],
  "performance_impact": "medium",
  "accessibility_impact": "high",
  "memory_sections_updated": ["vision_logic", "vqa_orchestration"]
}
```

## Section 2: Circular Dependency Prevention

The 5-layer architecture migration established a strict dependency flow: `shared` → `core` → `application` → `infrastructure` → `apps`. Task dependencies must mirror this flow to prevent circularity and maintain the integrity of the monolith.

* **Layer Flow Enforcement**: Tasks are assigned to specific layers. A task in the `application` layer can depend on `core` or `shared` tasks but never on `infrastructure` or `apps`.
* **Cross-Layer DAG Validation**: Any task spanning multiple layers requires a Direct Acyclic Graph (DAG) validation before initialization.
* **Phase Alignment**: Tasks are organized into 8 sequential phases. A task in Phase 3 (Core Engines) cannot depend on a task in Phase 5 (Infrastructure Adapters).
* **Same-Phase DAGs**: Dependencies within a single phase must form a DAG. If two tasks in the `core/vision` cluster require each other, they must be merged into a single atomic task to maintain the DAG structure.

## Section 3: Impact Propagation Model

The blast radius of a task determines the scope of verification required upon completion.

1. **Local (1 File)**: Changes to utility functions or internal logic. Example: Updating a helper in `shared/utils/timing.py`.
2. **Module (1 Directory)**: Affects a specific domain cluster. Example: Refactoring the `core/ocr/fallback_chain.py`.
3. **Layer (1 Architecture Layer)**: Impacts all modules within a layer. Example: Modifying the base class in `shared/schemas/base.py`.
4. **System (Cross-Layer)**: Changes that propagate through the entire pipeline. Example: Altering the frame processing logic in `application/frame_processing/` affects `core/vision`, `core/vqa`, and `apps/realtime`.

### Module Blast Radius Mapping

| Module | Classification | Impact Scope |
|:-------|:---------------|:-------------|
| shared/config | System | Global settings propagation |
| core/vision | Layer | Spatial perception and depth map consumers |
| application/pipelines | Layer | Orchestration and concurrency models |
| infrastructure/llm | Module | Ollama and SiliconFlow adapter consumers |
| apps/api | Local | Specific REST endpoint consumers |

## Section 4: Regression Cascade Prevention

To prevent a single failure from stalling the entire 150-task pipeline, the system employs gate rules and regression detection.

* **Gate Rules**: A task is considered "blocked" until all upstream dependencies are marked as completed.
* **Upstream Verification**: Each task must pass its own specific unit tests plus a subset of tests from its upstream dependencies to ensure no breaking changes were introduced.
* **Execution Gating**: No downstream task in the `apps/realtime` module can start if its dependencies in `core/speech` or `core/vision` have failing tests.
* **Regression Detection**: The system compares total test counts and pass rates before and after each task. Any drop in coverage or success rate triggers an immediate stop and rollback.

## Section 5: DAG Enforcement

The task system is a mathematical DAG where the topological sort determines the precise execution order for the 14 domain clusters.

* **Mandatory Sorting**: Tasks within each phase are executed according to their topological order.
* **Architectural Violations**: Any detected cycle is treated as a high-severity architectural violation. Work must stop immediately to refactor the dependencies into a DAG.
* **Adjacency List Storage**: The DAG is stored as a JSON adjacency list, allowing for rapid traversal and dependency checking.
* **Governance Review**: If a task requires a dependency that violates the 5-layer hierarchy, it must undergo a governance review to determine if the architecture needs adjustment or if the task should be refactored.

## Section 6: Dependency Visualization Format

The full dependency graph of 150 tasks is persisted in a structured JSON format to allow for automated visualization and status tracking.

### DAG Storage Format

```json
{
  "nodes": [
    {
      "id": "T-042",
      "phase": 3,
      "cluster": "vision",
      "status": "in_progress",
      "layer": "core"
    },
    {
      "id": "T-045",
      "phase": 3,
      "cluster": "vqa",
      "status": "pending",
      "layer": "core"
    }
  ],
  "edges": [
    {
      "from": "T-042",
      "to": "T-045",
      "type": "blocks",
      "reason": "VQA requires spatial data from vision pipeline"
    }
  ]
}
```

This format enables the generation of visual maps to identify bottlenecks in the development pipeline and ensures that the 500ms hot path SLA remains the priority throughout the implementation of all 150 tasks.
