"""
Shared Types Module
====================

**Single source of truth** for all data structures used across
the Voice-Vision Assistant pipeline.

Every module (spatial, vqa_engine, scene_graph, etc.) MUST import
types from ``shared.schemas`` rather than defining their own.

This ``__init__`` re-exports the canonical symbols so that legacy
``from shared import X`` references continue to resolve.
"""

from shared.schemas import (  # noqa: F401
    BoundingBox,
    DepthEstimator,
    DepthMap,
    Detection,
    Direction,
    NavigationOutput,
    ObjectDetector,
    ObstacleRecord,
    OCRResult,
    OCRWord,
    PerceptionResult,
    Priority,
    ReasoningResult,
    SegmentationMask,
    Segmenter,
    SizeCategory,
    SpatialRelation,
    Verbosity,
)

__all__ = [
    # Enums
    "Direction",
    "Priority",
    "SizeCategory",
    "SpatialRelation",
    "Verbosity",
    # Core data structures
    "BoundingBox",
    "DepthMap",
    "Detection",
    "NavigationOutput",
    "ObstacleRecord",
    "OCRResult",
    "OCRWord",
    "PerceptionResult",
    "ReasoningResult",
    "SegmentationMask",
    # Abstract base classes
    "DepthEstimator",
    "ObjectDetector",
    "Segmenter",
]
