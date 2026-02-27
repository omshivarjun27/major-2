# T-077: vram-profiling-analysis

> Phase: P4 | Cluster: CL-VIS | Risk: Medium | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Profile GPU VRAM usage across all components to identify optimization opportunities. Map VRAM consumption to specific models and operations. Current peak is 3.1GB; target is staying well within the 8GB budget while enabling potential for larger models or concurrent processing.

## Implementation Plan

1. Create VRAM profiling utilities in `shared/utils/vram_profiler.py`.
2. Profile VRAM usage for each component:
   - YOLO detector (ONNX)
   - MiDaS depth estimator
   - Qwen-VL / vision model
   - Ollama LLM embeddings
   - FAISS index (if GPU-backed)
3. Measure VRAM at:
   - Idle state
   - Single request processing
   - Peak concurrent load
4. Identify top 3 VRAM consumers.
5. Document findings with recommendations for optimization.

## Files to Create

| File | Purpose |
|------|---------|
| `shared/utils/vram_profiler.py` | VRAM profiling utilities |
| `scripts/profile_vram.py` | VRAM profiling script |
| `docs/performance/vram-analysis.md` | VRAM usage analysis |

## Acceptance Criteria

- [ ] VRAM profiler utility created and working
- [ ] All major components profiled
- [ ] Peak VRAM usage documented
- [ ] Top 3 VRAM consumers identified
- [ ] Optimization recommendations provided
- [ ] Profiling is repeatable

## Upstream Dependencies

T-073 (baseline capture)

## Downstream Unblocks

T-078 (INT8 quantization)

## Estimated Scope

Small-Medium. Profiling and analysis, ~150-200 lines of code.
