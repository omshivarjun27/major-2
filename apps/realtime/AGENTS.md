# Realtime Context

## Purpose
Module responsible for realtime functionality.

## Key Files
- `agent.py`: Implementation/configuration file.
- `AGENTS.md`: Implementation/configuration file.
- `entrypoint.py`: Implementation/configuration file.
- `prompts.py`: Implementation/configuration file.
- `session_manager.py`: Implementation/configuration file.
- `tool_router.py`: Implementation/configuration file.
- `user_data.py`: Implementation/configuration file.
- `vision_controller.py`: Implementation/configuration file.
- `voice_controller.py`: Implementation/configuration file.
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
