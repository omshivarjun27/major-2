# Memory Context

## Purpose
Module responsible for memory functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `api_endpoints.py`: Implementation/configuration file.
- `api_schema.py`: Implementation/configuration file.
- `cloud_sync.py`: Implementation/configuration file.
- `config.py`: Implementation/configuration file.
- `conflict_resolver.py`: Implementation/configuration file.
- `embeddings.py`: Implementation/configuration file.
- `event_detection.py`: Implementation/configuration file.
- `faiss_sync.py`: Implementation/configuration file.
- `indexer.py`: Implementation/configuration file.
- ... and 13 more files.

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
