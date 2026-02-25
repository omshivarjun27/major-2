# T-011: p0-security-integration-smoke-test

> Phase: P0 | Cluster: CL-TQA | Risk: Critical | State: not_started

## Objective

End-to-end verification that SecretProvider, PII scrubbing, and encryption work together.
Create pytest-compatible integration tests (no Docker daemon required).

## Current State (Codebase Audit 2026-02-25)

### Existing Security Tests
- `tests/performance/test_secrets_scan.py` (175 LOC) — regex-based secret detection in source files
- `tests/performance/test_access_control_fuzz.py` (130 LOC) — debug endpoint fuzzing
- `tests/test_encryption.py` (103 LOC) — EncryptionManager roundtrip tests

### Testing Patterns Available
- `env_overrides(monkeypatch)` fixture for temporary env var changes
- AsyncClient + ASGITransport for FastAPI endpoint testing
- pytest async mode = auto (no decorator needed)

### What T-011 Integrates
| Component | Source Task | Verification |
|-----------|-----------|--------------|
| SecretProvider | T-001, T-002 | Returns correct values, handles missing keys |
| PII Scrubber | T-008 | API keys redacted from log output |
| Encryption | T-006 | Encrypt/decrypt roundtrip works |
| Consent Encryption | T-007 | Consent files encrypted at rest |
| Docker Non-Root | T-003 | Verified by CI docker job (NOT in pytest) |

## Implementation Plan

### Step 1: Create test file

Create `tests/integration/test_p0_security_smoke.py`:

```python
"""P0 Security Integration Smoke Test.

Verifies that all P0 security components work together:
- SecretProvider returns expected values
- PII scrubber catches all API key formats
- EncryptionManager encrypts/decrypts consent-format JSON
- Components integrate cleanly (no import errors, no runtime crashes)
"""
import logging
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
```

### Step 2: SecretProvider integration tests

```python
class TestSecretProviderIntegration:
    """Verify SecretProvider works end-to-end."""

    SECRET_KEYS = [
        "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DEEPGRAM_API_KEY",
        "OLLAMA_API_KEY", "ELEVEN_API_KEY", "OLLAMA_VL_API_KEY", "TAVUS_API_KEY",
    ]

    def test_provider_returns_set_secrets(self, monkeypatch):
        """When env vars are set, provider returns their values."""
        for key in self.SECRET_KEYS:
            monkeypatch.setenv(key, f"test-value-{key}")
        from shared.config.secret_provider import create_secret_provider
        provider = create_secret_provider()
        for key in self.SECRET_KEYS:
            assert provider.get_secret(key) == f"test-value-{key}"

    def test_provider_returns_none_for_missing(self, monkeypatch):
        """When env vars are unset, provider returns None."""
        for key in self.SECRET_KEYS:
            monkeypatch.delenv(key, raising=False)
        from shared.config.secret_provider import create_secret_provider
        provider = create_secret_provider()
        for key in self.SECRET_KEYS:
            assert provider.get_secret(key) is None

    def test_provider_health_check(self):
        """Provider health check returns boolean."""
        from shared.config.secret_provider import create_secret_provider
        provider = create_secret_provider()
        assert isinstance(provider.health_check(), bool)
```

### Step 3: PII scrubber integration tests

```python
class TestPIIScrubberIntegration:
    """Verify PII scrubber catches all API key formats in logs."""

    TEST_KEYS = {
        "LIVEKIT_API_KEY": "APIabcdef1234567890",
        "LIVEKIT_API_SECRET": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
        "DEEPGRAM_API_KEY": "dg_abc123def456ghi789jkl012mno345",
        "OLLAMA_API_KEY": "ol1234567890abcdef1234567890abcdef",
        "ELEVEN_API_KEY": "abcdef1234567890abcdef1234567890",
        "OLLAMA_VL_API_KEY": "ol_abcdef1234567890abcdef1234567890",
        "TAVUS_API_KEY": "tvs_abcdef1234567890abcdef",
    }

    def test_all_key_formats_scrubbed(self):
        """None of the 7 API key formats appear in scrubbed log output."""
        from shared.logging.logging_config import PIIScrubFilter
        scrubber = PIIScrubFilter(enabled=True)
        for key_name, test_value in self.TEST_KEYS.items():
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=f"Connecting with {key_name}={test_value}",
                args=None, exc_info=None,
            )
            scrubber.filter(record)
            assert test_value not in record.msg, \
                f"{key_name} value leaked through PII scrubber: {record.msg}"
```

### Step 4: Encryption integration tests

```python
class TestEncryptionIntegration:
    """Verify encryption works for consent-format JSON."""

    def test_encrypt_decrypt_consent_json(self, monkeypatch, tmp_path):
        """EncryptionManager roundtrips consent-format JSON."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key-for-p0-smoke")
        from shared.utils.encryption import EncryptionManager
        enc = EncryptionManager(enabled=True)

        consent = {
            "opt_in": True,
            "save_raw_media": False,
            "reason": "User agreed",
            "timestamp": "2026-02-25T00:00:00Z",
        }
        path = tmp_path / "consent.json"
        enc.save_json_encrypted(path, consent)

        # File should not contain plaintext
        raw = path.read_bytes()
        assert b"opt_in" not in raw, "Consent data not encrypted"

        # Decrypted should match original
        loaded = enc.load_json_decrypted(path)
        assert loaded == consent

    def test_tampered_file_detected(self, monkeypatch, tmp_path):
        """Tampered encrypted files raise on decrypt."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key-for-p0-smoke")
        from shared.utils.encryption import EncryptionManager
        enc = EncryptionManager(enabled=True)

        path = tmp_path / "tampered.json"
        enc.save_json_encrypted(path, {"test": True})

        # Tamper with the file
        data = path.read_bytes()
        path.write_bytes(data[:-5] + b"XXXXX")

        with pytest.raises(Exception):
            enc.load_json_decrypted(path)
```

### Step 5: Cross-component integration

```python
class TestCrossComponentIntegration:
    """Verify components don't conflict with each other."""

    def test_all_security_modules_importable(self):
        """All P0 security modules import without error."""
        from shared.config.secret_provider import SecretProvider, create_secret_provider
        from shared.utils.encryption import EncryptionManager, get_encryption_manager
        from shared.logging.logging_config import PIIScrubFilter, configure_logging
        # No ImportError = pass

    def test_secret_provider_and_encryption_coexist(self, monkeypatch):
        """SecretProvider and EncryptionManager can both be active."""
        monkeypatch.setenv("MEMORY_ENCRYPTION_KEY", "test-key")
        monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram")
        from shared.config.secret_provider import create_secret_provider
        from shared.utils.encryption import EncryptionManager
        provider = create_secret_provider()
        enc = EncryptionManager(enabled=True)
        assert provider.get_secret("DEEPGRAM_API_KEY") == "test-deepgram"
        assert enc.active is True
```

## Files to Create

| File | Purpose |
|------|---------|
| `tests/integration/test_p0_security_smoke.py` | P0 security integration tests |

## Tests (Summary)

| Class | Test Count |
|-------|-----------|
| TestSecretProviderIntegration | 3 |
| TestPIIScrubberIntegration | 1 (parametrized over 7 keys) |
| TestEncryptionIntegration | 2 |
| TestCrossComponentIntegration | 2 |
| **Total** | **8+** |

## Acceptance Criteria

- [ ] test_p0_security_smoke.py created in tests/integration/
- [ ] All SecretProvider tests pass
- [ ] All PII scrubber tests pass (7 key formats verified)
- [ ] Encryption roundtrip test passes
- [ ] Tamper detection test passes
- [ ] Cross-component import test passes
- [ ] `pytest tests/integration/test_p0_security_smoke.py -v` passes
- [ ] ruff check clean

## Upstream Dependencies

T-001, T-003, T-004, T-008 (all components must be implemented)

## Downstream Unblocks

T-012 (baseline metrics can reference test pass rate including these tests)

## Estimated Scope

- New: ~200 LOC test file
- Risk: Low (test-only, no production code changes)
