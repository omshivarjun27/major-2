# T-052: p2-async-conversion-verification

> Phase: P2 | Cluster: CL-TQA | Risk: High | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T14:30:00Z

## Objective

Verify all blocking calls have been eliminated from latency-sensitive code paths. Run the async audit tool produced by T-046 as a regression check. Confirm OllamaEmbedder operates non-blocking by measuring event loop latency before and after embedding calls (target: < 5ms loop block). Profile the hot path end-to-end and verify that no synchronous HTTP calls remain in the detection, frame processing, or RAG query pipelines. Produce a final performance comparison report against the P0 baseline metrics from T-012. This is the second integration closeout task for Phase 2.

## Current State (Codebase Audit 2026-02-27)

- T-044 (OllamaEmbedder async) is **complete**. The embedder uses aiohttp with connection pooling and retry logic.
- T-045 (LLM client async) must be complete before this verification.
- T-046 (async-audit-sweep) must be complete, providing the audit tool and report that this task uses as a regression check.
- T-051 (god-file-split-validation) must be complete, confirming the decomposed agent structure is stable.
- The hot path includes: frame capture -> object detection (YOLO) -> segmentation -> depth estimation -> spatial fusion -> RAG queries -> TTS output.
- The 500ms end-to-end SLA and 300ms pipeline timeout are the performance targets.
- P0 baseline metrics from T-012 (if they exist) provide the comparison point.

## Implementation Plan

### Step 1: Run async audit regression check

Execute the audit tool or tests produced by T-046. Confirm zero critical blocking calls in `core/` and `application/`. Verify the audit report at `docs/audits/p2_async_audit.md` is current.

### Step 2: Measure event loop latency during embedding

Write a benchmark that:
1. Starts an asyncio event loop
2. Schedules a periodic task that records timestamps every 1ms
3. Runs an OllamaEmbedder call
4. Measures the maximum gap between periodic task executions
5. Asserts the gap is < 5ms (proving the embedding call doesn't block the loop)

### Step 3: Profile hot path end-to-end

Instrument the hot path from frame input to navigation output:
- Measure time spent in each pipeline stage
- Identify any stage that blocks the event loop
- Verify total latency stays within 500ms SLA
- Verify pipeline timeout of 300ms is respected

### Step 4: Verify no synchronous HTTP calls in hot path

Grep the hot-path code for `requests.`, `urllib.request`, and other synchronous HTTP patterns. Confirm zero matches. Cross-reference with T-046's audit findings.

### Step 5: Compare against P0 baseline

If P0 baseline metrics exist (from T-012), produce a comparison:
- Event loop latency: P0 vs P2
- Hot path end-to-end latency: P0 vs P2
- Embedding call duration: P0 (sync) vs P2 (async)
- Pipeline stage breakdown

### Step 6: Produce verification report

Create `docs/baselines/p2_metrics.json` with structured performance data and `docs/validations/p2_async_verification.md` with the human-readable report.

## Files to Create

| File | Purpose |
|------|---------|
| `docs/baselines/p2_metrics.json` | Structured performance metrics for P2 baseline |
| `docs/validations/p2_async_verification.md` | Human-readable verification report |
| `tests/performance/test_async_verification.py` | Event loop latency and hot path benchmarks |

## Files to Modify

| File | Change |
|------|--------|
| `tests/integration/AGENTS.md` | Document async verification test coverage |
| `AGENTS.md` | Update performance assumptions section with P2 results |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/performance/test_async_verification.py` | `test_event_loop_latency_during_embedding` - measure loop block during embedding, assert < 5ms |
| | `test_event_loop_latency_during_llm_call` - measure loop block during LLM completion, assert < 5ms |
| | `test_hot_path_under_500ms` - profile full pipeline, assert total < 500ms |
| | `test_pipeline_timeout_respected` - verify 300ms pipeline timeout is enforced |
| | `test_no_sync_http_in_hot_path` - static analysis confirming no synchronous HTTP imports |
| | `test_async_audit_regression` - re-run T-046 audit checks as regression gate |

## Acceptance Criteria

- [ ] Async audit regression check passes (zero critical blocking calls)
- [ ] Event loop latency during embedding calls < 5ms
- [ ] Event loop latency during LLM calls < 5ms
- [ ] No synchronous HTTP calls in hot-path code (detection, frame processing, RAG)
- [ ] Hot path end-to-end latency within 500ms SLA
- [ ] Pipeline timeout of 300ms respected
- [ ] Performance comparison report produced against P0 baseline
- [ ] `docs/baselines/p2_metrics.json` created with structured metrics
- [ ] All tests pass: `pytest tests/ --timeout=180`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-046 (async-audit-sweep), T-051 (p2-god-file-split-validation). The audit tool and god file validation must both be complete before this final verification.

## Downstream Unblocks

None. This is the final closeout task for Phase 2.

## Estimated Scope

- New code: ~120 LOC (benchmark tests + metrics JSON + verification report)
- Modified code: ~20 LOC (AGENTS.md updates)
- Tests: ~80 LOC (6 test functions)
- Risk: High. This is the final P2 gate. If event loop latency exceeds 5ms or hot path exceeds 500ms, it indicates incomplete async conversion. Mitigation: T-044, T-045, and T-046 should have already resolved all blocking calls before this verification runs.
