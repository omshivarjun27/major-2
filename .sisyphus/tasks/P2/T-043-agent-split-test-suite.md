# T-043: agent-split-test-suite

> Phase: P2 | Cluster: CL-APV | Risk: High | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T12:30:00Z

## Objective

Create a comprehensive test suite for the decomposed agent modules. Write unit tests for session_manager, vision_controller, voice_controller, and tool_router as isolated units. Write integration tests verifying all 28 REST endpoints still return correct responses through the coordinator delegation layer. Add WebRTC session lifecycle tests confirming creation, reconnection, and teardown paths work end-to-end. Target a minimum of 60 new test functions covering the 4 extracted modules and the slimmed coordinator.

## Current State (Codebase Audit 2026-02-27)

- The agent.py god file split is **complete** (T-038 through T-042 all finished).
- `apps/realtime/agent.py` is now 288 LOC, acting as a pure coordinator.
- Four extracted modules exist and are functional:
  - `apps/realtime/session_manager.py` (T-038, session lifecycle)
  - `apps/realtime/vision_controller.py` (T-039, perception dispatch)
  - `apps/realtime/voice_controller.py` (T-040, audio pipeline)
  - `apps/realtime/tool_router.py` (T-041, capability routing)
- No dedicated test files exist yet for the extracted modules.
- Existing tests in `tests/` target the old monolithic agent.py structure.
- The 28 REST endpoints are served through the coordinator's delegation layer but lack targeted integration coverage for the new module boundaries.

## Implementation Plan

### Step 1: Create test fixtures for extracted modules

Add a `tests/unit/apps/realtime/conftest.py` with shared fixtures: mock LiveKit context, mock session participants, sample frames, and mock tool registrations. Each fixture should isolate one module from its dependencies using `unittest.mock`.

### Step 2: Write session_manager unit tests

Create `tests/unit/apps/realtime/test_session_manager.py` with tests covering:
- Session creation with valid LiveKit context
- Session teardown and resource cleanup
- Reconnection handling after disconnect
- Participant join/leave tracking
- Timeout handler invocation
- Error propagation on invalid session state

Target: 12+ test functions.

### Step 3: Write vision_controller unit tests

Create `tests/unit/apps/realtime/test_vision_controller.py` with tests covering:
- Frame capture dispatch to detection pipeline
- Model selection (YOLO, MiDaS, segmentation)
- Result aggregation from multiple vision engines
- Streaming multi-frame workflow
- Graceful fallback when vision engines are unavailable
- Frame caching behavior

Target: 12+ test functions.

### Step 4: Write voice_controller unit tests

Create `tests/unit/apps/realtime/test_voice_controller.py` with tests covering:
- STT routing to Deepgram adapter
- TTS dispatch to ElevenLabs adapter
- Conversation state transitions
- Silence detection callback handling
- Audio buffer management
- Speech segmentation edge cases

Target: 12+ test functions.

### Step 5: Write tool_router unit tests

Create `tests/unit/apps/realtime/test_tool_router.py` with tests covering:
- Query type classification (visual, search, QR/AR, general)
- Tool registration and lookup
- Dispatch to correct capability handler
- Multi-tool query aggregation
- Parameter validation for tool calls
- Error handling for unknown tool types

Target: 12+ test functions.

### Step 6: Write coordinator integration tests

Create `tests/integration/test_agent_coordinator.py` with tests covering:
- All 28 REST endpoints return correct responses through delegation
- Coordinator wires module dependencies correctly at init
- Cross-module error propagation works end-to-end
- WebRTC session lifecycle (create, reconnect, teardown)

Target: 12+ test functions.

### Step 7: Run full suite and verify coverage

Execute `pytest tests/ --timeout=180` and confirm all new tests pass alongside existing tests. Verify no regressions in the existing 429+ test suite.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/apps/realtime/conftest.py` | Shared fixtures for extracted module tests |
| `tests/unit/apps/realtime/test_session_manager.py` | Unit tests for session lifecycle module |
| `tests/unit/apps/realtime/test_vision_controller.py` | Unit tests for vision dispatch module |
| `tests/unit/apps/realtime/test_voice_controller.py` | Unit tests for audio pipeline module |
| `tests/unit/apps/realtime/test_tool_router.py` | Unit tests for capability routing module |
| `tests/integration/test_agent_coordinator.py` | Integration tests for coordinator delegation |

## Files to Modify

| File | Change |
|------|--------|
| `tests/AGENTS.md` | Document new test file locations and coverage targets |
| `tests/unit/apps/realtime/AGENTS.md` | Add module-level test documentation |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/apps/realtime/test_session_manager.py` | 12+ functions: session create, teardown, reconnect, participant tracking, timeouts, error states |
| `tests/unit/apps/realtime/test_vision_controller.py` | 12+ functions: frame dispatch, model selection, result aggregation, streaming, fallbacks, caching |
| `tests/unit/apps/realtime/test_voice_controller.py` | 12+ functions: STT routing, TTS dispatch, conversation state, silence detection, buffers, segmentation |
| `tests/unit/apps/realtime/test_tool_router.py` | 12+ functions: query classification, tool registration, dispatch, multi-tool, validation, error handling |
| `tests/integration/test_agent_coordinator.py` | 12+ functions: 28 endpoint delegation, dependency wiring, error propagation, WebRTC lifecycle |

## Acceptance Criteria

- [ ] Minimum 60 new test functions across all test files
- [ ] Each extracted module (session_manager, vision_controller, voice_controller, tool_router) has 12+ unit tests
- [ ] Integration tests verify all 28 REST endpoints through coordinator delegation
- [ ] WebRTC session lifecycle tests cover creation, reconnection, and teardown
- [ ] All new tests pass: `pytest tests/unit/apps/realtime/ -v`
- [ ] Integration tests pass: `pytest tests/integration/test_agent_coordinator.py -v`
- [ ] No regressions in existing test suite: `pytest tests/ --timeout=180`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-042 (agent-coordinator-slim). All four extracted modules must exist before tests can target them. T-042 is complete.

## Downstream Unblocks

T-049 (agent-architecture-documentation), T-051 (p2-god-file-split-validation)

## Estimated Scope

- New code: ~900 LOC (6 test files + conftest)
- Modified code: ~20 lines (AGENTS.md updates)
- Tests: 60+ new test functions
- Risk: Medium. Tests depend on mocking LiveKit and external service adapters correctly. Mitigation: use existing mock patterns from the test suite.
