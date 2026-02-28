1. Folder Purpose
- Ollama-based LLM adapter for local/offline reasoning; enables Qwen-VL style reasoning and embedding access.
- Serves as the primary path for LLM calls when Ollama is available, with clean separation from external providers.
- The adapter is designed to be swapped with minimal disruption to callers.

2. Contained Components
- Ollama API bridge (server/client interface)
- Wrapper around qwen3-embedding:4b for embeddings retrieval
- Lightweight error handling primitives and logging hooks

3. Dependency Graph
- Shared utilities and infrastructure layer provide configuration, logging, and error models.
- Depends on infrastructure/llm for routing decisions and on embeddings for retrieval augmentation.
- No external provider calls beyond local Ollama services in the default path.

4. Task Tracking
- Implement the Ollama request pipeline and response normalization.
- Wire embedding calls to the OllamaEmbedder, ensuring synchronous behavior aligns with TD-003.
- Add basic health and version reporting for Ollama service compatibility checks.

5. Design Thinking
- Favor deterministic latency with local execution when possible.
- Define a clear contract for request/response to enable reuse by memory and VQA components.
- Ensure compatibility with testing harness to reproduce reasoning results.

6. Research Notes
- Ollama provides a self-contained runtime; explore version pinning and model packaging options.
- Embeddings engine (OllamaEmbedder) can block; consider isolation boundaries to protect the event loop.

7. Risk Assessment
- Local dependency risk: Ollama service downtime would impact reasoning throughput.
- Embedding calls may block; monitor and avoid cascading latency.
- Version drift with model packs; establish simple rollback paths.

8. Improvement Suggestions
- Add a lightweight cache for recent reasoning results to reduce recomputation.
- Expose a health endpoint with ready/healthy states for orchestration.
- Document upgrade path when Ollama model bundles change.

9. Folder Change Log
- Created infrastructure/llm/ollama/AGENTS.md outlining the Ollama adapter role and plan.
- Included notes on latency, embedding coupling, and health checks.
