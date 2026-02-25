# T-007: consent-state-encryption

> Phase: P0 | Cluster: CL-SEC | Risk: Critical | State: not_started

## Objective

Encrypt the consent storage and persist it to disk. Currently consent is in-memory only
and lost on process restart. Add at-rest encryption with integrity verification.

## Current State (Codebase Audit 2026-02-25)

### Consent Storage
- **Location**: `core/memory/ingest.py`, MemoryIngester class
- **Storage**: In-memory dict `self._consent_log: Dict[str, Dict]` (line 72)
- **NOT persisted to disk** — all consent lost on restart
- **NOT encrypted** — even if it were persisted

### record_consent() (lines 344-378)
```python
def record_consent(self, device_id, opt_in, save_raw_media, reason=None):
    key = device_id or "default"
    consent_entry = {
        "opt_in": opt_in,
        "save_raw_media": save_raw_media,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    self._consent_log[key] = consent_entry
    return {"memory_enabled": opt_in, "save_raw_media": save_raw_media and opt_in}
```

### get_consent() (lines 380-388)
```python
def get_consent(self, device_id=None):
    key = device_id or "default"
    entry = self._consent_log.get(key, {})
    return {
        "memory_enabled": entry.get("opt_in", True),
        "save_raw_media": entry.get("save_raw_media", False),
    }
```

### API Endpoints
- POST `/memory/consent` (api_endpoints.py lines 239-259): calls `ingester.record_consent()`
- GET `/memory/consent/{device_id}` (lines 262-269): calls `ingester.get_consent()`

### EncryptionManager (after T-006)
Already provides `save_json_encrypted()` and `load_json_decrypted()` — perfect for consent files.

### Data directory
- `data/` exists with `memory_backup/` and `memory_index/`
- NO `data/consent/` directory exists

## Implementation Plan

### Step 1: Create consent storage directory

In `MemoryIngester.__init__()`, ensure consent directory exists:
```python
self._consent_dir = Path(config.data_dir) / "consent"
self._consent_dir.mkdir(parents=True, exist_ok=True)
```

### Step 2: Persist consent on write

Modify `record_consent()` to save to disk:
```python
def record_consent(self, device_id, opt_in, save_raw_media, reason=None):
    key = device_id or "default"
    consent_entry = {
        "opt_in": opt_in,
        "save_raw_media": save_raw_media,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    self._consent_log[key] = consent_entry

    # Persist encrypted
    enc = get_encryption_manager()
    consent_path = self._consent_dir / f"{key}.json"
    enc.save_json_encrypted(consent_path, consent_entry)
    logger.info("Consent recorded for device=%s opt_in=%s", key, opt_in)

    return {"memory_enabled": opt_in, "save_raw_media": save_raw_media and opt_in}
```

### Step 3: Load consent on startup

In `MemoryIngester.__init__()`, load existing consent files:
```python
def _load_persisted_consent(self) -> None:
    """Load consent records from encrypted files on disk."""
    enc = get_encryption_manager()
    for consent_file in self._consent_dir.glob("*.json"):
        try:
            entry = enc.load_json_decrypted(consent_file)
            device_id = consent_file.stem
            self._consent_log[device_id] = entry
            logger.debug("Loaded consent for device=%s", device_id)
        except Exception as e:
            logger.error("Failed to load consent file %s: %s", consent_file, e)
            # Tampered or corrupted — reject this consent (fail-safe to no-consent)
```

### Step 4: Add integrity verification

Fernet already provides HMAC authentication (tamper detection). If a consent file
is modified outside the application, `load_json_decrypted()` will raise `InvalidToken`.
This is handled in Step 3's except block — tampered files are rejected.

Add explicit integrity check in `get_consent()`:
```python
def get_consent(self, device_id=None):
    key = device_id or "default"
    entry = self._consent_log.get(key)
    if entry is None:
        # Try loading from disk (might have been written by another process)
        self._try_load_consent(key)
        entry = self._consent_log.get(key, {})
    return {
        "memory_enabled": entry.get("opt_in", True),
        "save_raw_media": entry.get("save_raw_media", False),
    }
```

### Step 5: Handle encryption disabled gracefully

If `MEMORY_ENCRYPTION_KEY` is not set, EncryptionManager falls back to plain I/O.
Consent files will be stored as plaintext JSON. This is acceptable for local dev
but should be documented as a security gap for production.

## Files to Modify

| File | Change |
|------|--------|
| `core/memory/ingest.py` | Add consent persistence (write on record, load on init) |

## Files to Create

None (data/consent/ created at runtime).

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_memory_ingest.py` | (extend TestConsentTracking class) |
| | Consent persists to encrypted file on disk |
| | Consent loaded from disk on MemoryIngester init |
| | Tampered consent file rejected (fails to decrypt) |
| | Missing consent returns default (opt_in=True, save_raw=False) |
| | Multiple device IDs stored in separate files |
| | Consent survives MemoryIngester restart (create, destroy, recreate) |

## Acceptance Criteria

- [ ] record_consent() persists to data/consent/{device_id}.json
- [ ] Consent files encrypted at rest (when MEMORY_ENCRYPTION_KEY set)
- [ ] Consent loaded on MemoryIngester initialization
- [ ] Tampered consent files detected and rejected
- [ ] Existing API endpoints (/memory/consent) unchanged
- [ ] Default consent behavior preserved (opt_in=True when no record)
- [ ] All existing consent tests pass
- [ ] New persistence tests pass
- [ ] ruff check clean, lint-imports clean

## Upstream Dependencies

T-006 (hardened EncryptionManager with PBKDF2)

## Downstream Unblocks

T-011 (security smoke test verifies consent encryption)

## Estimated Scope

- Modified: ~50 lines in ingest.py
- Tests: ~80 LOC new
- Risk: Medium (persistence change affects consent behavior)
