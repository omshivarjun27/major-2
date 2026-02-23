---
id: ISSUE-005
title: FAISS Uses Brute-Force IndexFlatL2 Without Approximate Search
severity: high
source_artifact: architecture_risks.md
architecture_layer: core
---

## Description
The FAISS vector index uses `IndexFlatL2` (exact brute-force search) with a `max_vectors=5000` limit. This performs O(n) linear scan for every query.

## Root Cause
`IndexFlatL2` was chosen for simplicity during initial implementation. No migration to approximate nearest-neighbor (ANN) index was performed as the dataset grew.

## Impact
At scale (>10K memories), search latency will exceed the 250ms latency budget. Even at 5K vectors, brute-force L2 scan is suboptimal for a real-time assistive application where memory queries compete with perception pipeline for resources.

## Reproducibility
always

## Remediation Plan
1. Replace `IndexFlatL2` with `IndexIVFFlat` or `IndexHNSWFlat` for sub-linear search.
2. Add periodic index rebuild/training step when vector count exceeds threshold.
3. Benchmark both options with 5K and 10K vectors to validate latency improvement.
4. Ensure backward compatibility: migrate existing index files on upgrade.

## Implementation Suggestion
```python
import faiss

# Replace in FAISSIndexer.__init__():
# Before: self.index = faiss.IndexFlatL2(dim)
# After:
quantizer = faiss.IndexFlatL2(dim)
self.index = faiss.IndexIVFFlat(quantizer, dim, nlist=100)
# Train index when enough vectors accumulated:
if self.index.ntotal >= 100:
    self.index.train(vectors)
```

## GPU Impact
FAISS can optionally use GPU (`faiss-gpu`) for faster search, but current `faiss-cpu` is adequate at 5K vectors. GPU FAISS would consume ~100MB additional VRAM.

## Cloud Impact
N/A — FAISS runs locally.

## Acceptance Criteria
- [ ] FAISS index type changed to ANN (IVFFlat or HNSWFlat)
- [ ] Search latency under 50ms for 5K vectors (down from ~20ms brute-force)
- [ ] Existing index migration path tested and documented
- [ ] Benchmark results recorded for 1K, 5K, 10K vector counts
