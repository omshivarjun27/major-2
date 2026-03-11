# Performance Baseline Report

**Generated:** 2026-03-10T22:56:17.585336

## Summary

| Component | Median (ms) | P95 (ms) | P99 (ms) | Samples |
|-----------|-------------|----------|----------|---------|
| circuit_breaker_import | 0.04 | 0.04 | 0.04 | 5 |
| circuit_breaker_overhead | 0.06 | 0.11 | 0.32 | 100 |
| config_import | 0.03 | 0.24 | 0.24 | 5 |
| degradation_refresh | 0.12 | 0.31 | 0.57 | 50 |
| health_registry_summary | 0.14 | 0.17 | 0.44 | 100 |
| retry_policy_overhead | 0.03 | 0.05 | 0.38 | 50 |
| stt_failover | 1.05 | 1.24 | 1.24 | 5 |
| tts_failover | 0.42 | 0.61 | 0.61 | 5 |

## Memory Usage

- **RAM Usage:** 612.9 MB
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

- Baseline RAM: 612.9 MB