# T-062: edge-tts-local-fallback

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:50:00Z

## Objective

Implement a local TTS fallback adapter using `edge-tts` (Microsoft Edge's free TTS service) or `pyttsx3` (fully offline) that activates when ElevenLabs is unavailable. The fallback must produce audible speech output within 2 seconds of the ElevenLabs circuit breaker opening. Provides a compatible interface with the existing TTSManager local_fn signature.

## Implementation Plan

1. Create `infrastructure/speech/local/edge_tts_fallback.py` with a `LocalTTSFallback` class that:
   - Primary: Uses `edge-tts` for natural-sounding offline TTS (uses Microsoft edge voices, free).
   - Secondary: Falls back to `pyttsx3` if edge-tts is unavailable (fully offline).
   - Provides `synthesize(text: str) -> bytes` sync method (compatible with TTSManager.local_fn).
   - Provides `async_synthesize(text: str) -> bytes` async method.
2. Configure voice selection via settings (default: "en-US-AriaNeural" for edge-tts).
3. Add `edge-tts` and `pyttsx3` to `requirements-extras.txt`.
4. Add `LOCAL_TTS_VOICE` config to `shared/config/settings.py`.
5. Handle missing dependencies gracefully (try edge-tts -> pyttsx3 -> error message).
6. Write unit tests in `tests/unit/test_edge_tts_fallback.py`.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `infrastructure/speech/local/edge_tts_fallback.py` | Local TTS fallback adapter |
| `infrastructure/speech/local/__init__.py` | Update exports |
| `shared/config/settings.py` | Add LOCAL_TTS_VOICE config |
| `requirements-extras.txt` | Add edge-tts, pyttsx3 dependencies |
| `tests/unit/test_edge_tts_fallback.py` | Unit tests |

## Acceptance Criteria

- [x] LocalTTSFallback provides both sync and async synthesize methods
- [x] Primary path uses edge-tts for natural voice
- [x] Secondary path uses pyttsx3 for fully offline operation
- [x] Compatible with TTSManager.local_fn signature (sync callable)
- [x] Graceful handling when neither dependency is installed
- [x] Voice configurable via settings
- [x] Synthesis latency < 1 second for typical sentences
- [x] Unit tests pass with mocked TTS engines (34 tests)

## Upstream Dependencies

None (independent implementation)

## Downstream Unblocks

T-064 (TTS failover manager)

## Estimated Scope

Medium. New adapter implementation, ~200-250 lines of production code.
