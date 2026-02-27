# VRAM Profiling Analysis

**Generated:** 2026-02-27T23:45:33.675154

## Device Information

- **GPU:** Not available (CPU mode)

## Summary

| Metric | Value | Budget | Status |
|--------|-------|--------|--------|
| Components Profiled | 4 | - | - |
| Estimated Peak VRAM | 0 MB | 8192 MB | OK |
| Budget Remaining | 8192 MB | - | - |

## Component Breakdown

| Component | Idle (MB) | Active (MB) | Peak (MB) | Load (ms) | Status |
|-----------|-----------|-------------|-----------|-----------|--------|
| PyTorch Baseline | - | - | - | - | N/A (CUDA not available) |
| FAISS Index (5K vectors) | 0.0 | 0.0 | 0.0 | 51 | OK |
| YOLO Detector | - | - | - | - | N/A (No module named 'core.vision.object_detector') |
| MiDaS Depth | - | - | - | - | N/A (No module named 'core.vision.depth_estimator') |

## Top VRAM Consumers

1. **FAISS Index (5K vectors)**: 0 MB (0.0% of budget)

## Notes

- VRAM measurements are approximate and may vary based on GPU driver and CUDA version.
- Peak VRAM includes PyTorch workspace and CUDA context overhead.
- Budget target of 8GB allows headroom for RTX 4060 (8GB VRAM).