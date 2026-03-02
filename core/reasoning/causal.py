"""
Causal Reasoning Module (T-123).

Builds causal graphs from observations, infers causality between events,
and provides explanations ("why did X happen?") and predictions.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.reasoning.reasoning_foundation import (
    BaseReasoner,
    ReasoningChain,
    ReasoningConfig,
    ReasoningStep,
    ReasoningType,
)

logger = logging.getLogger("causal-reasoning")


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class CausalFactor:
    """A node in the causal graph."""

    factor_id: str
    description: str
    factor_type: str = "cause"  # "cause" | "effect" | "condition"
    confidence: float = 0.5
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "description": self.description,
            "factor_type": self.factor_type,
            "confidence": round(self.confidence, 3),
            "evidence_count": len(self.evidence),
        }


@dataclass
class CausalLink:
    """An edge in the causal graph."""

    cause: CausalFactor
    effect: CausalFactor
    strength: float = 0.5  # 0-1
    mechanism: str = ""
    is_direct: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cause": self.cause.factor_id,
            "effect": self.effect.factor_id,
            "strength": round(self.strength, 3),
            "mechanism": self.mechanism,
            "is_direct": self.is_direct,
        }


class CausalGraph:
    """A directed acyclic graph of causal relationships."""

    def __init__(self) -> None:
        self._nodes: Dict[str, CausalFactor] = {}
        self._edges: List[CausalLink] = []

    @property
    def nodes(self) -> List[CausalFactor]:
        return list(self._nodes.values())

    @property
    def edges(self) -> List[CausalLink]:
        return list(self._edges)

    def add_node(self, factor: CausalFactor) -> None:
        self._nodes[factor.factor_id] = factor

    def add_edge(self, link: CausalLink) -> None:
        # Ensure nodes exist
        if link.cause.factor_id not in self._nodes:
            self._nodes[link.cause.factor_id] = link.cause
        if link.effect.factor_id not in self._nodes:
            self._nodes[link.effect.factor_id] = link.effect
        self._edges.append(link)

    def get_causes(self, factor_id: str) -> List[CausalFactor]:
        """Get all direct causes of a factor."""
        return [e.cause for e in self._edges if e.effect.factor_id == factor_id]

    def get_effects(self, factor_id: str) -> List[CausalFactor]:
        """Get all direct effects of a factor."""
        return [e.effect for e in self._edges if e.cause.factor_id == factor_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
        }


# =============================================================================
# Causal Reasoner
# =============================================================================


class CausalReasoner(BaseReasoner):
    """Reasons about cause-and-effect relationships.

    Builds causal graphs from observations, explains why things happened,
    and predicts potential effects of observed causes.

    Usage::

        reasoner = CausalReasoner()
        chain = await reasoner.reason({
            "observations": [
                {"type": "door_opened", "timestamp_ms": 1000},
                {"type": "person_entered", "timestamp_ms": 1500},
            ]
        })
    """

    # Common causal templates for blind-navigation scenarios
    CAUSAL_TEMPLATES: Dict[str, List[str]] = {
        "door_opened": ["person_entering", "draft", "noise_change"],
        "person_approaching": ["greeting", "collision_risk", "social_interaction"],
        "car_horn": ["traffic_danger", "pedestrian_warning"],
        "falling": ["injury_risk", "obstacle_present"],
        "running": ["emergency", "exercise", "late_arrival"],
        "alarm": ["emergency_evacuation", "security_alert"],
        "siren": ["emergency_vehicle", "road_clearing"],
    }

    def __init__(self, config: Optional[ReasoningConfig] = None):
        self._config = config or ReasoningConfig()
        self._total_graphs = 0

    @property
    def reason_type(self) -> ReasoningType:
        return ReasoningType.CAUSAL

    async def reason(self, context: Dict[str, Any]) -> ReasoningChain:
        """Build causal graph from observations and generate explanation."""
        start_ms = time.time() * 1000
        chain = ReasoningChain(metadata={"type": "causal"})

        try:
            observations = context.get("observations", [])
            if not observations:
                chain.final_answer = "No observations available for causal analysis."
                chain.total_latency_ms = time.time() * 1000 - start_ms
                return chain

            # Step 1: Build graph
            graph = self.build_causal_graph(observations)
            chain.add_step(ReasoningStep(
                step_type="build_graph",
                output_data=graph.to_dict(),
                confidence=0.6,
                timestamp_ms=time.time() * 1000,
            ))

            # Step 2: Find key causal paths
            explanations: List[str] = []
            for node in graph.nodes:
                if node.factor_type == "effect":
                    explanation = self.explain_why(graph, node.factor_id)
                    if explanation:
                        explanations.append(explanation)

            chain.add_step(ReasoningStep(
                step_type="explain",
                output_data={"explanations": explanations},
                confidence=0.5,
                timestamp_ms=time.time() * 1000,
            ))

            # Step 3: Predict effects
            predictions: List[str] = []
            for node in graph.nodes:
                if node.factor_type == "cause":
                    effects = self.predict_effects(graph, node.factor_id)
                    for eff in effects:
                        predictions.append(f"{node.description} may lead to {eff.description}")

            chain.add_step(ReasoningStep(
                step_type="predict",
                output_data={"predictions": predictions},
                confidence=0.4,
                timestamp_ms=time.time() * 1000,
            ))

            # Combine
            summary_parts: List[str] = []
            if explanations:
                summary_parts.extend(explanations[:3])
            if predictions:
                summary_parts.extend(predictions[:3])

            chain.final_answer = ". ".join(summary_parts) if summary_parts else "No causal patterns identified."
            chain.total_latency_ms = time.time() * 1000 - start_ms
            self._total_graphs += 1
            return chain

        except Exception as exc:
            logger.error("Causal reasoning failed: %s", exc)
            chain.final_answer = "Unable to perform causal analysis."
            chain.total_latency_ms = time.time() * 1000 - start_ms
            return chain

    def build_causal_graph(self, observations: List[Dict[str, Any]]) -> CausalGraph:
        """Build a causal graph from a list of observations."""
        graph = CausalGraph()

        factors: List[CausalFactor] = []
        for i, obs in enumerate(observations):
            obs_type = obs.get("type", obs.get("event_type", f"event_{i}"))
            factor = CausalFactor(
                factor_id=f"f_{i}",
                description=obs_type.replace("_", " "),
                factor_type="cause",
                confidence=obs.get("confidence", 0.5),
                evidence=[str(obs)],
            )
            factors.append(factor)
            graph.add_node(factor)

        # Infer causal links between consecutive observations
        for i in range(len(factors) - 1):
            link = self._infer_causality(factors[i], factors[i + 1])
            if link:
                graph.add_edge(link)

        # Add template-based effects
        for factor in factors:
            desc_key = factor.description.replace(" ", "_")
            if desc_key in self.CAUSAL_TEMPLATES:
                for effect_desc in self.CAUSAL_TEMPLATES[desc_key]:
                    effect = CausalFactor(
                        factor_id=f"eff_{factor.factor_id}_{effect_desc}",
                        description=effect_desc.replace("_", " "),
                        factor_type="effect",
                        confidence=0.4,
                    )
                    graph.add_node(effect)
                    graph.add_edge(CausalLink(
                        cause=factor,
                        effect=effect,
                        strength=0.5,
                        mechanism="template_inference",
                        is_direct=True,
                    ))

        return graph

    def _infer_causality(
        self, event_a: CausalFactor, event_b: CausalFactor
    ) -> Optional[CausalLink]:
        """Infer if there's a causal link between two sequential events."""
        # Simple heuristic: consecutive events have weak causal link
        return CausalLink(
            cause=event_a,
            effect=event_b,
            strength=0.3,
            mechanism="temporal_sequence",
            is_direct=True,
        )

    def explain_why(self, graph: CausalGraph, target_factor_id: str) -> str:
        """Generate an explanation for why a factor occurred."""
        causes = graph.get_causes(target_factor_id)
        if not causes:
            return ""

        target = graph._nodes.get(target_factor_id)
        if not target:
            return ""

        cause_descs = [c.description for c in causes]
        return f"{target.description} likely because of {', '.join(cause_descs)}"

    def predict_effects(
        self, graph: CausalGraph, cause_id: str
    ) -> List[CausalFactor]:
        """Predict potential effects of a given cause."""
        return graph.get_effects(cause_id)

    def health(self) -> Dict[str, Any]:
        return {
            "type": self.reason_type.value,
            "total_graphs_built": self._total_graphs,
            "template_count": len(self.CAUSAL_TEMPLATES),
            "status": "ok",
        }
