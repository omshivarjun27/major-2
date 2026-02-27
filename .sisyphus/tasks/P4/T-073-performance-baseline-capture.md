# T-073: performance-baseline-capture

> Phase: P4 | Cluster: CL-TQA | Risk: Low | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Establish comprehensive performance baselines for all pipeline components before optimization work begins. Capture current latency metrics for STT, TTS, LLM, vision processing, FAISS queries, and end-to-end hot path. Document VRAM usage at idle and under load. These baselines will serve as the reference point for measuring optimization improvements throughout Phase 4.

## Implementation Plan

1. Create `tests/performance/test_baseline_capture.py` with systematic latency measurements.
2. Measure individual component latencies:
   - STT (Deepgram): Target <100ms
   - TTS (ElevenLabs): Target <100ms
   - VQA/LLM (Ollama): Target <300ms
   - Vision pipeline: Target <300ms
   - FAISS query: Target <50ms
3. Measure end-to-end hot path latency (target <500ms).
4. Profile VRAM usage using `nvidia-smi` or `torch.cuda.memory_allocated()`.
5. Generate baseline report in `docs/performance/baseline-report.md`.
6. Store metrics in a structured format for comparison after optimizations.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/performance/test_baseline_capture.py` | Baseline measurement tests |
| `docs/performance/baseline-report.md` | Documented baseline metrics |
| `scripts/capture_baseline.py` | Standalone baseline capture script |

## Acceptance Criteria

- [ ] All component latencies measured and documented
- [ ] End-to-end hot path latency captured
- [ ] VRAM usage at idle and peak load documented
- [ ] Baseline report generated with clear metrics table
- [ ] Metrics stored in machine-readable format (JSON/YAML)
- [ ] Tests are repeatable and produce consistent results (±10% variance)

## Upstream Dependencies

T-072 (P3 exit criteria - resilience complete)

## Downstream Unblocks

T-074 through T-090 (all P4 optimization tasks)

## Estimated Scope

Small. Measurement and documentation, ~150-200 lines of test code.
