# core/vision/AGENTS.md
Ultra-low-latency spatial perception optimized for real-time blind navigation.
**Key Focus**: Performance, memory efficiency, and deterministic timing.

## WHERE TO LOOK
- `spatial.py` (1157 LOC): Main engine for obstacle detection & depth-aware fusion.
- `visual.py`: Specialized vision processors (color, lighting, scene attributes).
- `video_processing.py`: Frame extraction, normalization, and video stream utilities.

## ULTRA-LOW-LATENCY CONSTANTS
These constants are tuned for the RTX 4060 target. **DO NOT increase without NFR testing**.
- `MAX_DETECTIONS = 2`          # Keeps fusion complexity constant.
- `MAX_MASK_SIZE = (160, 120)`  # Aggressive downscale to keep segmentation fast.
- `DEPTH_DOWNSCALE = 4`         # Sub-sampled depth map resolution.
- `SKIP_SEGMENTATION_BELOW_MS = 50` # Heuristic skip for performance.
- `GC_AFTER_FRAME = True`       # Explicitly trigger GC every frame to prevent spikes.

## ARCHITECTURE & CONVENTIONS
- **BaseDetector ABC**: All detectors (YOLO, MiDaS, Mock) must implement `detect()` or `estimate()`.
- **Inference**: Uses `onnxruntime` by default for CPU/GPU efficiency.
- **Lazy Imports**: `torch`, `PIL`, and `cv2` are imported only inside the specific detector/processor methods.
- **Resource Management**: Uses a custom `ScopedResource` pattern to ensure GPU memory is freed in the event of pipeline hangs.

## DISAMBIGUATION
- **core.vision** focuses on **raw speed** and low-level obstacle detection.
- **core.vqa.perception** focuses on **full scene understanding** and integration with the SceneGraph + LMM.
- **Use core.vision** for: Micro-navigation, hazard detection, collision avoidance.
- **Use core.vqa** for: General scene description, visual questions, complex reasoning.
