# Performance Baseline Report

**Generated:** 2026-02-28T00:36:06.012916

## Summary

| Component | Median (ms) | P95 (ms) | P99 (ms) | Samples |
|-----------|-------------|----------|----------|---------|
| circuit_breaker_import | 0.05 | 0.31 | 0.31 | 5 |
| circuit_breaker_overhead | 0.06 | 0.15 | 0.96 | 100 |
| config_import | 0.03 | 0.04 | 0.04 | 5 |
| degradation_refresh | 0.13 | 0.51 | 1.23 | 50 |
| health_registry_summary | 0.13 | 0.52 | 4.87 | 100 |
| retry_policy_overhead | 0.03 | 0.04 | 0.04 | 50 |
| stt_failover | 0.22 | 0.64 | 0.64 | 5 |
| tts_failover | 0.02 | 0.03 | 0.03 | 5 |

## Memory Usage

- **RAM Usage:** 517.1 MB
- **VRAM (Idle):** 0.0 MB
- **VRAM (Peak):** 0.0 MB

## SLA Targets

| Component | Target | Status |
|-----------|--------|--------|
| Hot Path (e2e) | <500ms | TBD |
| Vision Pipeline | <300ms | TBD |
| STT | <100ms | TBD |
| TTS | <100ms | TBD |
| FAISS Query | <50ms | TBD |
| VRAM Budget | <8GB | OK |

## Notes

- Baseline RAM: 517.1 MB