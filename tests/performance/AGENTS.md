# tests/performance/AGENTS.md
17 NFR/SLA test files: verifying non-functional requirements.
**Run Command**: `pytest tests/performance/ --timeout=300`.

## PERFORMANCE SLA TABLE
| Metric | Threshold | Test File |
|--------|-----------|-----------|
| **Total Latency** | ≤1000ms | `test_latency_sla.py` |
| **Hot Path** | ≤500ms | `test_latency_sla.py` |
| **Sustained FPS** | 10 FPS | `test_sustained_fps.py` |
| **Frame Drop** | <5% | `test_sustained_fps.py` |
| **Import Latency**| <2000ms (orch), <500ms (cfg) | `test_latency_sla.py` |

## TEST COVERAGE
| File | Verifies |
|------|----------|
| `test_latency_sla.py` | Latency for individual engines and the full pipeline. |
| `test_sustained_fps.py` | Sustained 10 FPS throughput over 60 seconds. |
| `test_memory_leak.py` | No unbounded resource growth over 1000 iterations. |
| `test_pii_scrubbing.py` | Redaction of emails, keys, and face IDs in logs. |
| `test_encryption_at_rest.py` | Face embeddings are stored as encrypted blobs. |
| `test_consent_enforcement.py` | Memory/Face operations are blocked until consent is set. |
| `test_graceful_degradation.py` | System starts when optional features are disabled. |
| `test_resource_threshold.py` | Config parameter boundaries (e.g., worker counts 1-8). |
| `test_offline_behavior.py` | Core functionality persists without network connection. |
| `test_access_control_fuzz.py` | Debug endpoints reject fuzz queries without auth. |

## SHARED CONVENTIONS
- **Fixture Chaining**: Uses the `env_overrides` fixture from `conftest.py` to test different config profiles.
- **NFR Scope**: These tests verify **SYSTEM PROPERTIES**, not unit behavior.
- **Config-Driven**: Many tests assert that current environment settings are within safe operational limits.
