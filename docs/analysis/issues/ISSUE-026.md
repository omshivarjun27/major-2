---
id: ISSUE-026
title: YOLODetector Silent Fallback to MockObjectDetector Without Runtime Alert
severity: medium
source_artifact: data_flows.md
architecture_layer: core
---

## Description
When `YOLODetector` fails to load (missing ONNX model file, CUDA unavailable, etc.), the perception pipeline silently falls through to `MockObjectDetector` without logging a runtime alert. The user and system operators receive no indication that real object detection has been replaced by a mock that returns synthetic detections.

## Root Cause
The factory function `create_detector()` in `core/vqa/perception.py` catches the YOLO load failure and returns the mock detector as a graceful degradation path. However, no warning or metric is emitted to distinguish real detection from mock data.

## Impact
- Users receive fabricated detection data from the mock detector without any indication
- Navigation cues based on mock data are meaningless and potentially misleading for a blind user
- Debugging perception issues is difficult when mock/real status is not observable
- Silent degradation masks model deployment failures

## Reproducibility
likely

## Remediation Plan
1. Add a `WARNING`-level log when falling back to `MockObjectDetector`.
2. Set a runtime flag (e.g., `detector.is_mock`) that can be checked by downstream components.
3. Surface mock status through the `/health` API endpoint.
4. Optionally prefix navigation cues with a disclaimer when using mock detections.

## Implementation Suggestion
```python
def create_detector(use_yolo: bool = False, model_path: str = None) -> ObjectDetector:
    if use_yolo:
        try:
            detector = YOLODetector(model_path)
            logger.info("YOLODetector initialized successfully")
            return detector
        except Exception as e:
            logger.warning(
                "YOLODetector failed to load (%s), falling back to MockObjectDetector. "
                "Spatial perception will use synthetic data.", e
            )
    detector = MockObjectDetector()
    detector.is_mock = True  # Flag for downstream checks
    return detector
```

## GPU Impact
YOLO model uses ~200MB VRAM on RTX 4060. Mock detector uses no GPU. Silent fallback to mock frees GPU resources without notification.

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] WARNING-level log emitted when falling back to MockObjectDetector
- [ ] `is_mock` flag available on detector instances
- [ ] `/health` endpoint reports whether real or mock detector is active
- [ ] Navigation cues indicate degraded mode when mock detector is in use
