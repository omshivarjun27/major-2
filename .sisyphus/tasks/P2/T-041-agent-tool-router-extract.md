# T-041: agent-tool-router-extract

> Phase: P2 | Cluster: CL-APV | Risk: Critical | State: completed | created_at: 2026-02-25T18:00:00Z | completed_at: 2026-02-25T20:00:00Z

## Objective

Extract function routing and tool dispatch from agent.py into `apps/realtime/tool_router.py`. This module classifies incoming query types (visual, search, QR/AR, general) and maps them to the appropriate capability handler. It owns the intent classification logic, tool registration table, and response aggregation for multi-tool queries. The tool router depends on vision_controller and voice_controller being extracted first, since it dispatches work to both. All function-call definitions, parameter validation, and tool error handling currently scattered through agent.py consolidate here.

## Current State (Codebase Audit 2026-02-27)

- **COMPLETED** during the P2 architecture remediation work.
- `apps/realtime/tool_router.py` exists as a fully functional module.
- Classifies query types and dispatches to appropriate capability handlers.
- Intent classification, tool registration, and response aggregation implemented.
- All function-call definitions and parameter validation extracted from agent.py.

## Implemented Files

| File | Purpose |
|------|---------|
| `apps/realtime/tool_router.py` | Query classification, tool dispatch, response aggregation |

## Evidence of Completion

- `apps/realtime/tool_router.py` exists with full tool routing implementation.
- `apps/realtime/agent.py` imports and delegates tool dispatch to tool_router.
- No tool routing logic remains in agent.py.

## Acceptance Criteria

- [x] `apps/realtime/tool_router.py` created with function routing logic
- [x] Query type classification (visual, search, QR/AR, general) extracted
- [x] Tool registration table and lookup extracted
- [x] Response aggregation for multi-tool queries extracted
- [x] Parameter validation for tool calls extracted
- [x] Error handling for unknown tool types extracted
- [x] Dispatches to vision_controller and voice_controller
- [x] Agent coordinator delegates tool routing to this module
- [x] `ruff check .` clean
- [x] `lint-imports` clean

## Upstream Dependencies

T-039 (vision controller), T-040 (voice controller).

## Downstream Unblocks

T-042

## Estimated Scope

- New code: ~300+ LOC (tool_router.py)
- Modified code: agent.py further reduced after this extraction
- Risk: Critical (tool routing is the dispatching core of the agent)
