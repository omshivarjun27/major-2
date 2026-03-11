# Resilience Context

## Purpose
Module responsible for resilience functionality.

## Key Files
- `circuit_breaker.py`: Implementation/configuration file.
- `degradation_coordinator.py`: Implementation/configuration file.
- `error_classifier.py`: Implementation/configuration file.
- `health_registry.py`: Implementation/configuration file.
- `livekit_monitor.py`: Implementation/configuration file.
- `retry_policy.py`: Implementation/configuration file.
- `timeout_config.py`: Implementation/configuration file.
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
