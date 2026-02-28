# T-066: graceful-degradation-coordinator

> Phase: P3 | Cluster: CL-APP | Risk: Medium | State: completed | created_at: 2026-02-27T16:00:00Z

## Objective

Implement a graceful degradation coordinator that orchestrates system behavior when one or more services are degraded. The coordinator uses the service health registry to determine the current degradation level and adjusts system behavior accordingly: disabling non-critical features, switching to fallback providers, and informing the user about reduced capabilities via TTS. The user must never experience silence or confusion when services fail.

## Implementation Plan

1. Create `infrastructure/resilience/degradation_coordinator.py` with a `DegradationCoordinator` class that:
   - Monitors the service health registry for state changes.
   - Defines degradation levels: FULL (all healthy), PARTIAL (some degraded), MINIMAL (critical services down), OFFLINE (no cloud services).
   - Implements degradation policies per level:
     - PARTIAL: Disable non-critical features (Tavus, search), continue with fallbacks.
     - MINIMAL: Switch to local STT/TTS, disable search, warn user.
     - OFFLINE: Local-only mode with Whisper + Edge TTS.
   - Provides `get_degradation_level()` for other components.
   - Announces degradation changes to user via TTS ("I'm switching to offline mode").
2. Subscribe to circuit breaker state-change callbacks for real-time coordination.
3. Write unit tests in `tests/unit/test_degradation_coordinator.py`.

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/resilience/degradation_coordinator.py` | Degradation coordinator |
| `infrastructure/resilience/__init__.py` | Update exports |
| `tests/unit/test_degradation_coordinator.py` | Unit tests |

## Acceptance Criteria

- [x] Four degradation levels defined (FULL, PARTIAL, MINIMAL, OFFLINE)
- [x] Degradation policies implemented for each level
- [x] Real-time response to circuit breaker state changes
- [x] User notified of degradation via TTS announcements (async callback support)
- [x] `get_degradation_level()` returns current level
- [x] Non-critical features disabled gracefully in degraded modes
- [x] Unit tests cover all degradation transitions (36 tests passing)

## Upstream Dependencies

T-063 (STT failover), T-064 (TTS failover), T-065 (health registry)

## Downstream Unblocks

T-071 (chaos tests)

## Estimated Scope

Medium-Large. Coordination logic with state machine, ~250-350 lines of production code.
