# Configs Context

## Purpose
Module responsible for configs functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `config.yaml`: Implementation/configuration file.
- `development.yaml`: Implementation/configuration file.
- `production.yaml`: Implementation/configuration file.
- `staging.yaml`: Implementation/configuration file.

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
