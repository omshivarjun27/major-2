# T-117: CLIP Action Recognition Model

## Status: completed

## Objective
Integrate OpenAI CLIP model to classify actions from short video segments (1-3 seconds). Define action vocabulary of 50 common indoor activities. Implement frame sampling strategy: extract 4 evenly-spaced frames per clip. Target classification latency under 200ms per clip. Support both zero-shot (text prompts) and fine-tuned classification modes.

## Requirements
- CLIP model integration for action classification
- 50 common indoor activity vocabulary (IndoorAction enum)
- Zero-shot classification via text prompts (ACTION_PROMPTS)
- Frame sampling: 4 evenly-spaced frames per clip
- Classification latency < 200ms target
- Graceful fallback to motion heuristics when CLIP unavailable
- Fine-tuned model path support

## Implementation Plan
1. Define IndoorAction enum with 50 indoor activities
2. Create ACTION_PROMPTS mapping for zero-shot classification
3. Implement CLIPConfig dataclass with model/device/sampling settings
4. Implement CLIPActionResult with to_dict() and user_cue
5. Implement CLIPActionRecognizer with lazy CLIP loading
6. Add frame sampling (4 evenly-spaced frames)
7. Add text embedding caching for performance
8. Add mock classifier fallback
9. Create factory function

## Files Modified
- `core/action/clip_recognizer.py` - CLIP action recognition module
- `core/action/__init__.py` - Updated exports
- `tests/unit/test_clip_recognizer.py` - 40+ unit tests

## Test Coverage
- IndoorAction enum completeness (50 actions)
- ACTION_PROMPTS coverage
- CLIPConfig defaults and custom values
- CLIPActionResult serialization and user cues
- Frame sampling (exact, fewer, more, evenly-spaced)
- Mock classification (static, motion, empty, single frame)
- Statistics tracking (classifications, latency)
- Factory function
- Edge cases (float32, grayscale, large clips, high motion)

## Acceptance Criteria
- [x] 50 indoor action vocabulary defined
- [x] Zero-shot CLIP classification with text prompts
- [x] Frame sampling extracts 4 evenly-spaced frames
- [x] Graceful fallback when CLIP unavailable
- [x] Factory function for creation
- [x] Unit tests passing
