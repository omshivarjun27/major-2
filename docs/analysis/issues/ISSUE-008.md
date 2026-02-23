---
id: ISSUE-008
title: Agent.py Is a 1,900-Line God Object
severity: medium
source_artifact: architecture_risks.md
architecture_layer: apps
---

## Description
`apps/realtime/agent.py` is a 1,900-line monolithic file containing: the system prompt (272 lines), `UserData` dataclass (~30 fields), `AllyVisionAgent` class, all LiveKit function tools, spatial trigger logic, debounce logic, proactive mode, and session management.

## Root Cause
Rapid feature development concentrated all real-time agent logic in a single file. No refactoring pass was performed to extract concerns into separate modules.

## Impact
- Difficult to test individual components in isolation
- High coupling between unrelated concerns (prompts, tools, state management)
- Merge conflict bottleneck for team development
- Hard to review and reason about changes
- Violates single-responsibility principle

## Reproducibility
always

## Remediation Plan
1. Extract system prompt into `apps/realtime/agent_prompts.py`.
2. Extract function tools into `apps/realtime/agent_tools.py`.
3. Extract `UserData` into `apps/realtime/agent_state.py`.
4. Extract spatial trigger logic into `apps/realtime/spatial_triggers.py`.
5. Keep `agent.py` as a thin orchestrator that imports and coordinates extracted modules.
6. Ensure all existing tests still pass after refactoring.

## Implementation Suggestion
```
apps/realtime/
├── agent.py              # Thin orchestrator (~200 lines)
├── agent_prompts.py      # System prompt constants
├── agent_tools.py        # LiveKit function tool implementations
├── agent_state.py        # UserData dataclass + session management
├── spatial_triggers.py   # Spatial trigger + debounce logic
└── entrypoint.py         # Existing launcher
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] `agent.py` reduced to <300 lines (orchestrator only)
- [ ] Each extracted module is independently testable
- [ ] All existing tests pass without modification
- [ ] No circular imports introduced
