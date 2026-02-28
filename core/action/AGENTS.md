## 1. Purpose
Document the CLIP-based action recognition workers within the core/action module, including how gestures and motions are inferred and surfaced to higher layers.

## 2. Key components
- ActionRecognizer: CLIP-based model-driven recognizer for human gestures and motions.
- ClipBuffer: buffers 16-frame clips with stride 4; minimum confidence threshold 0.3.

## 3. Status
IN PROGRESS. Implementation aligns with the shared feature flag system via action_enabled().

## 4. Dependencies
- Depends on shared/ for configuration and utilities.
- Interfaces with memory and vision modules for alignment with scene context.

## 5. Interfaces and integration
- Used by the perception pipeline to annotate actions; results feed decision logic in application layer.
- Activation toggled by action_enabled() flag in shared config.

## 6. Testing & validation
- Unit tests for ActionRecognizer and ClipBuffer behavior.
- Integration tests validating gesture/motion detection in simulated scenarios when feature flags enable it.

## 7. Risks & mitigations
- Potential misclassification of gestures. Mitigation: confidence thresholds and cross-modal validation.
- Latency risk on long clips. Mitigation: fixed clip length and stride, efficient buffering.

## 8. Documentation & references
- Internal references to core/action components and integration points.

## 9. Notes
- Placeholder behavior may be refined as more robust datasets for action recognition are assembled.
