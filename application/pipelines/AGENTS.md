# Pipelines Context

## Purpose
Module responsible for pipelines functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `audio_manager.py`: Implementation/configuration file.
- `cancellation.py`: Implementation/configuration file.
- `debouncer.py`: Implementation/configuration file.
- `frame_sampler.py`: Implementation/configuration file.
- `integration.py`: Implementation/configuration file.
- `perception_pool.py`: Implementation/configuration file.
- `perception_telemetry.py`: Implementation/configuration file.
- `pipeline_monitor.py`: Implementation/configuration file.
- `streaming_tts.py`: Implementation/configuration file.
- ... and 3 more files.

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
