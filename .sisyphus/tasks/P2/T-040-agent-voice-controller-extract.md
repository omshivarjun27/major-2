# T-040: agent-voice-controller-extract

> Phase: P2 | Cluster: CL-APV | Risk: Critical | State: completed | created_at: 2026-02-25T16:00:00Z | completed_at: 2026-02-25T18:00:00Z

## Objective

Extract voice interaction logic from agent.py into `apps/realtime/voice_controller.py`. This module manages STT routing to Deepgram, TTS dispatch to ElevenLabs, and conversation state tracking. It owns the audio pipeline callbacks, silence detection handlers, and speech segmentation logic. The voice controller coordinates with `core/speech/` for voice routing and `infrastructure/speech/` for provider adapters. All voice-related state machines and audio buffer management currently inlined in agent.py move to this dedicated module.

## Current State (Codebase Audit 2026-02-27)

- **COMPLETED** during the P2 architecture remediation work.
- `apps/realtime/voice_controller.py` exists as a fully functional module.
- Manages STT routing, TTS dispatch, conversation state tracking.
- Audio pipeline callbacks and silence detection handlers extracted.
- Coordinates with `core/speech/` and `infrastructure/speech/`.

## Implemented Files

| File | Purpose |
|------|---------|
| `apps/realtime/voice_controller.py` | Voice interaction, STT/TTS dispatch, conversation state |

## Evidence of Completion

- `apps/realtime/voice_controller.py` exists with full voice pipeline implementation.
- `apps/realtime/agent.py` imports and delegates voice work to voice_controller.
- No voice processing logic remains in agent.py.
- Unit tests in `tests/unit/test_voice_controller.py` (15 tests) validate the module.

## Acceptance Criteria

- [x] `apps/realtime/voice_controller.py` created with voice interaction logic
- [x] STT routing to Deepgram adapter extracted
- [x] TTS dispatch to ElevenLabs adapter extracted
- [x] Conversation state tracking extracted
- [x] Audio pipeline callbacks and silence detection handlers moved
- [x] Speech segmentation logic extracted
- [x] Coordinates with `core/speech/` and `infrastructure/speech/`
- [x] Agent coordinator delegates voice work to this module
- [x] `ruff check .` clean
- [x] `lint-imports` clean

## Upstream Dependencies

T-038 (session manager extraction must complete first).

## Downstream Unblocks

T-041, T-042

## Estimated Scope

- New code: ~350+ LOC (voice_controller.py)
- Modified code: agent.py further reduced after this extraction
- Tests: 15 unit tests in test_voice_controller.py
- Risk: Critical (touches audio pipeline and real-time STT/TTS flow)
