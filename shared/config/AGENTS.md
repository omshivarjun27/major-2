## 1. Purpose
- Centralize and standardize runtime configuration for the base layer.
- Use Pydantic BaseSettings to load, validate, and type-enforce environment variables.
- Expose at least 85 environment variables across the application with sensible defaults.
- Implement 7 feature flags to enable/disable critical capabilities safely.
- Ensure no cross-layer imports and confine config access to the shared layer.
- Provide a single source of truth for configuration to reduce drift and misconfiguration.

## 2. Components
- Pydantic BaseSettings subclass that maps env vars to strongly-typed fields.
- Nested Config groups for logical separation (e.g., security, logging, memory).
- Validation via validators to enforce formats (e.g., URL, path, boolean-ish strings).
- Feature flags collection with explicit enabled/disabled semantics.
- Secrets handling through os.environ and vault-backed fetch when available.
- Utility helpers for casting and defaulting values.
- Integration hooks for CI validation and import-linter checks.

## 3. Dependencies
- Python 3.10+ is required.
- Pydantic is the primary validation library.
- No imports from lower layers are allowed; config is a shared, non-IO helper.
- Requires a plan for secrets management if/when replacement is needed (e.g., Vault).
- CI enforces linting and type-checking against the config module.
- Documentation and tests exist under tests/config.

## 4. Tasks
- Enumerate and document all 85+ environment variables with usage context.
- Implement 7 feature flags with clear default states and safety checks.
- Expose a clean API for other modules to read config values without direct env access.
- Add unit tests for validation rules and boundary cases.
- Integrate with the plan to fail gracefully on misconfigurations.
- Ensure defaults are sensible to enable safe first-run experiences.
- Add migration notes for potential future config format changes.

## 5. Design
- Flat, explicit mapping from env vars to typed fields; avoid magic values.
- Grouped fields by concern, not by file location, to simplify maintenance.
- Defaults chosen to minimize surprises in new environments.
- Feature flags guarded by runtime checks to prevent partial startup.
- Secrets are never logged; sensitive values are redacted in logs.
- Tests cover both positive and negative validation paths.
- The module is import-safe and read-only for other layers.

## 6. Research
- Best-practice: keep all config sources in one central place and validate at startup.
- Use strong types and validators to catch misconfig before runtime.
- Separate secrets management from application logic to reduce surface area.
- Review shows typical patterns: default fallbacks, environment variable rendering,
  and permissive error behavior on missing non-critical vars.
- Evaluate whether all 85+ vars are still needed; prune where appropriate.

## 7. Risk
- Missing or misnamed environment variables causing startup failures.
- Secrets exposure if logs include values; mitigated by redaction.
- Feature flags left in inconsistent states across deployments.
- Drift between documented defaults and actual env values.
- Secret rotation and vault integration complexity.

## 8. Improvements
- Add a dedicated docs generator to export env var usage to PRD.
- Introduce a test matrix for various environment configurations.
- Add a small CLI to dump current effective configuration for debugging.
- Introduce a lint rule to ensure no direct os.environ access outside this module.
- Implement circular import guards to maintain the 5-layer boundary.

## 9. Change Log
- Created AGENTS.md for shared/config to codify env var strategy and feature flags.
- Documented the 85+ vars and 7 flags to guide future changes.
- Set expectations for secrets handling and validation at startup.
- Updated to align with the 9-section AGENTS.md template.
