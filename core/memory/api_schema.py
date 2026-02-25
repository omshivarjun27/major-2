"""
Memory Engine - API Schema Module
==================================

Pydantic models for memory API request/response validation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Enums
# ============================================================================


class PrivacyFlag(str, Enum):
    """Privacy level for stored memories."""

    NORMAL = "normal"
    SENSITIVE = "sensitive"
    REDACTED = "redacted"


class EmbeddingStatus(str, Enum):
    """Status of embedding generation."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    DEDUPLICATED = "deduplicated"
    REJECTED = "rejected"


class QueryMode(str, Enum):
    """Mode for RAG query responses."""

    SHORT = "short"
    VERBOSE = "verbose"


# ============================================================================
# Memory Store Schemas
# ============================================================================


class MemoryStoreRequest(BaseModel):
    """Request to store a multimodal memory."""

    # Multimodal inputs (at least one required)
    image_base64: Optional[str] = Field(None, description="Base64-encoded image")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio")
    transcript: Optional[str] = Field(None, max_length=10000, description="Text transcription")
    scene_graph: Optional[Dict[str, Any]] = Field(None, description="Scene graph JSON")

    # User-provided metadata
    user_label: Optional[str] = Field(None, max_length=200, description="User label for the memory")
    device_id: Optional[str] = Field(None, max_length=100, description="Device identifier")
    session_id: Optional[str] = Field(None, max_length=100, description="Session identifier")

    # Privacy settings
    save_raw: bool = Field(False, description="Save raw image/audio (requires consent)")

    @field_validator("transcript", "user_label")
    @classmethod
    def strip_whitespace(cls, v):
        if v is not None:
            return v.strip()
        return v


class MemoryStoreResponse(BaseModel):
    """Response from storing a memory."""

    id: str = Field(..., description="Unique memory ID")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    expiry: str = Field(..., description="ISO8601 retention expiry date")
    summary: str = Field(..., description="Auto-generated 1-2 line summary")
    embedding_status: EmbeddingStatus = Field(..., description="Status of embedding generation")

    # Performance metrics (optional)
    ingest_time_ms: Optional[float] = None
    embedding_time_ms: Optional[float] = None


# ============================================================================
# Memory Search Schemas
# ============================================================================


class MemorySearchRequest(BaseModel):
    """Request to search memories."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    k: int = Field(5, ge=1, le=50, description="Number of results to return")
    time_window_days: Optional[int] = Field(None, ge=1, le=365, description="Limit to recent N days")
    session_id: Optional[str] = Field(None, description="Limit to specific session")
    include_scene_graph: bool = Field(False, description="Include full scene graph in results")


class MemoryHit(BaseModel):
    """Single search result."""

    id: str = Field(..., description="Memory ID")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    summary: str = Field(..., description="Memory summary")
    score: float = Field(..., ge=0, le=1, description="Similarity score")
    scene_graph_ref: Optional[str] = Field(None, description="Reference to scene graph")
    user_label: Optional[str] = Field(None, description="User-provided label")

    # Optional full data
    scene_graph: Optional[Dict[str, Any]] = Field(None, description="Full scene graph if requested")


class MemorySearchResponse(BaseModel):
    """Response from memory search."""

    query: str = Field(..., description="Original query")
    results: List[MemoryHit] = Field(default_factory=list, description="Search results")
    total_searched: int = Field(0, description="Total memories searched")
    search_time_ms: float = Field(0, description="Search time in milliseconds")


# ============================================================================
# Memory Query (RAG) Schemas
# ============================================================================


class MemoryCitation(BaseModel):
    """Citation for a memory used in RAG response."""

    memory_id: str = Field(..., description="Memory ID")
    timestamp: str = Field(..., description="Memory timestamp")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to query")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from memory")


class MemoryQueryRequest(BaseModel):
    """Request for RAG-based memory query."""

    query: str = Field(..., min_length=1, max_length=500, description="Natural language query")
    mode: QueryMode = Field(QueryMode.SHORT, description="Response mode")
    k: int = Field(5, ge=1, le=20, description="Number of memories to retrieve")
    time_window_days: Optional[int] = Field(None, ge=1, le=365, description="Limit to recent N days")
    require_evidence: bool = Field(True, description="Only answer if evidence exists")


class MemoryQueryResponse(BaseModel):
    """Response from RAG memory query."""

    answer: str = Field(..., description="Natural language answer")
    confidence: float = Field(..., ge=0, le=1, description="Answer confidence")
    has_evidence: bool = Field(..., description="Whether evidence was found")
    citations: List[MemoryCitation] = Field(default_factory=list, description="Memory citations")

    # Optional verbose details
    reasoning: Optional[str] = Field(None, description="Reasoning explanation (verbose mode)")

    # Performance metrics
    retrieval_time_ms: float = Field(0, description="Time to retrieve memories")
    reasoning_time_ms: float = Field(0, description="Time for LLM reasoning")


# ============================================================================
# Memory Record Schema
# ============================================================================


class MemoryRecord(BaseModel):
    """Full memory record with all metadata."""

    id: str = Field(..., description="Unique memory ID")
    timestamp: str = Field(..., description="ISO8601 creation timestamp")
    expiry: str = Field(..., description="ISO8601 retention expiry")

    # Content
    summary: str = Field(..., description="Auto-generated summary")
    transcript: Optional[str] = Field(None, description="Original transcript")
    scene_graph: Optional[Dict[str, Any]] = Field(None, description="Scene graph data")
    scene_graph_ref: Optional[str] = Field(None, description="External scene graph reference")

    # Metadata
    user_label: Optional[str] = Field(None, description="User-provided label")
    device_id: Optional[str] = Field(None, description="Device identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")

    # Status
    embedding_status: EmbeddingStatus = Field(EmbeddingStatus.PENDING)
    privacy_flag: PrivacyFlag = Field(PrivacyFlag.NORMAL)
    has_raw_image: bool = Field(False)
    has_raw_audio: bool = Field(False)

    # Vector info
    vector_dim: Optional[int] = Field(None, description="Embedding dimension")


# ============================================================================
# Consent Schema
# ============================================================================


class MemoryConsentRequest(BaseModel):
    """Request to set memory consent preferences."""

    opt_in: bool = Field(..., description="Whether user consents to memory storage")
    save_raw_media: bool = Field(False, description="Allow saving raw image/audio")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for consent change")
    device_id: Optional[str] = Field(None, description="Device identifier")


class MemoryConsentResponse(BaseModel):
    """Response from consent update."""

    consent_recorded: bool = Field(..., description="Whether consent was recorded")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    current_settings: Dict[str, bool] = Field(..., description="Current consent settings")


# ============================================================================
# Delete Schemas
# ============================================================================


class MemoryDeleteResponse(BaseModel):
    """Response from memory deletion."""

    deleted: bool = Field(..., description="Whether deletion was successful")
    id: Optional[str] = Field(None, description="Deleted memory ID")
    count: int = Field(0, description="Number of memories deleted")


# ============================================================================
# Debug Schema
# ============================================================================


class MemoryDebugInfo(BaseModel):
    """Debug information for a session."""

    session_id: str
    memory_count: int
    embedding_dims: Optional[int]
    index_size: int
    recent_ingests: List[Dict[str, Any]]
    sample_search_results: Optional[List[MemoryHit]]
