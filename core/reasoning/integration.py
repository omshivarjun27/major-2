"""
Reasoning Integration Module (T-124).

Combines temporal, spatial, and causal reasoning into a unified result.
Weights each reasoning type and generates a combined answer.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.reasoning.causal import CausalReasoner
from core.reasoning.reasoning_foundation import (
    BaseReasoner,
    ReasoningChain,
    ReasoningType,
)
from core.reasoning.spatial import SpatialReasoner
from core.reasoning.temporal import TemporalReasoner

logger = logging.getLogger("reasoning-integration")


# =============================================================================
# Config & Data Structures
# =============================================================================


@dataclass
class IntegratedReasoningConfig:
    """Configuration for integrated reasoning."""

    temporal_weight: float = 0.3
    spatial_weight: float = 0.4
    causal_weight: float = 0.3
    min_confidence: float = 0.25
    max_total_latency_ms: float = 300.0


@dataclass
class IntegratedResult:
    """Result from integrated multi-modal reasoning."""

    temporal_chain: Optional[ReasoningChain] = None
    spatial_chain: Optional[ReasoningChain] = None
    causal_chain: Optional[ReasoningChain] = None
    combined_answer: str = ""
    combined_confidence: float = 0.0
    total_latency_ms: float = 0.0
    reasoning_types_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "temporal": self.temporal_chain.to_dict() if self.temporal_chain else None,
            "spatial": self.spatial_chain.to_dict() if self.spatial_chain else None,
            "causal": self.causal_chain.to_dict() if self.causal_chain else None,
            "combined_answer": self.combined_answer,
            "combined_confidence": round(self.combined_confidence, 3),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "reasoning_types_used": self.reasoning_types_used,
        }

    @property
    def user_cue(self) -> str:
        """Generate a spoken cue from the combined answer."""
        if self.combined_answer:
            return self.combined_answer
        return "Analysis complete."


# =============================================================================
# Integrated Reasoner
# =============================================================================


class IntegratedReasoner:
    """Combines temporal, spatial, and causal reasoning.

    Runs relevant reasoners in parallel (simulated) and merges results
    with configurable weights.

    Usage::

        reasoner = IntegratedReasoner(
            temporal=TemporalReasoner(),
            spatial=SpatialReasoner(),
            causal=CausalReasoner(),
        )
        result = await reasoner.reason("What is happening?", context)
    """

    def __init__(
        self,
        config: Optional[IntegratedReasoningConfig] = None,
        temporal: Optional[TemporalReasoner] = None,
        spatial: Optional[SpatialReasoner] = None,
        causal: Optional[CausalReasoner] = None,
    ):
        self.config = config or IntegratedReasoningConfig()
        self._temporal = temporal
        self._spatial = spatial
        self._causal = causal
        self._total_integrations = 0
        logger.info(
            "IntegratedReasoner created: temporal=%s, spatial=%s, causal=%s",
            temporal is not None,
            spatial is not None,
            causal is not None,
        )

    async def reason(
        self, question: str, context: Dict[str, Any]
    ) -> IntegratedResult:
        """Run integrated reasoning across all available reasoners."""
        start_ms = time.time() * 1000
        result = IntegratedResult()

        try:
            # Select relevant reasoners
            relevant = self._select_relevant_reasoners(question, context)

            chains: Dict[str, ReasoningChain] = {}

            for reasoner in relevant:
                try:
                    chain = await reasoner.reason(context)
                    rt = reasoner.reason_type.value
                    chains[rt] = chain
                    result.reasoning_types_used.append(rt)

                    if reasoner.reason_type == ReasoningType.TEMPORAL:
                        result.temporal_chain = chain
                    elif reasoner.reason_type == ReasoningType.SPATIAL:
                        result.spatial_chain = chain
                    elif reasoner.reason_type == ReasoningType.CAUSAL:
                        result.causal_chain = chain
                except Exception as exc:
                    logger.warning("Reasoner %s failed: %s", reasoner.reason_type.value, exc)

            # Combine results
            result = self._combine_results(result, chains)
            result.total_latency_ms = time.time() * 1000 - start_ms
            self._total_integrations += 1
            return result

        except Exception as exc:
            logger.error("Integrated reasoning failed: %s", exc)
            result.combined_answer = "Unable to complete integrated analysis."
            result.total_latency_ms = time.time() * 1000 - start_ms
            return result

    def _select_relevant_reasoners(
        self, question: str, context: Dict[str, Any]
    ) -> List[BaseReasoner]:
        """Select reasoners relevant to the question/context."""
        q = question.lower()
        relevant: List[BaseReasoner] = []

        temporal_keywords = ["when", "before", "after", "timeline", "sequence", "happened"]
        spatial_keywords = ["where", "position", "left", "right", "near", "scene"]
        causal_keywords = ["why", "cause", "effect", "because", "reason"]

        if self._temporal and (
            any(kw in q for kw in temporal_keywords)
            or "events" in context
        ):
            relevant.append(self._temporal)

        if self._spatial and (
            any(kw in q for kw in spatial_keywords)
            or "entities" in context
        ):
            relevant.append(self._spatial)

        if self._causal and (
            any(kw in q for kw in causal_keywords)
            or "observations" in context
        ):
            relevant.append(self._causal)

        # If nothing matched, try all available
        if not relevant:
            if self._temporal:
                relevant.append(self._temporal)
            if self._spatial:
                relevant.append(self._spatial)
            if self._causal:
                relevant.append(self._causal)

        return relevant

    def _combine_results(
        self, result: IntegratedResult, chains: Dict[str, ReasoningChain]
    ) -> IntegratedResult:
        """Combine reasoning chains into an integrated result."""
        if not chains:
            result.combined_answer = "No reasoning results available."
            result.combined_confidence = 0.0
            return result

        weights = {
            "temporal": self.config.temporal_weight,
            "spatial": self.config.spatial_weight,
            "causal": self.config.causal_weight,
        }

        answers: List[str] = []
        weighted_conf = 0.0
        total_weight = 0.0

        for rt, chain in chains.items():
            w = weights.get(rt, 0.3)
            if chain.final_answer and chain.total_confidence >= self.config.min_confidence:
                answers.append(chain.final_answer)
                weighted_conf += chain.total_confidence * w
                total_weight += w

        result.combined_answer = self._generate_combined_answer(chains)
        result.combined_confidence = weighted_conf / total_weight if total_weight > 0 else 0.0
        return result

    def _generate_combined_answer(self, chains: Dict[str, ReasoningChain]) -> str:
        """Generate a unified answer from multiple reasoning chains."""
        parts: List[str] = []

        for rt in ["spatial", "temporal", "causal"]:  # Order: where, when, why
            chain = chains.get(rt)
            if chain and chain.final_answer:
                parts.append(chain.final_answer)

        return " ".join(parts) if parts else "No reasoning conclusions available."

    def health(self) -> Dict[str, Any]:
        return {
            "temporal": self._temporal.health() if self._temporal else None,
            "spatial": self._spatial.health() if self._spatial else None,
            "causal": self._causal.health() if self._causal else None,
            "total_integrations": self._total_integrations,
        }


# =============================================================================
# Factory
# =============================================================================


def create_integrated_reasoner(
    config: Optional[IntegratedReasoningConfig] = None,
    temporal: Optional[TemporalReasoner] = None,
    spatial: Optional[SpatialReasoner] = None,
    causal: Optional[CausalReasoner] = None,
) -> IntegratedReasoner:
    """Factory function for IntegratedReasoner."""
    return IntegratedReasoner(
        config=config,
        temporal=temporal,
        spatial=spatial,
        causal=causal,
    )
