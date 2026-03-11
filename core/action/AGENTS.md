# Action Context

## Purpose
Module responsible for action functionality.

## Key Files
- `action_context.py`: Implementation/configuration file.
- `action_recognizer.py`: Implementation/configuration file.
- `AGENTS.md`: Implementation/configuration file.
- `clip_recognizer.py`: Implementation/configuration file.
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
