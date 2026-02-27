# T-078: int8-quantization-implementation

> Phase: P4 | Cluster: CL-VIS | Risk: High | State: completed | created_at: 2026-02-27T20:00:00Z

## Objective

Implement INT8 quantization for vision models (YOLO, MiDaS) to reduce VRAM usage and improve inference speed. Balance precision loss against the critical 300ms vision processing budget. Validate that quantized models maintain acceptable accuracy for the blind assistance use case.

## Implementation Plan

1. Research INT8 quantization options for ONNX models.
2. Create quantization scripts for:
   - YOLO object detector → INT8
   - MiDaS depth estimator → INT8
3. Implement model loader that selects quantized vs full-precision based on config.
4. Benchmark quantized models:
   - Inference latency comparison
   - VRAM usage comparison
   - Accuracy/quality comparison
5. Add `ENABLE_QUANTIZATION` feature flag in settings.
6. Create A/B comparison tests.

## Files to Create/Modify

| File | Purpose |
|------|---------|
| `scripts/quantize_models.py` | Model quantization script |
| `core/vision/model_loader.py` | Quantization-aware model loading |
| `shared/config/settings.py` | Add ENABLE_QUANTIZATION flag |
| `tests/performance/test_quantization.py` | Quantization benchmark tests |

## Acceptance Criteria

- [ ] YOLO quantized to INT8 with <5% accuracy loss
- [ ] MiDaS quantized to INT8 with acceptable depth quality
- [ ] VRAM reduction measured and documented
- [ ] Inference speedup measured and documented
- [ ] Vision processing stays within 300ms budget
- [ ] Feature flag allows runtime selection
- [ ] Quantized models work correctly in full pipeline

## Upstream Dependencies

T-077 (VRAM profiling)

## Downstream Unblocks

T-083 (frame processing optimization)

## Estimated Scope

Large. Model quantization with validation, ~300-400 lines of code.
