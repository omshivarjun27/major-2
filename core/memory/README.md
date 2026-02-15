# Memory Engine

Local RAG memory system for the Voice-Vision-Assistant.

## Overview

The memory engine provides:
- **FAISS-based vector indexing** for efficient similarity search
- **Multimodal ingestion** (text, image, audio, scene graph)
- **Conversational RAG** with Claude Opus 4.6 (primary) or qwen3-vl (fallback)
- **Privacy-first design** with opt-in consent and retention policies
- **Multi-backend LLM** support with automatic fallback chain

## Quick Start

```python
from memory_engine import MemoryIngester, MemoryRetriever, RAGReasoner
from memory_engine.api_schema import MemoryStoreRequest, MemoryQueryRequest

# Store a memory
response = await ingester.ingest(MemoryStoreRequest(
    transcript="I put my keys on the kitchen table",
    scene_graph={"objects": ["keys", "table"]}
))

# Query memories
answer = await reasoner.query(MemoryQueryRequest(
    query="Where are my keys?"
))
# -> "Based on my memory from 2024-01-01 12:00: You put your keys on the kitchen table"
```

## Configuration

Set these environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_ENABLED` | `true` | Enable/disable memory engine |
| `MEMORY_RETENTION_DAYS` | `30` | Days to retain memories |
| `MEMORY_MAX_VECTORS` | `5000` | Maximum indexed memories |
| `MEMORY_INDEX_PATH` | `./data/memory_index/` | Index storage path |
| `EMBEDDING_MODEL` | `qwen3-embedding:4b` | Text embedding model |
| `RAG_K` | `5` | Memories to retrieve for RAG |
| `ANTHROPIC_API_KEY` | _(empty)_ | Claude Opus 4.6 API key (optional) |

## LLM Backends

| Role | Backend | Use Case |
|------|---------|----------|
| `memory` | Claude Opus 4.6 | RAG reasoning, scenario analysis |
| `vision` | qwen3-vl (Ollama) | Image-grounded VQA |
| `fallback` | Ollama → Stub | When primary is unavailable |

Fallback chain: `Claude Opus 4.6 → qwen3-vl → StubLLMClient`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/memory/store` | POST | Store multimodal memory |
| `/memory/search` | POST | Search by text query |
| `/memory/query` | POST | RAG-based Q&A |
| `/memory/{id}` | GET | Get specific memory |
| `/memory/consent` | POST | Set privacy preferences |
| `/memory/{id}` | DELETE | Delete memory |
| `/memory/health` | GET | System health status |

## Architecture

```
memory_engine/
├── __init__.py        # Package exports
├── config.py          # Environment configuration
├── api_schema.py      # Pydantic request/response models
├── embeddings.py      # Text/image/audio embedders
├── indexer.py         # FAISS index management
├── ingest.py          # Multimodal ingestion pipeline
├── retriever.py       # Vector search API
├── rag_reasoner.py    # Conversational RAG with LLM
├── llm_client.py      # Multi-backend: Claude Opus 4.6, Ollama, Stub
├── maintenance.py     # Retention & backup tasks
└── api_endpoints.py   # FastAPI router
```

## Privacy

- **Default**: Raw images/audio are NOT stored
- **Opt-in**: User must explicitly consent via `/memory/consent`
- **Retention**: Memories auto-expire after configured days
- **Delete**: Users can purge all memories anytime
