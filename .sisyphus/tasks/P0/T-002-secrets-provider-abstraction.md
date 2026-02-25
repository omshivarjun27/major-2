# T-002: secrets-provider-abstraction

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Implement the SecretProvider ABC and two concrete backends created in T-001. Add provider
selection logic to settings.py that auto-detects the environment (Docker vs local).

## Current State (Codebase Audit 2026-02-25)

- T-001 creates the SecretProvider ABC and basic structure
- T-002 is the implementation/wiring task that makes settings.py actually use it
- settings.py currently has a flat CONFIG dict, no provider pattern
- No python-dotenv in requirements.txt
- Docker detection: no existing utility for this

## Dependency on T-001

T-001 creates `shared/config/secret_provider.py` with the ABC and factory.
T-002 wires it into `settings.py` and ensures the auto-detection logic works end-to-end.

Note: In practice, T-001 and T-002 overlap significantly. T-001 creates the abstraction,
T-002 validates and completes the wiring. They will likely execute as a single unit.

## Implementation Plan

### Step 1: Verify T-001 deliverables exist

Confirm these are in place from T-001:
- `shared/config/secret_provider.py` with SecretProvider ABC
- EnvFileProvider and EnvironmentProvider implementations
- `create_secret_provider()` factory

### Step 2: Wire auto-detection into settings.py

At the top of `shared/config/settings.py`, before CONFIG dict:

```python
from shared.config.secret_provider import create_secret_provider

_secret_provider = create_secret_provider()
logger.info("Secret provider: %s", type(_secret_provider).__name__)
```

### Step 3: Replace 7 secret key lookups

In the CONFIG dict, change:
```python
# Before (T-001 partial):
"OLLAMA_VL_API_KEY": _secrets.get_secret("OLLAMA_VL_API_KEY") or "",

# After (T-002 validated):
"OLLAMA_VL_API_KEY": _secret_provider.get_secret("OLLAMA_VL_API_KEY") or "",
"TAVUS_API_KEY": _secret_provider.get_secret("TAVUS_API_KEY") or "",
```

### Step 4: Add provider accessor

```python
def get_secret_provider() -> "SecretProvider":
    """Access the active secret provider for health checks."""
    return _secret_provider
```

### Step 5: Validate environment detection

Test that:
- In normal pytest: EnvFileProvider is selected (no /.dockerenv)
- With DOCKER=true env var: EnvironmentProvider is selected
- With /.dockerenv file: EnvironmentProvider is selected

## Files to Modify

| File | Change |
|------|--------|
| `shared/config/settings.py` | Wire _secret_provider, replace 7 lookups, add accessor |
| `shared/config/__init__.py` | Export get_secret_provider |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_secret_provider.py` | (extends T-001 tests) |
| | Auto-detection returns EnvFileProvider when not in Docker |
| | Auto-detection returns EnvironmentProvider when DOCKER=true |
| | settings.py CONFIG has all 7 keys populated from provider |
| | get_secret_provider() returns active instance |
| | Provider health_check callable |
| | supports_rotation returns False for both |

## Acceptance Criteria

- [ ] settings.py imports and uses create_secret_provider()
- [ ] 7 secret keys read through provider (not os.environ.get)
- [ ] 75 non-secret config vars still use os.environ.get (unchanged)
- [ ] Auto-detection selects correct provider based on environment
- [ ] get_secret_provider() exported and functional
- [ ] All existing tests pass
- [ ] ruff check clean, lint-imports clean

## Upstream Dependencies

T-001 (SecretProvider ABC and implementations must exist)

## Downstream Unblocks

T-004, T-009

## Estimated Scope

- Modified code: ~20 lines in settings.py, ~5 in __init__.py
- Tests: ~60 LOC (extending T-001 tests)
- Risk: Low (completing wiring from T-001)
