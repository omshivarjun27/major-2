# T-049: agent-architecture-documentation

> Phase: P2 | Cluster: CL-GOV | Risk: Low | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T13:30:00Z

## Objective

Document the new decomposed agent module architecture. Write clear descriptions of each module's responsibility: session_manager (lifecycle), vision_controller (perception dispatch), voice_controller (audio pipeline), tool_router (capability routing), and the coordinator (wiring and delegation). Update `apps/realtime/AGENTS.md` with the module map, data flow diagrams, and interface contracts. Add a migration guide explaining how the monolithic agent.py was split, so future contributors understand the module boundaries.

## Current State (Codebase Audit 2026-02-27)

- The agent.py decomposition is **complete** (T-038 through T-042 all finished).
- `apps/realtime/agent.py` is 288 LOC, serving as a pure coordinator.
- Four extracted modules are functional in `apps/realtime/`:
  - `session_manager.py` handles WebRTC session lifecycle
  - `vision_controller.py` handles frame capture and model dispatch
  - `voice_controller.py` handles STT/TTS and conversation state
  - `tool_router.py` handles query classification and capability dispatch
- T-043 (agent-split-test-suite) is the upstream dependency, ensuring the modules are tested before documentation is finalized.
- Current `apps/realtime/AGENTS.md` (if it exists) still describes the monolithic agent.py structure.
- No migration guide exists explaining the decomposition rationale or module boundaries.
- `docs/architecture.md` references the old agent.py structure.

## Implementation Plan

### Step 1: Write module responsibility descriptions

For each of the 5 modules (4 extracted + coordinator), write a concise description covering:
- What the module owns
- What it delegates to other modules
- Its public interface (key classes, functions, async entry points)
- Its dependencies (which layers it imports from)

### Step 2: Create data flow diagrams

Draw ASCII or Mermaid diagrams showing:
- Request flow from LiveKit through coordinator to controllers
- Vision pipeline: coordinator -> vision_controller -> core/vision/ -> application/frame_processing/
- Voice pipeline: coordinator -> voice_controller -> core/speech/ -> infrastructure/speech/
- Tool routing: coordinator -> tool_router -> vision_controller / voice_controller

### Step 3: Document interface contracts

For each module, list the public methods with their signatures, return types, and behavioral contracts. Include error handling expectations and timeout behavior.

### Step 4: Write migration guide

Explain:
- Why agent.py was split (1900+ LOC god file, single responsibility violations)
- How the split was performed (T-038 through T-042 sequence)
- Where each category of logic ended up
- How to add new functionality (which module to extend)
- Common pitfalls (circular imports, shared state)

### Step 5: Update existing documentation

Update `apps/realtime/AGENTS.md`, `docs/architecture.md`, and `AGENTS.md` repository structure section to reflect the new module layout.

## Files to Create

| File | Purpose |
|------|---------|
| `docs/architecture/agent-decomposition.md` | Migration guide and decomposition rationale |

## Files to Modify

| File | Change |
|------|--------|
| `apps/realtime/AGENTS.md` | Rewrite with module map, data flow diagrams, interface contracts |
| `docs/architecture.md` | Update realtime agent section to reflect decomposed structure |
| `AGENTS.md` | Update repository structure section with new module descriptions |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_docs_accuracy.py` | `test_agent_modules_documented` - verify each .py file in apps/realtime/ has a corresponding section in AGENTS.md |

## Acceptance Criteria

- [ ] Each of the 5 modules has a clear responsibility description in `apps/realtime/AGENTS.md`
- [ ] Data flow diagrams show request routing through the coordinator
- [ ] Interface contracts documented for all public methods
- [ ] Migration guide explains the decomposition rationale and sequence
- [ ] `docs/architecture.md` updated with new module structure
- [ ] `AGENTS.md` repository structure reflects the decomposed agent
- [ ] Future contributors can determine which module to modify for a given change
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-043 (agent-split-test-suite). Documentation should reflect the tested, validated module structure. T-043 depends on T-042 which is complete.

## Downstream Unblocks

T-050 (p2-tech-debt-reassessment)

## Estimated Scope

- New code: ~200 LOC (documentation markdown)
- Modified code: ~100 LOC (updates to existing docs)
- Tests: ~20 LOC (1 documentation accuracy test)
- Risk: Low. Documentation-only task with no code behavior changes. The only risk is documenting interfaces that later change, but T-043's test suite mitigates this.
