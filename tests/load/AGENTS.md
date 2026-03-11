# Load Context

## Purpose
Module responsible for load functionality.

## Key Files
- `conftest.py`: Implementation/configuration file.
- `locustfile.py`: Implementation/configuration file.
- `README.md`: Implementation/configuration file.
- `test_concurrent_users.py`: Implementation/configuration file.
- `test_load_infrastructure.py`: Implementation/configuration file.

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
