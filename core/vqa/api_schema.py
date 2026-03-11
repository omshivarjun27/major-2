"""
VQA Engine - API Schema Module
===============================

Pydantic models for VQA API request/response validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Enums
# ============================================================================

class PriorityLevel(str, Enum):
    """Obstacle priority levels."""
    CRITICAL = "critical"
    NEAR = "near"
    FAR = "far"
    SAFE = "safe"


class DirectionType(str, Enum):
    """Direction from user's viewpoint."""
    FAR_LEFT = "far left"
    LEFT = "left"
    SLIGHTLY_LEFT = "slightly left"
    CENTER = "ahead"
    SLIGHTLY_RIGHT = "slightly right"
    RIGHT = "right"
    FAR_RIGHT = "far right"


class ResponseSource(str, Enum):
    """Source of VQA response."""
    LLM = "llm"
    CACHE = "cache"
    FALLBACK = "fallback"
    ERROR = "error"


# ============================================================================
# Bounding Box Schema
# ============================================================================

class BoundingBoxSchema(BaseModel):
    """Bounding box coordinates."""
    x: int = Field(..., description="Top-left X coordinate")
    y: int = Field(..., description="Top-left Y coordinate")
    width: int = Field(..., ge=1, description="Box width")
    height: int = Field(..., ge=1, description="Box height")

    @property
    def center(self) -> tuple:
        return (self.x + self.width // 2, self.y + self.height // 2)


# ============================================================================
# Perception Schemas
# ============================================================================

class DetectionSchema(BaseModel):
    """Single detection result."""
    id: str = Field(..., description="Unique detection ID")
    class_name: str = Field(..., alias="class", description="Object class")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    bbox: BoundingBoxSchema = Field(..., description="Bounding box")

    model_config = ConfigDict(populate_by_name=True)


class ObstacleSchema(BaseModel):
    """Fused obstacle record."""
    id: str = Field(..., description="Obstacle ID")
    class_name: str = Field(..., alias="class", description="Object class")
    distance_m: float = Field(..., description="Distance in meters")
    direction: DirectionType = Field(..., description="Relative direction")
    direction_deg: float = Field(..., description="Direction angle in degrees")
    priority: PriorityLevel = Field(..., description="Priority level")
    confidence: float = Field(..., ge=0, le=1, description="Combined confidence")
    action: str = Field(..., description="Recommended action")
    is_uncertain: bool = Field(False, description="Whether result is uncertain")

    model_config = ConfigDict(populate_by_name=True)


class DepthInfoSchema(BaseModel):
    """Depth estimation info."""
    min_m: float = Field(..., description="Minimum depth in region")
    median_m: float = Field(..., description="Median depth in region")
    variance: float = Field(..., description="Depth variance")


# ============================================================================
# Perception Request/Response
# ============================================================================

class PerceptionFrameRequest(BaseModel):
    """Request for perception on a frame."""
    image_base64: str = Field(..., description="Base64 encoded JPEG image")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    run_segmentation: bool = Field(True, description="Run segmentation")
    run_depth: bool = Field(True, description="Run depth estimation")
    max_detections: int = Field(5, ge=1, le=20, description="Max detections")


class PerceptionFrameResponse(BaseModel):
    """Response from perception pipeline."""
    session_id: str = Field(..., description="Session ID")
    timestamp: str = Field(..., description="ISO timestamp")
    detections: List[DetectionSchema] = Field(..., description="Detection results")
    obstacles: List[ObstacleSchema] = Field(..., description="Fused obstacles")
    summary: str = Field(..., description="Scene summary for TTS")
    has_critical: bool = Field(..., description="Whether critical obstacles exist")
    processing_time_ms: float = Field(..., description="Total processing time")

    # Optional detailed data
    depth_info: Optional[DepthInfoSchema] = None
    image_size: List[int] = Field([640, 480], description="[width, height]")


# ============================================================================
# VQA Request/Response
# ============================================================================

class VQAAskRequest(BaseModel):
    """Request for VQA question answering."""
    question: str = Field(..., min_length=1, max_length=500, description="Question to answer")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    image_base64: Optional[str] = Field(None, description="Optional image for question")
    use_image: bool = Field(True, description="Whether to use image in reasoning")
    use_context: bool = Field(True, description="Whether to use session context")
    max_tokens: int = Field(150, ge=10, le=500, description="Max tokens in response")


class VQAAskResponse(BaseModel):
    """Response from VQA reasoning."""
    answer: str = Field(..., description="Answer to the question")
    confidence: float = Field(..., ge=0, le=1, description="Answer confidence")
    source: ResponseSource = Field(..., description="Response source")
    processing_time_ms: float = Field(..., description="Processing time")
    tokens_used: int = Field(0, description="Tokens used by LLM")
    safety_prefix: str = Field("", description="Safety prefix if uncertain")

    # Optional context
    obstacles_used: int = Field(0, description="Number of obstacles in context")
    session_id: Optional[str] = None


# ============================================================================
# Session Schemas
# ============================================================================

class SessionInfo(BaseModel):
    """Session information."""
    id: str = Field(..., description="Session ID")
    created_at: datetime = Field(..., description="Creation time")
    last_active: datetime = Field(..., description="Last activity time")
    entry_count: int = Field(..., description="Number of entries")
    critical_count: int = Field(..., description="Critical obstacles seen")
    duration_sec: float = Field(..., description="Session duration")


class SessionReplayEntry(BaseModel):
    """Single entry in session replay."""
    timestamp: datetime = Field(..., description="Entry timestamp")
    obstacles: List[ObstacleSchema] = Field(..., description="Obstacles at this time")
    question: Optional[str] = Field(None, description="VQA question if any")
    answer: Optional[str] = Field(None, description="VQA answer if any")


class SessionReplayResponse(BaseModel):
    """Response for session replay."""
    session: SessionInfo = Field(..., description="Session info")
    entries: List[SessionReplayEntry] = Field(..., description="Replay entries")
    total_entries: int = Field(..., description="Total entry count")


# ============================================================================
# Batch Schemas
# ============================================================================

class BatchPerceptionRequest(BaseModel):
    """Request for batch perception on multiple frames."""
    images_base64: List[str] = Field(..., min_length=1, max_length=10)
    session_id: Optional[str] = None


class BatchPerceptionResponse(BaseModel):
    """Response from batch perception."""
    results: List[PerceptionFrameResponse]
    total_processing_time_ms: float


# ============================================================================
# Health/Status Schemas
# ============================================================================

class HealthStatus(BaseModel):
    """System health status."""
    status: str = Field(..., description="Overall status")
    perception_ready: bool = Field(..., description="Perception pipeline ready")
    llm_ready: bool = Field(..., description="LLM ready")
    memory_entries: int = Field(..., description="Entries in memory")
    active_sessions: int = Field(..., description="Active sessions")
    avg_latency_ms: float = Field(..., description="Average latency")


class PerformanceMetrics(BaseModel):
    """Performance metrics."""
    avg_perception_ms: float
    avg_vqa_ms: float
    cache_hit_rate: float
    total_requests: int
    uptime_sec: float


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail for API responses."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail


# ============================================================================
# WebSocket Schemas
# ============================================================================

class WSPerceptionFrame(BaseModel):
    """WebSocket perception frame message."""
    type: str = "perception_frame"
    frame_id: int
    obstacles: List[ObstacleSchema]
    summary: str
    timestamp: str


class WSVQAAnswer(BaseModel):
    """WebSocket VQA answer message."""
    type: str = "vqa_answer"
    question_id: str
    answer: str
    confidence: float
