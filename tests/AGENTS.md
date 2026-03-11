# Tests Context

## Purpose
Testing directory for tests.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `conftest.py`: Implementation/configuration file.
- `conftest_vision.py`: Implementation/configuration file.
- `generated_scenarios.json`: Implementation/configuration file.
- `test_action_engine.py`: Implementation/configuration file.
- `test_audio_engine.py`: Implementation/configuration file.
- `test_ci_smoke.py`: Implementation/configuration file.
- `test_confidence_cascade.py`: Implementation/configuration file.
- `test_continuous_processing.py`: Implementation/configuration file.
- `test_debug_visualizer.py`: Implementation/configuration file.
- ... and 20 more files.

## Patterns and Conventions
- Follow standard Python naming conventions.
- Maintain modularity and single responsibility.
- Refer to `conductor/` or root guidelines for specific architectural patterns.

## Dependencies
- Interacts with sibling modules and shared utilities.
- Relies on core/ and shared/ components.

## Gotchas and Important Notes
- Ensure paths are resolved relative to the project root.
- Watch out for circular dependencies when importing from other modules.
