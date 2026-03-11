# Unit Context

## Purpose
Module responsible for unit functionality.

## Key Files
- `AGENTS.md`: Implementation/configuration file.
- `test_action_context.py`: Implementation/configuration file.
- `test_action_recognition_edge_cases.py`: Implementation/configuration file.
- `test_async_audit.py`: Implementation/configuration file.
- `test_async_blocking_regression.py`: Implementation/configuration file.
- `test_audio_events_edge_cases.py`: Implementation/configuration file.
- `test_backup_scheduler.py`: Implementation/configuration file.
- `test_braille_classifier.py`: Implementation/configuration file.
- `test_braille_segmenter.py`: Implementation/configuration file.
- `test_cache_manager.py`: Implementation/configuration file.
- ... and 82 more files.

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
