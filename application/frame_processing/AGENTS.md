# Frame_processing Context

## Purpose
Module responsible for frame processing functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `confidence_cascade.py`: Implementation/configuration file.
- `frame_orchestrator.py`: Implementation/configuration file.
- `freshness.py`: Implementation/configuration file.
- `live_frame_manager.py`: Implementation/configuration file.
- `spatial_binding.py`: Implementation/configuration file.
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
