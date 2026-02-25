# T-006: encryption-utility-audit

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Audit and harden `shared/utils/encryption.py`. Remove the duplicate encryption file.
Verify integration with SecretProvider for key material retrieval.

## Current State (Codebase Audit 2026-02-25)

### Encryption Implementation
- `shared/utils/encryption.py` (182 lines) — CANONICAL, used by all imports
- `shared/encryption.py` (182 lines) — DUPLICATE, byte-identical, NEVER imported anywhere
- Algorithm: Fernet (AES-128-CBC + HMAC-SHA256)
- Key derivation: `hashlib.sha256(raw_key.encode()).digest()` — single-pass SHA-256
- Key source: `MEMORY_ENCRYPTION_KEY` env var (raw string → SHA-256 → base64 → Fernet)
- Graceful fallback: if no key set or cryptography not installed, passes through unencrypted

### Key Derivation Weakness
SHA-256 is NOT a key derivation function. It has no:
- Salt (same password always produces same key)
- Iteration count (no computational cost, vulnerable to brute force)
- Memory hardness

Should be replaced with PBKDF2 (stdlib `hashlib.pbkdf2_hmac`) or similar.

### Consumers
1. `core/memory/indexer.py` (line 25): `from shared.utils.encryption import get_encryption_manager`
2. `core/face/face_embeddings.py` (line 26): `from shared.utils.encryption import get_encryption_manager`
3. `tests/test_encryption.py`: `from shared.utils.encryption import EncryptionManager, reset_encryption_manager`
4. `tests/performance/test_graceful_degradation.py`
5. `tests/performance/test_model_download_retry.py`

### What's stored encrypted
- FAISS index files (core/memory/indexer.py)
- Face embedding .npy files (core/face/face_embeddings.py)
- Face identity metadata JSON (core/face/face_embeddings.py)

## Implementation Plan

### Step 1: Delete duplicate file

Delete `shared/encryption.py` (182 lines). Confirm zero imports:
```bash
grep -r "from shared.encryption import\|import shared.encryption" --include="*.py"
```
Expected: zero matches.

### Step 2: Upgrade key derivation to PBKDF2

Replace in `shared/utils/encryption.py`:

```python
# Before (weak):
derived = hashlib.sha256(raw_key.encode()).digest()

# After (hardened):
import os
salt = os.environ.get(f"{key_env_var}_SALT", "voice-vision-default-salt").encode()
derived = hashlib.pbkdf2_hmac(
    "sha256",
    raw_key.encode(),
    salt,
    iterations=100_000,
)
```

Notes:
- PBKDF2 is in Python stdlib (no new dependency)
- Salt from env var with fallback default (allows per-deployment uniqueness)
- 100k iterations is OWASP recommended minimum for SHA-256
- Fernet still uses AES-128-CBC internally (Fernet limitation, acceptable for at-rest)

### Step 3: Add migration path for existing encrypted files

Existing files were encrypted with SHA-256-derived key. After PBKDF2 upgrade,
old files won't decrypt. Add migration support:

```python
def _try_decrypt_with_fallback(self, token: bytes) -> bytes:
    """Try PBKDF2 key first, fall back to legacy SHA-256 key."""
    try:
        return self._fernet.decrypt(token)
    except InvalidToken:
        if self._legacy_fernet:
            logger.warning("Decrypting with legacy key derivation — re-encrypt recommended")
            return self._legacy_fernet.decrypt(token)
        raise
```

Keep legacy Fernet as fallback during transition period. Log warnings when used.

### Step 4: Add audit logging

```python
def encrypt(self, data: bytes) -> bytes:
    if not self.active:
        return data
    logger.debug("encrypt: %d bytes", len(data))
    return self._fernet.encrypt(data)

def decrypt(self, token: bytes) -> bytes:
    if not self.active:
        return token
    logger.debug("decrypt: %d bytes", len(token))
    # ... existing logic with fallback
```

### Step 5: Document cryptographic choices

Add docstring header explaining:
- Why Fernet (stdlib-friendly, authenticated encryption)
- Why PBKDF2 (stdlib, OWASP recommended, no new dependency)
- Why not AES-256-GCM (would require pycryptodome — unnecessary complexity for at-rest)
- Key rotation strategy (change env var, re-encrypt on next write)

### Step 6: Wire SecretProvider for key retrieval

After T-001 completes, encryption key should come from SecretProvider:

```python
from shared.config.secret_provider import create_secret_provider

# In EncryptionManager.__init__:
if not raw_key:
    provider = create_secret_provider()
    raw_key = provider.get_secret(key_env_var) or ""
```

This is a soft dependency — if SecretProvider isn't available yet, os.environ fallback works.

## Files to Delete

| File | Reason |
|------|--------|
| `shared/encryption.py` | Duplicate of shared/utils/encryption.py, zero imports |

## Files to Modify

| File | Change |
|------|--------|
| `shared/utils/encryption.py` | PBKDF2 KDF, legacy fallback, audit logging, docstring |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/test_encryption.py` | (extend existing 103 LOC) |
| | PBKDF2-derived key produces valid Fernet tokens |
| | Legacy SHA-256 files still decryptable (migration) |
| | Salt from env var used when present |
| | Default salt used when env var absent |
| | Audit log messages emitted on encrypt/decrypt |
| | No raw key material in log output |

## Acceptance Criteria

- [ ] `shared/encryption.py` deleted
- [ ] Zero imports of `shared.encryption` in codebase
- [ ] Key derivation uses PBKDF2 with >= 100k iterations
- [ ] Salt configurable via env var
- [ ] Legacy SHA-256 fallback for existing encrypted files
- [ ] Warning logged when legacy decryption used
- [ ] Audit logging on encrypt/decrypt (byte count only, no data)
- [ ] No key material logged at any level
- [ ] All existing encryption tests pass
- [ ] New tests for PBKDF2 and legacy migration
- [ ] ruff check clean, lint-imports clean

## Upstream Dependencies

T-001 (SecretProvider — soft dependency, os.environ fallback acceptable)

## Downstream Unblocks

T-007 (consent encryption uses hardened EncryptionManager)

## Estimated Scope

- Deleted: 182 LOC (duplicate)
- Modified: ~40 lines in encryption.py
- Tests: ~60 LOC new
- Risk: Medium (key derivation change requires migration path)
