# Vqa Context

## Purpose
Module responsible for vqa functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `api_endpoints.py`: Implementation/configuration file.
- `api_schema.py`: Implementation/configuration file.
- `memory.py`: Implementation/configuration file.
- `multi_frame_vqa.py`: Implementation/configuration file.
- `orchestrator.py`: Implementation/configuration file.
- `perception.py`: Implementation/configuration file.
- `priority_scene.py`: Implementation/configuration file.
- `scene_graph.py`: Implementation/configuration file.
- `scene_narrator.py`: Implementation/configuration file.
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
