# Realtime Context

## Purpose
Module responsible for realtime functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `benchmark.py`: Implementation/configuration file.
- `calibrate_depth.py`: Implementation/configuration file.
- `EVALUATION_FORMS.md`: Implementation/configuration file.
- `metrics.py`: Implementation/configuration file.
- `realtime_test.py`: Implementation/configuration file.
- `replay_tool.py`: Implementation/configuration file.
- `SAFETY_PROTOCOLS.md`: Implementation/configuration file.
- `session_logger.py`: Implementation/configuration file.
- `TEST_PLAN.md`: Implementation/configuration file.
- ... and 1 more files.

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
