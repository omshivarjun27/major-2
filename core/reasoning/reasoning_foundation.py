"""
Reasoning Engine Foundation (T-120).

Provides base abstractions for the reasoning pipeline: BaseReasoner ABC,
ReasoningChain, ReasoningCache, and ReasoningOrchestrator that dispatches
to registered reasoners (temporal, spatial, causal).
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("reasoning-foundation")


# =============================================================================
# Enums & Config
# =============================================================================


class ReasoningType(str, Enum):
    """Types of reasoning supported by the engine."""

    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    CAUSAL = "causal"
    COMPOSITE = "composite"


@dataclass
class ReasoningConfig:
    """Configuration for reasoning components."""

    max_reasoning_steps: int = 5
    confidence_threshold: float = 0.3
    timeout_ms: float = 300.0
    enable_caching: bool = True
    cache_ttl_s: float = 60.0


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""

    step_type: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    latency_ms: float = 0.0
    timestamp_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type,
            "confidence": round(self.confidence, 3),
            "latency_ms": round(self.latency_ms, 1),
        }


@dataclass
class ReasoningChain:
    """A chain of reasoning steps leading to a conclusion."""

    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    total_confidence: float = 0.0
    total_latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "total_confidence": round(self.total_confidence, 3),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "step_count": len(self.steps),
            "metadata": self.metadata,
        }

    def add_step(self, step: ReasoningStep) -> None:
        """Append a step and update chain totals."""
        self.steps.append(step)
        self.total_latency_ms += step.latency_ms
        if self.steps:
            self.total_confidence = sum(s.confidence for s in self.steps) / len(self.steps)


# =============================================================================
# Abstract Base
# =============================================================================


class BaseReasoner(ABC):
    """Abstract base class for all reasoners."""

    @abstractmethod
    async def reason(self, context: Dict[str, Any]) -> ReasoningChain:
        """Execute reasoning on the given context."""

    @property
    @abstractmethod
    def reason_type(self) -> ReasoningType:
        """Return the type of reasoning this reasoner performs."""

    def health(self) -> Dict[str, Any]:
        return {"type": self.reason_type.value, "status": "ok"}


# =============================================================================
# Cache
# =============================================================================


class ReasoningCache:
    """Simple TTL cache for reasoning results."""

    def __init__(self, ttl_s: float = 60.0):
        self._ttl_s = ttl_s
        self._cache: Dict[str, Tuple[ReasoningChain, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[ReasoningChain]:
        """Get cached chain if still valid."""
        if key in self._cache:
            chain, ts = self._cache[key]
            if time.time() - ts < self._ttl_s:
                self._hits += 1
                return chain
            del self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, chain: ReasoningChain) -> None:
        self._cache[key] = (chain, time.time())

    def clear(self) -> None:
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses), 3),
        }


# =============================================================================
# Orchestrator
# =============================================================================


class ReasoningOrchestrator:
    """Dispatches questions to registered reasoners and merges results.

    Usage::

        orchestrator = ReasoningOrchestrator(config, [temporal, spatial, causal])
        chain = await orchestrator.orchestrate("What happened?", context)
    """

    def __init__(
        self,
        config: Optional[ReasoningConfig] = None,
        reasoners: Optional[List[BaseReasoner]] = None,
    ):
        self.config = config or ReasoningConfig()
        self._reasoners: Dict[ReasoningType, BaseReasoner] = {}
        for r in (reasoners or []):
            self._reasoners[r.reason_type] = r
        self._cache = ReasoningCache(self.config.cache_ttl_s) if self.config.enable_caching else None
        self._total_orchestrations = 0
        logger.info(
            "ReasoningOrchestrator initialized with %d reasoners: %s",
            len(self._reasoners),
            list(self._reasoners.keys()),
        )

    async def orchestrate(
        self, question: str, context: Dict[str, Any]
    ) -> ReasoningChain:
        """Run the appropriate reasoner(s) and return a merged chain."""
        start_ms = time.time() * 1000

        # Check cache
        cache_key = f"{question}:{hash(str(sorted(context.items())) if context else '')}"
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            reasoner = self._select_reasoner(question, context)
            if reasoner is None:
                return ReasoningChain(
                    final_answer="No suitable reasoning strategy found.",
                    total_confidence=0.0,
                    total_latency_ms=time.time() * 1000 - start_ms,
                )

            chain = await reasoner.reason(context)
            chain.total_latency_ms = time.time() * 1000 - start_ms
            chain.metadata["reasoner"] = reasoner.reason_type.value

            if self._cache:
                self._cache.set(cache_key, chain)

            self._total_orchestrations += 1
            return chain

        except Exception as exc:
            logger.error("Orchestration failed: %s", exc)
            return ReasoningChain(
                final_answer="Reasoning unavailable at this time.",
                total_confidence=0.0,
                total_latency_ms=time.time() * 1000 - start_ms,
                metadata={"error": str(exc)},
            )

    def _select_reasoner(
        self, question: str, context: Dict[str, Any]
    ) -> Optional[BaseReasoner]:
        """Select the best reasoner based on question keywords and context."""
        q = question.lower()

        temporal_keywords = ["when", "before", "after", "how long", "sequence", "timeline", "happened"]
        spatial_keywords = ["where", "left", "right", "near", "far", "between", "position", "location"]
        causal_keywords = ["why", "because", "cause", "effect", "result", "lead to", "reason"]

        if any(kw in q for kw in temporal_keywords) and ReasoningType.TEMPORAL in self._reasoners:
            return self._reasoners[ReasoningType.TEMPORAL]
        if any(kw in q for kw in spatial_keywords) and ReasoningType.SPATIAL in self._reasoners:
            return self._reasoners[ReasoningType.SPATIAL]
        if any(kw in q for kw in causal_keywords) and ReasoningType.CAUSAL in self._reasoners:
            return self._reasoners[ReasoningType.CAUSAL]

        # Fallback: first available
        if self._reasoners:
            return next(iter(self._reasoners.values()))
        return None

    def _merge_chains(self, chains: List[ReasoningChain]) -> ReasoningChain:
        """Merge multiple reasoning chains into a composite."""
        if not chains:
            return ReasoningChain()

        all_steps = []
        answers = []
        total_conf = 0.0

        for chain in chains:
            all_steps.extend(chain.steps)
            if chain.final_answer:
                answers.append(chain.final_answer)
            total_conf += chain.total_confidence

        return ReasoningChain(
            steps=all_steps,
            final_answer=" | ".join(answers),
            total_confidence=total_conf / len(chains) if chains else 0.0,
            metadata={"merged_from": len(chains)},
        )

    def health(self) -> Dict[str, Any]:
        return {
            "reasoners": {rt.value: r.health() for rt, r in self._reasoners.items()},
            "cache": self._cache.stats() if self._cache else None,
            "total_orchestrations": self._total_orchestrations,
        }


# =============================================================================
# Factory
# =============================================================================


def create_reasoning_orchestrator(
    reasoners: Optional[List[BaseReasoner]] = None,
    config: Optional[ReasoningConfig] = None,
) -> ReasoningOrchestrator:
    """Factory function for ReasoningOrchestrator."""
    return ReasoningOrchestrator(config=config, reasoners=reasoners)
