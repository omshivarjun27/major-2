"""
VQA Engine - FastAPI Endpoints
===============================

REST API endpoints for perception and VQA.
"""

import asyncio
import base64
import io
import logging
import time
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from PIL import Image

from .api_schema import (
    BoundingBoxSchema,
    DetectionSchema,
    DirectionType,
    ErrorResponse,
    HealthStatus,
    ObstacleSchema,
    PerceptionFrameRequest,
    PerceptionFrameResponse,
    PerformanceMetrics,
    PriorityLevel,
    ResponseSource,
    SessionInfo,
    SessionReplayEntry,
    SessionReplayResponse,
    VQAAskRequest,
    VQAAskResponse,
)
from .memory import MemoryConfig, VQAMemory
from .perception import PerceptionPipeline
from .perception import create_pipeline as create_perception_pipeline
from .priority_scene import PrioritySceneAnalyzer
from .scene_graph import SceneGraphBuilder
from .spatial_fuser import FusionConfig, SpatialFuser
from .vqa_reasoner import VQAReasoner
from .vqa_reasoner import VQARequest as InternalVQARequest

# Import debug visualizer
try:
    from shared.debug import DebugVisualizer, render_debug_image
    DEBUG_TOOLS_AVAILABLE = True
except ImportError:
    DEBUG_TOOLS_AVAILABLE = False

# Import speech-VQA bridge
try:
    from core.speech import VoiceAskConfig, VoiceAskPipeline
    VOICE_BRIDGE_AVAILABLE = True
except ImportError:
    VOICE_BRIDGE_AVAILABLE = False

logger = logging.getLogger("vqa-api")

# Create router
router = APIRouter(prefix="/vqa", tags=["vqa"])

# Global instances (initialized on startup)
_perception: Optional[PerceptionPipeline] = None
_fuser: Optional[SpatialFuser] = None
_reasoner: Optional[VQAReasoner] = None
_memory: Optional[VQAMemory] = None
_scene_builder: Optional[SceneGraphBuilder] = None
_priority_analyzer: Optional[PrioritySceneAnalyzer] = None
_debug_visualizer = None
_voice_pipeline = None
_start_time: float = 0

# Metrics
_metrics = {
    "perception_times": [],
    "vqa_times": [],
    "total_requests": 0,
}


# ============================================================================
# Initialization
# ============================================================================

def init_vqa_api(
    llm_client=None,
    model: str = "qwen3.5:397b-cloud",
    use_mock_detector: bool = True,
    memory_persist_path: Optional[str] = None,
):
    """
    Initialize VQA API components.

    Call this at application startup.
    """
    global _perception, _fuser, _reasoner, _memory, _scene_builder, _start_time
    global _priority_analyzer, _debug_visualizer, _voice_pipeline

    _perception = create_perception_pipeline(use_mock=use_mock_detector)
    _fuser = SpatialFuser(FusionConfig())
    _reasoner = VQAReasoner(llm_client=llm_client, model=model)
    _memory = VQAMemory(MemoryConfig(persist_path=memory_persist_path))
    _scene_builder = SceneGraphBuilder()
    _priority_analyzer = PrioritySceneAnalyzer()
    _start_time = time.time()

    # Initialize debug visualizer if available
    if DEBUG_TOOLS_AVAILABLE:
        from shared.debug import DebugVisualizer
        _debug_visualizer = DebugVisualizer()
        logger.info("Debug visualizer initialized")

    # Initialize voice pipeline if available
    if VOICE_BRIDGE_AVAILABLE:
        from core.speech import VoiceAskPipeline
        _voice_pipeline = VoiceAskPipeline()
        logger.info("Voice pipeline initialized")

    logger.info("VQA API initialized")


def get_router() -> APIRouter:
    """Get the FastAPI router."""
    return router


# ============================================================================
# Perception Endpoints
# ============================================================================

@router.post(
    "/perception/frame",
    response_model=PerceptionFrameResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def process_perception_frame(request: PerceptionFrameRequest):
    """
    Process a single frame through the full perception pipeline.

    Returns detections, segmentation masks, depth estimation,
    and fused obstacle records.
    """
    global _metrics

    if not _perception:
        raise HTTPException(500, "Perception pipeline not initialized")

    start_time = time.time()
    _metrics["total_requests"] += 1

    try:
        # Decode image
        image = _decode_image(request.image_base64)

        # Run perception pipeline
        perception_result = await _perception.process(image)

        # Build scene graph
        scene_graph = _scene_builder.build(perception_result)

        # Apply spatial fusion
        fused_result = _fuser.fuse(perception_result)

        # Get or create session
        session_id = request.session_id or f"session_{int(time.time()*1000)}"

        # Store in memory
        _memory.store(scene_graph, session_id)

        # Build response
        detections = [
            DetectionSchema(
                id=d.id,
                **{"class": d.class_name},
                confidence=d.confidence,
                bbox=BoundingBoxSchema(
                    x=d.bbox.x_min,
                    y=d.bbox.y_min,
                    width=d.bbox.width,
                    height=d.bbox.height,
                ),
            )
            for d in perception_result.detections
        ]

        obstacles = [
            ObstacleSchema(
                id=o.id,
                **{"class": o.class_name},
                distance_m=o.distance_m,
                direction=DirectionType(o.direction.value),
                direction_deg=o.direction_deg,
                priority=PriorityLevel(o.priority.value),
                confidence=o.detection_confidence,
                action=o.action_recommendation,
                is_uncertain=fused_result.obstacles[i].is_uncertain if i < len(fused_result.obstacles) else False,
            )
            for i, o in enumerate(scene_graph.obstacles)
        ]

        elapsed_ms = (time.time() - start_time) * 1000
        _metrics["perception_times"].append(elapsed_ms)
        _metrics["perception_times"] = _metrics["perception_times"][-100:]  # Keep last 100

        return PerceptionFrameResponse(
            session_id=session_id,
            timestamp=perception_result.timestamp,
            detections=detections,
            obstacles=obstacles,
            summary=scene_graph.summary,
            has_critical=any(o.priority == PriorityLevel.CRITICAL for o in obstacles),
            processing_time_ms=elapsed_ms,
            image_size=list(perception_result.image_size),
        )

    except ValueError as e:
        raise HTTPException(400, f"Invalid request: {e}")
    except Exception as e:
        logger.exception("Perception failed")
        raise HTTPException(500, f"Perception failed: {e}")


# ============================================================================
# VQA Endpoints
# ============================================================================

@router.post(
    "/ask",
    response_model=VQAAskResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def ask_vqa_question(request: VQAAskRequest):
    """
    Answer a visual question using the VQA reasoner.

    Combines perception results with LLM reasoning for
    accurate, navigation-focused answers.
    """
    global _metrics

    if not _reasoner:
        raise HTTPException(500, "VQA reasoner not initialized")

    start_time = time.time()
    _metrics["total_requests"] += 1

    try:
        # Decode image if provided
        image = None
        if request.image_base64:
            image = _decode_image(request.image_base64)

        # Get session context if requested
        session_id = request.session_id or f"session_{int(time.time()*1000)}"
        scene_graph = None
        fused_result = None

        if request.use_context and _memory:
            # Get recent scene from memory
            recent = _memory.get_session_history(session_id, limit=1)
            if recent:
                import json
                json.loads(recent[0].scene_graph_json)
                # Note: Would need to reconstruct SceneGraph from dict

        # If image provided, run perception
        if image and _perception:
            perception_result = await _perception.process(image)
            scene_graph = _scene_builder.build(perception_result)
            fused_result = _fuser.fuse(perception_result)

            # Store in memory
            _memory.store(scene_graph, session_id, question=request.question)

        # Build VQA request
        vqa_request = InternalVQARequest(
            question=request.question,
            image=image,
            scene_graph=scene_graph,
            fused_result=fused_result,
            use_image=request.use_image and image is not None,
            max_tokens=request.max_tokens,
        )

        # Get answer
        response = await _reasoner.answer(vqa_request)

        # Update memory with answer
        if _memory and fused_result:
            recent = _memory.get_session_history(session_id, limit=1)
            if recent:
                _memory.store_vqa_response(recent[0].id, response)

        elapsed_ms = (time.time() - start_time) * 1000
        _metrics["vqa_times"].append(elapsed_ms)
        _metrics["vqa_times"] = _metrics["vqa_times"][-100:]

        return VQAAskResponse(
            answer=response.get_full_answer(),
            confidence=response.confidence,
            source=ResponseSource(response.source),
            processing_time_ms=elapsed_ms,
            tokens_used=response.tokens_used,
            safety_prefix=response.safety_prefix,
            obstacles_used=len(fused_result.obstacles) if fused_result else 0,
            session_id=session_id,
        )

    except ValueError as e:
        raise HTTPException(400, f"Invalid request: {e}")
    except Exception as e:
        logger.exception("VQA failed")
        raise HTTPException(500, f"VQA failed: {e}")


# ============================================================================
# Session Endpoints
# ============================================================================

@router.get(
    "/session/{session_id}/replay",
    response_model=SessionReplayResponse,
)
async def get_session_replay(
    session_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """
    Get session replay data for debugging or review.
    """
    if not _memory:
        raise HTTPException(500, "Memory not initialized")

    session = _memory.get_session(session_id)
    if not session:
        raise HTTPException(404, f"Session not found: {session_id}")

    replay_data = _memory.get_replay_data(session_id)

    entries = []
    for entry in replay_data[:limit]:
        obstacles = []
        scene_data = entry.get("scene", {})
        for obs_data in scene_data.get("obstacles", []):
            obstacles.append(ObstacleSchema(
                id=obs_data.get("id", ""),
                **{"class": obs_data.get("class", "unknown")},
                distance_m=obs_data.get("distance_m", 0),
                direction=DirectionType(obs_data.get("direction", "ahead")),
                direction_deg=obs_data.get("direction_deg", 0),
                priority=PriorityLevel(obs_data.get("priority", "safe")),
                confidence=obs_data.get("confidence", 0),
                action=obs_data.get("action", ""),
            ))

        from datetime import datetime
        entries.append(SessionReplayEntry(
            timestamp=datetime.fromisoformat(entry["timestamp_human"]),
            obstacles=obstacles,
            question=entry.get("question"),
            answer=entry.get("answer"),
        ))

    from datetime import datetime
    session_info = SessionInfo(
        id=session.id,
        created_at=datetime.fromtimestamp(session.created_at),
        last_active=datetime.fromtimestamp(session.last_active),
        entry_count=session.entry_count,
        critical_count=session.critical_count,
        duration_sec=session.last_active - session.created_at,
    )

    return SessionReplayResponse(
        session=session_info,
        entries=entries,
        total_entries=len(replay_data),
    )


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its data."""
    if not _memory:
        raise HTTPException(500, "Memory not initialized")

    if not _memory.get_session(session_id):
        raise HTTPException(404, f"Session not found: {session_id}")

    _memory.clear_session(session_id)
    return {"status": "deleted", "session_id": session_id}


# ============================================================================
# Health/Status Endpoints
# ============================================================================

@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Check system health."""
    avg_latency = 0.0
    if _metrics["perception_times"]:
        avg_latency = sum(_metrics["perception_times"]) / len(_metrics["perception_times"])

    return HealthStatus(
        status="healthy" if _perception else "degraded",
        perception_ready=_perception is not None,
        llm_ready=_reasoner is not None and _reasoner._llm is not None,
        memory_entries=len(_memory._entries) if _memory else 0,
        active_sessions=len(_memory.list_sessions()) if _memory else 0,
        avg_latency_ms=avg_latency,
    )


@router.get("/metrics", response_model=PerformanceMetrics)
async def get_metrics():
    """Get performance metrics."""
    avg_perception = 0.0
    avg_vqa = 0.0

    if _metrics["perception_times"]:
        avg_perception = sum(_metrics["perception_times"]) / len(_metrics["perception_times"])
    if _metrics["vqa_times"]:
        avg_vqa = sum(_metrics["vqa_times"]) / len(_metrics["vqa_times"])

    cache_hit_rate = 0.0
    if _reasoner:
        stats = _reasoner.get_stats()
        cache_hit_rate = stats.get("cache_hit_rate", 0.0)

    return PerformanceMetrics(
        avg_perception_ms=avg_perception,
        avg_vqa_ms=avg_vqa,
        cache_hit_rate=cache_hit_rate,
        total_requests=_metrics["total_requests"],
        uptime_sec=time.time() - _start_time if _start_time else 0,
    )


# ============================================================================
# Utility Functions
# ============================================================================

def _decode_image(image_base64: str) -> Image.Image:
    """Decode base64 image to PIL Image."""
    try:
        # Remove data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        return image
    except Exception as e:
        raise ValueError(f"Invalid image data: {e}")


# ============================================================================
# Voice Ask Endpoint (POST /voice/ask)
# ============================================================================

@router.post("/voice/ask")
async def voice_ask(
    audio_base64: str = Query(..., description="Base64-encoded audio input"),
    image_base64: Optional[str] = Query(None, description="Base64-encoded image for visual context"),
    sample_rate: int = Query(16000, description="Audio sample rate"),
):
    """
    Process voice query end-to-end: STT → VQA → TTS.

    Target latencies:
    - STT: ≤100ms
    - VQA: ≤300ms
    - TTS: ≤100ms
    - Total: ≤500ms

    Returns spoken response audio and detailed telemetry.
    """
    if not VOICE_BRIDGE_AVAILABLE:
        raise HTTPException(501, "Voice bridge not available - install speech_vqa_bridge module")

    if not _voice_pipeline:
        raise HTTPException(500, "Voice pipeline not initialized")

    try:
        # Process through voice pipeline
        result = await _voice_pipeline.process_base64_audio(
            audio_base64=audio_base64,
            image_base64=image_base64,
            sample_rate=sample_rate,
        )

        return JSONResponse(content={
            "spoken_response": result.get("spoken_response", ""),
            "audio_base64": result.get("audio_base64", ""),
            "telemetry": result.get("telemetry", {}),
        })

    except asyncio.TimeoutError:
        raise HTTPException(504, "Voice request timed out")
    except Exception as e:
        logger.exception("Voice ask failed")
        raise HTTPException(500, f"Voice ask failed: {e}")


# ============================================================================
# Priority Scene Endpoint (/vqa/ask?mode=priority)
# ============================================================================

@router.post("/ask/priority")
async def ask_priority_scene(
    image_base64: str = Query(..., description="Base64-encoded image"),
    top_n: int = Query(3, ge=1, le=10, description="Number of top hazards to return"),
):
    """
    Analyze scene for top-N highest-risk hazards.

    Priority ranking based on:
    - Distance (closer = higher priority)
    - Direction (center/path = higher priority)
    - Confidence (detection quality)
    - Collision risk (estimated time to contact)

    Returns hazards in short_cue format for TTS output.
    """
    if not _perception or not _priority_analyzer:
        raise HTTPException(500, "Priority analyzer not initialized")

    start_time = time.time()

    try:
        # Decode and process image
        image = _decode_image(image_base64)

        # Run perception
        perception_result = await _perception.process(
            image,
            run_depth=True,
            run_segmentation=False,
        )

        # Convert detections to analyzer format
        detections = []
        for det in perception_result.detections:
            detections.append({
                "class": det.class_name,
                "confidence": det.confidence,
                "bbox": [det.bbox.x_min, det.bbox.y_min,
                        det.bbox.x_max, det.bbox.y_max],
                "depth": det.depth_m,
            })

        # Analyze with priority scene
        priority_result = _priority_analyzer.analyze(
            detections,
            depth_map=perception_result.depth_map,
            image_width=perception_result.image_size[0],
            image_height=perception_result.image_size[1],
            top_n=top_n,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return JSONResponse(content={
            "top_hazards": [h.to_dict() for h in priority_result.top_hazards],
            "total_detected": priority_result.total_detected,
            "highest_severity": priority_result.highest_severity.name.lower(),
            "path_clear": priority_result.path_clear,
            "navigation_cue": priority_result.navigation_cue,
            "processing_time_ms": round(elapsed_ms, 1),
        })

    except ValueError as e:
        raise HTTPException(400, f"Invalid request: {e}")
    except Exception as e:
        logger.exception("Priority scene analysis failed")
        raise HTTPException(500, f"Priority analysis failed: {e}")


# ============================================================================
# Debug Visualizer Endpoint (/perception/debug)
# ============================================================================

@router.post("/perception/debug")
async def debug_perception(
    image_base64: str = Query(..., description="Base64-encoded input image"),
    show_detections: bool = Query(True, description="Show detection bounding boxes"),
    show_depth: bool = Query(True, description="Show depth map overlay"),
    show_segmentation: bool = Query(False, description="Show segmentation overlay"),
    show_hazards: bool = Query(True, description="Show hazard annotations"),
):
    """
    Generate annotated debug image with perception outputs.

    Overlays include:
    - Bounding boxes with class labels and confidence
    - Depth values in meters
    - Segmentation masks (optional)
    - Hazard priority indicators

    Returns base64-encoded annotated image.
    """
    if not DEBUG_TOOLS_AVAILABLE:
        raise HTTPException(501, "Debug tools not available - install debug_tools module")

    if not _perception or not _debug_visualizer:
        raise HTTPException(500, "Debug visualizer not initialized")

    start_time = time.time()

    try:
        # Decode image
        image = _decode_image(image_base64)
        image_array = np.array(image)

        # Run perception
        perception_result = await _perception.process(
            image,
            run_depth=show_depth,
            run_segmentation=show_segmentation,
        )

        # Build layers list
        layers = []
        if show_depth and perception_result.depth_map is not None:
            layers.append("depth")
        if show_segmentation and perception_result.segmentation_mask is not None:
            layers.append("segmentation")
        if show_detections:
            layers.append("detections")
        if show_hazards:
            layers.append("hazards")

        # Format detections for visualizer
        detections = []
        for det in perception_result.detections:
            detections.append({
                "class": det.class_name,
                "confidence": det.confidence,
                "bbox": [det.bbox.x_min, det.bbox.y_min,
                        det.bbox.x_max, det.bbox.y_max],
                "depth": det.depth_m,
            })

        # Get hazards if requested
        hazards = None
        if show_hazards and _priority_analyzer:
            priority_result = _priority_analyzer.analyze(
                detections,
                depth_map=perception_result.depth_map,
                image_width=perception_result.image_size[0],
                image_height=perception_result.image_size[1],
            )
            hazards = [h.to_dict() for h in priority_result.top_hazards]

        # Render debug image
        debug_result = _debug_visualizer.render(
            image_array,
            detections=detections,
            depth_map=perception_result.depth_map,
            segmentation_mask=perception_result.segmentation_mask,
            hazards=hazards,
            layers=layers,
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return JSONResponse(content={
            "image_base64": debug_result.image_base64,
            "image_format": debug_result.image_format,
            "dimensions": {
                "width": debug_result.width,
                "height": debug_result.height,
            },
            "num_annotations": debug_result.num_annotations,
            "layers_rendered": debug_result.layers_rendered,
            "processing_time_ms": round(elapsed_ms, 1),
            "detections_count": len(detections),
            "hazards_count": len(hazards) if hazards else 0,
        })

    except ValueError as e:
        raise HTTPException(400, f"Invalid request: {e}")
    except Exception as e:
        logger.exception("Debug visualization failed")
        raise HTTPException(500, f"Debug visualization failed: {e}")


# ============================================================================
# Cleanup
# ============================================================================

async def cleanup_vqa_api():
    """Cleanup VQA API resources."""
    global _perception, _fuser, _reasoner, _memory
    global _priority_analyzer, _debug_visualizer, _voice_pipeline

    if _memory and _memory.config.persist_path:
        _memory._save_to_disk()

    _perception = None
    _fuser = None
    _reasoner = None
    _memory = None
    _priority_analyzer = None
    _debug_visualizer = None
    _voice_pipeline = None

    logger.info("VQA API cleanup complete")
