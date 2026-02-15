"""
Memory Engine Package
=====================

Local RAG memory system with FAISS indexing, multimodal embeddings,
and conversational retrieval for the Voice-Vision Assistant.

Components:
- config: Memory-specific configuration
- api_schema: Pydantic models for API validation
- embeddings: Text/image/audio embedding generation
- indexer: FAISS index management
- ingest: Multimodal memory ingestion
- retriever: Vector search API
- rag_reasoner: Conversational RAG with qwen3-vl
- maintenance: Retention enforcement and backup
"""

from .config import MemoryConfig, get_memory_config
from .api_schema import (
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryRecord,
    MemoryHit,
    MemoryConsentRequest,
)
from .embeddings import TextEmbedder, MultimodalFuser
from .indexer import FAISSIndexer
from .ingest import MemoryIngester
from .retriever import MemoryRetriever
from .rag_reasoner import RAGReasoner
from .maintenance import MemoryMaintenance
from .llm_client import (
    ClaudeClient,
    OllamaClient,
    StubLLMClient,
    BaseLLMClient,
    LLMRole,
    init_backends,
    get_backend,
    register_backend,
)

__all__ = [
    # Config
    "MemoryConfig",
    "get_memory_config",
    # Schemas
    "MemoryStoreRequest",
    "MemoryStoreResponse",
    "MemorySearchRequest",
    "MemorySearchResponse",
    "MemoryQueryRequest",
    "MemoryQueryResponse",
    "MemoryRecord",
    "MemoryHit",
    "MemoryConsentRequest",
    # Core components
    "TextEmbedder",
    "MultimodalFuser",
    "FAISSIndexer",
    "MemoryIngester",
    "MemoryRetriever",
    "RAGReasoner",
    "MemoryMaintenance",
    # LLM backends
    "ClaudeClient",
    "OllamaClient",
    "StubLLMClient",
    "BaseLLMClient",
    "LLMRole",
    "init_backends",
    "get_backend",
    "register_backend",
]

__version__ = "1.0.0"
