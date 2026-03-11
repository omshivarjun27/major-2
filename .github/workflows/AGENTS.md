# Workflows Context

## Purpose
Module responsible for workflows functionality.

## Key Files
- `ci.yml`: Implementation/configuration file.
- `deploy-production.yml`: Implementation/configuration file.
- `deploy-staging.yml`: Implementation/configuration file.
- `gemini-dispatch.yml`: Implementation/configuration file.
- `gemini-invoke.yml`: Implementation/configuration file.
- `gemini-plan-execute.yml`: Implementation/configuration file.
- `gemini-review.yml`: Implementation/configuration file.
- `gemini-scheduled-triage.yml`: Implementation/configuration file.
- `gemini-triage.yml`: Implementation/configuration file.
- `security.yml`: Implementation/configuration file.

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
