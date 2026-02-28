# T-038: agent-session-manager-extract

> Phase: P2 | Cluster: CL-APV | Risk: Critical | State: completed | created_at: 2026-02-25T10:00:00Z | completed_at: 2026-02-25T14:00:00Z

## Objective

Extract session lifecycle management from agent.py into `apps/realtime/session_manager.py`. This module handles WebRTC session creation, teardown, and reconnection logic. The extraction isolates session state from the monolithic agent, giving each lifecycle phase a clear boundary. All session-related callbacks, timeout handlers, and participant tracking move into the new module. The agent coordinator will import and delegate to the session manager rather than embedding this logic inline. Backward compatibility with existing LiveKit session flows must be preserved throughout the extraction.

## Current State (Codebase Audit 2026-02-27)

- **COMPLETED** during the P2 architecture remediation work.
- `apps/realtime/session_manager.py` exists as a fully functional module (~739 LOC).
- Handles WebRTC session lifecycle: creation, teardown, reconnection, participant tracking.
- The coordinator (`agent.py`, 288 LOC) delegates all session management to this module.
- All session-related callbacks and timeout handlers have been moved from the monolith.

## Implemented Files

| File | Purpose | LOC |
|------|---------|-----|
| `apps/realtime/session_manager.py` | Session lifecycle management | ~739 |

## Evidence of Completion

- `apps/realtime/session_manager.py` exists with full session lifecycle implementation.
- `apps/realtime/agent.py` imports and delegates to session_manager (288 LOC coordinator).
- No session lifecycle logic remains in agent.py.

## Acceptance Criteria

- [x] `apps/realtime/session_manager.py` created with session lifecycle management
- [x] WebRTC session creation, teardown, and reconnection logic extracted
- [x] Participant join/leave tracking in session_manager
- [x] Timeout handlers moved from agent.py
- [x] Agent coordinator imports and delegates to session_manager
- [x] Backward compatibility with existing LiveKit session flows preserved
- [x] `ruff check .` clean
- [x] `lint-imports` clean

## Upstream Dependencies

BASE-015 (entry point task for agent decomposition).

## Downstream Unblocks

T-039, T-040, T-041, T-042

## Estimated Scope

- New code: ~739 LOC (session_manager.py)
- Modified code: agent.py reduced from 1,900 to ~1,200 LOC after this extraction
- Risk: Critical (first extraction from the god file, sets pattern for subsequent extractions)
