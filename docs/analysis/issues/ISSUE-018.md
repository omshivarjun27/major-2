---
id: ISSUE-018
title: No Health Check for Local Embedding Service (OllamaEmbedder)
severity: low
source_artifact: architecture_risks.md
architecture_layer: core
---

## Description
`OllamaEmbedder` in `core/memory/embeddings.py` calls the Ollama embedding endpoint but has no startup health check or periodic liveness probe. If the Ollama embedding model (`qwen3-embedding:4b`) is not loaded or the Ollama service is down, embeddings silently fail or return error vectors.

## Root Cause
No `is_ready()` or health-check method was implemented on the embedder. The system assumes the embedding service is always available.

## Impact
Silent failure when the embedding model is not loaded. Memory ingestion produces zero/garbage vectors, leading to incorrect similarity search results. The user would not be informed that the memory system is degraded.

## Reproducibility
possible

## Remediation Plan
1. Add an `is_ready()` method to `OllamaEmbedder` that probes the Ollama embedding endpoint.
2. Call `is_ready()` during application startup and log a clear warning if unavailable.
3. Implement circuit-breaker on repeated embedding failures.
4. Surface degradation status through the `/health` API endpoint.

## Implementation Suggestion
```python
class OllamaEmbedder:
    def is_ready(self) -> bool:
        try:
            test_embedding = self.embed_text("health check")
            return test_embedding is not None and len(test_embedding) > 0
        except Exception:
            return False
```

## GPU Impact
The embedding model (`qwen3-embedding:4b`) uses ~2GB VRAM on the RTX 4060. Health check helps detect if the model was evicted from GPU memory.

## Cloud Impact
N/A — embedding runs locally via Ollama.

## Acceptance Criteria
- [ ] `is_ready()` method added to `OllamaEmbedder`
- [ ] Health check called on startup with clear log message
- [ ] `/health` endpoint reports embedding service status
- [ ] Circuit-breaker prevents repeated failed embedding attempts
