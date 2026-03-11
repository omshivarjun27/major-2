# Audio Context

## Purpose
Module responsible for audio functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `audio_event_detector.py`: Implementation/configuration file.
- `audio_fusion.py`: Implementation/configuration file.
- `enhanced_detector.py`: Implementation/configuration file.
- `ssl.py`: Implementation/configuration file.
- `__init__.py`: Implementation/configuration file.

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
