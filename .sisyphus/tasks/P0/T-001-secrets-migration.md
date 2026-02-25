# T-001: secrets-migration

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Create a SecretProvider abstraction in `shared/config/` with two concrete implementations:
(a) `EnvFileProvider` that reads from `.env` files for local development, and
(b) `EnvironmentProvider` that reads from OS environment variables for Docker/CI.

Refactor `shared/config/settings.py` to retrieve the 7 API keys through the SecretProvider
interface instead of direct `os.environ.get()` calls. Backward compatibility preserved.

## Current State (Codebase Audit 2026-02-25)

- `shared/config/settings.py` (372 lines) uses a flat `CONFIG = {}` dict with 82 `os.environ.get()` calls
- No SecretProvider abstraction exists
- No python-dotenv dependency (env vars read directly from OS)
- 7 secret keys scattered across CONFIG dict:
  - Line 28: `OLLAMA_VL_API_KEY`
  - Line 33: `TAVUS_API_KEY`
  - Lines not in CONFIG but used by LiveKit agent: `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
  - Lines not in CONFIG but used by infrastructure: `DEEPGRAM_API_KEY`, `ELEVEN_API_KEY`, `OLLAMA_API_KEY`
- Feature flags and non-secret config vars use `os.environ.get()` with safe defaults
- Config accessed via helper functions: `get_spatial_config()`, `get_face_config()`, etc.

## Implementation Plan

### Step 1: Create SecretProvider ABC

Create `shared/config/secret_provider.py`:

```python
from abc import ABC, abstractmethod
from typing import Optional

class SecretProvider(ABC):
    """Abstraction for secret retrieval."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret by key name. Returns None if not found."""
        ...

    def supports_rotation(self) -> bool:
        """Whether this provider supports key rotation. Extension point."""
        return False

    def health_check(self) -> bool:
        """Verify the provider is operational."""
        return True
```

### Step 2: Implement EnvFileProvider

In same file or separate `shared/config/env_file_provider.py`:

```python
class EnvFileProvider(SecretProvider):
    """Reads secrets from .env file (local development)."""

    def __init__(self, env_path: str = ".env"):
        self._secrets: dict[str, str] = {}
        self._load(env_path)

    def _load(self, path: str) -> None:
        # Parse .env file manually (no python-dotenv dependency)
        # Format: KEY=VALUE, ignore comments (#), blank lines
        ...

    def get_secret(self, key: str) -> Optional[str]:
        return self._secrets.get(key)

    def health_check(self) -> bool:
        return len(self._secrets) > 0
```

### Step 3: Implement EnvironmentProvider

```python
class EnvironmentProvider(SecretProvider):
    """Reads secrets from OS environment variables (Docker/CI)."""

    def get_secret(self, key: str) -> Optional[str]:
        value = os.environ.get(key, "").strip()
        return value if value else None

    def health_check(self) -> bool:
        return True  # OS env is always available
```

### Step 4: Add provider factory

```python
def create_secret_provider() -> SecretProvider:
    """Auto-detect environment and return appropriate provider."""
    if _is_docker():
        return EnvironmentProvider()
    return EnvFileProvider()

def _is_docker() -> bool:
    """Detect if running inside Docker."""
    return (
        os.path.exists("/.dockerenv")
        or os.environ.get("DOCKER", "").lower() == "true"
        or os.environ.get("CONTAINER", "").lower() == "true"
    )
```

### Step 5: Refactor settings.py

Replace direct `os.environ.get()` for the 7 secret keys with SecretProvider calls:

```python
from shared.config.secret_provider import create_secret_provider

_secrets = create_secret_provider()

CONFIG = {
    # Secret keys - via provider
    "OLLAMA_VL_API_KEY": _secrets.get_secret("OLLAMA_VL_API_KEY") or "",
    "TAVUS_API_KEY": _secrets.get_secret("TAVUS_API_KEY") or "",
    # ... (7 total)

    # Non-secret config - keep os.environ.get() as-is
    "SPATIAL_PERCEPTION_ENABLED": os.environ.get(...),
    # ...
}
```

Only the 7 API keys change. All other 75 config vars keep `os.environ.get()`.

## Files to Create

| File | Purpose |
|------|---------|
| `shared/config/secret_provider.py` | ABC + EnvFileProvider + EnvironmentProvider + factory |

## Files to Modify

| File | Change |
|------|--------|
| `shared/config/settings.py` | Replace 7 `os.environ.get()` calls for secret keys with `_secrets.get_secret()` |
| `shared/config/__init__.py` | Export `SecretProvider`, `create_secret_provider` |

## Secret Keys (Exhaustive List)

1. `LIVEKIT_API_KEY`
2. `LIVEKIT_API_SECRET`
3. `DEEPGRAM_API_KEY`
4. `OLLAMA_API_KEY`
5. `ELEVEN_API_KEY`
6. `OLLAMA_VL_API_KEY`
7. `TAVUS_API_KEY`

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_secret_provider.py` | EnvFileProvider reads .env correctly |
| | EnvironmentProvider reads os.environ correctly |
| | Factory returns EnvironmentProvider in Docker context |
| | Factory returns EnvFileProvider otherwise |
| | get_secret returns None for missing keys |
| | health_check returns True/False appropriately |
| | .env parsing handles comments, blank lines, quotes |
| `tests/integration/test_settings_secrets.py` | settings.py loads secrets through provider |
| | Backward compat: CONFIG still has expected keys |

## Acceptance Criteria

- [ ] SecretProvider ABC with get_secret, supports_rotation, health_check
- [ ] EnvFileProvider reads .env without python-dotenv dependency
- [ ] EnvironmentProvider reads os.environ
- [ ] Factory auto-detects Docker vs local
- [ ] settings.py uses provider for 7 secret keys only
- [ ] All other 75 config vars unchanged (os.environ.get)
- [ ] All existing tests pass (no behavioral regression)
- [ ] New unit tests for provider (>= 8 test functions)
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

None (entry point task).

## Downstream Unblocks

T-002, T-004, T-006, T-008, T-009

## Estimated Scope

- New code: ~120 LOC
- Modified code: ~15 lines in settings.py
- Tests: ~100 LOC
- Risk: Low (additive abstraction, backward compatible)
