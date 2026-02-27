# T-088: pipeline-instrumentation

> Phase: P4 | Cluster: CL-APP | Risk: Low | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Add comprehensive instrumentation to all pipeline stages for ongoing performance monitoring. Implement timing decorators, structured logging for latency, and request tracing. Enable detailed performance analysis without significant overhead.

## Implementation Plan

1. Create instrumentation utilities in `shared/utils/instrumentation.py`.
2. Implement timing decorators:
   - `@timed(stage_name)` for sync functions
   - `@async_timed(stage_name)` for async functions
3. Add structured latency logging:
   - Log entry/exit with timestamps
   - Include request context (frame_id, session_id)
   - JSON format for easy parsing
4. Implement request tracing:
   - Unique trace ID per request
   - Parent-child span relationships
5. Create latency summary endpoint in API.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `shared/utils/instrumentation.py` | Instrumentation utilities |
| `shared/utils/tracing.py` | Request tracing utilities |
| `apps/api/routes/metrics.py` | Metrics endpoints |
| `tests/unit/test_instrumentation.py` | Instrumentation tests |

## Acceptance Criteria

- [ ] Timing decorators implemented and tested
- [ ] Structured latency logging in place
- [ ] Request tracing with unique IDs
- [ ] Metrics endpoint exposes latency data
- [ ] Instrumentation overhead < 1ms per request
- [ ] Integration with existing logging infrastructure

## Upstream Dependencies

T-073 (baseline capture)

## Downstream Unblocks

T-089 (SLA compliance), Phase 5 (monitoring)

## Estimated Scope

Small-Medium. Instrumentation utilities, ~200-250 lines of code.
