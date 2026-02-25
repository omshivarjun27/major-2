# T-033: storage-adapter-mvp

> Phase: P1 | Cluster: CL-INF | Risk: Low | State: not_started

## Objective

Create a `StorageAdapter` ABC and `LocalFileStorage` implementation in
`infrastructure/storage/`. Currently the directory contains only `__init__.py` (empty)
and `AGENTS.md` — a pure stub. This task delivers a minimal but functional storage
abstraction that the rest of the system can use for persisting JSON data, binary blobs,
listing stored keys, deleting entries, and reporting health.

`LocalFileStorage` uses the local filesystem with a configurable base directory. Keys
map to file paths within the base directory. JSON data is stored as `.json` files,
binary data as `.bin` files. This replaces direct `open()`/`json.dump()` calls
scattered across the codebase with a centralized, testable storage layer.

## Current State (Codebase Audit 2026-02-25)

- `infrastructure/storage/` contains only:
  - `__init__.py` (empty)
  - `AGENTS.md` (stub documentation)
- No storage abstraction exists. Various modules use raw file I/O:
  - `core/memory/indexer.py` uses `faiss.write_index()` / `faiss.read_index()` + JSON.
  - `core/face/face_embeddings.py` uses `save_json_encrypted()` from shared/utils.
  - `core/memory/ingest.py` uses `json.dump()` / `json.load()` for consent files.
- `shared/utils/encryption.py` provides `save_json_encrypted()` / `load_json_decrypted()`.
- The infrastructure layer can import from `shared/` only (not from core/ or application/).
- No health check pattern for storage exists.

## Implementation Plan

### Step 1: Define StorageAdapter ABC

```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class StorageAdapter(ABC):
    @abstractmethod
    async def save_json(self, key: str, data: Any) -> None: ...

    @abstractmethod
    async def load_json(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    async def save_binary(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    async def load_binary(self, key: str) -> Optional[bytes]: ...

    @abstractmethod
    async def delete(self, key: str) -> bool: ...

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def health(self) -> dict: ...
```

### Step 2: Implement LocalFileStorage

Map keys to filesystem paths: `{base_dir}/{key}.json` or `{base_dir}/{key}.bin`.
Use `asyncio.to_thread()` for all file I/O to avoid blocking the event loop.
Sanitize keys to prevent path traversal (reject `..`, absolute paths).

### Step 3: Add key validation and path sanitization

```python
def _validate_key(self, key: str) -> Path:
    if ".." in key or key.startswith("/") or key.startswith("\\"):
        raise ValueError(f"Invalid storage key: {key}")
    return self._base_dir / key
```

### Step 4: Add health check

Report base directory existence, disk space available, and total stored item count.

### Step 5: Create factory function

```python
def create_storage_adapter(storage_type: str = "local", **kwargs) -> StorageAdapter:
    if storage_type == "local":
        return LocalFileStorage(base_dir=kwargs.get("base_dir", "data/storage"))
    raise ValueError(f"Unknown storage type: {storage_type}")
```

### Step 6: Write 8 unit tests

Cover save/load JSON, save/load binary, delete, list keys, path traversal rejection,
and health check.

## Files to Create

| File | Purpose |
|------|---------|
| `infrastructure/storage/adapter.py` | StorageAdapter ABC + LocalFileStorage implementation |
| `tests/unit/test_storage_adapter.py` | 8 unit tests for StorageAdapter |

## Files to Modify

| File | Change |
|------|--------|
| `infrastructure/storage/__init__.py` | Export StorageAdapter, LocalFileStorage, create_storage_adapter |
| `infrastructure/storage/AGENTS.md` | Document storage abstraction, key format, health check |
| `infrastructure/AGENTS.md` | Reference new storage adapter module |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_storage_adapter.py` | `test_save_and_load_json` - save dict, load back, verify equality |
| | `test_save_and_load_binary` - save bytes, load back, verify equality |
| | `test_delete_removes_file` - save then delete, verify exists() returns False |
| | `test_list_keys_returns_stored` - save 3 items, list_keys, verify all 3 returned |
| | `test_list_keys_with_prefix` - save items with different prefixes, filter by prefix |
| | `test_load_missing_returns_none` - load non-existent key, verify None returned |
| | `test_path_traversal_rejected` - key with ".." raises ValueError |
| | `test_health_reports_base_dir` - verify health() returns base_dir and item_count |

## Acceptance Criteria

- [ ] `StorageAdapter` ABC defined with all 8 methods
- [ ] `LocalFileStorage` implements all methods using filesystem + asyncio.to_thread
- [ ] Key validation rejects path traversal attempts
- [ ] JSON round-trip preserves data exactly
- [ ] Binary round-trip preserves bytes exactly
- [ ] `list_keys()` supports optional prefix filtering
- [ ] `health()` returns dict with `base_dir`, `exists`, `item_count`
- [ ] `create_storage_adapter()` factory returns configured storage
- [ ] All 8 tests pass: `pytest tests/unit/test_storage_adapter.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean (infrastructure/ imports only from shared/)
- [ ] `infrastructure/storage/AGENTS.md` updated

## Upstream Dependencies

None (entry point task for the Infrastructure cluster).

## Downstream Unblocks

T-034 (monitoring-adapter-mvp) — monitoring may use storage for metric persistence.

## Estimated Scope

- New code: ~180 LOC (ABC ~40, LocalFileStorage ~100, factory ~20, key validation ~20)
- Modified code: ~5 lines in __init__.py
- Tests: ~120 LOC
- Risk: Low. Self-contained infrastructure module with no external dependencies.
