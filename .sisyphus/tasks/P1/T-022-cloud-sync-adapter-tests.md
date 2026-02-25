# T-022: cloud-sync-adapter-tests

> Phase: P1 | Cluster: CL-MEM | Risk: Low | State: not_started

## Objective

Write comprehensive unit tests for `CloudSyncAdapter` and its backends in
`core/memory/cloud_sync.py`. The adapter (390 lines) has three backend implementations
(`StubCloudBackend`, `MilvusCloudBackend`, `WeaviateCloudBackend`) and orchestrates
periodic synchronization of local FAISS vectors to a cloud vector store. This task
writes 8 tests covering the stub backend operations, adapter lifecycle, periodic flush
behavior, and health reporting. No code changes to `cloud_sync.py` itself.

Testing the stub backend validates the in-memory cosine similarity search, upsert/delete
operations, and the adapter's enable/disable logic without requiring external cloud
services (Milvus or Weaviate).

## Current State (Codebase Audit 2026-02-25)

- `cloud_sync.py` is at `core/memory/cloud_sync.py` (390 lines).
- `CloudSyncConfig` dataclass (line 28): `enabled`, `backend_type`, `sync_interval_s`,
  `batch_size`, `collection_name`, `connection_url`.
- `SyncRecord` dataclass (line 40): `id`, `vector`, `metadata`, `timestamp`.
- `CloudVectorBackend` ABC (line 52): `connect()`, `upsert()`, `search()`, `delete()`,
  `health()`, `disconnect()`.
- `StubCloudBackend` (lines 75-145): in-memory dict storage, cosine similarity search
  via numpy dot product, always returns `{"status": "stub", "connected": True}` for health.
- `MilvusCloudBackend` (lines 150-230): pymilvus-based, creates collection with schema,
  upserts via `collection.upsert()`, searches via `collection.search()`.
- `WeaviateCloudBackend` (lines 235-310): weaviate-client-based, creates class schema,
  batch upserts, near-vector queries.
- `CloudSyncAdapter` (lines 315-390): `enqueue()` adds records to internal queue,
  `flush()` upserts batch to backend, `start_periodic()` spawns asyncio task that
  flushes every `sync_interval_s`, `stop()` cancels periodic task, `health()` reports
  queue size and backend health.
- No tests exist for any cloud sync component.
- `StubCloudBackend` is the default when `backend_type="stub"` or unrecognized.

## Implementation Plan

### Step 1: Create test file with StubCloudBackend fixtures

Set up a pytest fixture that creates a `StubCloudBackend` and a `CloudSyncAdapter`
with stub configuration (enabled=True, backend_type="stub", sync_interval_s=1).

```python
import pytest
import numpy as np
from core.memory.cloud_sync import (
    CloudSyncConfig, CloudSyncAdapter, StubCloudBackend, SyncRecord
)

@pytest.fixture
def stub_backend():
    backend = StubCloudBackend()
    backend.connect()
    yield backend
    backend.disconnect()

@pytest.fixture
def sync_adapter(stub_backend):
    config = CloudSyncConfig(enabled=True, backend_type="stub", sync_interval_s=60)
    adapter = CloudSyncAdapter(config=config, backend=stub_backend)
    return adapter
```

### Step 2: Write 4 StubCloudBackend operation tests

Test connect/upsert/search/delete lifecycle of the stub backend directly.

### Step 3: Write 2 CloudSyncAdapter lifecycle tests

Test enqueue + flush cycle and enable/disable behavior.

### Step 4: Write periodic flush test

Use a short sync interval (0.1s) and verify records are flushed after waiting.

### Step 5: Write health check test

Verify health() returns expected fields (queue_size, backend status).

## Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_cloud_sync.py` | 8 unit tests for CloudSyncAdapter and StubCloudBackend |

## Files to Modify

| File | Change |
|------|--------|
| `core/memory/AGENTS.md` | Document cloud sync test coverage |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_cloud_sync.py` | `test_stub_connect_and_health` - connect stub, verify health returns connected=True |
| | `test_stub_upsert_stores_records` - upsert 3 records, verify internal storage count |
| | `test_stub_search_cosine_similarity` - upsert known vectors, search with query vector, verify top result matches closest |
| | `test_stub_delete_removes_record` - upsert then delete by ID, verify record absent |
| | `test_adapter_enqueue_and_flush` - enqueue 5 records, flush, verify backend received all 5 |
| | `test_adapter_disabled_skips_flush` - create adapter with enabled=False, enqueue, flush, verify backend is empty |
| | `test_adapter_periodic_flush` - start periodic with 0.1s interval, enqueue records, await 0.3s, verify flushed |
| | `test_adapter_health_reports_queue_size` - enqueue 3 records without flushing, verify health reports queue_size=3 |

## Acceptance Criteria

- [ ] All 8 tests pass: `pytest tests/unit/test_cloud_sync.py -v`
- [ ] `StubCloudBackend` cosine similarity search returns correct nearest neighbor
- [ ] Adapter enable/disable controls whether flush actually sends to backend
- [ ] Periodic flush test confirms records reach backend within 2x the sync interval
- [ ] Health check returns `queue_size` and backend status dict
- [ ] No modifications to `core/memory/cloud_sync.py`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean
- [ ] `core/memory/AGENTS.md` updated

## Upstream Dependencies

T-018 (faiss-indexer-persistence) — CloudSyncAdapter depends on working indexer save/load.

## Downstream Unblocks

None (leaf task in the Memory cluster).

## Estimated Scope

- New code: ~0 LOC (test-only task)
- Modified code: ~0 lines
- Tests: ~150 LOC
- Risk: Low. Pure test addition, no production code changes.
