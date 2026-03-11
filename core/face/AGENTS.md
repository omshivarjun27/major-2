# Face Context

## Purpose
Module responsible for face functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `consent_audit.py`: Implementation/configuration file.
- `face_detector.py`: Implementation/configuration file.
- `face_embeddings.py`: Implementation/configuration file.
- `face_social_cues.py`: Implementation/configuration file.
- `face_tracker.py`: Implementation/configuration file.
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
