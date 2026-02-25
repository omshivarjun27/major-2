# T-021: ingest-pipeline-hardening

> Phase: P1 | Cluster: CL-MEM | Risk: Medium | State: not_started

## Schema

- **Phase**: P1
- **Cluster**: CL-MEM
- **Objective**: See below
- **Upstream Deps**: [T-018, T-020, T-017]
- **Downstream Impact**: []
- **Risk Tier**: Medium
- **Test Layers**: [Unit, Integration]
- **Doc Mutation Map**: [core/memory/AGENTS.md]
- **Versioning Impact**: minor
- **Governance Level**: standard
- **Regression Sensitivity**: medium
- **Parallelization Eligible**: no
- **Execution Environment**: Local GPU
- **Current State**: not_started
- **Estimated LOC**: ~200 new, ~40 modified
- **Test Count Target**: 8

## Objective

Harden `MemoryIngester` in `core/memory/ingest.py` with four missing capabilities: input
validation, hash-based deduplication, batch ingestion, and partial-success error recovery.

The current ingester accepts anything and silently stores garbage. An empty transcript
produces a "Memory recorded" stub. An oversized base64 image string consumes memory
without bounds. Identical memories pile up because nothing checks for duplicates. And
there's no way to ingest multiple items in a single call, forcing callers into serial
loops that block the event loop.

This task adds validation gates, a content-hash dedup cache, a `ingest_batch()` method
with partial-success reporting, and structured error responses that tell the caller
exactly what went wrong.

## Current State (Codebase Audit 2026-02-25)

- `core/memory/ingest.py` is 442 lines. `MemoryIngester` is the only public class.
- Constructor (line 53): accepts `indexer`, `text_embedder`, `fuser`, `config`, `llm_client`.
- `ingest()` (line 86): async method that processes a single `MemoryStoreRequest`:
  1. Generates UUID memory_id (line 103)
  2. Decodes image/audio from base64 (lines 112-113)
  3. Generates summary via `_generate_summary()` (line 117)
  4. Computes embedding via `_compute_embedding()` (line 126)
  5. Adds to FAISS index (line 135)
  6. Optionally stores raw media (line 149)
- No input validation at all. Empty `transcript`, `None` scene_graph, and empty `image_base64` all pass through.
- No deduplication. Calling `ingest()` twice with the same transcript and scene_graph creates two index entries.
- No batch ingestion method. Callers must loop over individual `ingest()` calls.
- Error handling (line 177): catches all exceptions and stores a zero-vector with "Error during ingestion" summary. This pollutes the index with useless entries.
- `_decode_image()` (line 283): decodes base64 to PIL Image. No size limit.
- `_decode_audio()` (line 293): decodes base64 to bytes. No size limit.
- `_generate_summary()` (line 206): template-based, truncates to 200 chars. Produces "Memory recorded" for empty inputs.
- `_compute_embedding()` (line 265): calls `self._fuser.fuse()` synchronously.
- `_store_scene_graph()` (line 301): stores hash reference. No validation.
- Consent tracking with `_consent_log` dict and `_consent_dir` persistence (lines 75-80, lines 353-429).
- `get_stats()` (line 431): returns `total_ingested`, `avg_ingest_time_ms`, `index_size`.
- `hashlib` is already imported (line 10).
- `MemoryStoreRequest` from `api_schema.py`: fields `transcript`, `image_base64`, `audio_base64`, `scene_graph`, `user_label`, `session_id`, `save_raw`.

## Implementation Plan

### Step 1: Add input validation

Create a `_validate_request()` method that runs before any processing:

```python
class IngestValidationError(Exception):
    """Raised when an ingest request fails validation."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _validate_request(self, request: MemoryStoreRequest) -> None:
    """Validate ingest request. Raises IngestValidationError on failure."""
    # Must have at least one content source
    has_text = bool(request.transcript and request.transcript.strip())
    has_image = bool(request.image_base64)
    has_audio = bool(request.audio_base64)
    has_scene = bool(request.scene_graph)

    if not (has_text or has_image or has_audio or has_scene):
        raise IngestValidationError("Request has no content: provide transcript, image, audio, or scene_graph")

    # Text length limit
    if request.transcript and len(request.transcript) > 50_000:
        raise IngestValidationError(f"Transcript too long: {len(request.transcript)} chars (max 50000)")

    # Image size limit (base64 string, ~4MB decoded = ~5.3MB base64)
    if request.image_base64 and len(request.image_base64) > 6_000_000:
        raise IngestValidationError(f"Image too large: {len(request.image_base64)} chars (max ~4MB decoded)")

    # Audio size limit (~10MB decoded = ~13.3MB base64)
    if request.audio_base64 and len(request.audio_base64) > 14_000_000:
        raise IngestValidationError(f"Audio too large: {len(request.audio_base64)} chars (max ~10MB decoded)")
```

### Step 2: Add hash-based deduplication

Compute a content hash from the request's meaningful fields and check against a
dedup cache before processing:

```python
def _compute_content_hash(self, request: MemoryStoreRequest) -> str:
    """SHA-256 hash of request content for dedup."""
    import hashlib
    h = hashlib.sha256()
    if request.transcript:
        h.update(request.transcript.strip().lower().encode("utf-8"))
    if request.scene_graph:
        sg = json.dumps(request.scene_graph, sort_keys=True)
        h.update(sg.encode("utf-8"))
    if request.image_base64:
        # Hash first 1000 chars of base64 (enough to distinguish images)
        h.update(request.image_base64[:1000].encode("utf-8"))
    return h.hexdigest()
```

Store seen hashes in a bounded dict (LRU-style, max 10000 entries) with the corresponding
memory_id. When a duplicate is detected, return early with the existing memory_id and a
`DEDUPLICATED` status instead of re-indexing.

### Step 3: Add batch ingestion

Create `ingest_batch()` that processes multiple requests with partial-success reporting:

```python
@dataclass
class BatchIngestResult:
    """Result from a batch ingestion."""
    total: int
    succeeded: int
    failed: int
    deduplicated: int
    results: List[MemoryStoreResponse]
    errors: List[Dict[str, str]]  # {"memory_id": ..., "error": ...}
    total_time_ms: float


async def ingest_batch(
    self,
    requests: List[MemoryStoreRequest],
    consent_given: bool = False,
    stop_on_error: bool = False,
) -> BatchIngestResult:
    """Ingest multiple memories with partial-success tracking.

    Args:
        requests: List of store requests
        consent_given: Whether user has given storage consent
        stop_on_error: If True, abort batch on first failure

    Returns:
        BatchIngestResult with per-item outcomes
    """
    start = time.time()
    results = []
    errors = []
    dedup_count = 0

    for req in requests:
        try:
            resp = await self.ingest(req, consent_given=consent_given)
            if resp.embedding_status == EmbeddingStatus.DEDUPLICATED:
                dedup_count += 1
            results.append(resp)
        except Exception as e:
            error_entry = {"index": len(results) + len(errors), "error": str(e)}
            errors.append(error_entry)
            if stop_on_error:
                break

    return BatchIngestResult(
        total=len(requests),
        succeeded=len(results),
        failed=len(errors),
        deduplicated=dedup_count,
        results=results,
        errors=errors,
        total_time_ms=(time.time() - start) * 1000,
    )
```

### Step 4: Improve error recovery

Replace the current catch-all that stores a zero-vector with cleaner error handling:

1. On validation failure: return immediately with `REJECTED` status. Don't store anything.
2. On embedding failure: log the error, return with `FAILED` status. Don't pollute the index with zero-vectors.
3. On indexing failure: log the error, return with `FAILED` status.
4. Only store to the index on success.

Remove the current fallback code at lines 181-193 that stores zero-vector entries on failure.

### Step 5: Add DEDUPLICATED and REJECTED to EmbeddingStatus

Update `api_schema.py` to include the new status values:

```python
class EmbeddingStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"
    DEDUPLICATED = "deduplicated"
    REJECTED = "rejected"
```

### Step 6: Wire validation and dedup into ingest()

Update the `ingest()` method flow:

```python
async def ingest(self, request, consent_given=False):
    # 1. Validate
    try:
        self._validate_request(request)
    except IngestValidationError as e:
        return MemoryStoreResponse(
            id="", timestamp=..., expiry=...,
            summary=f"Rejected: {e.reason}",
            embedding_status=EmbeddingStatus.REJECTED,
        )

    # 2. Dedup check
    content_hash = self._compute_content_hash(request)
    if content_hash in self._dedup_cache:
        existing_id = self._dedup_cache[content_hash]
        return MemoryStoreResponse(
            id=existing_id, ...,
            embedding_status=EmbeddingStatus.DEDUPLICATED,
        )

    # 3. Process (existing logic)
    # 4. On success, store hash in dedup cache
    self._dedup_cache[content_hash] = memory_id
```

## Files to Create

| File | Purpose |
|------|---------|
| (none) | All changes are modifications to existing files |

## Files to Modify

| File | Change |
|------|--------|
| `core/memory/ingest.py` | Add `IngestValidationError`, `_validate_request()`, `_compute_content_hash()`, dedup cache, `ingest_batch()`, `BatchIngestResult`. Refactor `ingest()` error handling. Remove zero-vector fallback. |
| `core/memory/api_schema.py` | Add `DEDUPLICATED` and `REJECTED` values to `EmbeddingStatus` enum. |
| `core/memory/AGENTS.md` | Document validation rules, dedup behavior, batch ingestion API. |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_ingest_hardening.py` | `test_reject_empty_request` - no transcript, image, audio, or scene_graph |
| | `test_reject_oversized_transcript` - transcript > 50000 chars |
| | `test_reject_oversized_image` - image_base64 > 6MB |
| | `test_dedup_returns_existing_id` - second identical request returns DEDUPLICATED |
| | `test_dedup_different_content_creates_new` - similar but different content creates new entry |
| | `test_batch_ingest_partial_success` - batch with mix of valid and invalid items |
| | `test_batch_stop_on_error` - batch with stop_on_error=True aborts after first failure |
| `tests/integration/test_ingest_integration.py` | `test_ingest_roundtrip_with_validation` - validate, ingest, search, verify result |

## Acceptance Criteria

- [ ] Empty requests (no transcript, image, audio, or scene_graph) are rejected with `REJECTED` status
- [ ] Oversized transcripts (>50000 chars) are rejected
- [ ] Oversized base64 images (>6MB string) are rejected
- [ ] Duplicate content returns the existing memory_id with `DEDUPLICATED` status
- [ ] Dedup cache is bounded (max 10000 entries)
- [ ] `ingest_batch()` processes multiple requests and reports per-item outcomes
- [ ] `ingest_batch()` with `stop_on_error=True` stops after first failure
- [ ] Failed ingestions no longer store zero-vector entries in the index
- [ ] `EmbeddingStatus` enum has `DEDUPLICATED` and `REJECTED` values
- [ ] `BatchIngestResult` dataclass reports `total`, `succeeded`, `failed`, `deduplicated`
- [ ] All existing ingest tests continue to pass
- [ ] 8 new test functions covering validation, dedup, batch, and error recovery
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean

## Upstream Dependencies

T-018 (faiss-indexer-persistence): reliable index persistence needed for ingest testing.
T-020 (embedding-async-wrapper): async embedding methods used by updated `_compute_embedding()`.
T-017 (navigation-output-formatter): provides ObstacleRecord and NavigationOutput types
that may appear in scene_graph data ingested by the memory pipeline.

## Downstream Unblocks

No tasks directly depend on T-021. This is a terminal task in the CL-MEM cluster DAG.
The hardened ingester benefits the RAGReasoner and API endpoints immediately upon merge.

## Estimated Scope

- New code: ~200 LOC (validation, dedup, batch, BatchIngestResult, error refactoring)
- Modified code: ~40 lines in existing `ingest()` and `api_schema.py`
- Tests: ~150 LOC
- Risk: Medium (modifying ingest flow, adding new enum values, removing zero-vector fallback)
