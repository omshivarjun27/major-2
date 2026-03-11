# Performance Context

## Purpose
Module responsible for performance functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `conftest.py`: Implementation/configuration file.
- `test_access_control_fuzz.py`: Implementation/configuration file.
- `test_agent_startup.py`: Implementation/configuration file.
- `test_async_verification.py`: Implementation/configuration file.
- `test_baseline_capture.py`: Implementation/configuration file.
- `test_benchmark_report.py`: Implementation/configuration file.
- `test_chaos.py`: Implementation/configuration file.
- `test_consent_enforcement.py`: Implementation/configuration file.
- `test_debug_access_control.py`: Implementation/configuration file.
- ... and 38 more files.

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
