---
id: ISSUE-017
title: TemporalFilter Thread Safety — Tracks Dict Mutated Without Locks
severity: low
source_artifact: architecture_risks.md
architecture_layer: core
---

## Description
`TemporalFilter._tracks` dictionary in `core/vqa/spatial_fuser.py` is mutated (add, update, delete entries) without any synchronization primitives. This is safe only if called from a single asyncio event loop thread.

## Root Cause
The implementation assumes single-threaded access via the asyncio event loop. No explicit lock or documentation of this constraint exists.

## Impact
If `fuse()` is ever called from multiple threads (e.g., via `WorkerPool` or `PerceptionWorkerPool` with `ThreadPoolExecutor`), race conditions on the `_tracks` dictionary could cause corrupted state, missed detections, or crashes.

## Reproducibility
rare

## Remediation Plan
1. Option A: Add `threading.Lock` around `_tracks` mutations for thread-safe operation.
2. Option B: Document the single-thread constraint explicitly in the class docstring and add a runtime assertion.
3. Add a unit test that verifies concurrent access behavior.

## Implementation Suggestion
```python
import threading

class TemporalFilter:
    def __init__(self, config: FusionConfig):
        self.config = config
        self._tracks: Dict[str, TrackedObject] = {}
        self._lock = threading.Lock()

    def update(self, detections, depth_map):
        with self._lock:
            # existing mutation logic
            ...
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] `threading.Lock` added to `TemporalFilter` OR single-thread constraint documented
- [ ] No data races detectable under concurrent access test
- [ ] Docstring updated with thread-safety guarantees
