# T-085: end-to-end-latency-validation

> Phase: P4 | Cluster: CL-TQA | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Validate end-to-end hot path latency meets the 500ms SLA after all optimizations. Measure the complete user interaction loop from voice input to voice output. Create comprehensive latency breakdown showing contribution from each component.

## Implementation Plan

1. Create end-to-end latency test harness.
2. Measure complete interaction scenarios:
   - Voice question → Text answer (STT → LLM → TTS)
   - Vision question → Description (Camera → VQA → TTS)
   - Mixed interaction (Voice + Vision → Response)
3. Generate latency breakdown:
   - STT: X ms
   - Processing/LLM: X ms
   - TTS: X ms
   - Overhead: X ms
4. Validate against 500ms SLA:
   - p50, p95, p99 percentiles
   - Success rate
5. Document any scenarios that exceed SLA.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/performance/test_e2e_latency.py` | End-to-end latency tests |
| `docs/performance/e2e-latency-report.md` | Latency validation report |

## Acceptance Criteria

- [ ] Complete interaction loop measured
- [ ] Latency breakdown by component documented
- [ ] p95 latency < 500ms for voice interactions
- [ ] p95 latency < 800ms for vision interactions
- [ ] All scenarios documented with metrics
- [ ] SLA compliance confirmed

## Upstream Dependencies

T-082 (LLM optimization), T-083 (frame processing), T-084 (speech optimization)

## Downstream Unblocks

T-089 (SLA compliance validation)

## Estimated Scope

Medium. Testing and validation, ~200-250 lines of code.
