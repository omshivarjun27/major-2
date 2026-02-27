# Hot-Path Profiling Report

**Generated:** 2026-02-27T23:29:35.322777
**Iterations:** 10

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Average Latency | 400.8ms | <500ms | OK |
| P95 Latency | 459.0ms | <500ms | OK |
| SLA Pass Rate | 100.0% | 100% | OK |

## Top Bottlenecks

| Rank | Component | Avg (ms) | Max (ms) | % of Total | Location |
|------|-----------|----------|----------|------------|----------|
| 1 | llm | 219.1 | 263.2 | 54.7% | infrastructure/llm/ollama_client.py |
| 2 | tts | 91.7 | 108.8 | 22.9% | infrastructure/speech/elevenlabs_tts.py |
| 3 | stt | 90.0 | 104.6 | 22.5% | infrastructure/speech/deepgram_stt.py |
| 4 | overhead | 0.0 | 0.0 | 0.0% | application/pipelines/voice_pipeline.py |

## Optimization Recommendations

1. **llm** (generate()): LLM latency is within acceptable range
2. **tts** (synthesize()): TTS is within acceptable range
3. **stt** (transcribe()): STT is within acceptable range
4. **overhead** (orchestrate()): Orchestration overhead is acceptable

## Iteration Details

| # | STT (ms) | LLM (ms) | TTS (ms) | Overhead | Total | Status |
|---|----------|----------|----------|----------|-------|--------|
| 1 | 100.3 | 186.5 | 94.7 | 0.0 | 381.5 | OK |
| 2 | 83.5 | 232.9 | 93.2 | 0.0 | 409.7 | OK |
| 3 | 102.6 | 248.0 | 108.4 | 0.0 | 459.0 | OK |
| 4 | 104.6 | 203.6 | 63.7 | 0.0 | 371.9 | OK |
| 5 | 102.3 | 249.8 | 78.3 | 0.0 | 430.4 | OK |
| 6 | 88.9 | 217.9 | 108.8 | 0.0 | 415.6 | OK |
| 7 | 73.3 | 170.1 | 108.1 | 0.0 | 351.5 | OK |
| 8 | 87.2 | 216.2 | 91.7 | 0.0 | 395.2 | OK |
| 9 | 83.6 | 263.2 | 93.1 | 0.0 | 439.8 | OK |
| 10 | 73.9 | 202.3 | 76.9 | 0.0 | 353.2 | OK |