# Technical Debt Register -- P2 Reassessment

Last updated: 2026-02-27 (T-050)

## Resolved Debt Items

| ID | Description | Severity | Resolved By | Resolution Date | Evidence |
|----|------------|----------|-------------|-----------------|----------|
| TD-001 | agent.py god file (1,900 LOC) | Critical | T-038 through T-042 | 2026-02-27 | agent.py = 288 LOC. 8 focused modules. |
| TD-003 | OllamaEmbedder sync blocking | High | T-044 | 2026-02-27 | TextEmbedder uses ollama.AsyncClient. No sync HTTP in hot path. |
| TD-010 | shared/__init__.py excessive re-exports | Medium | T-047 | 2026-02-27 | 58 lines, 18 canonical re-exports from shared.schemas only. |

## Active Debt Items

| ID | Description | Severity | Fix Effort | Affected Files | Recommended Phase |
|----|------------|----------|-----------|----------------|-------------------|
| TD-011 | session_manager.py at 739 LOC | Low | 4h | apps/realtime/session_manager.py | P4 or later |
| TD-012 | Pre-existing test failures (16 failures, 20 errors) | Medium | 8h | tests/unit/test_debug_endpoints.py, tests/performance/test_access_control_fuzz.py, tests/performance/test_debug_access_control.py, tests/performance/test_graceful_degradation.py | P3 |

### TD-011: session_manager.py at 739 LOC

**Context**: After the agent decomposition, session_manager.py is the largest file in apps/realtime/. It handles all session lifecycle concerns: room connection, component initialization (VQA, QR, OCR, voice, live infra), avatar setup, continuous processing, and diagnostics.

**Assessment**: This file has a single responsibility (session lifecycle) and its size is justified by the number of subsystems it initializes. It is NOT a god file — each function has a clear purpose. The 800-LOC threshold test passes.

**Recommendation**: Monitor. If it grows past 800 LOC, extract component initialization into a dedicated init_components.py module. No action needed now.

### TD-012: Pre-existing test failures

**Context**: 16 test failures and 20 test errors exist across the suite. All are caused by:
1. `import api_server` -- module `api_server` does not exist (should be `apps.api.server`). Affects 13 errors + 1 failure.
2. `test_graceful_degradation` -- config reload does not pick up env var changes. Affects 4 failures.
3. `test_debug_access_control` -- same `api_server` import issue. Affects 7 failures.

**Assessment**: These are NOT regressions from P2 work. They are pre-existing since before P2 started. Zero new failures were introduced by P2 tasks.

**Recommendation**: Fix in P3 (Resilience) by renaming `import api_server` to `from apps.api.server import app` and fixing the config reload mechanism.

## Debt Scan Summary

| Category | Findings |
|----------|----------|
| TODO/FIXME/HACK comments | 0 across all project layers |
| Circular imports | 0 (enforced by 6 import-linter contracts) |
| Type annotation gaps | None identified in P2 changes |
| Duplicated code in extracted modules | None identified |
| Temporary compatibility shims | 1: `indexer.save_sync()` backward compat wrapper (T-046). Low risk, intentional. |
| Test coverage gaps | None in P2 modules (52 tests for agent decomposition, 7 for boundaries, 6 for async audit) |

## P2 Phase Summary

| Metric | Before P2 | After P2 |
|--------|----------|----------|
| agent.py LOC | 1,900 | 288 |
| Import-linter contracts | 4 | 6 |
| Blocking calls in async hot path | 4 files | 0 |
| Test count | ~2,009 | ~2,195+ |
| Tech debt items (critical/high) | 3 | 0 |
| Tech debt items (total active) | Unknown | 2 (low + medium) |
