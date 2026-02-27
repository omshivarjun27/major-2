# T-084: stt-tts-latency-optimization

> Phase: P4 | Cluster: CL-INF | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Optimize STT and TTS latency to achieve <100ms each. Focus on connection pooling, audio chunk sizing, streaming configurations, and local fallback performance. Ensure smooth voice interaction even under load.

## Implementation Plan

1. Profile Deepgram STT latency:
   - Connection establishment time
   - Audio chunk processing time
   - Final transcript delivery time
2. Optimize STT configuration:
   - Interim results for faster feedback
   - Optimal chunk size for streaming
   - Connection keep-alive
3. Profile ElevenLabs TTS latency:
   - API response time
   - Audio generation time
   - Streaming chunk delivery
4. Optimize TTS configuration:
   - Response streaming
   - Audio format optimization
   - Connection pooling
5. Benchmark local fallbacks (Whisper, Edge TTS) against cloud.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `infrastructure/speech/stt_optimizer.py` | STT optimization utilities |
| `infrastructure/speech/tts_optimizer.py` | TTS optimization utilities |
| `tests/performance/test_speech_latency.py` | Speech latency benchmarks |

## Acceptance Criteria

- [ ] STT latency <100ms for typical utterances
- [ ] TTS latency <100ms for short responses
- [ ] Connection pooling implemented
- [ ] Streaming configurations optimized
- [ ] Local fallback latency documented
- [ ] Configuration tuned for target hardware

## Upstream Dependencies

T-074 (hot path profiling)

## Downstream Unblocks

T-084 (end-to-end latency validation)

## Estimated Scope

Medium. Configuration and optimization, ~150-200 lines of code.
