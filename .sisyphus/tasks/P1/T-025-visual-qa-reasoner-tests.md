# T-025: visual-qa-reasoner-tests

> Phase: P1 | Cluster: CL-VQA | Risk: Low | State: not_started

## Objective

Write unit tests for `VQAReasoner` and `QuickAnswers` in `core/vqa/vqa_reasoner.py`. This 581-line
module contains the LLM integration layer, caching logic, MicroNav fallback formatting, and a
pattern-matching fast path for common navigation queries. Tests must verify QuickAnswers pattern
matching across all three query categories, MicroNavFormatter output structure, VQAReasoner behavior
with a mock LLM client, cache hit/miss mechanics, safety prefix generation from fused results, and
stats tracking accuracy. These tests ensure the reasoning layer works correctly without requiring
a live LLM endpoint.

## Current State (Codebase Audit 2026-02-25)

- `core/vqa/vqa_reasoner.py` is 581 lines with 5 main classes: `PromptTemplates`, `MicroNavFormatter`, `VQARequest`, `VQAResponse`, `VQAReasoner`, `QuickAnswers`.
- `PromptTemplates` (lines 31-113): static class with SYSTEM, SPATIAL, IDENTIFY, DESCRIBE, SAFETY_WARNING, and MICRONAV template strings. Six `@classmethod` formatters.
- `MicroNavFormatter` (lines 119-242): formats `FusedResult` into ultra-brief TTS phrases. Has `CLOCK_POSITIONS` dict mapping angle ranges to clock positions. Methods: `format()`, `_format_obstacle()`, `_format_distance()`, `_format_direction()`, `_format_critical_action()`, `_format_action()`.
- `VQARequest` (lines 249-258): dataclass with question, image, scene_graph, fused_result, use_image, max_tokens (150), temperature (0.2).
- `VQAResponse` (lines 261-285): dataclass with answer, confidence, processing_time_ms, tokens_used, source ("llm"/"cache"/"fallback"), safety_prefix. Has `get_full_answer()` method.
- `VQAReasoner` (lines 292-517): accepts `llm_client`, `model`, `api_base`, `use_micronav_fallback`. Cache is a dict with 5s TTL and 128-entry max. `answer()` checks cache first, tries LLM, falls back to MicroNav, then returns error. Stats: `_total_requests`, `_cache_hits`, `_avg_latency_ms`. `_reason_with_llm()` builds messages with system prompt, optional base64 image, scene context.
- `QuickAnswers` (lines 523-581): static class with `PATTERNS` dict for "clear", "obstacles", "directions" categories. `try_quick_answer()` matches `question.lower()` against patterns and returns deterministic answers based on `FusedResult` state.
- `MicroNavFormatter._format_distance()` has special handling for inf and NaN depth values (line 189).
- Cache key generation at `_get_cache_key()` uses first 50 chars of lowercase question plus top-3 obstacle class:depth pairs.
- `_encode_image()` resizes to max 512px, converts to RGB, saves as JPEG quality 80, returns base64.
- Module imports `FusedResult` and `FusedObstacle` from `core.vqa.spatial_fuser`.

## Implementation Plan

### Step 1: Create test file with mock dependencies

Create `tests/unit/test_vqa_reasoner.py`. Build mock `FusedResult` and `FusedObstacle` objects
that can be configured with arbitrary obstacle lists, depths, and bounding boxes. Create a mock
LLM client that mimics the OpenAI `chat.completions.create()` async interface and returns
configurable responses.

### Step 2: Test QuickAnswers pattern matching

Test each of the three pattern categories ("clear", "obstacles", "directions"). For "clear" patterns,
test with empty obstacles (expect "Path clear"), with critical obstacle (expect "Warning" prefix),
and with non-critical closest obstacle. For "obstacles" patterns, test with zero and multiple
obstacles. Verify that non-matching questions return `None`.

### Step 3: Test MicroNavFormatter output

Create a `FusedResult` with 2 obstacles at known positions and depths. Call `formatter.format()`
and verify the output contains the object count, primary obstacle description, and action
recommendation. Test with empty obstacles to get "Path clear ahead."

### Step 4: Test VQAReasoner with mock LLM

Build a `VQAReasoner` with a mock LLM client. Create a `VQARequest` with question, scene_graph,
and fused_result. Call `await reasoner.answer(request)`. Verify the response has `source == "llm"`,
non-zero confidence, and the answer text from the mock.

### Step 5: Test cache behavior

Call `reasoner.answer()` twice with the same request. Verify the second call returns
`source == "cache"` and has processing_time_ms close to 0.5. Test that a different question
produces a cache miss. Verify the cache max of 128 entries is respected by inserting 130 entries
and checking the dict size.

### Step 6: Test safety prefix generation

Create a `FusedResult` with a critical obstacle. Build a `VQARequest` with this fused result.
Verify the response's `safety_prefix` is non-empty and contains "Warning" or "Stop". Test
`get_full_answer()` concatenates the prefix with the answer.

### Step 7: Test stats tracking

Make 5 requests (3 unique, 2 cache hits). Call `reasoner.get_stats()` and verify
`total_requests == 5`, `cache_hits == 2`, `cache_hit_rate` is approximately 0.4.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_vqa_reasoner.py` | 6 test cases for VQAReasoner + QuickAnswers |

## Files to Modify

| File | Change |
|------|--------|
| `core/vqa/AGENTS.md` | Add test coverage note for vqa_reasoner.py |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_vqa_reasoner.py` | `TestQuickAnswers::test_clear_path_patterns` |
| | `TestQuickAnswers::test_obstacle_patterns` |
| | `TestQuickAnswers::test_nonmatching_returns_none` |
| | `TestMicroNavFormatter::test_format_with_obstacles` |
| | `TestMicroNavFormatter::test_format_empty_scene` |
| | `TestVQAReasoner::test_answer_with_mock_llm` |
| | `TestVQAReasoner::test_cache_hit_on_repeat` |
| | `TestVQAReasoner::test_safety_prefix_critical` |
| | `TestVQAReasoner::test_stats_tracking` |

## Acceptance Criteria

- [ ] All 9 tests pass with `pytest tests/unit/test_vqa_reasoner.py -v`
- [ ] QuickAnswers tests cover all three PATTERNS categories
- [ ] Mock LLM client mimics `chat.completions.create()` async interface
- [ ] Cache test confirms `source == "cache"` on second identical request
- [ ] Safety prefix test verifies `get_full_answer()` prepends prefix to answer text
- [ ] Stats test validates `total_requests`, `cache_hits`, and `cache_hit_rate` values
- [ ] MicroNavFormatter test verifies "Path clear ahead." for empty obstacles
- [ ] No test requires a live Ollama or OpenAI endpoint
- [ ] `ruff check tests/unit/test_vqa_reasoner.py` passes clean
- [ ] `lint-imports` passes with no architecture violations
- [ ] All async tests work with pytest auto mode (no manual `@pytest.mark.asyncio`)

## Upstream Dependencies

- **T-024** (perception-orchestrator-tests): Perception tests validate the data structures (`PerceptionResult`, `SceneGraph`) that feed into the reasoner. Completing T-024 confirms the input contracts.

## Downstream Unblocks

- None. T-025 is a terminal node in the VQA cluster DAG.

## Estimated Scope

- **Effort**: ~4 hours
- **Lines of test code**: 250-320
- **Risk**: Low. All LLM calls are mocked. `FusedResult` and `FusedObstacle` are simple dataclasses that can be constructed directly.
- **Parallel**: Yes. Can run alongside any non-VQA task.
- **Environment**: Local GPU not required. Pure CPU mocked tests.
