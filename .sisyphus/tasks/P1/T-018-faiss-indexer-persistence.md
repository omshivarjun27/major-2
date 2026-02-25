# T-018: faiss-indexer-persistence

> Phase: P1 | Cluster: CL-MEM | Risk: Medium | State: not_started

## Schema

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: See below
- **Upstream Deps**: []
- **Downstream Impact**: [T-019, T-022]
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [core/memory/AGENTS.md]
- **Versioning Impact**: patch
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: yes
- **Execution Environment**: Local GPU
- **Current State**: not_started
- **Estimated LOC**: ~180 new, ~60 modified
- **Test Count Target**: 8

## Objective

Harden the `FAISSIndexer.save()` and `_load()` methods in `core/memory/indexer.py` to
survive crashes, power loss, and silent corruption. The current persistence logic writes
the FAISS binary and metadata JSON directly to their final paths. If the process dies
mid-write, the next startup loads a truncated file and silently resets to an empty index,
losing all stored memories.

This task adds three protective layers: atomic writes via temp-file-then-rename, SHA-256
checksum validation on load, and automatic backup rotation keeping the last 3 snapshots.
Together these changes make the persistence path safe for production use without changing
the public API surface.

## Current State (Codebase Audit 2026-02-25)

- `core/memory/indexer.py` is 622 lines. `FAISSIndexer` is the primary class.
- `IndexMetadata` dataclass (line 48): fields `id`, `timestamp`, `expiry`, `summary`, `session_id`, `user_label`, `scene_graph_ref`, `vector_idx`.
- `save()` starts at line 387. It writes two files:
  - `index.faiss` via `faiss.write_index()` (or encrypted bytes via `enc.save_encrypted()`)
  - `metadata.json` via `json.dump()` (or `enc.save_json_encrypted()`)
- Neither write is atomic. A crash between writing `index.faiss` and `metadata.json` leaves an inconsistent state.
- `_load()` starts at line 447. On any exception it logs an error and resets to empty state (line 501-506), losing all data silently.
- No checksum validation exists. A bit-flip in the FAISS binary or truncated JSON will either crash or silently produce wrong results.
- No backup rotation. Once overwritten, the previous snapshot is gone.
- `MockFAISSIndexer` (line 540) has no-op `save()`, unaffected by this task.
- Thread safety via `threading.RLock` (line 111) already wraps `save()`.
- Encryption support uses `shared.utils.encryption.get_encryption_manager` (imported at line 25-27).
- `shutil` is already imported (line 11) for `clear()`.
- The `_index_path` is a `Path` object (line 90), created with `mkdir(parents=True, exist_ok=True)` in `save()`.

## Implementation Plan

### Step 1: Add checksum utilities

Add two private methods to `FAISSIndexer`:

```python
def _compute_checksum(self, file_path: Path) -> str:
    """SHA-256 hex digest of a file."""
    import hashlib
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _write_checksum(self, file_path: Path, checksum: str) -> None:
    """Write checksum to a .sha256 sidecar file."""
    sidecar = file_path.with_suffix(file_path.suffix + ".sha256")
    sidecar.write_text(checksum)

def _verify_checksum(self, file_path: Path) -> bool:
    """Verify file against its .sha256 sidecar. Returns True if valid or no sidecar exists."""
    sidecar = file_path.with_suffix(file_path.suffix + ".sha256")
    if not sidecar.exists():
        return True  # Legacy files without checksums pass
    expected = sidecar.read_text().strip()
    actual = self._compute_checksum(file_path)
    return actual == expected
```

### Step 2: Implement atomic save

Rewrite `save()` to use a temp directory strategy:

1. Create a temporary directory inside `_index_path` named `.tmp_save_{uuid}`.
2. Write `index.faiss` and `metadata.json` into the temp directory.
3. Compute and write `.sha256` sidecar files for both.
4. Rename the current live files to a backup directory (Step 3).
5. Rename temp files to their final names using `os.replace()` (atomic on POSIX, best-effort on Windows).
6. Clean up the temp directory.

If any step fails after the backup but before the rename, the backup remains intact for recovery.

### Step 3: Add backup rotation

Before each save overwrites the current files, rotate existing snapshots:

1. Name backups as `backup_001/`, `backup_002/`, `backup_003/` inside `_index_path`.
2. Shift existing backups: `backup_003` is deleted, `backup_002` becomes `backup_003`, `backup_001` becomes `backup_002`.
3. Copy current `index.faiss` + `metadata.json` + sidecar files into `backup_001/`.
4. Expose a configurable `max_backups` parameter (default 3) on the constructor.

### Step 4: Add corruption recovery to _load()

Enhance `_load()` with checksum verification and backup fallback:

1. Verify checksums for `index.faiss` and `metadata.json`.
2. If verification fails, log a warning and attempt to load from `backup_001/`.
3. If `backup_001/` also fails, try `backup_002/`, then `backup_003/`.
4. If all backups fail, log an error and start with an empty index (current behavior).
5. Track recovery events in a `_recovery_log` list for health reporting.

### Step 5: Add save_metadata to JSON payload

Include checksum and backup info in the metadata JSON:

```python
payload = {
    "metadata": meta_dict,
    "id_to_idx": self._id_to_idx,
    "next_idx": self._next_idx,
    "deleted_indices": self._deleted_indices,
    "dimension": self._dimension,
    "saved_at": datetime.utcnow().isoformat() + "Z",
    "index_checksum": index_checksum,
    "backup_count": len(existing_backups),
}
```

### Step 6: Update MockFAISSIndexer

No changes needed. `MockFAISSIndexer.save()` is a no-op and should remain so.

## Files to Create

| File | Purpose |
|------|---------|
| (none) | All changes are modifications to existing files |

## Files to Modify

| File | Change |
|------|--------|
| `core/memory/indexer.py` | Add `_compute_checksum()`, `_write_checksum()`, `_verify_checksum()`, `_rotate_backups()` methods. Rewrite `save()` for atomic writes with checksums. Rewrite `_load()` with checksum verification and backup fallback. Add `max_backups` constructor parameter. |
| `core/memory/AGENTS.md` | Document the new persistence guarantees: atomic writes, checksum validation, backup rotation. |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_indexer_persistence.py` | `test_save_creates_checksum_sidecars` |
| | `test_load_verifies_checksums` |
| | `test_corrupted_index_falls_back_to_backup` |
| | `test_corrupted_metadata_falls_back_to_backup` |
| | `test_backup_rotation_keeps_max_three` |
| | `test_atomic_save_survives_interrupted_write` |
| | `test_save_load_round_trip_preserves_data` |
| `tests/integration/test_indexer_recovery.py` | `test_recovery_from_all_backups_corrupted` |

## Acceptance Criteria

- [ ] `save()` writes to a temp location first, then atomically renames to final path
- [ ] SHA-256 checksum sidecar files (`.sha256`) are written alongside `index.faiss` and `metadata.json`
- [ ] `_load()` verifies checksums before accepting loaded data
- [ ] When checksum verification fails, `_load()` attempts recovery from backup directories
- [ ] Backup rotation retains the 3 most recent snapshots
- [ ] Old backups beyond `max_backups` are deleted during rotation
- [ ] `MockFAISSIndexer` remains unaffected (no-op save)
- [ ] Encryption path (when `enc.active`) also gets atomic writes and checksums
- [ ] All existing indexer tests continue to pass
- [ ] 8 new test functions covering persistence, corruption, and recovery
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

None. This is an entry-point task for the CL-MEM cluster.

## Downstream Unblocks

T-019 (rag-retriever-mvp): depends on reliable index persistence for retriever testing.
T-022 (cloud-sync-adapter-tests): depends on stable indexer save/load for sync integration.

## Estimated Scope

- New code: ~120 LOC (checksum utils, atomic save, backup rotation, recovery logic)
- Modified code: ~60 lines in existing `save()` and `_load()` methods
- Tests: ~130 LOC
- Risk: Medium (modifying persistence path, but backward compatible with existing data)
