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

# ── Canonical types re-exported from shared ─────────────────────────────
from shared.schemas import (
    BoundingBox,
    DepthEstimator,
    DepthMap,
    Detection,
    Direction,
    NavigationOutput,
    ObjectDetector,
    ObstacleRecord,
    PerceptionResult,
    Priority,
    SegmentationMask,
    Segmenter,
    SizeCategory,
    SpatialRelation,
)

from .api_endpoints import (
    cleanup_vqa_api,
    get_router,
    init_vqa_api,
)
from .api_endpoints import (
    router as vqa_router,
)
from .api_schema import (
    DetectionSchema,
    DirectionType,
    HealthStatus,
    ObstacleSchema,
    PerceptionFrameRequest,
    PerceptionFrameResponse,
    PerformanceMetrics,
    PriorityLevel,
    SessionReplayResponse,
    VQAAskRequest,
    VQAAskResponse,
)
from .memory import (
    MemoryConfig,
    SceneEntry,
    Session,
    VQAMemory,
)
from .perception import (
    EdgeAwareSegmenter,
    MiDaSDepthEstimator,
    MockObjectDetector,
    PerceptionPipeline,
    SimpleDepthEstimator,
    YOLODetector,
    create_depth_estimator,
)
from .perception import (
    create_detector as create_object_detector,
)
from .perception import (
    create_pipeline as create_perception_pipeline,
)
from .priority_scene import (
    DirectionZone,
    Hazard,
    HazardSeverity,
    PrioritySceneAnalyzer,
    PrioritySceneResult,
    analyze_priority_scene,
    get_top_hazards,
)
from .scene_graph import (
    SceneGraph,
    SceneGraphBuilder,
    SceneNode,
    build_scene_graph,
    obstacle_to_speech,
)
from .spatial_fuser import (
    FusedObstacle,
    FusedResult,
    FusionConfig,
    SpatialFuser,
    TemporalFilter,
    TrackedObject,
)
from .vqa_reasoner import (
    MicroNavFormatter,
    PromptTemplates,
    QuickAnswers,
    VQAReasoner,
    VQARequest,
    VQAResponse,
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
