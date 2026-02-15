"""
Priority Scene Module
=====================

Provides hazard ranking and prioritization for navigation safety.
Returns top-3 highest-risk obstacles based on:
- Distance (closer = higher priority)
- Direction (center/path = higher priority)
- Confidence (higher detection confidence = more reliable)
- Collision risk (estimated time-to-contact)
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("priority-scene")


# ============================================================================
# Enums and Constants
# ============================================================================

class HazardSeverity(Enum):
    """Hazard severity levels."""
    CRITICAL = auto()    # Immediate danger
    HIGH = auto()        # Significant risk
    MEDIUM = auto()      # Moderate concern
    LOW = auto()         # Minor hazard
    MINIMAL = auto()     # Negligible risk


class DirectionZone(Enum):
    """Directional zones for hazard classification."""
    CENTER = "center"           # Directly ahead (most dangerous)
    LEFT_CENTER = "left-center"
    RIGHT_CENTER = "right-center"
    FAR_LEFT = "far-left"
    FAR_RIGHT = "far-right"
    ABOVE = "above"
    BELOW = "below"


# Weight factors for risk scoring
RISK_WEIGHTS = {
    "distance": 0.35,
    "direction": 0.25,
    "confidence": 0.15,
    "collision_risk": 0.25,
}

# Direction zone risk multipliers
DIRECTION_RISK = {
    DirectionZone.CENTER: 1.0,
    DirectionZone.LEFT_CENTER: 0.8,
    DirectionZone.RIGHT_CENTER: 0.8,
    DirectionZone.FAR_LEFT: 0.5,
    DirectionZone.FAR_RIGHT: 0.5,
    DirectionZone.ABOVE: 0.3,
    DirectionZone.BELOW: 0.6,
}

# Obstacle type base risk
OBSTACLE_TYPE_RISK = {
    "person": 0.9,
    "vehicle": 1.0,
    "car": 1.0,
    "truck": 1.0,
    "bus": 1.0,
    "motorcycle": 0.95,
    "bicycle": 0.85,
    "dog": 0.7,
    "cat": 0.5,
    "chair": 0.6,
    "table": 0.6,
    "pole": 0.75,
    "fire hydrant": 0.7,
    "stairs": 0.8,
    "curb": 0.65,
    "hole": 0.9,
    "default": 0.6,
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Hazard:
    """Represents a detected hazard with risk assessment."""
    
    # Identification
    object_id: str
    class_name: str
    
    # Position
    distance_m: float
    direction: DirectionZone
    direction_str: str  # Human-readable direction
    
    # Bounding box (normalized 0-1)
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    
    # Risk assessment
    detection_confidence: float
    risk_score: float
    severity: HazardSeverity
    collision_time_sec: Optional[float] = None
    
    # Metadata
    short_cue: str = ""  # Brief TTS-friendly description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.object_id,
            "name": self.class_name,
            "distance_m": round(self.distance_m, 2),
            "direction": self.direction_str,
            "direction_zone": self.direction.value,
            "bbox": list(self.bbox),
            "confidence": round(self.detection_confidence, 3),
            "risk_score": round(self.risk_score, 3),
            "severity": self.severity.name.lower(),
            "collision_time_sec": round(self.collision_time_sec, 2) if self.collision_time_sec else None,
            "short_cue": self.short_cue,
        }


@dataclass
class PrioritySceneResult:
    """Result of priority scene analysis."""
    
    # Top hazards
    top_hazards: List[Hazard]
    all_hazards: List[Hazard]
    
    # Summary
    total_detected: int
    highest_severity: HazardSeverity
    path_clear: bool
    
    # Timing
    processing_time_ms: float
    
    # Navigation suggestion
    navigation_cue: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "top_hazards": [h.to_dict() for h in self.top_hazards],
            "total_detected": self.total_detected,
            "highest_severity": self.highest_severity.name.lower(),
            "path_clear": self.path_clear,
            "navigation_cue": self.navigation_cue,
            "processing_time_ms": round(self.processing_time_ms, 1),
        }


# ============================================================================
# Priority Scene Analyzer
# ============================================================================

class PrioritySceneAnalyzer:
    """
    Analyzes scene for prioritized hazard detection.
    
    Returns top-3 highest-risk obstacles for immediate awareness.
    """
    
    def __init__(
        self,
        walking_speed_ms: float = 1.4,  # Average walking speed
        critical_distance_m: float = 1.5,  # Distance for CRITICAL severity
        high_distance_m: float = 3.0,     # Distance for HIGH severity
        medium_distance_m: float = 5.0,   # Distance for MEDIUM severity
    ):
        self.walking_speed_ms = walking_speed_ms
        self.critical_distance_m = critical_distance_m
        self.high_distance_m = high_distance_m
        self.medium_distance_m = medium_distance_m
        
        # Stats
        self._total_analyses = 0
        self._avg_processing_ms = 0.0
    
    def analyze(
        self,
        detections: List[Dict[str, Any]],
        depth_map: Optional[Any] = None,
        image_width: int = 640,
        image_height: int = 480,
        top_n: int = 3,
    ) -> PrioritySceneResult:
        """
        Analyze detections and return prioritized hazards.
        
        Args:
            detections: List of detection dicts with keys:
                - class: object class name
                - confidence: detection confidence
                - bbox: [x1, y1, x2, y2] (pixel coords)
                - depth: optional depth value in meters
            depth_map: Optional depth map array
            image_width: Image width for direction calculation
            image_height: Image height
            top_n: Number of top hazards to return
            
        Returns:
            PrioritySceneResult with top hazards
        """
        start_time = time.time()
        
        hazards = []
        
        for i, det in enumerate(detections):
            hazard = self._process_detection(
                det, i, depth_map, image_width, image_height
            )
            if hazard:
                hazards.append(hazard)
        
        # Sort by risk score (highest first)
        hazards.sort(key=lambda h: h.risk_score, reverse=True)
        
        # Get top-N
        top_hazards = hazards[:top_n]
        
        # Determine overall state
        highest_severity = HazardSeverity.MINIMAL
        for h in hazards:
            if h.severity.value < highest_severity.value:
                highest_severity = h.severity
        
        path_clear = not any(
            h.direction in {DirectionZone.CENTER, DirectionZone.LEFT_CENTER, DirectionZone.RIGHT_CENTER}
            and h.distance_m < self.high_distance_m
            for h in hazards
        )
        
        # Generate navigation cue
        navigation_cue = self._generate_navigation_cue(top_hazards, path_clear)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Update stats
        self._total_analyses += 1
        self._avg_processing_ms = (self._avg_processing_ms * 0.9) + (processing_time * 0.1)
        
        return PrioritySceneResult(
            top_hazards=top_hazards,
            all_hazards=hazards,
            total_detected=len(hazards),
            highest_severity=highest_severity,
            path_clear=path_clear,
            processing_time_ms=processing_time,
            navigation_cue=navigation_cue,
        )
    
    def _process_detection(
        self,
        det: Dict[str, Any],
        index: int,
        depth_map: Optional[Any],
        image_width: int,
        image_height: int,
    ) -> Optional[Hazard]:
        """Process a single detection into a hazard."""
        try:
            class_name = det.get("class", det.get("label", "unknown"))
            confidence = det.get("confidence", det.get("score", 0.5))
            bbox = det.get("bbox", det.get("box", [0, 0, 1, 1]))
            
            # Normalize bbox if in pixel coords
            if bbox[2] > 1:
                bbox = [
                    bbox[0] / image_width,
                    bbox[1] / image_height,
                    bbox[2] / image_width,
                    bbox[3] / image_height,
                ]
            
            # Get distance
            distance = det.get("depth", det.get("distance", None))
            if distance is None and depth_map is not None:
                distance = self._estimate_depth_from_map(bbox, depth_map)
            if distance is None:
                distance = self._estimate_depth_from_bbox(bbox)
            
            # Get direction
            direction, direction_str = self._get_direction(bbox, image_width, image_height)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(
                class_name, distance, direction, confidence
            )
            
            # Determine severity
            severity = self._determine_severity(distance, direction, risk_score)
            
            # Calculate collision time
            collision_time = None
            if direction in {DirectionZone.CENTER, DirectionZone.LEFT_CENTER, DirectionZone.RIGHT_CENTER}:
                collision_time = distance / self.walking_speed_ms
            
            # Generate short cue
            short_cue = self._generate_short_cue(class_name, direction_str, distance)
            
            return Hazard(
                object_id=f"haz-{index:03d}",
                class_name=class_name,
                distance_m=distance,
                direction=direction,
                direction_str=direction_str,
                bbox=tuple(bbox),
                detection_confidence=confidence,
                risk_score=risk_score,
                severity=severity,
                collision_time_sec=collision_time,
                short_cue=short_cue,
            )
            
        except Exception as e:
            logger.warning(f"Failed to process detection: {e}")
            return None
    
    def _get_direction(
        self,
        bbox: List[float],
        image_width: int,
        image_height: int,
    ) -> Tuple[DirectionZone, str]:
        """Determine direction zone from bounding box."""
        # Get center of bbox (normalized)
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        
        # Determine horizontal zone
        if center_x < 0.2:
            h_zone = "far-left"
            h_name = "far left"
        elif center_x < 0.4:
            h_zone = "left-center"
            h_name = "left"
        elif center_x > 0.8:
            h_zone = "far-right"
            h_name = "far right"
        elif center_x > 0.6:
            h_zone = "right-center"
            h_name = "right"
        else:
            h_zone = "center"
            h_name = "ahead"
        
        # Check vertical position
        if center_y < 0.3:
            direction_zone = DirectionZone.ABOVE
            direction_str = f"{h_name} above"
        elif center_y > 0.8:
            direction_zone = DirectionZone.BELOW
            direction_str = f"{h_name} below"
        else:
            direction_zone = DirectionZone(h_zone)
            direction_str = h_name
        
        return direction_zone, direction_str
    
    def _estimate_depth_from_map(
        self,
        bbox: List[float],
        depth_map: Any,
    ) -> Optional[float]:
        """Estimate depth from depth map."""
        try:
            import numpy as np
            
            h, w = depth_map.shape[:2]
            x1 = int(bbox[0] * w)
            y1 = int(bbox[1] * h)
            x2 = int(bbox[2] * w)
            y2 = int(bbox[3] * h)
            
            # Get center region
            cx1 = x1 + (x2 - x1) // 4
            cx2 = x2 - (x2 - x1) // 4
            cy1 = y1 + (y2 - y1) // 4
            cy2 = y2 - (y2 - y1) // 4
            
            region = depth_map[cy1:cy2, cx1:cx2]
            if region.size > 0:
                return float(np.median(region))
            
            return None
        except Exception:
            return None
    
    def _estimate_depth_from_bbox(self, bbox: List[float]) -> float:
        """Estimate depth from bounding box size."""
        # Larger bbox = closer object
        bbox_height = bbox[3] - bbox[1]
        bbox_width = bbox[2] - bbox[0]
        bbox_area = bbox_height * bbox_width
        
        # Simple inverse relationship
        # Very rough estimate: area ~0.5 → ~1m, area ~0.1 → ~5m
        if bbox_area > 0.3:
            return 1.0
        elif bbox_area > 0.1:
            return 2.0 + (0.3 - bbox_area) * 10
        else:
            return 5.0 + (0.1 - bbox_area) * 50
    
    def _calculate_risk_score(
        self,
        class_name: str,
        distance: float,
        direction: DirectionZone,
        confidence: float,
    ) -> float:
        """Calculate overall risk score (0-1)."""
        # Distance score (closer = higher risk)
        if distance <= self.critical_distance_m:
            distance_score = 1.0
        elif distance <= self.high_distance_m:
            distance_score = 0.7 + 0.3 * (1 - (distance - self.critical_distance_m) / 
                                          (self.high_distance_m - self.critical_distance_m))
        elif distance <= self.medium_distance_m:
            distance_score = 0.4 + 0.3 * (1 - (distance - self.high_distance_m) / 
                                          (self.medium_distance_m - self.high_distance_m))
        else:
            distance_score = max(0.1, 0.4 * (1 - (distance - self.medium_distance_m) / 10))
        
        # Direction score
        direction_score = DIRECTION_RISK.get(direction, 0.5)
        
        # Confidence score
        confidence_score = confidence
        
        # Collision risk (simplified - based on direction and distance)
        if direction in {DirectionZone.CENTER, DirectionZone.LEFT_CENTER, DirectionZone.RIGHT_CENTER}:
            collision_score = 1.0 - min(1.0, distance / 10.0)
        else:
            collision_score = 0.2
        
        # Object type modifier
        type_modifier = OBSTACLE_TYPE_RISK.get(class_name.lower(), OBSTACLE_TYPE_RISK["default"])
        
        # Weighted combination
        risk_score = (
            RISK_WEIGHTS["distance"] * distance_score +
            RISK_WEIGHTS["direction"] * direction_score +
            RISK_WEIGHTS["confidence"] * confidence_score +
            RISK_WEIGHTS["collision_risk"] * collision_score
        ) * type_modifier
        
        # Proximity urgency bonus (not affected by type modifier)
        # Ensures closer objects always rank above distant ones
        if distance <= self.critical_distance_m:
            risk_score += 0.3
        elif distance <= self.high_distance_m:
            risk_score += 0.15
        
        return min(1.0, risk_score)
    
    def _determine_severity(
        self,
        distance: float,
        direction: DirectionZone,
        risk_score: float,
    ) -> HazardSeverity:
        """Determine hazard severity level."""
        # Distance is the primary factor for blind navigation safety
        if distance <= self.critical_distance_m:
            return HazardSeverity.CRITICAL
        elif distance <= self.high_distance_m:
            return HazardSeverity.HIGH
        elif distance <= self.medium_distance_m:
            return HazardSeverity.MEDIUM
        elif risk_score >= 0.2:
            return HazardSeverity.LOW
        else:
            return HazardSeverity.MINIMAL
    
    def _generate_short_cue(
        self,
        class_name: str,
        direction: str,
        distance: float,
    ) -> str:
        """Generate short TTS-friendly cue."""
        # Format distance
        if distance < 1:
            dist_str = f"{int(distance * 100)} centimeters"
        elif distance < 10:
            dist_str = f"{distance:.1f} meters"
        else:
            dist_str = f"{int(distance)} meters"
        
        return f"{class_name} {direction}, {dist_str}"
    
    def _generate_navigation_cue(
        self,
        top_hazards: List[Hazard],
        path_clear: bool,
    ) -> str:
        """Generate navigation suggestion."""
        if path_clear:
            return "Path appears clear ahead."
        
        if not top_hazards:
            return "Area scanned, no immediate hazards."
        
        # Analyze positions of top hazards
        center_hazards = [h for h in top_hazards if h.direction == DirectionZone.CENTER]
        left_hazards = [h for h in top_hazards if "left" in h.direction.value]
        right_hazards = [h for h in top_hazards if "right" in h.direction.value]
        
        if center_hazards:
            closest = min(center_hazards, key=lambda h: h.distance_m)
            if closest.distance_m < self.critical_distance_m:
                return f"Stop! {closest.class_name} directly ahead, {closest.distance_m:.1f} meters."
            elif left_hazards and not right_hazards:
                return "Suggest moving right to avoid obstacles."
            elif right_hazards and not left_hazards:
                return "Suggest moving left to avoid obstacles."
            else:
                return f"Caution: {closest.class_name} ahead at {closest.distance_m:.1f} meters."
        
        return "Proceed with caution, obstacles detected nearby."
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "total_analyses": self._total_analyses,
            "avg_processing_ms": round(self._avg_processing_ms, 2),
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def analyze_priority_scene(
    detections: List[Dict],
    depth_map: Optional[Any] = None,
    top_n: int = 3,
) -> Dict[str, Any]:
    """
    Quick priority scene analysis.
    
    Args:
        detections: Detection list
        depth_map: Optional depth map
        top_n: Number of top hazards
        
    Returns:
        Result dictionary
    """
    analyzer = PrioritySceneAnalyzer()
    result = analyzer.analyze(detections, depth_map, top_n=top_n)
    return result.to_dict()


def get_top_hazards(
    detections: List[Dict],
    depth_map: Optional[Any] = None,
) -> List[Dict]:
    """Get top 3 hazards from detections."""
    result = analyze_priority_scene(detections, depth_map)
    return result.get("top_hazards", [])
