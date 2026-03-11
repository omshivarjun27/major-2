# Docs Context

## Purpose
Documentation and reference materials.

## Key Files
- `accessibility-audit.md`: Implementation/configuration file.
- `AGENTS.md`: Implementation/configuration file.
- `architecture.md`: Implementation/configuration file.
- `benchmarking-protocol.md`: Implementation/configuration file.
- `canary-deployment.md`: Implementation/configuration file.
- `configuration.md`: Implementation/configuration file.
- `DataFlow.md`: Implementation/configuration file.
- `docs-index.md`: Implementation/configuration file.
- `HLD.md`: Implementation/configuration file.
- `LLD.md`: Implementation/configuration file.
- ... and 14 more files.

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
