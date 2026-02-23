---
id: ISSUE-009
title: Hardcoded Camera FOV and Resolution Assumptions
severity: medium
source_artifact: architecture_risks.md
architecture_layer: core
---

## Description
Camera parameters are hardcoded throughout the perception pipeline:
- FOV hardcoded at 70° in `SceneGraphBuilder.HORIZONTAL_FOV = 70.0`
- Image width assumed 640px in `MicroNavFormatter._format_direction()`
- Default image size 640×480 in fallback paths

## Root Cause
Initial development used a single camera model. Camera metadata is not passed through the pipeline, and no configuration mechanism exists for camera parameters.

## Impact
Navigation directions will be incorrect for cameras with different FOV (e.g., wide-angle phone cameras at 90°+). Distance calculations and direction binning will be skewed, producing misleading spatial cues for blind users.

## Reproducibility
likely

## Remediation Plan
1. Add `camera_fov` and `image_resolution` to `configs/config.yaml`.
2. Pass actual camera metadata through the perception pipeline via `PerceptionResult`.
3. Update `SceneGraphBuilder` and `MicroNavFormatter` to use dynamic values.
4. Default to 70°/640×480 for backward compatibility.

## Implementation Suggestion
```yaml
# configs/config.yaml
camera:
  horizontal_fov_degrees: 70.0
  default_width: 640
  default_height: 480
```
```python
# SceneGraphBuilder
class SceneGraphBuilder:
    def __init__(self, fov: float = None):
        self.HORIZONTAL_FOV = fov or config.get("camera.horizontal_fov_degrees", 70.0)
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] FOV and resolution configurable via `config.yaml`
- [ ] `SceneGraphBuilder` and `MicroNavFormatter` use dynamic camera parameters
- [ ] Default values maintain backward compatibility
- [ ] Unit tests verify direction calculation accuracy with different FOV values
