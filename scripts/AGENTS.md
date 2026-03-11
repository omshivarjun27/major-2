# Scripts Context

## Purpose
Module responsible for scripts functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `async_audit.py`: Implementation/configuration file.
- `canary_analysis.py`: Implementation/configuration file.
- `canary_deploy.py`: Implementation/configuration file.
- `canary_promote.py`: Implementation/configuration file.
- `capture_baseline.py`: Implementation/configuration file.
- `check_deps.py`: Implementation/configuration file.
- `check_deps.sh`: Implementation/configuration file.
- `download_models.py`: Implementation/configuration file.
- `generate_release_notes.py`: Implementation/configuration file.
- ... and 15 more files.

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
