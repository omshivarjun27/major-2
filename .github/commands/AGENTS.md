# Commands Context

## Purpose
Module responsible for commands functionality.

## Key Files
- `gemini-invoke.toml`: Implementation/configuration file.
- `gemini-plan-execute.toml`: Implementation/configuration file.
- `gemini-review.toml`: Implementation/configuration file.
- `gemini-scheduled-triage.toml`: Implementation/configuration file.
- `gemini-triage.toml`: Implementation/configuration file.

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
