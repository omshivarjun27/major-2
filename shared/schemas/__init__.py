"""
Shared Types Module
====================

**Single source of truth** for all data structures used across
the Voice-Vision Assistant pipeline.

Every module (spatial, vqa_engine, scene_graph, etc.) MUST import
types from here rather than defining their own.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# ============================================================================
# Enums
# ============================================================================

class Priority(Enum):
    """Obstacle priority levels based on distance."""
    CRITICAL = "critical"      # < 1.0m — immediate stop/alert
    NEAR_HAZARD = "near"       # 1.0-2.0m — urgent audio cue
    FAR_HAZARD = "far"         # 2.0-5.0m — cautionary mention
    SAFE = "safe"              # > 5.0m — no action needed


class Direction(Enum):
    """Direction relative to user's centre of view."""
    FAR_LEFT = "far left"
    LEFT = "left"
    SLIGHTLY_LEFT = "slightly left"
    CENTER = "ahead"
    SLIGHTLY_RIGHT = "slightly right"
    RIGHT = "right"
    FAR_RIGHT = "far right"


class SizeCategory(Enum):
    """Relative size of detected object in frame."""
    SMALL = "small"      # < 5 % of frame
    MEDIUM = "medium"    # 5-25 % of frame
    LARGE = "large"      # > 25 % of frame


class SpatialRelation(Enum):
    """Spatial relationships between objects."""
    LEFT_OF = "left of"
    RIGHT_OF = "right of"
    ABOVE = "above"
    BELOW = "below"
    IN_FRONT_OF = "in front of"
    BEHIND = "behind"
    NEAR = "near"
    BLOCKING = "blocking"


# ============================================================================
# Core Data Structures
# ============================================================================

@dataclass
class BoundingBox:
    """Bounding box in pixel coordinates (x1, y1, x2, y2)."""
    x1: int
    y1: int
    x2: int
    y2: int

    # ── Backward-compat aliases ──
    @property
    def x_min(self) -> int:
        return self.x1

    @property
    def y_min(self) -> int:
        return self.y1

    @property
    def x_max(self) -> int:
        return self.x2

    @property
    def y_max(self) -> int:
        return self.y2

    @classmethod
    def from_xywh(cls, x: int, y: int, w: int, h: int) -> "BoundingBox":
        """Create BoundingBox from (x, y, width, height)."""
        return cls(x1=x, y1=y, x2=x + w, y2=y + h)

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_list(self) -> List[int]:
        """Return [x1, y1, x2, y2]."""
        return [self.x1, self.y1, self.x2, self.y2]

    def to_xywh(self) -> List[int]:
        """Return [x, y, w, h]."""
        return [self.x1, self.y1, self.width, self.height]

    def clamp(self, max_width: int, max_height: int) -> "BoundingBox":
        """Clamp box to image boundaries."""
        return BoundingBox(
            x1=max(0, min(self.x1, max_width)),
            y1=max(0, min(self.y1, max_height)),
            x2=max(0, min(self.x2, max_width)),
            y2=max(0, min(self.y2, max_height)),
        )


@dataclass
class OCRWord:
    """Single OCR word with optional bounding box."""

    text: str
    confidence: float
    bbox: Optional[BoundingBox] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "bbox": self.bbox.to_list() if self.bbox else None,
        }


@dataclass
class OCRResult:
    """Aggregated OCR output for a single image."""

    full_text: str
    words: List[OCRWord] = field(default_factory=list)
    confidence: float = 0.0
    backend: str = "unknown"
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_text": self.full_text,
            "words": [word.to_dict() for word in self.words],
            "confidence": round(self.confidence, 3),
            "backend": self.backend,
            "latency_ms": round(self.latency_ms, 1),
        }


@dataclass
class Detection:
    """Single object detection result."""
    id: str
    class_name: str
    confidence: float
    bbox: BoundingBox

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "class": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": self.bbox.to_xywh(),
            "centroid_px": list(self.bbox.center),
        }


@dataclass
class SegmentationMask:
    """Edge-aware segmentation mask for a detection."""
    detection_id: str
    mask: Optional[np.ndarray] = None       # Binary mask
    boundary_confidence: float = 0.5
    edge_pixels: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "boundary_confidence": round(self.boundary_confidence, 3),
            "mask_area_px": int(np.sum(self.mask)) if self.mask is not None else 0,
        }


@dataclass
class DepthMap:
    """Depth estimation result.

    ``get_region_depth`` returns ``(min, median, max)`` — the canonical
    three-stat tuple used everywhere in the pipeline.
    """
    depth_array: np.ndarray = None  # H × W depth values
    min_depth: float = 0.0
    max_depth: float = 10.0
    is_metric: bool = False         # True → values are calibrated metres

    # ── Alias support ──
    @classmethod
    def create(cls, depth_array=None, data=None, **kwargs):
        """Factory supporting both ``depth_array`` and ``data`` field names."""
        arr = depth_array if depth_array is not None else data
        return cls(depth_array=arr, **kwargs)

    @property
    def data(self) -> np.ndarray:
        """Alias for ``depth_array`` (backward compat)."""
        return self.depth_array

    @data.setter
    def data(self, value: np.ndarray):
        self.depth_array = value

    def get_depth_at(self, x: int, y: int) -> float:
        """Get depth value at pixel (x, y)."""
        if self.depth_array is not None and 0 <= y < self.depth_array.shape[0] and 0 <= x < self.depth_array.shape[1]:
            return float(self.depth_array[y, x])
        return float("inf")

    def get_region_depth(self, bbox: BoundingBox) -> Tuple[float, float, float]:
        """Get (min, median, max) depth within bounding box.

        This is the canonical return signature.  Code that previously
        expected ``(min, max, mean)`` should migrate.
        """
        if self.depth_array is None:
            return float("inf"), float("inf"), float("inf")
        y1 = max(0, bbox.y1)
        y2 = min(self.depth_array.shape[0], bbox.y2)
        x1 = max(0, bbox.x1)
        x2 = min(self.depth_array.shape[1], bbox.x2)
        if y2 <= y1 or x2 <= x1:
            return float("inf"), float("inf"), float("inf")
        region = self.depth_array[y1:y2, x1:x2]
        if region.size == 0:
            return float("inf"), float("inf"), float("inf")
        return float(np.min(region)), float(np.median(region)), float(np.max(region))


@dataclass
class PerceptionResult:
    """Combined perception pipeline output."""
    detections: List[Detection]
    masks: List[SegmentationMask]
    depth_map: DepthMap
    image_size: Tuple[int, int]  # (width, height)
    latency_ms: float
    timestamp: str
    frame_id: str = ""                # Unique frame identifier
    timestamp_epoch_ms: float = 0.0   # High-res epoch timestamp (ms)


@dataclass
class ObstacleRecord:
    """Fused spatial obstacle data (detection + segmentation + depth)."""
    id: str
    class_name: str
    bbox: BoundingBox
    centroid_px: Tuple[int, int]
    distance_m: float
    direction: Direction
    direction_deg: float               # Angle from centre (−45 … +45)
    mask_confidence: float
    detection_confidence: float        # Canonical field name
    priority: Priority
    size_category: Union[SizeCategory, str]
    action_recommendation: str

    # Backward-compat alias
    @property
    def detection_score(self) -> float:
        return self.detection_confidence

    def to_dict(self) -> Dict[str, Any]:
        sc = self.size_category.value if isinstance(self.size_category, SizeCategory) else self.size_category
        return {
            "id": self.id,
            "class": self.class_name,
            "bbox": self.bbox.to_xywh(),
            "centroid_px": list(self.centroid_px),
            "distance_m": round(self.distance_m, 2),
            "direction": self.direction.value,
            "direction_deg": round(self.direction_deg, 1),
            "mask_confidence": round(self.mask_confidence, 3),
            "confidence": round(self.detection_confidence, 3),
            "priority": self.priority.value,
            "size_category": sc,
            "action_recommendation": self.action_recommendation,
        }


@dataclass
class NavigationOutput:
    """Navigation cue output formats."""
    short_cue: str            # Brief TTS message
    verbose_description: str  # Detailed narration
    telemetry: List[Dict]     # JSON telemetry for downstream
    has_critical: bool        # Whether critical obstacles exist

    def to_dict(self) -> Dict[str, Any]:
        return {
            "short_cue": self.short_cue,
            "verbose_description": self.verbose_description,
            "telemetry": self.telemetry,
            "has_critical": self.has_critical,
        }


# ============================================================================
# Abstract Base Classes for Pipeline Stages
# ============================================================================

class ObjectDetector(ABC):
    """Abstract base class for object detection."""

    @abstractmethod
    async def detect(self, image: Any) -> List[Detection]:
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


class Segmenter(ABC):
    """Abstract base class for segmentation."""

    @abstractmethod
    async def segment(self, image: Any, detections: List[Detection]) -> List[SegmentationMask]:
        pass


class DepthEstimator(ABC):
    """Abstract base class for depth estimation."""

    @abstractmethod
    async def estimate(self, image: Any) -> DepthMap:
        pass
