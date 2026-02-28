1. Folder Purpose
- This directory houses adapters that interface with Large Language Models (LLMs).
- It routes requests to local Ollama or SiliconFlow backends and provides a stable surface for reasoning tasks.
- Central goal: minimize surface area changes when swapping providers and preserve latency targets.

2. Contained Components
- infrastructure/llm/ollama/AGENTS.md (Ollama LLM adapter)
- infrastructure/llm/siliconflow/AGENTS.md (SiliconFlow LLM adapter)
- infrastructure/llm/embeddings/AGENTS.md (OllamaEmbedder synchronization layer)
- (Note: Each subfolder may evolve independently; this AGENTS.md documents intent.)

3. Dependency Graph
- Shared layer -> core -> application -> infrastructure/llm
- Adapters rely on shared utilities for logging, config, and error shapes.
- No external circuit-breakers for providers are configured by default.

4. Task Tracking
- Wire basic request/response paths for Ollama and SiliconFlow adapters.
- Introduce a small health query wrapper for each provider.
- Ensure embedding/LLM calls do not block the entire event loop more than TD-003 allows.
- Document provider-specific failure modes and fallback options where applicable.

5. Design Thinking
- Prefer local execution for latency-critical reasoning paths.
- Maintain a uniform API surface to simplify orchestration in the memory and VQA layers.
- Ensure side-channel data (PII) is scrubbed in logs and metrics when possible.

6. Research Notes
- Ollama is favored for low-latency, local reasoning; SiliconFlow offers alternative capabilities.
- Embeddings channel (embeddings/AGENTS.md) interacts with the OllamaEmbedder wrapper and can block if not async-aware.
- Consider future quantization or model merges to reduce VRAM usage.

7. Risk Assessment
- Single-provider SPOF risk in both Ollama and SiliconFlow; no circuit-breakers by default.
- Local adapters depend on CPU/GPU availability; monitor for resource contention.
- Potential drift in model capabilities requiring version pinning and regression tests.

8. Improvement Suggestions
- Add lightweight health endpoints for each adapter with timeouts under 200ms.
- Introduce a versioning note per provider and mapping to capabilities used by the planner.
- Start a changelog segment for model backends to ease rollback.

9. Folder Change Log
- Created infrastructure/llm/AGENTS.md with 9-section structure and initial guidance.
- Documented current coupling to shared utilities and the non-use of circuit-breakers by default.
- Plan includes health wrappers and latency-conscious design notes.
