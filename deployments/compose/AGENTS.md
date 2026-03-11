# Compose Context

## Purpose
Module responsible for compose functionality.

## Key Files
- `docker-compose.dev.yml`: Implementation/configuration file.
- `docker-compose.prod.yml`: Implementation/configuration file.
- `docker-compose.staging.yml`: Implementation/configuration file.
- `docker-compose.test.yml`: Implementation/configuration file.

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
