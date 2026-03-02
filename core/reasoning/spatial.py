"""
Spatial Reasoning Module (T-122).

Infers spatial relations between detected entities (left-of, right-of,
blocking, near, far) and generates scene descriptions for navigation.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.reasoning.reasoning_foundation import (
    BaseReasoner,
    ReasoningChain,
    ReasoningConfig,
    ReasoningStep,
    ReasoningType,
)

logger = logging.getLogger("spatial-reasoning")


# =============================================================================
# Data Structures
# =============================================================================


class SpatialRelationType(str, Enum):
    """Types of spatial relations between entities."""

    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"
    ABOVE = "above"
    BELOW = "below"
    IN_FRONT = "in_front"
    BEHIND = "behind"
    NEAR = "near"
    FAR = "far"
    BLOCKING = "blocking"
    INSIDE = "inside"
    OUTSIDE = "outside"
    BETWEEN = "between"


@dataclass
class SpatialEntity:
    """An entity with spatial properties."""

    entity_id: str
    label: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # x, y, depth
    size: str = "medium"  # small/medium/large
    confidence: float = 0.5
    bbox: Optional[Tuple[int, int, int, int]] = None  # x1, y1, x2, y2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "label": self.label,
            "position": list(self.position),
            "size": self.size,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class SpatialRelation:
    """A spatial relation between two entities."""

    subject: SpatialEntity
    relation: SpatialRelationType
    object: SpatialEntity
    confidence: float = 0.0
    distance_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject.label,
            "relation": self.relation.value,
            "object": self.object.label,
            "confidence": round(self.confidence, 3),
            "distance_m": round(self.distance_m, 2) if self.distance_m else None,
        }

    def describe(self) -> str:
        dist = f" ({self.distance_m:.1f}m)" if self.distance_m else ""
        return f"{self.subject.label} is {self.relation.value.replace('_', ' ')} {self.object.label}{dist}"


# =============================================================================
# Spatial Reasoner
# =============================================================================


class SpatialReasoner(BaseReasoner):
    """Reasons about spatial relationships between detected entities.

    Takes entity positions (x, y, depth) and infers relations such as
    left-of, right-of, near, far, blocking, etc.

    Usage::

        reasoner = SpatialReasoner()
        entities = [SpatialEntity("e1", "chair", (0.3, 0.5, 2.0)), ...]
        chain = await reasoner.reason({"entities": entities})
    """

    def __init__(self, config: Optional[ReasoningConfig] = None):
        self._config = config or ReasoningConfig()
        self._total_relations = 0

    @property
    def reason_type(self) -> ReasoningType:
        return ReasoningType.SPATIAL

    async def reason(self, context: Dict[str, Any]) -> ReasoningChain:
        """Analyze spatial relationships from context entities."""
        start_ms = time.time() * 1000
        chain = ReasoningChain(metadata={"type": "spatial"})

        try:
            entities = context.get("entities", [])
            if not entities:
                chain.final_answer = "No spatial entities to analyze."
                chain.total_latency_ms = time.time() * 1000 - start_ms
                return chain

            # Step 1: Parse entities
            chain.add_step(ReasoningStep(
                step_type="parse_entities",
                output_data={"count": len(entities)},
                confidence=1.0,
                timestamp_ms=time.time() * 1000,
            ))

            # Step 2: Compute relations
            relations = self.compute_relations(entities)
            chain.add_step(ReasoningStep(
                step_type="compute_relations",
                output_data={"relation_count": len(relations)},
                confidence=0.7 if relations else 0.3,
                timestamp_ms=time.time() * 1000,
            ))

            # Step 3: Describe scene
            description = self.describe_scene(entities, relations)
            chain.add_step(ReasoningStep(
                step_type="describe_scene",
                output_data={"description": description},
                confidence=0.6,
                timestamp_ms=time.time() * 1000,
            ))

            chain.final_answer = description
            chain.total_latency_ms = time.time() * 1000 - start_ms
            return chain

        except Exception as exc:
            logger.error("Spatial reasoning failed: %s", exc)
            chain.final_answer = "Unable to analyze spatial relationships."
            chain.total_latency_ms = time.time() * 1000 - start_ms
            return chain

    def compute_relations(
        self, entities: List[SpatialEntity]
    ) -> List[SpatialRelation]:
        """Compute pairwise spatial relations between entities."""
        relations: List[SpatialRelation] = []
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                e1, e2 = entities[i], entities[j]
                rel_type = self._infer_relation(e1, e2)
                dist = self._estimate_distance(e1, e2)
                conf = min(e1.confidence, e2.confidence) * 0.8
                relations.append(SpatialRelation(
                    subject=e1,
                    relation=rel_type,
                    object=e2,
                    confidence=conf,
                    distance_m=dist,
                ))
                self._total_relations += 1
        return relations

    def _infer_relation(
        self, e1: SpatialEntity, e2: SpatialEntity
    ) -> SpatialRelationType:
        """Infer the dominant spatial relation between two entities."""
        x1, y1, d1 = e1.position
        x2, y2, d2 = e2.position

        dx = x2 - x1
        dy = y2 - y1
        dd = d2 - d1

        # Depth-based relations take priority
        if abs(dd) > 1.0:
            if dd < 0:
                return SpatialRelationType.IN_FRONT
            return SpatialRelationType.BEHIND

        # Blocking: similar depth, centered, close
        dist = self._estimate_distance(e1, e2)
        if dist < 0.5 and abs(dx) < 0.2:
            return SpatialRelationType.BLOCKING

        # Horizontal
        if abs(dx) > abs(dy) * 1.5:
            return SpatialRelationType.LEFT_OF if dx < 0 else SpatialRelationType.RIGHT_OF

        # Vertical
        if abs(dy) > abs(dx) * 1.5:
            return SpatialRelationType.ABOVE if dy < 0 else SpatialRelationType.BELOW

        # Distance
        if dist < 1.5:
            return SpatialRelationType.NEAR
        return SpatialRelationType.FAR

    def _estimate_distance(
        self, e1: SpatialEntity, e2: SpatialEntity
    ) -> float:
        """Estimate 3D distance between two entities."""
        x1, y1, d1 = e1.position
        x2, y2, d2 = e2.position
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (d2 - d1) ** 2)

    def describe_scene(
        self,
        entities: List[SpatialEntity],
        relations: List[SpatialRelation],
    ) -> str:
        """Generate a natural-language scene description."""
        if not entities:
            return "Scene is empty."

        parts: List[str] = [f"Scene contains {len(entities)} objects:"]
        for e in entities[:5]:
            parts.append(f"  - {e.label} ({e.size}, depth {e.position[2]:.1f}m)")

        if relations:
            parts.append("Spatial relations:")
            for r in sorted(relations, key=lambda x: -x.confidence)[:5]:
                parts.append(f"  - {r.describe()}")

        return " ".join(parts)

    def health(self) -> Dict[str, Any]:
        return {
            "type": self.reason_type.value,
            "total_relations_computed": self._total_relations,
            "status": "ok",
        }
