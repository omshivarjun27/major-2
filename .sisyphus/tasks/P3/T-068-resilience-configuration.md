# T-068: resilience-configuration

> Phase: P3 | Cluster: CL-INF | Risk: Low | State: completed | created_at: 2026-02-27T16:00:00Z | completed_at: 2026-02-27T19:55:00Z

## Objective

Consolidate all resilience-related configuration into `shared/config/settings.py` and ensure all circuit breakers, retry policies, and timeouts read from centralized config rather than hardcoded values. Add environment variable support for all resilience parameters so deployment environments can tune thresholds without code changes.

## Implementation Plan

1. Add resilience configuration section to `shared/config/settings.py`:
   - Per-service circuit breaker thresholds (failure_threshold, reset_timeout_s).
   - Per-service retry configs (max_retries, base_delay_s, max_delay_s).
   - Timeout values (STT, TTS, LLM, Search, Avatar).
   - Fallback settings (WHISPER_MODEL_SIZE, LOCAL_TTS_VOICE).
   - Degradation settings (auto_notify_user, min_announce_interval_s).
2. Add corresponding environment variables (e.g., `CB_DEEPGRAM_THRESHOLD=3`).
3. Update `infrastructure/resilience/circuit_breaker.py` registry to read from config.
4. Update `infrastructure/resilience/retry_policy.py` SERVICE_RETRY_CONFIGS to read from config.
5. Write unit tests verifying config loading and defaults.

## Files to Modify

| File | Purpose |
|------|---------|
| `shared/config/settings.py` | Add resilience configuration section |
| `infrastructure/resilience/circuit_breaker.py` | Read thresholds from config |
| `infrastructure/resilience/retry_policy.py` | Read retry configs from config |
| `tests/unit/test_resilience_config.py` | Config loading tests |

## Acceptance Criteria

- [x] All resilience parameters configurable via environment variables
- [x] Sane defaults for all parameters (works without explicit config)
- [x] Circuit breakers read thresholds from centralized config
- [x] Retry policies read settings from centralized config
- [x] Environment variable overrides work correctly
- [x] Unit tests verify config loading, defaults, and overrides
- [x] No hardcoded resilience values remaining in adapter code

## Upstream Dependencies

T-060 (retry wiring), T-067 (timeout standardization)

## Downstream Unblocks

T-072 (P3 exit criteria)

## Estimated Scope

Small-Medium. Config consolidation, ~120-180 lines of changes.
