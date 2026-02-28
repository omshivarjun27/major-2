# T-042: agent-coordinator-slim

> Phase: P2 | Cluster: CL-APV | Risk: Critical | State: completed | created_at: 2026-02-25T20:00:00Z | completed_at: 2026-02-25T22:00:00Z

## Objective

Slim agent.py down to a pure coordinator role under 500 lines of code. The coordinator imports session_manager, vision_controller, voice_controller, and tool_router, then wires their dependencies at initialization. It retains only the top-level LiveKit agent entrypoint, plugin registration, and cross-module error propagation. All 28 REST endpoints must remain functional through the coordinator's delegation layer. Backward compatibility with the existing `apps.realtime.entrypoint` launcher is mandatory. No business logic should remain in agent.py after this task.

## Current State (Codebase Audit 2026-02-27)

- **COMPLETED** during the P2 architecture remediation work.
- `apps/realtime/agent.py` is now **288 LOC** — a pure coordinator.
- Imports and wires session_manager, vision_controller, voice_controller, and tool_router.
- Retains only LiveKit agent entrypoint, plugin registration, and cross-module error propagation.
- All 28 REST endpoints functional through delegation.
- Backward compatible with `apps.realtime.entrypoint`.

## Implemented Files

| File | Purpose | LOC |
|------|---------|-----|
| `apps/realtime/agent.py` | Pure coordinator — imports & wires 4 modules | 288 |
| `apps/realtime/session_manager.py` | Session lifecycle (extracted T-038) | ~739 |
| `apps/realtime/vision_controller.py` | Vision dispatch (extracted T-039) | ~400+ |
| `apps/realtime/voice_controller.py` | Voice pipeline (extracted T-040) | ~350+ |
| `apps/realtime/tool_router.py` | Tool routing (extracted T-041) | ~300+ |

## Evidence of Completion

- `agent.py` is 288 LOC (target was <500 LOC). ✅
- No business logic remains in agent.py — only wiring, entrypoint, and error propagation.
- `lint-imports` passes with 6 contracts including the realtime module DAG.
- Previous 1,900 LOC god file decomposed into 5 focused modules.

## Acceptance Criteria

- [x] `agent.py` under 500 lines of code (actual: 288 LOC)
- [x] Imports and wires session_manager, vision_controller, voice_controller, tool_router
- [x] Only LiveKit entrypoint, plugin registration, and error propagation remain
- [x] All 28 REST endpoints functional through delegation
- [x] Backward compatible with `apps.realtime.entrypoint`
- [x] No business logic in agent.py
- [x] `ruff check .` clean
- [x] `lint-imports` clean (6 contracts, 0 violations)

## Upstream Dependencies

T-041 (tool router extraction — final step in decomposition chain).

## Downstream Unblocks

T-043, T-048, T-051

## Estimated Scope

- Modified code: agent.py reduced from ~1,900 LOC to 288 LOC
- Net change: -1,612 LOC from agent.py (moved to 4 extracted modules)
- Risk: Critical (final step in god file decomposition; must preserve all functionality)
