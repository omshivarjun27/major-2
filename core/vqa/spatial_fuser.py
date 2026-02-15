"""
VQA Engine - Spatial Fusion Module
===================================

Combines detection, segmentation, and depth outputs with temporal
filtering for smooth, reliable obstacle tracking.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Canonical types from shared module ────────────────────────────────────
from shared.schemas import (
    BoundingBox,
    Detection,
    SegmentationMask,
    DepthMap,
    PerceptionResult,
    ObstacleRecord,
    Priority,
    Direction,
)

logger = logging.getLogger("vqa-spatial-fuser")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class FusionConfig:
    """Configuration for spatial fusion pipeline."""
    
    # Temporal filter settings
    temporal_window_sec: float = 0.5      # Sliding window for smoothing
    min_track_confidence: float = 0.3     # Minimum confidence to track
    max_velocity_m_per_sec: float = 5.0   # Maximum expected movement speed
    
    # IOU matching settings
    iou_threshold: float = 0.3            # Minimum IOU for matching
    
    # Depth fusion settings
    depth_weight: float = 0.6             # Weight for depth in fusion
    mask_weight: float = 0.4              # Weight for segmentation
    
    # Safety margins (meters)
    critical_margin: float = 0.3          # Extra margin for critical zone
    
    # Max tracks to maintain
    max_tracks: int = 20


# ============================================================================
# Tracked Object
# ============================================================================

@dataclass
class TrackedObject:
    """
    Persistent tracking record for a detected object.
    Maintains history for temporal filtering.
    """
    id: str
    class_name: str
    first_seen: float
    last_seen: float
    
    # History (most recent first)
    bbox_history: List[BoundingBox] = field(default_factory=list)
    depth_history: List[float] = field(default_factory=list)
    confidence_history: List[float] = field(default_factory=list)
    
    # Smoothed values
    smoothed_depth: float = 0.0
    smoothed_confidence: float = 0.0
    velocity_estimate: Tuple[float, float] = (0.0, 0.0)  # px/sec, m/sec
    
    hits: int = 0
    misses: int = 0
    
    def update(self, detection: Detection, depth: float, timestamp: float):
        """Update track with new measurement."""
        self.last_seen = timestamp
        self.hits += 1
        self.misses = 0
        
        # Add to history (limit to 10 frames)
        self.bbox_history.insert(0, detection.bbox)
        self.depth_history.insert(0, depth)
        self.confidence_history.insert(0, detection.confidence)
        
        if len(self.bbox_history) > 10:
            self.bbox_history = self.bbox_history[:10]
            self.depth_history = self.depth_history[:10]
            self.confidence_history = self.confidence_history[:10]
        
        # Update smoothed values with exponential moving average
        alpha = 0.7  # Smoothing factor
        if len(self.depth_history) == 1:
            self.smoothed_depth = depth
            self.smoothed_confidence = detection.confidence
        else:
            self.smoothed_depth = alpha * depth + (1 - alpha) * self.smoothed_depth
            self.smoothed_confidence = alpha * detection.confidence + (1 - alpha) * self.smoothed_confidence
        
        # Estimate velocity if enough history
        if len(self.bbox_history) >= 2:
            dt = max(0.001, self.last_seen - self.first_seen) / len(self.bbox_history)
            dx = self.bbox_history[0].center[0] - self.bbox_history[1].center[0]
            dd = self.depth_history[0] - self.depth_history[1]
            self.velocity_estimate = (dx / dt, dd / dt)
    
    def predict_position(self, dt: float) -> Tuple[int, int]:
        """Predict bbox center after dt seconds."""
        if not self.bbox_history:
            return (0, 0)
        cx, cy = self.bbox_history[0].center
        vx, _ = self.velocity_estimate
        return (int(cx + vx * dt), cy)
    
    def mark_missed(self):
        """Mark frame where track was not matched."""
        self.misses += 1
    
    def is_stale(self, current_time: float, max_age: float = 0.5) -> bool:
        """Check if track is too old."""
        return current_time - self.last_seen > max_age or self.misses > 3
    
    def get_current_bbox(self) -> Optional[BoundingBox]:
        """Get most recent bounding box."""
        return self.bbox_history[0] if self.bbox_history else None


# ============================================================================
# Temporal Filter
# ============================================================================

class TemporalFilter:
    """
    Applies temporal smoothing to perception outputs.
    Reduces jitter and improves tracking stability.
    """
    
    def __init__(self, config: FusionConfig):
        self.config = config
        self._tracks: Dict[str, TrackedObject] = {}
        self._next_id = 0
    
    def update(
        self,
        detections: List[Detection],
        depth_map: DepthMap,
        timestamp: float,
    ) -> List[TrackedObject]:
        """
        Update tracks with new detections.
        Returns currently active tracks.
        """
        # Remove stale tracks
        stale_ids = [
            tid for tid, track in self._tracks.items()
            if track.is_stale(timestamp)
        ]
        for tid in stale_ids:
            del self._tracks[tid]
        
        # Match detections to existing tracks
        matched_tracks, unmatched_detections = self._match_detections(
            detections, timestamp
        )
        
        # Update matched tracks
        for track, det in matched_tracks:
            _, depth, _ = depth_map.get_region_depth(det.bbox)
            track.update(det, depth, timestamp)
        
        # Create new tracks for unmatched detections
        for det in unmatched_detections:
            if det.confidence >= self.config.min_track_confidence:
                _, depth, _ = depth_map.get_region_depth(det.bbox)
                track_id = f"track_{self._next_id}"
                self._next_id += 1
                
                track = TrackedObject(
                    id=track_id,
                    class_name=det.class_name,
                    first_seen=timestamp,
                    last_seen=timestamp,
                )
                track.update(det, depth, timestamp)
                self._tracks[track_id] = track
        
        # Mark missed tracks
        matched_track_ids = {t.id for t, _ in matched_tracks}
        for tid, track in self._tracks.items():
            if tid not in matched_track_ids:
                track.mark_missed()
        
        # Limit total tracks
        if len(self._tracks) > self.config.max_tracks:
            sorted_tracks = sorted(
                self._tracks.items(),
                key=lambda x: (x[1].misses, -x[1].smoothed_confidence),
            )
            for tid, _ in sorted_tracks[self.config.max_tracks:]:
                del self._tracks[tid]
        
        return list(self._tracks.values())
    
    def _match_detections(
        self,
        detections: List[Detection],
        timestamp: float,
    ) -> Tuple[List[Tuple[TrackedObject, Detection]], List[Detection]]:
        """Match detections to existing tracks using IOU."""
        matched = []
        unmatched_dets = list(detections)
        
        # Sort tracks by confidence (match confident ones first)
        sorted_tracks = sorted(
            self._tracks.values(),
            key=lambda t: t.smoothed_confidence,
            reverse=True,
        )
        
        for track in sorted_tracks:
            if not unmatched_dets:
                break
            
            best_iou = 0.0
            best_det = None
            best_idx = -1
            
            # Predict where track should be
            dt = timestamp - track.last_seen
            predicted_center = track.predict_position(dt)
            
            for i, det in enumerate(unmatched_dets):
                # Must be same class
                if det.class_name != track.class_name:
                    continue
                
                # Calculate IOU with current bbox
                current_bbox = track.get_current_bbox()
                if current_bbox:
                    iou = self._calculate_iou(current_bbox, det.bbox)
                    if iou > best_iou:
                        best_iou = iou
                        best_det = det
                        best_idx = i
            
            if best_det and best_iou >= self.config.iou_threshold:
                matched.append((track, best_det))
                unmatched_dets.pop(best_idx)
        
        return matched, unmatched_dets
    
    @staticmethod
    def _calculate_iou(box1: BoundingBox, box2: BoundingBox) -> float:
        """Calculate Intersection over Union of two bounding boxes."""
        x1 = max(box1.x_min, box2.x_min)
        y1 = max(box1.y_min, box2.y_min)
        x2 = min(box1.x_max, box2.x_max)
        y2 = min(box1.y_max, box2.y_max)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        union = box1.area + box2.area - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def reset(self):
        """Clear all tracks."""
        self._tracks.clear()
        self._next_id = 0


# ============================================================================
# Spatial Fuser
# ============================================================================

class SpatialFuser:
    """
    Main fusion class that combines detection, segmentation, and depth
    with temporal filtering.
    
    Usage:
        fuser = SpatialFuser()
        fused_result = fuser.fuse(perception_result)
    """
    
    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()
        self._temporal_filter = TemporalFilter(self.config)
        self._last_fusion_time = 0.0
    
    def fuse(
        self,
        perception: PerceptionResult,
        apply_temporal: bool = True,
    ) -> "FusedResult":
        """
        Fuse perception outputs into unified spatial representation.
        
        Args:
            perception: Raw perception outputs
            apply_temporal: Whether to apply temporal smoothing
            
        Returns:
            FusedResult with smoothed obstacles and metrics
        """
        timestamp = time.time()
        dt = timestamp - self._last_fusion_time
        self._last_fusion_time = timestamp
        
        # Create mask lookup
        mask_lookup = {m.detection_id: m for m in perception.masks}
        
        # Apply temporal filtering if enabled
        if apply_temporal:
            tracks = self._temporal_filter.update(
                perception.detections,
                perception.depth_map,
                timestamp,
            )
        else:
            tracks = None
        
        # Build fused obstacles
        fused_obstacles = []
        
        for det in perception.detections:
            # Get depth info
            min_depth, median_depth, depth_var = perception.depth_map.get_region_depth(det.bbox)
            
            # Get mask info
            mask = mask_lookup.get(det.id)
            mask_conf = mask.boundary_confidence if mask else 0.5
            
            # Apply depth weight
            combined_depth = median_depth
            
            # Apply temporal smoothing if track exists
            track_match = None
            if tracks:
                for track in tracks:
                    if track.class_name == det.class_name:
                        track_bbox = track.get_current_bbox()
                        if track_bbox:
                            iou = self._temporal_filter._calculate_iou(track_bbox, det.bbox)
                            if iou > 0.5:
                                track_match = track
                                break
            
            if track_match:
                combined_depth = track_match.smoothed_depth
                combined_conf = track_match.smoothed_confidence
            else:
                combined_conf = det.confidence
            
            # Calculate fused confidence
            fused_conf = (
                self.config.depth_weight * (1.0 - min(depth_var, 1.0)) +
                self.config.mask_weight * mask_conf
            ) * combined_conf
            
            # Determine if uncertain (for safety warnings)
            is_uncertain = (
                combined_conf < 0.4 or
                depth_var > 2.0 or
                mask_conf < 0.3
            )
            
            # Create fused obstacle
            fused = FusedObstacle(
                id=det.id,
                class_name=det.class_name,
                bbox=det.bbox,
                depth_m=combined_depth,
                depth_variance=depth_var,
                fused_confidence=fused_conf,
                mask_confidence=mask_conf,
                is_uncertain=is_uncertain,
                track_id=track_match.id if track_match else None,
            )
            fused_obstacles.append(fused)
        
        # Sort by depth (closest first)
        fused_obstacles.sort(key=lambda o: o.depth_m)
        
        return FusedResult(
            obstacles=fused_obstacles,
            tracks=tracks or [],
            frame_dt=dt,
            timestamp=timestamp,
            perception=perception,
        )
    
    def reset(self):
        """Reset temporal state."""
        self._temporal_filter.reset()


# ============================================================================
# Fused Data Structures
# ============================================================================

@dataclass
class FusedObstacle:
    """
    Obstacle with fused depth, mask, and tracking information.
    """
    id: str
    class_name: str
    bbox: BoundingBox
    depth_m: float
    depth_variance: float
    fused_confidence: float
    mask_confidence: float
    is_uncertain: bool
    track_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "class": self.class_name,
            "bbox": self.bbox.to_xywh(),
            "depth_m": round(self.depth_m, 2),
            "depth_variance": round(self.depth_variance, 3),
            "fused_confidence": round(self.fused_confidence, 3),
            "mask_confidence": round(self.mask_confidence, 3),
            "is_uncertain": self.is_uncertain,
            "track_id": self.track_id,
        }
    
    def get_priority(self) -> Priority:
        """Determine priority based on depth."""
        if self.depth_m < 1.0:
            return Priority.CRITICAL
        elif self.depth_m < 2.0:
            return Priority.NEAR_HAZARD
        elif self.depth_m < 5.0:
            return Priority.FAR_HAZARD
        return Priority.SAFE


@dataclass
class FusedResult:
    """
    Complete result of spatial fusion.
    """
    obstacles: List[FusedObstacle]
    tracks: List[TrackedObject]
    frame_dt: float
    timestamp: float
    perception: PerceptionResult
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "obstacles": [o.to_dict() for o in self.obstacles],
            "track_count": len(self.tracks),
            "frame_dt_ms": round(self.frame_dt * 1000, 1),
            "timestamp": self.timestamp,
            "has_uncertain": any(o.is_uncertain for o in self.obstacles),
        }
    
    def get_closest(self) -> Optional[FusedObstacle]:
        """Get closest obstacle."""
        return self.obstacles[0] if self.obstacles else None
    
    def get_critical(self) -> List[FusedObstacle]:
        """Get critical obstacles (< 1m)."""
        return [o for o in self.obstacles if o.get_priority() == Priority.CRITICAL]
    
    def generate_safety_prefix(self) -> str:
        """Generate safety prefix for uncertain situations."""
        if any(o.is_uncertain for o in self.obstacles[:3]):  # Check top 3 closest
            return "Possible: "
        return ""
