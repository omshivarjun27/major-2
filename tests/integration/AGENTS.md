# Integration Context

## Purpose
Module responsible for integration functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `test_agent_coordinator.py`: Implementation/configuration file.
- `test_canary.py`: Implementation/configuration file.
- `test_deepgram.py`: Implementation/configuration file.
- `test_failover_scenarios.py`: Implementation/configuration file.
- `test_frame_spatial_integration.py`: Implementation/configuration file.
- `test_memory_hybrid.py`: Implementation/configuration file.
- `test_memory_search.py`: Implementation/configuration file.
- `test_p0_security_smoke.py`: Implementation/configuration file.
- `test_p1_pipeline.py`: Implementation/configuration file.
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
