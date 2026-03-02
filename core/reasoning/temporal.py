"""
Temporal Reasoning Module (T-121).

Detects temporal patterns, relations, and sequences from observed events.
Builds timeline summaries for blind-user narration.
"""

from __future__ import annotations

import collections
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

from core.reasoning.reasoning_foundation import (
    BaseReasoner,
    ReasoningChain,
    ReasoningConfig,
    ReasoningStep,
    ReasoningType,
)

logger = logging.getLogger("temporal-reasoning")


# =============================================================================
# Data Structures
# =============================================================================


class TemporalRelation(str, Enum):
    """Allen's interval algebra relations (simplified)."""

    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    OVERLAPS = "overlaps"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    SIMULTANEOUS = "simultaneous"


@dataclass
class TemporalEvent:
    """An event with temporal extent."""

    event_type: str
    timestamp_ms: float
    duration_ms: float = 0.0
    description: str = ""
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def end_ms(self) -> float:
        return self.timestamp_ms + self.duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp_ms": self.timestamp_ms,
            "duration_ms": self.duration_ms,
            "description": self.description,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class TemporalPattern:
    """A detected temporal pattern between events."""

    events: List[TemporalEvent] = field(default_factory=list)
    relation: TemporalRelation = TemporalRelation.BEFORE
    confidence: float = 0.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "relation": self.relation.value,
            "confidence": round(self.confidence, 3),
            "description": self.description,
        }


# =============================================================================
# Temporal Reasoner
# =============================================================================


class TemporalReasoner(BaseReasoner):
    """Reasons about temporal sequences and patterns.

    Maintains an event buffer and detects temporal relations between
    events (before/after/during/overlaps/simultaneous).

    Usage::

        reasoner = TemporalReasoner()
        reasoner.add_event(TemporalEvent(event_type="person_appeared", timestamp_ms=1000))
        reasoner.add_event(TemporalEvent(event_type="door_opened", timestamp_ms=2000))
        chain = await reasoner.reason({"question": "What happened?"})
    """

    def __init__(self, config: Optional[ReasoningConfig] = None):
        self._config = config or ReasoningConfig()
        self._event_buffer: Deque[TemporalEvent] = collections.deque(maxlen=100)
        self._pattern_count = 0

    @property
    def reason_type(self) -> ReasoningType:
        return ReasoningType.TEMPORAL

    def add_event(self, event: TemporalEvent) -> None:
        """Add a temporal event to the buffer."""
        self._event_buffer.append(event)

    async def reason(self, context: Dict[str, Any]) -> ReasoningChain:
        """Analyze temporal patterns in the event buffer."""
        start_ms = time.time() * 1000
        chain = ReasoningChain(metadata={"type": "temporal"})

        try:
            events = list(self._event_buffer)
            if not events:
                chain.final_answer = "No temporal events recorded yet."
                chain.total_latency_ms = time.time() * 1000 - start_ms
                return chain

            # Step 1: Sort events
            events.sort(key=lambda e: e.timestamp_ms)
            chain.add_step(ReasoningStep(
                step_type="sort_events",
                output_data={"event_count": len(events)},
                confidence=1.0,
                latency_ms=0,
                timestamp_ms=time.time() * 1000,
            ))

            # Step 2: Detect patterns
            patterns = self._detect_patterns(events)
            chain.add_step(ReasoningStep(
                step_type="detect_patterns",
                output_data={"pattern_count": len(patterns)},
                confidence=0.7 if patterns else 0.3,
                latency_ms=0,
                timestamp_ms=time.time() * 1000,
            ))

            # Step 3: Summarize
            summary = self._summarize_timeline(patterns, events)
            chain.add_step(ReasoningStep(
                step_type="summarize",
                output_data={"summary": summary},
                confidence=0.6,
                latency_ms=0,
                timestamp_ms=time.time() * 1000,
            ))

            chain.final_answer = summary
            chain.total_latency_ms = time.time() * 1000 - start_ms
            return chain

        except Exception as exc:
            logger.error("Temporal reasoning failed: %s", exc)
            chain.final_answer = "Unable to analyze temporal patterns."
            chain.total_latency_ms = time.time() * 1000 - start_ms
            return chain

    def _detect_patterns(self, events: List[TemporalEvent]) -> List[TemporalPattern]:
        """Detect temporal patterns between consecutive event pairs."""
        patterns: List[TemporalPattern] = []
        for i in range(len(events) - 1):
            e1, e2 = events[i], events[i + 1]
            relation = self._compute_temporal_relation(e1, e2)
            conf = min(e1.confidence, e2.confidence) * 0.8
            desc = f"{e1.event_type} {relation.value} {e2.event_type}"
            patterns.append(TemporalPattern(
                events=[e1, e2],
                relation=relation,
                confidence=conf,
                description=desc,
            ))
            self._pattern_count += 1
        return patterns

    def _compute_temporal_relation(
        self, e1: TemporalEvent, e2: TemporalEvent
    ) -> TemporalRelation:
        """Compute the temporal relation between two events."""
        gap_ms = abs(e2.timestamp_ms - e1.timestamp_ms)

        # Simultaneous: events within 100ms of each other
        if gap_ms < 100:
            return TemporalRelation.SIMULTANEOUS

        # Check overlap using intervals
        e1_end = e1.end_ms
        e2_end = e2.end_ms

        if e1.timestamp_ms <= e2.timestamp_ms:
            if e1_end <= e2.timestamp_ms:
                return TemporalRelation.BEFORE
            if e1.timestamp_ms == e2.timestamp_ms:
                return TemporalRelation.STARTS_WITH
            if e1_end >= e2_end:
                return TemporalRelation.DURING
            if e1_end == e2_end:
                return TemporalRelation.ENDS_WITH
            return TemporalRelation.OVERLAPS
        else:
            return TemporalRelation.AFTER

    def _summarize_timeline(
        self, patterns: List[TemporalPattern], events: List[TemporalEvent]
    ) -> str:
        """Generate a natural-language timeline summary."""
        if not events:
            return "No events to summarize."

        if len(events) == 1:
            e = events[0]
            return f"Observed: {e.description or e.event_type}."

        parts: List[str] = []
        parts.append(f"Timeline of {len(events)} events:")
        for i, e in enumerate(events[:5]):  # Cap at 5 for brevity
            label = e.description or e.event_type
            parts.append(f"  {i + 1}. {label}")

        if patterns:
            key_pattern = max(patterns, key=lambda p: p.confidence)
            parts.append(f"Key relation: {key_pattern.description}.")

        return " ".join(parts)

    def health(self) -> Dict[str, Any]:
        return {
            "type": self.reason_type.value,
            "buffer_size": len(self._event_buffer),
            "patterns_detected": self._pattern_count,
            "status": "ok",
        }
