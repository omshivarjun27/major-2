# T-061: whisper-local-stt-fallback

> Phase: P3 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:45:00Z

## Objective

Implement a local Whisper-based STT fallback adapter that activates when Deepgram is unavailable. The adapter uses OpenAI's Whisper (via `faster-whisper` or `whisper` package) running on the local GPU to provide offline speech-to-text. The fallback must activate within 2 seconds of Deepgram circuit breaker opening. The adapter provides a compatible interface so the voice pipeline can switch transparently.

## Implementation Plan

1. Create `infrastructure/speech/local/whisper_stt.py` with a `WhisperSTT` class that:
   - Lazy-loads the Whisper model on first use (to avoid VRAM overhead when not needed).
   - Provides `transcribe(audio_bytes) -> str` async method.
   - Uses the "tiny" or "base" model for low latency (~200-500ms per utterance).
   - Supports configurable model size via settings.
2. Create `infrastructure/speech/local/__init__.py` with exports.
3. Add `WHISPER_MODEL_SIZE` config to `shared/config/settings.py` (default: "base").
4. Add `faster-whisper` to `requirements-extras.txt` (optional dependency).
5. Implement lazy loading: model loaded only when fallback is first needed.
6. Handle the case where Whisper is not installed (graceful error message).
7. Write unit tests with mocked Whisper model in `tests/unit/test_whisper_stt.py`.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `infrastructure/speech/local/__init__.py` | Package init |
| `infrastructure/speech/local/whisper_stt.py` | Local Whisper STT adapter |
| `shared/config/settings.py` | Add WHISPER_MODEL_SIZE config |
| `requirements-extras.txt` | Add faster-whisper dependency |
| `tests/unit/test_whisper_stt.py` | Unit tests |

## Acceptance Criteria

- [x] WhisperSTT class provides `transcribe()` async method
- [x] Model is lazy-loaded (not loaded at import time)
- [x] Configurable model size (tiny/base/small)
- [x] Graceful handling when faster-whisper is not installed
- [x] Transcription latency < 1 second for typical utterances
- [x] VRAM usage documented (tiny: ~100MB, base: ~200MB)
- [x] Unit tests pass with mocked model (32 tests)

## Upstream Dependencies

None (independent implementation)

## Downstream Unblocks

T-063 (STT failover manager)

## Estimated Scope

Medium. New adapter implementation, ~200-250 lines of production code.
