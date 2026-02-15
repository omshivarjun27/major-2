"""
VQA Engine - Scene Graph Module
===============================

Converts raw perception outputs (detections, masks, depth) into
structured scene graphs with spatial relationships and obstacle records.

All core data types are imported from ``shared`` — do NOT redefine them here.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Canonical types from shared module ────────────────────────────────────
from shared.schemas import (  # noqa: F401  – re-exported for backward compat
    BoundingBox,
    Detection,
    SegmentationMask,
    DepthMap,
    PerceptionResult,
    Priority,
    Direction,
    SizeCategory,
    SpatialRelation,
    ObstacleRecord,
)

logger = logging.getLogger("vqa-scene-graph")


# ============================================================================
# Scene-Graph–specific Data Structures
# ============================================================================

# Note: ObstacleRecord.to_dict() is defined in shared/__init__.py


# ── Helpers formerly on the local ObstacleRecord ──

def obstacle_to_speech(obs: ObstacleRecord) -> str:
    """Generate TTS-friendly description of an obstacle."""
    dist_str = _format_distance(obs.distance_m)
    return f"{obs.class_name} {dist_str} {obs.direction.value}"


def _format_distance(d: float) -> str:
    """Format distance for natural speech."""
    if d < 1.0:
        return "very close" if d < 0.5 else "half meter"
    elif d < 2.0:
        return f"{d:.1f} meters"
    else:
        return f"{int(round(d))} meters"


@dataclass
class SceneNode:
    """
    Node in the scene graph representing a detected entity.
    Contains spatial and semantic information.
    """
    id: str
    class_name: str
    bbox: BoundingBox
    centroid: Tuple[int, int]
    depth: float
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: List[Tuple[str, "SceneNode"]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "class": self.class_name,
            "bbox": self.bbox.to_xywh(),
            "centroid": list(self.centroid),
            "depth": round(self.depth, 2),
            "confidence": round(self.confidence, 3),
            "attributes": self.attributes,
            "relations": [(r[0], r[1].id) for r in self.relations],
        }


@dataclass
class SceneGraph:
    """
    Complete scene graph with nodes and spatial relationships.
    Used as input to VQA reasoning.
    """
    nodes: List[SceneNode]
    obstacles: List[ObstacleRecord]
    image_size: Tuple[int, int]
    timestamp: str
    summary: str = ""
    frame_id: str = ""                # Linked frame identifier
    timestamp_epoch_ms: float = 0.0   # High-res epoch timestamp (ms)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "obstacles": [o.to_dict() for o in self.obstacles],
            "image_size": list(self.image_size),
            "timestamp": self.timestamp,
            "frame_id": self.frame_id,
            "timestamp_epoch_ms": self.timestamp_epoch_ms,
            "summary": self.summary,
            "obstacle_count": len(self.obstacles),
            "has_critical": any(o.priority == Priority.CRITICAL for o in self.obstacles),
        }
    
    def get_closest_obstacle(self) -> Optional[ObstacleRecord]:
        """Get the closest (most critical) obstacle."""
        if not self.obstacles:
            return None
        return min(self.obstacles, key=lambda o: o.distance_m)
    
    def get_critical_obstacles(self) -> List[ObstacleRecord]:
        """Get all critical obstacles."""
        return [o for o in self.obstacles if o.priority == Priority.CRITICAL]
    
    def generate_summary(self) -> str:
        """Generate natural language summary of the scene."""
        if not self.obstacles:
            return "The path ahead appears clear with no obstacles detected."
        
        critical = self.get_critical_obstacles()
        if critical:
            closest = critical[0]
            return f"Warning: {closest.class_name} detected {_format_distance(closest.distance_m)} {closest.direction.value}. {closest.action_recommendation}."
        
        closest = self.get_closest_obstacle()
        if closest:
            return f"{len(self.obstacles)} object(s) detected. Closest: {closest.class_name} {_format_distance(closest.distance_m)} {closest.direction.value}."
        
        return "Scene analyzed."


# ============================================================================
# Scene Graph Builder
# ============================================================================

class SceneGraphBuilder:
    """
    Builds scene graphs from perception results.
    Handles coordinate transforms, relationship inference, and prioritization.
    """
    
    # Camera FOV assumption for direction calculation
    HORIZONTAL_FOV = 70.0  # degrees
    
    # Priority thresholds (meters)
    CRITICAL_THRESHOLD = 1.0
    NEAR_THRESHOLD = 2.0
    FAR_THRESHOLD = 5.0
    
    def __init__(self, image_width: int = 640, image_height: int = 480):
        self._img_width = image_width
        self._img_height = image_height
    
    def build(self, perception: PerceptionResult) -> SceneGraph:
        """Build scene graph from perception result."""
        self._img_width, self._img_height = perception.image_size
        
        # Create mask lookup
        mask_lookup = {m.detection_id: m for m in perception.masks}
        
        # Build obstacle records
        obstacles = []
        nodes = []
        
        for det in perception.detections:
            # Get depth for this detection
            _, median_depth, _ = perception.depth_map.get_region_depth(det.bbox)
            
            # Handle invalid depth
            if median_depth == float('inf') or median_depth > 100:
                # Estimate from y-position (bottom = closer)
                cy = det.bbox.center[1]
                median_depth = 0.5 + (1 - cy / self._img_height) * 9.5
            
            # Get mask confidence
            mask = mask_lookup.get(det.id)
            mask_conf = mask.boundary_confidence if mask else 0.5
            
            # Calculate direction
            direction, angle = self._calculate_direction(det.bbox.center[0])
            
            # Calculate priority
            priority = self._calculate_priority(median_depth)
            
            # Calculate size category
            size_cat = self._calculate_size(det.bbox)
            
            # Generate action
            action = self._generate_action(direction, median_depth, priority)
            
            # Create obstacle record
            obstacle = ObstacleRecord(
                id=det.id,
                class_name=det.class_name,
                bbox=det.bbox,
                centroid_px=det.bbox.center,
                distance_m=median_depth,
                direction=direction,
                direction_deg=angle,
                mask_confidence=mask_conf,
                detection_confidence=det.confidence,
                priority=priority,
                size_category=size_cat,
                action_recommendation=action,
            )
            obstacles.append(obstacle)
            
            # Create scene node
            node = SceneNode(
                id=det.id,
                class_name=det.class_name,
                bbox=det.bbox,
                centroid=det.bbox.center,
                depth=median_depth,
                confidence=det.confidence,
                attributes={
                    "priority": priority.value,
                    "size": size_cat.value,
                    "direction": direction.value,
                },
            )
            nodes.append(node)
        
        # Sort obstacles by priority then distance
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.NEAR_HAZARD: 1,
            Priority.FAR_HAZARD: 2,
            Priority.SAFE: 3,
        }
        obstacles.sort(key=lambda o: (priority_order[o.priority], o.distance_m))
        
        # Infer spatial relations between nodes
        self._infer_relations(nodes)
        
        # Build scene graph
        scene_graph = SceneGraph(
            nodes=nodes,
            obstacles=obstacles,
            image_size=perception.image_size,
            timestamp=perception.timestamp,
            frame_id=getattr(perception, 'frame_id', ''),
            timestamp_epoch_ms=getattr(perception, 'timestamp_epoch_ms', 0.0),
        )
        scene_graph.summary = scene_graph.generate_summary()
        
        return scene_graph
    
    def _calculate_direction(self, center_x: int) -> Tuple[Direction, float]:
        """Calculate direction and angle from image center."""
        # Normalize to -1 to 1
        normalized_x = (center_x - self._img_width / 2) / (self._img_width / 2)
        
        # Calculate angle
        angle = normalized_x * (self.HORIZONTAL_FOV / 2)
        
        # Determine direction category
        if angle < -25:
            direction = Direction.FAR_LEFT
        elif angle < -15:
            direction = Direction.LEFT
        elif angle < -5:
            direction = Direction.SLIGHTLY_LEFT
        elif angle < 5:
            direction = Direction.CENTER
        elif angle < 15:
            direction = Direction.SLIGHTLY_RIGHT
        elif angle < 25:
            direction = Direction.RIGHT
        else:
            direction = Direction.FAR_RIGHT
        
        return direction, angle
    
    def _calculate_priority(self, distance: float) -> Priority:
        """Determine priority based on distance."""
        if distance < self.CRITICAL_THRESHOLD:
            return Priority.CRITICAL
        elif distance < self.NEAR_THRESHOLD:
            return Priority.NEAR_HAZARD
        elif distance < self.FAR_THRESHOLD:
            return Priority.FAR_HAZARD
        else:
            return Priority.SAFE
    
    def _calculate_size(self, bbox: BoundingBox) -> SizeCategory:
        """Categorize object size relative to frame."""
        area_ratio = bbox.area / (self._img_width * self._img_height)
        if area_ratio > 0.25:
            return SizeCategory.LARGE
        elif area_ratio > 0.05:
            return SizeCategory.MEDIUM
        else:
            return SizeCategory.SMALL
    
    def _generate_action(self, direction: Direction, distance: float, priority: Priority) -> str:
        """Generate action recommendation."""
        if priority == Priority.SAFE:
            return "safe to proceed"
        
        if priority == Priority.CRITICAL:
            prefix = "stop, "
        elif priority == Priority.NEAR_HAZARD:
            prefix = ""
        else:
            prefix = "be aware, "
        
        if direction in [Direction.FAR_LEFT, Direction.LEFT, Direction.SLIGHTLY_LEFT]:
            return f"{prefix}step right"
        elif direction in [Direction.FAR_RIGHT, Direction.RIGHT, Direction.SLIGHTLY_RIGHT]:
            return f"{prefix}step left"
        else:
            if priority == Priority.CRITICAL:
                return "stop and reassess"
            return "proceed with caution"
    
    def _infer_relations(self, nodes: List[SceneNode]):
        """Infer spatial relationships between nodes."""
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                # Check horizontal relationship
                if node_a.centroid[0] < node_b.centroid[0] - 50:
                    node_a.relations.append((SpatialRelation.LEFT_OF.value, node_b))
                    node_b.relations.append((SpatialRelation.RIGHT_OF.value, node_a))
                elif node_a.centroid[0] > node_b.centroid[0] + 50:
                    node_a.relations.append((SpatialRelation.RIGHT_OF.value, node_b))
                    node_b.relations.append((SpatialRelation.LEFT_OF.value, node_a))
                
                # Check depth relationship
                if abs(node_a.depth - node_b.depth) > 1.0:
                    if node_a.depth < node_b.depth:
                        node_a.relations.append((SpatialRelation.IN_FRONT_OF.value, node_b))
                        node_b.relations.append((SpatialRelation.BEHIND.value, node_a))
                    else:
                        node_a.relations.append((SpatialRelation.BEHIND.value, node_b))
                        node_b.relations.append((SpatialRelation.IN_FRONT_OF.value, node_a))
                
                # Check proximity
                dist = ((node_a.centroid[0] - node_b.centroid[0])**2 + 
                       (node_a.centroid[1] - node_b.centroid[1])**2) ** 0.5
                if dist < 100:
                    node_a.relations.append((SpatialRelation.NEAR.value, node_b))
                    node_b.relations.append((SpatialRelation.NEAR.value, node_a))


def build_scene_graph(perception: PerceptionResult) -> SceneGraph:
    """Convenience function to build scene graph from perception result."""
    builder = SceneGraphBuilder(*perception.image_size)
    return builder.build(perception)
