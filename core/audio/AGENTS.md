## 1. Purpose
Document the audio-layer agents responsible for acoustic sensing and fusion within the core/audio module.

## 2. Key components
- SoundSourceLocalizer: localizes the sound source using a microphone array when available, or a degraded mono input as a fallback.
- AudioEventDetector: detects and classifies audio events relevant to navigation and awareness.
- AudioVisionFuser: fuses audio cues with visual inputs to produce coherent multi-modal signals.

## 3. Status
IN PROGRESS. Implementation follows the core architectural pattern and is gated by the shared feature flag mechanism via audio_enabled().

## 4. Dependencies
- Depends on shared/ for configuration, utilities, and feature flags.
- Interfaces with vision and memory submodules as part of the perception loop.

## 5. Interfaces and integration
- Invoked by the perception pipeline; results are propagated to the reasoning/decision stages.
- Activation controlled by audio_enabled() flag in the shared configuration.

## 6. Testing & validation
- Unit tests for each component; integration tests for multi-modal fusion pathways when the flag is enabled.
- Tests should verify correct gating by audio_enabled() and graceful fallback behavior.

## 7. Risks & mitigations
- Risk: false positives/negatives in audio event detection. Mitigation: thresholding, cross-modal validation.
- Risk: localization drift with noisy inputs. Mitigation: sensor fusion with vision data.

## 8. Documentation & references
- Internal references: core/audio/AGENTS.md (this file) and related components.

## 9. Notes
- Hardware availability may influence testing; design favors graceful degradation and feature-flag-driven enablement.
