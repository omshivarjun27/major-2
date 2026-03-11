# Performance Context

## Purpose
Module responsible for performance functionality.

## Key Files
- `baseline-metrics.json`: Implementation/configuration file.
- `baseline-report.md`: Implementation/configuration file.
- `hot-path-analysis.md`: Implementation/configuration file.
- `hot-path-metrics.json`: Implementation/configuration file.
- `load-test-results.md`: Implementation/configuration file.
- `vram-analysis.md`: Implementation/configuration file.

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
