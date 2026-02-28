# T-065: service-health-registry

> Phase: P3 | Cluster: CL-INF | Risk: Low | State: completed | created_at: 2026-02-27T16:00:00Z

## Objective

Create a centralized service health registry that aggregates circuit breaker states from all 6 services into a single queryable interface. Provides a `/health/services` REST endpoint and an async `get_service_health()` function for internal use. This enables monitoring, alerting, and the degradation coordinator to make informed decisions.

## Implementation Plan

1. Create `infrastructure/resilience/health_registry.py` with a `ServiceHealthRegistry` class that:
   - Aggregates all registered circuit breakers via `get_all_breakers()`.
   - Provides `get_health_summary() -> dict` with per-service status.
   - Provides `is_degraded() -> bool` (any circuit open).
   - Provides `get_degraded_services() -> list[str]`.
   - Computes an overall system health score (0-100%).
2. Add a `/health/services` endpoint to `apps/api/server.py`.
3. The registry is read-only — it queries circuit breaker states on demand.
4. Include uptime, last failure time, and failure rate per service.
5. Write unit tests in `tests/unit/test_health_registry.py`.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `infrastructure/resilience/health_registry.py` | Centralized health registry |
| `infrastructure/resilience/__init__.py` | Export new symbols |
| `apps/api/server.py` | Add /health/services endpoint |
| `tests/unit/test_health_registry.py` | Unit tests |

## Acceptance Criteria

- [x] Registry aggregates all registered circuit breaker states
- [x] `get_health_summary()` returns per-service status with details
- [x] `is_degraded()` returns True when any circuit is OPEN
- [x] Overall health score computed correctly (0-100%)
- [x] REST endpoint `/health/services` returns JSON health summary
- [x] REST endpoint `/health/services/{service_name}` for individual service
- [x] Unit tests pass (32 tests passing)

## Upstream Dependencies

T-054, T-055, T-056, T-057, T-058, T-059

## Downstream Unblocks

T-066 (degradation coordinator)

## Estimated Scope

Small-Medium. Aggregation logic + REST endpoint, ~150-200 lines of production code.
