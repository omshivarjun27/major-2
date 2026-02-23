---
id: ISSUE-021
title: pytest-timeout Not Installed Despite Being Configured in pyproject.toml
severity: medium
source_artifact: ci_summary.json
architecture_layer: cross-cutting
---

## Description
`pyproject.toml` configures `timeout = 120` for pytest, but the `pytest-timeout` package is not installed in the virtual environment. This results in a configuration warning and timeout enforcement being silently disabled.

## Root Cause
The `pytest-timeout` package was configured in `pyproject.toml` but not added to `requirements.txt` or `requirements-extras.txt` as a dependency.

## Impact
Tests that hang (e.g., due to deadlocks, infinite loops, or waiting on unavailable services) will never timeout and will block CI indefinitely. The timeout configuration gives a false sense of safety.

## Reproducibility
always

## Remediation Plan
1. Add `pytest-timeout>=2.2.0` to dev dependencies in `pyproject.toml` and/or `requirements.txt`.
2. Verify that the configured `timeout = 120` takes effect.
3. Add a test that validates timeout enforcement works.

## Implementation Suggestion
```bash
pip install pytest-timeout>=2.2.0
# Add to pyproject.toml [project.optional-dependencies] dev section:
# "pytest-timeout>=2.2.0"
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] `pytest-timeout` listed as a dev dependency
- [ ] `pytest --co` shows no "unknown config option: timeout" warning
- [ ] Tests exceeding 120 seconds are properly terminated
- [ ] CI pipeline benefits from timeout enforcement
