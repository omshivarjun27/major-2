# T-074: hot-path-profiling

> Phase: P4 | Cluster: CL-TQA | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Profile the end-to-end hot path to identify bottlenecks preventing achievement of the 500ms SLA. Use Python profiling tools (cProfile, py-spy, or line_profiler) to generate flame graphs and identify the top 5 time-consuming operations. Focus on the voice interaction loop: STT → LLM/VQA → TTS.

## Implementation Plan

1. Set up profiling infrastructure using py-spy for low-overhead production profiling.
2. Profile a representative hot-path scenario:
   - User speaks a question
   - STT transcribes
   - LLM/VQA processes
   - TTS synthesizes response
3. Generate flame graphs for visual analysis.
4. Identify top 5 bottlenecks by cumulative time.
5. Document findings with specific file/function locations.
6. Create optimization recommendations prioritized by impact.

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/profile_hot_path.py` | Profiling harness script |
| `docs/performance/hot-path-analysis.md` | Analysis and recommendations |

## Acceptance Criteria

- [ ] Flame graph generated for hot path execution
- [ ] Top 5 bottlenecks identified with specific locations
- [ ] Each bottleneck has measured time contribution
- [ ] Optimization recommendations documented
- [ ] Profile can be reproduced on demand

## Upstream Dependencies

T-073 (baseline capture)

## Downstream Unblocks

T-075 (pipeline latency optimization), T-082 (LLM optimization)

## Estimated Scope

Small-Medium. Profiling and analysis, ~100-150 lines of scripts.
