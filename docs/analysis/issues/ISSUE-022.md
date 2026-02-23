---
id: ISSUE-022
title: OllamaEmbedder.embed_text() Is Synchronous — Blocks Async Event Loop
severity: high
source_artifact: component_inventory.json
architecture_layer: core
---

## Description
`OllamaEmbedder.embed_text()` in `core/memory/embeddings.py` is a synchronous (blocking) method that makes HTTP calls to the Ollama embedding endpoint. When called from async context (e.g., within `MemoryIngester.ingest()` or `MemoryRetriever.search()`), it blocks the asyncio event loop, stalling all concurrent tasks including real-time perception and voice processing.

## Root Cause
The embedder was implemented as a synchronous class (the component inventory confirms `"async": false`). No `run_in_executor()` wrapper was added for async contexts. `OllamaHandler` (for LLM inference) is properly async, but `OllamaEmbedder` was not given the same treatment.

## Impact
Embedding requests (~50-200ms each) block the entire event loop. During memory ingestion or RAG queries, real-time voice input (STT), spatial perception, and TTS output are all stalled. This directly impacts the latency budget for an assistive real-time application.

## Reproducibility
always

## Remediation Plan
1. Convert `embed_text()` to an async method using `httpx.AsyncClient` or `aiohttp`.
2. Alternatively, wrap the synchronous call in `asyncio.get_event_loop().run_in_executor()`.
3. Add batch embedding support to amortize HTTP overhead.
4. Update all callers to `await` the embedding call.

## Implementation Suggestion
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OllamaEmbedder:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2)

    async def embed_text_async(self, text: str) -> np.ndarray:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.embed_text, text)

    # Or fully async:
    async def embed_text(self, text: str) -> np.ndarray:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            return np.array(response.json()["embedding"])
```

## GPU Impact
Embedding runs on local GPU (qwen3-embedding:4b, ~2GB VRAM). Making it async doesn't change GPU usage but prevents CPU-side blocking.

## Cloud Impact
N/A — embedding runs locally via Ollama.

## Acceptance Criteria
- [ ] `embed_text()` is non-blocking in async contexts (async method or run_in_executor)
- [ ] Event loop latency during embedding does not exceed 5ms (measured via asyncio debug mode)
- [ ] Memory ingestion and RAG queries do not stall real-time perception pipeline
- [ ] Batch embedding support added for multiple texts
