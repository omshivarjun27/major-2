# core/memory/AGENTS.md
Privacy-first local RAG engine: FAISS vector index + Ollama/Claude reasoning.
**Key Constraint**: `MEMORY_ENABLED=true` by default, but requires `/memory/consent` before storing data.

## WHERE TO LOOK
| File | Purpose |
|------|---------|
| `config.py` | MemoryConfig, retentions, max_vectors, index_path. |
| `embeddings.py` | TextEmbedder (qwen3-embedding:4b) & MultimodalFuser. |
| `indexer.py` | Thread-safe FAISS indexer with persistence and LRU eviction. |
| `ingest.py` | MemoryIngester: multimodal (text, image, audio, scene-graph) storage. |
| `retriever.py` | MemoryRetriever: vector similarity search (RAG_K=5). |
| `rag_reasoner.py` | RAGReasoner: orchestrates retrieval and prompt generation. |
| `llm_client.py` | Multi-backend LLM manager (Claude, Ollama, Stub). |
| `api_endpoints.py` | FastAPI router for storage, search, query, and consent. |
| `api_schema.py` | Pydantic models for memory records and RAG queries. |
| `maintenance.py` | MemoryMaintenance: auto-expiry and backup logic. |

## LLM FALLBACK CHAIN
`Claude Opus 4.6 (role="memory") → Ollama qwen3-vl (role="vision") → StubLLMClient (role="fallback")`

## ARCHITECTURE & CONVENTIONS
- **Lazy Load**: FAISS is loaded only on the first call to `indexer.py` to save startup time.
- **Privacy Enforcement**: All write-operations check `MemoryConsent` (stored in `data/consent/`).
- **Raw Media Storage**: `RAW_MEDIA_SAVE=false` by default; only metadata and embeddings are typically stored.
- **Concurrency**: `FAISSIndexer` uses a thread-safe mutex for index updates.

## DISAMBIGUATION
- **core.memory** handles **persistent**, multi-session RAG memory.
- **core.vqa.vqa_memory** handles **volatile**, session-scoped visual context only.
- **core.face.embeddings** handles face-specific recognition vectors (isolated from general RAG).

## NEXT STEPS
- Implement `infrastructure/storage` and `infrastructure/monitoring` to replace local file-based persistence for RAG metadata.
