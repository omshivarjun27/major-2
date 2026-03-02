"""
Action Context Integration — CLIP action recognition with scene context.

Combines CLIP-based action classification with environmental scene context
to produce richer, more accurate action descriptions and risk assessments
for blind/visually impaired users.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from core.action.clip_recognizer import (
    ACTION_PROMPTS,
    ALERT_ACTIONS,
    CLIPActionRecognizer,
    CLIPActionResult,
    IndoorAction,
)

logger = logging.getLogger("action-context")


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class ActionContextConfig:
    """Configuration for action-context integration."""

    scene_weight: float = 0.4
    action_weight: float = 0.6
    min_combined_confidence: float = 0.25
    max_context_age_ms: float = 5000
    enable_temporal_smoothing: bool = True


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class SceneContext:
    """Environmental scene context for action interpretation."""

    detected_objects: List[str] = field(default_factory=list)
    scene_type: str = "unknown"
    lighting: str = "normal"
    crowd_level: str = "empty"
    timestamp_ms: float = 0.0


@dataclass
class ActionContextResult:
    """Result combining action recognition with scene context."""

    action: IndoorAction
    confidence: float
    scene_context: SceneContext
    contextual_description: str
    is_alert: bool
    risk_level: str  # "safe", "caution", "danger"
    timestamp_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "action": self.action.value,
            "confidence": round(self.confidence, 3),
            "scene_type": self.scene_context.scene_type,
            "detected_objects": self.scene_context.detected_objects,
            "lighting": self.scene_context.lighting,
            "crowd_level": self.scene_context.crowd_level,
            "contextual_description": self.contextual_description,
            "is_alert": self.is_alert,
            "risk_level": self.risk_level,
            "timestamp_ms": self.timestamp_ms,
        }

    @property
    def user_cue(self) -> str:
        """Generate human-readable cue for the user."""
        if self.is_alert:
            return f"Alert: {self.contextual_description}"
        if self.risk_level == "danger":
            return f"Warning: {self.contextual_description}"
        if self.risk_level == "caution":
            return f"Caution: {self.contextual_description}"
        return self.contextual_description


# =============================================================================
# Integrator
# =============================================================================


# Scene types that elevate risk
_HIGH_RISK_SCENES = {"crosswalk", "road", "intersection", "parking", "construction"}
_MODERATE_RISK_SCENES = {"stairs", "escalator", "elevator", "kitchen", "bathroom"}

# Actions that are dangerous in certain scene contexts
_DANGEROUS_COMBOS: Dict[str, set] = {
    "crosswalk": {IndoorAction.RUNNING, IndoorAction.FALLING, IndoorAction.STUMBLING},
    "road": {IndoorAction.WALKING, IndoorAction.RUNNING, IndoorAction.FALLING},
    "stairs": {IndoorAction.RUNNING, IndoorAction.FALLING, IndoorAction.STUMBLING},
    "kitchen": {IndoorAction.FALLING, IndoorAction.STUMBLING},
}


class ActionContextIntegrator:
    """Integrates CLIP action recognition with scene context.

    Combines action classification results with environmental scene data
    to produce contextual descriptions and risk assessments. Supports
    temporal smoothing to reduce flickering between actions.

    Args:
        config: Integration configuration.
        clip_recognizer: Optional CLIP recognizer instance.
    """

    def __init__(
        self,
        config: Optional[ActionContextConfig] = None,
        clip_recognizer: Optional[CLIPActionRecognizer] = None,
    ):
        self.config = config or ActionContextConfig()
        self._clip_recognizer = clip_recognizer or CLIPActionRecognizer()
        self._history: deque[ActionContextResult] = deque(maxlen=20)
        self._total_analyses = 0
        self._total_latency_ms = 0.0

    async def analyze(
        self,
        clip: List[np.ndarray],
        scene_context: SceneContext,
        timestamp_ms: Optional[float] = None,
    ) -> ActionContextResult:
        """Analyze video clip with scene context.

        Args:
            clip: List of video frames (numpy arrays).
            scene_context: Current scene context information.
            timestamp_ms: Optional timestamp in milliseconds.

        Returns:
            ActionContextResult with contextual action analysis.
        """
        start_ms = time.time() * 1000
        ts = timestamp_ms or start_ms

        try:
            # Run CLIP classification
            clip_result: CLIPActionResult = await self._clip_recognizer.classify(
                clip, timestamp_ms=ts
            )

            # Compute combined confidence
            action = clip_result.action
            base_confidence = clip_result.confidence

            # Adjust confidence based on scene compatibility
            scene_boost = self._scene_compatibility_boost(action, scene_context)
            combined_confidence = (
                self.config.action_weight * base_confidence
                + self.config.scene_weight * scene_boost
            )

            # Clamp confidence
            combined_confidence = max(0.0, min(1.0, combined_confidence))

            # If below threshold, mark as unknown
            if combined_confidence < self.config.min_combined_confidence:
                action = IndoorAction.UNKNOWN
                combined_confidence = 0.0

            # Compute risk and description
            risk_level = self._compute_risk_level(action, scene_context, combined_confidence)
            description = self._generate_contextual_description(action, scene_context)
            is_alert = action in ALERT_ACTIONS or risk_level == "danger"

            result = ActionContextResult(
                action=action,
                confidence=combined_confidence,
                scene_context=scene_context,
                contextual_description=description,
                is_alert=is_alert,
                risk_level=risk_level,
                timestamp_ms=ts,
            )

            # Apply temporal smoothing if enabled
            if self.config.enable_temporal_smoothing and len(self._history) > 0:
                result = self._apply_temporal_smoothing(result, self._history)

            self._history.append(result)
            latency = time.time() * 1000 - start_ms
            self._total_analyses += 1
            self._total_latency_ms += latency

            return result

        except Exception as exc:
            logger.error("Action context analysis failed: %s", exc)
            return ActionContextResult(
                action=IndoorAction.UNKNOWN,
                confidence=0.0,
                scene_context=scene_context,
                contextual_description="Unable to analyze action",
                is_alert=False,
                risk_level="safe",
                timestamp_ms=ts,
            )

    def _scene_compatibility_boost(
        self, action: IndoorAction, scene_context: SceneContext
    ) -> float:
        """Compute a scene-compatibility score [0, 1] for the action."""
        score = 0.5  # Neutral default

        scene = scene_context.scene_type.lower()
        objects = [o.lower() for o in scene_context.detected_objects]

        # Indoor actions get a boost in indoor scenes
        indoor_scenes = {"indoor", "office", "home", "kitchen", "bathroom", "bedroom"}
        outdoor_scenes = {"outdoor", "crosswalk", "road", "park", "sidewalk"}

        indoor_actions = {
            IndoorAction.COOKING, IndoorAction.TYPING, IndoorAction.READING,
            IndoorAction.WRITING, IndoorAction.CLEANING,
        }
        outdoor_actions = {
            IndoorAction.RUNNING, IndoorAction.WALKING,
        }

        if action in indoor_actions and scene in indoor_scenes:
            score = 0.8
        elif action in outdoor_actions and scene in outdoor_scenes:
            score = 0.7

        # Object-based boosts
        if action == IndoorAction.OPENING_DOOR and "door" in objects:
            score = max(score, 0.9)
        if action == IndoorAction.COOKING and ("stove" in objects or "pot" in objects):
            score = max(score, 0.85)
        if action == IndoorAction.TYPING and ("keyboard" in objects or "computer" in objects):
            score = max(score, 0.85)

        # Crowd-based adjustments
        if scene_context.crowd_level == "crowded":
            social_actions = {
                IndoorAction.TALKING, IndoorAction.WAVING, IndoorAction.SHAKING_HANDS,
            }
            if action in social_actions:
                score = max(score, 0.75)

        return score

    def _compute_risk_level(
        self,
        action: IndoorAction,
        scene_context: SceneContext,
        confidence: float,
    ) -> str:
        """Compute risk level based on action, scene, and confidence.

        Args:
            action: Detected action.
            scene_context: Current scene context.
            confidence: Combined confidence score.

        Returns:
            Risk level string: "safe", "caution", or "danger".
        """
        scene = scene_context.scene_type.lower()

        # Falling/stumbling is always dangerous
        if action in {IndoorAction.FALLING, IndoorAction.STUMBLING}:
            return "danger"

        # Check dangerous action-scene combos
        dangerous_actions = _DANGEROUS_COMBOS.get(scene, set())
        if action in dangerous_actions:
            if confidence > 0.5:
                return "danger"
            return "caution"

        # High-risk scene types
        if scene in _HIGH_RISK_SCENES:
            if action in ALERT_ACTIONS:
                return "danger"
            return "caution"

        # Moderate-risk scenes
        if scene in _MODERATE_RISK_SCENES:
            if action in ALERT_ACTIONS:
                return "caution"

        # Low-visibility conditions
        if scene_context.lighting == "dim" or scene_context.lighting == "dark":
            if action in {IndoorAction.WALKING, IndoorAction.RUNNING}:
                return "caution"

        return "safe"

    def _generate_contextual_description(
        self,
        action: IndoorAction,
        scene_context: SceneContext,
    ) -> str:
        """Generate a contextual description of the action.

        Args:
            action: Detected action.
            scene_context: Current scene context.

        Returns:
            Human-readable contextual description.
        """
        # Base action description
        prompt = ACTION_PROMPTS.get(action, "")
        if not prompt:
            return f"Activity detected in {scene_context.scene_type} environment"

        base = prompt.replace("a person ", "Someone is ").replace("two people ", "Two people are ")

        # Add scene context
        parts = [base]

        scene = scene_context.scene_type.lower()
        if scene and scene != "unknown":
            parts.append(f"in a {scene} area")

        # Add relevant object context
        relevant_objects = scene_context.detected_objects[:3]
        if relevant_objects:
            obj_str = ", ".join(relevant_objects)
            parts.append(f"near {obj_str}")

        # Add lighting context if notable
        if scene_context.lighting in ("dim", "dark"):
            parts.append("in low light")

        # Add crowd context if notable
        if scene_context.crowd_level == "crowded":
            parts.append("in a crowded space")
        elif scene_context.crowd_level == "sparse":
            parts.append("with a few people around")

        return " ".join(parts)

    def _apply_temporal_smoothing(
        self,
        result: ActionContextResult,
        history: deque[ActionContextResult],
    ) -> ActionContextResult:
        """Apply temporal smoothing to reduce action flickering.

        Args:
            result: Current analysis result.
            history: Recent result history.

        Returns:
            Smoothed ActionContextResult.
        """
        if not history:
            return result

        now_ms = result.timestamp_ms
        max_age = self.config.max_context_age_ms

        # Filter recent history within the time window
        recent = [
            h for h in history
            if (now_ms - h.timestamp_ms) <= max_age
        ]

        if not recent:
            return result

        # Count action occurrences in recent history
        action_counts: Dict[IndoorAction, int] = {}
        action_confidences: Dict[IndoorAction, List[float]] = {}
        for h in recent:
            action_counts[h.action] = action_counts.get(h.action, 0) + 1
            if h.action not in action_confidences:
                action_confidences[h.action] = []
            action_confidences[h.action].append(h.confidence)

        # Include current result
        action_counts[result.action] = action_counts.get(result.action, 0) + 1
        if result.action not in action_confidences:
            action_confidences[result.action] = []
        action_confidences[result.action].append(result.confidence)

        # Find most common action
        most_common = max(action_counts, key=lambda a: action_counts[a])

        # If current action differs from consensus and has low confidence, smooth it
        if (
            most_common != result.action
            and action_counts[most_common] >= 2
            and result.confidence < 0.6
        ):
            avg_conf = sum(action_confidences[most_common]) / len(action_confidences[most_common])
            # Only override if consensus is strong enough
            if avg_conf > result.confidence:
                smoothed_conf = avg_conf * 0.8  # Slight penalty for smoothing
                return ActionContextResult(
                    action=most_common,
                    confidence=smoothed_conf,
                    scene_context=result.scene_context,
                    contextual_description=self._generate_contextual_description(
                        most_common, result.scene_context
                    ),
                    is_alert=most_common in ALERT_ACTIONS or result.risk_level == "danger",
                    risk_level=self._compute_risk_level(
                        most_common, result.scene_context, smoothed_conf
                    ),
                    timestamp_ms=result.timestamp_ms,
                )

        return result

    def health(self) -> Dict[str, Any]:
        """Get health status of the integrator."""
        avg_latency = 0.0
        if self._total_analyses > 0:
            avg_latency = self._total_latency_ms / self._total_analyses
        return {
            "total_analyses": self._total_analyses,
            "average_latency_ms": round(avg_latency, 1),
            "history_size": len(self._history),
            "temporal_smoothing": self.config.enable_temporal_smoothing,
            "clip_recognizer_health": self._clip_recognizer.health(),
        }


def create_action_context_integrator(
    config: Optional[ActionContextConfig] = None,
    clip_recognizer: Optional[CLIPActionRecognizer] = None,
) -> ActionContextIntegrator:
    """Factory function to create an ActionContextIntegrator.

    Args:
        config: Optional configuration.
        clip_recognizer: Optional CLIP recognizer instance.

    Returns:
        Configured ActionContextIntegrator.
    """
    return ActionContextIntegrator(config=config, clip_recognizer=clip_recognizer)
