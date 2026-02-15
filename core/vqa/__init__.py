"""
VQA Engine - Visual Question Answering Subsystem
================================================

A complete, low-latency VQA system integrating:
- Perception (detection, edge-aware segmentation, depth estimation)
- Spatial fusion and scene graph generation
- VQA reasoning with qwen3-vl
- Memory for context persistence
- Real-time API endpoints

Target latencies:
- STT→LLM: ≤100ms
- Vision pipeline: ≤300ms
- LLM→TTS: ≤100ms
- Total E2E: ≤500ms (fast mode)

Author: Voice-Vision Assistant Team
"""

from .perception import (
    MockObjectDetector,
    YOLODetector,
    EdgeAwareSegmenter,
    SimpleDepthEstimator,
    MiDaSDepthEstimator,
    PerceptionPipeline,
    create_pipeline as create_perception_pipeline,
    create_detector as create_object_detector,
    create_depth_estimator,
)

# ── Canonical types re-exported from shared ─────────────────────────────
from shared.schemas import (
    ObjectDetector,
    Segmenter,
    DepthEstimator,
    Detection,
    SegmentationMask,
    DepthMap,
    BoundingBox,
    PerceptionResult,
    ObstacleRecord,
    Priority,
    Direction,
    SizeCategory,
    SpatialRelation,
    NavigationOutput,
)

from .scene_graph import (
    SceneGraph,
    SceneNode,
    SceneGraphBuilder,
    build_scene_graph,
    obstacle_to_speech,
)
from .spatial_fuser import (
    SpatialFuser,
    FusionConfig,
    TemporalFilter,
    TrackedObject,
    FusedObstacle,
    FusedResult,
)
from .vqa_reasoner import (
    VQAReasoner,
    MicroNavFormatter,
    PromptTemplates,
    VQARequest,
    VQAResponse,
    QuickAnswers,
)
from .memory import (
    VQAMemory,
    SceneEntry,
    MemoryConfig,
    Session,
)
from .priority_scene import (
    PrioritySceneAnalyzer,
    Hazard,
    PrioritySceneResult,
    HazardSeverity,
    DirectionZone,
    analyze_priority_scene,
    get_top_hazards,
)
from .api_schema import (
    PerceptionFrameRequest,
    PerceptionFrameResponse,
    VQAAskRequest,
    VQAAskResponse,
    SessionReplayResponse,
    HealthStatus,
    PerformanceMetrics,
    ObstacleSchema,
    DetectionSchema,
    PriorityLevel,
    DirectionType,
)
from .api_endpoints import (
    router as vqa_router,
    init_vqa_api,
    cleanup_vqa_api,
    get_router,
)

__version__ = "1.0.0"
__all__ = [
    # Perception
    "ObjectDetector",
    "MockObjectDetector",
    "YOLODetector",
    "EdgeAwareSegmenter",
    "SimpleDepthEstimator",
    "MiDaSDepthEstimator",
    "PerceptionPipeline",
    "Detection",
    "SegmentationMask",
    "DepthMap",
    "BoundingBox",
    "PerceptionResult",
    "create_perception_pipeline",
    "create_object_detector",
    "create_depth_estimator",
    # Scene Graph
    "SceneGraph",
    "SceneNode",
    "SceneGraphBuilder",
    "ObstacleRecord",
    "Priority",
    "Direction",
    "SizeCategory",
    "SpatialRelation",
    "NavigationOutput",
    "build_scene_graph",
    "obstacle_to_speech",
    # Spatial Fusion
    "SpatialFuser",
    "FusionConfig",
    "TemporalFilter",
    "TrackedObject",
    "FusedObstacle",
    "FusedResult",
    # VQA Reasoning
    "VQAReasoner",
    "MicroNavFormatter",
    "PromptTemplates",
    "VQARequest",
    "VQAResponse",
    "QuickAnswers",
    # Memory
    "VQAMemory",
    "SceneEntry",
    "MemoryConfig",
    "Session",
    # Priority Scene
    "PrioritySceneAnalyzer",
    "Hazard",
    "PrioritySceneResult",
    "HazardSeverity",
    "DirectionZone",
    "analyze_priority_scene",
    "get_top_hazards",
    # API Schemas
    "PerceptionFrameRequest",
    "PerceptionFrameResponse",
    "VQAAskRequest",
    "VQAAskResponse",
    "SessionReplayResponse",
    "HealthStatus",
    "PerformanceMetrics",
    "ObstacleSchema",
    "DetectionSchema",
    "PriorityLevel",
    "DirectionType",
    # API Endpoints
    "vqa_router",
    "init_vqa_api",
    "cleanup_vqa_api",
    "get_router",
]
