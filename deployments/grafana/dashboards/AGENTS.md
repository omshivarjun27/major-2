# Dashboards Context

## Purpose
Module responsible for dashboards functionality.

## Key Files
- `health-status.json`: Implementation/configuration file.
- `pipeline-performance.json`: Implementation/configuration file.
- `service-resilience.json`: Implementation/configuration file.
- `system-health.json`: Implementation/configuration file.
- `user-activity.json`: Implementation/configuration file.

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
