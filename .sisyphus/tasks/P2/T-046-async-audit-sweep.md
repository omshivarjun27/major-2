# T-046: async-audit-sweep

> Phase: P2 | Cluster: CL-MEM | Risk: Medium | State: completed | created_at: 2026-02-27T12:00:00Z | completed_at: 2026-02-27T12:40:00Z

## Objective

Audit all remaining synchronous blocking calls across `core/` and `application/` layers. Search for `requests.get`, `requests.post`, `urllib`, synchronous `subprocess` calls, and any `time.sleep` usage that blocks the event loop in async contexts. Flag each finding with file path, line number, and blocking duration estimate. Convert any blocking calls found in hot-path code (detection pipeline, frame processing, RAG queries) to async equivalents. Produce a final audit report confirming zero blocking calls remain in latency-sensitive code paths.

## Current State (Codebase Audit 2026-02-27)

- T-044 (OllamaEmbedder async) is **complete**. The embedder no longer blocks the event loop during embedding calls.
- T-045 (LLM client async) is the other prerequisite, covering `infrastructure/llm/` adapters. It must be completed before this sweep to avoid rework.
- The hot path includes: frame capture, object detection (YOLO), segmentation, depth estimation, spatial fusion, RAG queries, and TTS output.
- The 500ms end-to-end SLA and 300ms pipeline timeout mean any blocking call in the hot path is a latency violation.
- No prior audit of synchronous calls has been performed across `core/` and `application/`.
- Known patterns to search: `requests.get`, `requests.post`, `requests.Session`, `urllib.request`, `subprocess.run`, `subprocess.call`, `time.sleep`, `open()` on network resources.

## Implementation Plan

### Step 1: Automated scan for blocking patterns

Write or run a script that greps `core/` and `application/` for known blocking patterns:
- `requests.get`, `requests.post`, `requests.put`, `requests.delete`, `requests.Session`
- `urllib.request.urlopen`, `urllib.request.urlretrieve`
- `subprocess.run`, `subprocess.call`, `subprocess.Popen` (without async wrappers)
- `time.sleep`
- `socket.` calls without async wrappers

Record each finding: file path, line number, function context, estimated blocking duration.

### Step 2: Classify findings by severity

Categorize each blocking call:
- **Critical**: In hot-path code (detection, frame processing, RAG). Must convert.
- **Medium**: In startup or configuration code. Convert if straightforward.
- **Low**: In debug/test utilities. Document but skip conversion.

### Step 3: Convert critical blocking calls

For each critical finding, replace with the async equivalent:
- `requests` calls become `aiohttp` calls
- `subprocess.run` becomes `asyncio.create_subprocess_exec`
- `time.sleep` becomes `asyncio.sleep`
- CPU-bound blocking becomes `asyncio.get_event_loop().run_in_executor()`

### Step 4: Convert medium-severity calls

Address medium-severity findings where the conversion is low-risk and improves overall async hygiene.

### Step 5: Produce audit report

Create `docs/audits/p2_async_audit.md` with:
- Total findings count by severity
- Each finding with file, line, pattern, resolution status
- Confirmation that zero critical blocking calls remain
- List of low-severity items deferred with justification

### Step 6: Write regression tests

Add tests that verify hot-path code doesn't introduce new blocking calls. These can be static analysis tests or runtime event-loop-latency checks.

## Files to Create

| File | Purpose |
|------|---------|
| `docs/audits/p2_async_audit.md` | Final audit report with findings and resolutions |
| `tests/unit/test_async_audit.py` | Regression tests for blocking call detection |

## Files to Modify

| File | Change |
|------|--------|
| Various files in `core/` | Convert blocking calls to async equivalents |
| Various files in `application/` | Convert blocking calls to async equivalents |
| `core/AGENTS.md` | Document async requirements for core layer |
| `application/AGENTS.md` | Document async requirements for application layer |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_async_audit.py` | `test_no_requests_in_core` - grep core/ for synchronous requests imports |
| | `test_no_requests_in_application` - grep application/ for synchronous requests imports |
| | `test_no_time_sleep_in_hot_path` - verify no time.sleep in detection/frame/RAG code |
| | `test_no_blocking_subprocess_in_hot_path` - verify no synchronous subprocess in hot path |
| | `test_event_loop_latency_during_embedding` - measure loop block during embedding call |
| | `test_event_loop_latency_during_detection` - measure loop block during detection call |

## Acceptance Criteria

- [ ] All `core/` and `application/` files scanned for blocking patterns
- [ ] Each finding documented with file path, line number, and severity
- [ ] Zero critical blocking calls remain in hot-path code
- [ ] `requests` library not imported in any hot-path module
- [ ] `time.sleep` not used in any async context
- [ ] Audit report produced at `docs/audits/p2_async_audit.md`
- [ ] Regression tests prevent reintroduction of blocking calls
- [ ] All tests pass: `pytest tests/ --timeout=180`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-044 (ollama-embedder-async, complete), T-045 (llm-client-async). Both async conversion tasks must finish before the sweep to avoid auditing code that's about to change.

## Downstream Unblocks

T-050 (p2-tech-debt-reassessment), T-052 (p2-async-conversion-verification)

## Estimated Scope

- New code: ~100 LOC (audit report + regression tests)
- Modified code: Variable, depends on findings. Estimate ~50-150 LOC of conversions.
- Tests: ~60 LOC (6 test functions)
- Risk: Medium. Converting blocking calls in core/ could introduce subtle async bugs. Mitigation: convert one file at a time, run full test suite after each change, use `run_in_executor()` as a safe fallback for CPU-bound code.
