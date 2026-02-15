"""
Memory Engine - API Endpoints Module
======================================

FastAPI router with memory storage, search, query, and management endpoints.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from .config import get_memory_config, MemoryConfig
from .api_schema import (
    MemoryStoreRequest,
    MemoryStoreResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryQueryRequest,
    MemoryQueryResponse,
    MemoryRecord,
    MemoryConsentRequest,
    MemoryConsentResponse,
    MemoryDeleteResponse,
    MemoryDebugInfo,
)
from .embeddings import create_embedders, TextEmbedder, MultimodalFuser
from .indexer import FAISSIndexer
from .ingest import MemoryIngester
from .retriever import MemoryRetriever
from .rag_reasoner import RAGReasoner
from .maintenance import MemoryMaintenance

logger = logging.getLogger("memory-api")

# Create router
router = APIRouter(tags=["memory"])

# Global instances (initialized lazily)
_config: Optional[MemoryConfig] = None
_indexer: Optional[FAISSIndexer] = None
_text_embedder: Optional[TextEmbedder] = None
_fuser: Optional[MultimodalFuser] = None
_ingester: Optional[MemoryIngester] = None
_retriever: Optional[MemoryRetriever] = None
_rag_reasoner: Optional[RAGReasoner] = None
_maintenance: Optional[MemoryMaintenance] = None


def _ensure_initialized():
    """Ensure all components are initialized."""
    global _config, _indexer, _text_embedder, _fuser
    global _ingester, _retriever, _rag_reasoner, _maintenance
    
    if _config is None:
        _config = get_memory_config()
    
    if not _config.enabled:
        raise HTTPException(status_code=503, detail="Memory engine is disabled")
    
    if _indexer is None:
        # Create embedders
        _text_embedder, img_emb, audio_emb, _fuser = create_embedders(_config)
        
        # Create indexer
        _indexer = FAISSIndexer(
            index_path=_config.index_path,
            dimension=_text_embedder.dimension,
            max_vectors=_config.max_vectors,
        )
        
        # Create ingester
        _ingester = MemoryIngester(
            indexer=_indexer,
            text_embedder=_text_embedder,
            fuser=_fuser,
            config=_config,
        )
        
        # Create retriever
        _retriever = MemoryRetriever(
            indexer=_indexer,
            text_embedder=_text_embedder,
            config=_config,
        )
        
        # Create RAG reasoner (without LLM for now)
        _rag_reasoner = RAGReasoner(
            retriever=_retriever,
            llm_client=None,  # Will be set externally if needed
            config=_config,
        )
        
        # Create maintenance
        _maintenance = MemoryMaintenance(
            indexer=_indexer,
            config=_config,
        )
        
        logger.info("Memory engine initialized")


def get_ingester() -> MemoryIngester:
    """Dependency to get ingester."""
    _ensure_initialized()
    return _ingester


def get_retriever() -> MemoryRetriever:
    """Dependency to get retriever."""
    _ensure_initialized()
    return _retriever


def get_rag_reasoner() -> RAGReasoner:
    """Dependency to get RAG reasoner."""
    _ensure_initialized()
    return _rag_reasoner


def get_maintenance() -> MemoryMaintenance:
    """Dependency to get maintenance."""
    _ensure_initialized()
    return _maintenance


# ============================================================================
# Memory Store Endpoints
# ============================================================================

@router.post("/store", response_model=MemoryStoreResponse)
async def store_memory(
    request: MemoryStoreRequest,
    ingester: MemoryIngester = Depends(get_ingester),
):
    """Store a multimodal memory.
    
    Accepts image, audio, transcript, and/or scene graph.
    Generates embeddings and stores in FAISS index.
    """
    try:
        # Check consent (if device_id provided)
        consent = ingester.get_consent(request.device_id)
        consent_given = consent.get("memory_enabled", True) and consent.get("save_raw_media", False)
        
        response = await ingester.ingest(request, consent_given=consent_given)
        return response
    except Exception as e:
        logger.error(f"Store failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Memory Search Endpoints
# ============================================================================

@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(
    request: MemorySearchRequest,
    retriever: MemoryRetriever = Depends(get_retriever),
):
    """Search memories by text query.
    
    Returns top-K similar memories with scores.
    """
    try:
        response = await retriever.search(request)
        return response
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Memory Query (RAG) Endpoints
# ============================================================================

@router.post("/query", response_model=MemoryQueryResponse)
async def query_memories(
    request: MemoryQueryRequest,
    reasoner: RAGReasoner = Depends(get_rag_reasoner),
):
    """Answer a natural language query using retrieved memories.
    
    Uses RAG pipeline with optional LLM reasoning.
    """
    try:
        response = await reasoner.query(request)
        return response
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Memory Retrieval Endpoints
# ============================================================================

@router.get("/{memory_id}", response_model=MemoryRecord)
async def get_memory(
    memory_id: str,
    retriever: MemoryRetriever = Depends(get_retriever),
):
    """Get a specific memory by ID."""
    record = retriever.get_memory(memory_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
    return record


@router.get("/session/{session_id}")
async def get_session_memories(
    session_id: str,
    limit: int = 50,
    retriever: MemoryRetriever = Depends(get_retriever),
):
    """Get all memories for a session."""
    memories = retriever.get_session_memories(session_id, limit=limit)
    return {"session_id": session_id, "memories": memories, "count": len(memories)}


@router.get("/recent")
async def get_recent_memories(
    hours: float = 24.0,
    limit: int = 20,
    retriever: MemoryRetriever = Depends(get_retriever),
):
    """Get recent memories from the last N hours."""
    memories = retriever.get_recent_memories(hours=hours, limit=limit)
    return {"hours": hours, "memories": memories, "count": len(memories)}


# ============================================================================
# Consent Endpoints
# ============================================================================

@router.post("/consent", response_model=MemoryConsentResponse)
async def set_consent(
    request: MemoryConsentRequest,
    ingester: MemoryIngester = Depends(get_ingester),
):
    """Set memory consent preferences.
    
    Controls whether memories are stored and if raw media is saved.
    """
    settings = ingester.record_consent(
        device_id=request.device_id,
        opt_in=request.opt_in,
        save_raw_media=request.save_raw_media,
        reason=request.reason,
    )
    
    return MemoryConsentResponse(
        consent_recorded=True,
        timestamp=datetime.utcnow().isoformat() + "Z",
        current_settings=settings,
    )


@router.get("/consent/{device_id}")
async def get_consent(
    device_id: str,
    ingester: MemoryIngester = Depends(get_ingester),
):
    """Get current consent settings for a device."""
    settings = ingester.get_consent(device_id)
    return {"device_id": device_id, "settings": settings}


# ============================================================================
# Delete Endpoints
# ============================================================================

@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_memory(memory_id: str):
    """Delete a specific memory."""
    _ensure_initialized()
    
    deleted = _indexer.delete(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
    
    return MemoryDeleteResponse(deleted=True, id=memory_id, count=1)


@router.post("/delete_all", response_model=MemoryDeleteResponse)
async def delete_all_memories(confirm: bool = False):
    """Delete all memories.
    
    Requires confirm=true for safety.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Set confirm=true to delete all memories",
        )
    
    _ensure_initialized()
    
    count = _indexer.size
    _indexer.clear()
    
    return MemoryDeleteResponse(deleted=True, count=count)


@router.delete("/session/{session_id}")
async def delete_session_memories(
    session_id: str,
    retriever: MemoryRetriever = Depends(get_retriever),
):
    """Delete all memories for a session."""
    _ensure_initialized()
    
    memories = retriever.get_session_memories(session_id, limit=1000)
    deleted = 0
    
    for mem in memories:
        if _indexer.delete(mem.id):
            deleted += 1
    
    return MemoryDeleteResponse(deleted=True, count=deleted)


# ============================================================================
# Maintenance Endpoints
# ============================================================================

@router.post("/maintenance/run")
async def run_maintenance(
    maintenance: MemoryMaintenance = Depends(get_maintenance),
):
    """Run maintenance tasks (retention enforcement, compaction, backup)."""
    report = await maintenance.run()
    return report


@router.get("/health")
async def get_health(
    maintenance: MemoryMaintenance = Depends(get_maintenance),
):
    """Get memory system health status."""
    return maintenance.get_health()


@router.get("/stats")
async def get_stats(
    ingester: MemoryIngester = Depends(get_ingester),
    retriever: MemoryRetriever = Depends(get_retriever),
    reasoner: RAGReasoner = Depends(get_rag_reasoner),
):
    """Get memory system statistics."""
    return {
        "ingest": ingester.get_stats(),
        "retrieval": retriever.get_stats(),
        "rag": reasoner.get_stats(),
    }


# ============================================================================
# Debug Endpoints
# ============================================================================

@router.get("/debug/{session_id}", response_model=MemoryDebugInfo)
async def debug_session(
    session_id: str,
    retriever: MemoryRetriever = Depends(get_retriever),
):
    """Get debug information for a session."""
    _ensure_initialized()
    
    memories = retriever.get_session_memories(session_id, limit=10)
    
    # Try a sample search
    sample_results = None
    if memories:
        try:
            search_req = MemorySearchRequest(query=memories[0].summary[:50], k=3)
            search_resp = await retriever.search(search_req)
            sample_results = search_resp.results
        except Exception:
            pass
    
    return MemoryDebugInfo(
        session_id=session_id,
        memory_count=len(memories),
        embedding_dims=_text_embedder.dimension if _text_embedder else None,
        index_size=_indexer.size if _indexer else 0,
        recent_ingests=[{
            "id": m.id,
            "timestamp": m.timestamp,
            "summary": m.summary[:100],
        } for m in memories[:5]],
        sample_search_results=sample_results,
    )


# ============================================================================
# Factory Function
# ============================================================================

def get_router() -> APIRouter:
    """Get the memory API router.
    
    Usage in main app:
        from core.memory.api_endpoints import get_router as get_memory_router
        app.include_router(get_memory_router(), prefix="/memory")
    """
    return router


def set_llm_client(client: Any):
    """Set the LLM client for RAG reasoning.
    
    Call this after initialization to enable LLM-based answers.
    
    Args:
        client: OpenAI-compatible or Ollama client
    """
    global _rag_reasoner
    
    _ensure_initialized()
    if _rag_reasoner:
        _rag_reasoner._llm_client = client
        logger.info("LLM client set for RAG reasoner")


def reset_for_testing():
    """Reset all global state (for testing)."""
    global _config, _indexer, _text_embedder, _fuser
    global _ingester, _retriever, _rag_reasoner, _maintenance
    
    _config = None
    _indexer = None
    _text_embedder = None
    _fuser = None
    _ingester = None
    _retriever = None
    _rag_reasoner = None
    _maintenance = None
