# T-029: face-consent-integration

> Phase: P1 | Cluster: CL-FACE | Risk: Medium | State: not_started

## Objective

Integrate `FaceEmbeddingStore` consent flow with the P0 encryption manager and add
three privacy features: consent audit trail logging, configurable data retention TTL,
and consent revocation cascade. `FaceEmbeddingStore` (307 lines in
`core/face/face_embeddings.py`) already uses `get_encryption_manager()` for disk I/O
and has basic consent gating (register checks `has_consent()`). This task adds:

1. **Audit trail**: log every consent grant, revocation, and data access to a structured
   JSON audit file at `data/consent/face_audit.jsonl`.
2. **Retention TTL**: auto-expire face embeddings older than a configurable TTL
   (default 90 days). Expired embeddings are deleted on next `identify()` or
   periodic cleanup call.
3. **Revocation cascade**: when consent is revoked for a person, delete all their
   embeddings from memory, remove disk files, and log the cascade event.

## Current State (Codebase Audit 2026-02-25)

- `core/face/face_embeddings.py` (307 lines):
  - `EmbeddingConfig` dataclass (line 18): `storage_dir`, `max_embeddings_per_person`,
    `similarity_threshold`, `encryption_enabled`.
  - `FaceIdentity` dataclass (line 30): `person_id`, `name`, `embeddings` (list of
    numpy arrays), `created_at`, `last_seen`, `consent_granted` (bool).
  - `FaceEmbeddingStore` class (line 55):
    - `register()` (line 80): checks `has_consent()`, adds embedding to identity.
    - `identify()` (line 110): compares query embedding against all stored, returns
      best match above similarity threshold.
    - `delete()` (line 140): removes identity by person_id.
    - `forget_all()` (line 155): clears all identities.
    - `save()` (line 170): persists to disk using `save_json_encrypted()` from
      `shared/utils/encryption`.
    - `load()` (line 195): loads from disk using `load_json_decrypted()`.
    - `has_consent()` (line 220): checks `FaceIdentity.consent_granted` flag.
    - `grant_consent()` / `revoke_consent()` (lines 230-250): toggle consent flag on identity.
  - Current `revoke_consent()` only sets `consent_granted = False` but does NOT delete
    embeddings or disk data.
- P0 `shared/utils/encryption.py` provides `get_encryption_manager()`, `save_json_encrypted()`,
  `load_json_decrypted()`.
- P0 `core/memory/ingest.py` has consent persistence to `data/consent/{device_id}.json` —
  can reuse the same directory pattern.
- No audit logging for consent events exists anywhere.
- No TTL or auto-expiry for face data.
- `shared/logging/logging_config.py` has `PIIScrubFilter` — audit trail should NOT go
  through PII scrubbing since it needs to record person_id for compliance.

## Implementation Plan

### Step 1: Add audit trail writer

Create a helper class `ConsentAuditLog` that appends structured JSON lines to
`data/consent/face_audit.jsonl`. Each entry: `timestamp`, `event_type`, `person_id`,
`details`. Use file locking for thread safety.

```python
@dataclass
class AuditEntry:
    timestamp: str
    event_type: str  # "consent_granted" | "consent_revoked" | "data_accessed" | "data_deleted" | "data_expired"
    person_id: str
    details: dict
```

### Step 2: Add TTL configuration and expiry check

Add `retention_ttl_days` to `EmbeddingConfig` (default 90). Add a `_check_expiry()`
method to `FaceEmbeddingStore` that iterates identities, compares `created_at` to
current time, and deletes expired ones. Call `_check_expiry()` at the start of
`identify()` and add a public `cleanup_expired()` method.

### Step 3: Implement revocation cascade

Enhance `revoke_consent()` to: (1) delete all embeddings for the person from memory,
(2) remove the person's disk files, (3) log the cascade to audit trail, (4) save the
updated store to disk.

### Step 4: Wire audit logging into existing methods

Add audit trail entries to `register()`, `identify()`, `grant_consent()`,
`revoke_consent()`, and `delete()`.

### Step 5: Write 7 unit tests

Cover audit trail writing, TTL expiry, revocation cascade, and integration with
encryption manager.

## Files to Create

| File | Purpose |
|------|---------|
| `core/face/consent_audit.py` | ConsentAuditLog class for structured audit trail |
| `tests/unit/test_face_consent.py` | 7 unit tests for consent integration |

## Files to Modify

| File | Change |
|------|--------|
| `core/face/face_embeddings.py` | Add TTL config, _check_expiry, enhanced revoke_consent, audit log wiring |
| `core/face/__init__.py` | Export ConsentAuditLog |
| `core/face/AGENTS.md` | Document consent audit trail, TTL, revocation cascade |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_face_consent.py` | `test_audit_log_writes_entry` - grant consent, verify audit file contains entry |
| | `test_revocation_deletes_embeddings` - register face, revoke consent, verify embeddings empty |
| | `test_revocation_removes_disk_files` - register + save, revoke, verify disk file removed |
| | `test_ttl_expiry_removes_old_identities` - create identity with old timestamp, call cleanup, verify removed |
| | `test_ttl_preserves_recent_identities` - create recent identity, call cleanup, verify preserved |
| | `test_identify_triggers_expiry_check` - expired identity not returned by identify() |
| | `test_audit_trail_records_cascade` - revoke consent, verify audit trail has both revoke and delete events |

## Acceptance Criteria

- [ ] Consent audit trail written to `data/consent/face_audit.jsonl` as JSONL
- [ ] Each audit entry has timestamp, event_type, person_id, details
- [ ] TTL expiry deletes identities older than `retention_ttl_days`
- [ ] `cleanup_expired()` is callable for periodic maintenance
- [ ] `identify()` automatically checks and removes expired identities
- [ ] `revoke_consent()` cascade: deletes embeddings + disk files + logs events
- [ ] Audit trail is NOT filtered by PIIScrubFilter (separate file, not log stream)
- [ ] All 7 tests pass: `pytest tests/unit/test_face_consent.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean (core/face imports only from shared/)
- [ ] `core/face/AGENTS.md` updated

## Upstream Dependencies

T-028 (face-tracker-tests) — verified tracker behavior.
T-001 (secret-provider) — encryption manager from P0.
T-027 (braille-classifier-expansion) — parallel completion required per DAG.

## Downstream Unblocks

None (leaf task in this phase).

## Estimated Scope

- New code: ~120 LOC (ConsentAuditLog ~50, expiry logic ~40, cascade ~30)
- Modified code: ~40 lines in face_embeddings.py
- Tests: ~120 LOC
- Risk: Medium. Touches consent and deletion logic. Requires careful test coverage
  for cascade correctness.
