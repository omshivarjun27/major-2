1. Folder Purpose
- OllamaEmbedder is the synchronous embedding provider used by the RAG reasoning path.
- This surface is responsible for converting text prompts into vector representations and should be thread-friendly.
- It is known to block the event loop; this file documents expectations and future mitigation paths.

2. Contained Components
- OllamaEmbedder wrapper (synch embeddings calls)
- Helper utilities for batching and normalization
- Logging hooks and error shaping for embedding results

3. Dependency Graph
- Shared config/logging influence both embedding and memory layers.
- Embeddings feed into the FAISS indexer and RAG reasoner, accessed by memory.
- No independent persistence in this folder; it relies on other layers for storage.

4. Task Tracking
- Stabilize the embedding call surface and ensure deterministic outputs.
- Minimize blocking by implementing a small batching window and optional async path in the future.
- Provide a basic health indicator for embedding throughput.

5. Design Thinking
- Balance latency with accuracy; embeddings are central to retrieval quality.
- Preserve a clean contract so memory and VQA layers can reuse results.
- Prepare for future optimizations without changing the public API.

6. Research Notes
- TD-003 notes that this component can block; explore micro-batching as a mitigation.
- Consider alternative embedding models if latency increases beyond budget.

7. Risk Assessment
- Blocking behavior may impact UI responsiveness under peak loads.
- Potential drift in embedding models could affect retrieval relevance.
- Licensing and size of embedding models should be tracked as the project evolves.

8. Improvement Suggestions
- Introduce a non-blocking variant or a local cache for recent embeddings.
- Add metrics for embeddings latency and cache hit rate.
- Document versioned embeddings to ease upgrades.

9. Folder Change Log
- Created infrastructure/llm/embeddings/AGENTS.md with the nine-section plan.
- Noted the synchronous nature and mitigation ideas for performance.
