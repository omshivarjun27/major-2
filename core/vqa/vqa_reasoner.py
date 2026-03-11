"""
VQA Engine - VQA Reasoner Module
=================================

Integrates perception outputs with LLM (qwen3-vl) for
visual question answering and micro-navigation formatting.
"""

import base64
import io
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PIL import Image

from shared.schemas import Priority

from .scene_graph import SceneGraph
from .spatial_fuser import FusedObstacle, FusedResult

logger = logging.getLogger("vqa-reasoner")


# ============================================================================
# Prompt Templates
# ============================================================================

class PromptTemplates:
    """
    Prompt templates for qwen3-vl VQA tasks.
    Optimized for minimal token usage while maintaining accuracy.
    """

    # Base system prompt for all VQA tasks
    SYSTEM = """You are Ally, a vision assistant for blind users. Give brief, clear audio-friendly answers.
Rules:
- Use clock positions (12 o'clock=ahead) or left/right
- Use metric distances (meters)
- Critical obstacles < 1m must warn first
- Be concise, no visual formatting
- If uncertain, say "possibly" or "unclear\""""

    # Spatial/navigation prompt
    SPATIAL = """Scene data:
{scene_json}

User asks: {question}

Reply in 1-2 sentences with distances and directions."""

    # Object identification prompt
    IDENTIFY = """Detected objects:
{objects}

User asks: {question}

Identify the specific object(s) briefly."""

    # Scene description prompt
    DESCRIBE = """Scene summary:
{summary}

Obstacles:
{obstacles}

Describe the scene briefly for navigation."""

    # Safety warning prompt
    SAFETY_WARNING = """Critical: {object} detected {distance}m {direction}.
{action}"""

    # MicroNav format for realtime navigation
    MICRONAV = """{safety_prefix}{count} object(s). {primary}. {action}."""

    @classmethod
    def format_spatial(cls, scene_json: str, question: str) -> str:
        return cls.SPATIAL.format(scene_json=scene_json, question=question)

    @classmethod
    def format_identify(cls, objects: str, question: str) -> str:
        return cls.IDENTIFY.format(objects=objects, question=question)

    @classmethod
    def format_describe(cls, summary: str, obstacles: str) -> str:
        return cls.DESCRIBE.format(summary=summary, obstacles=obstacles)

    @classmethod
    def format_safety(cls, obj: str, distance: float, direction: str, action: str) -> str:
        return cls.SAFETY_WARNING.format(
            object=obj,
            distance=f"{distance:.1f}",
            direction=direction,
            action=action,
        )

    @classmethod
    def format_micronav(
        cls,
        count: int,
        primary: str,
        action: str,
        safety_prefix: str = "",
    ) -> str:
        return cls.MICRONAV.format(
            safety_prefix=safety_prefix,
            count=count,
            primary=primary,
            action=action,
        )


# ============================================================================
# MicroNav Formatter
# ============================================================================

class MicroNavFormatter:
    """
    Formats perception results into ultra-brief navigation phrases.
    Target: <50 tokens for TTS output.
    """

    CLOCK_POSITIONS = {
        (-35, -25): "10 o'clock",
        (-25, -15): "11 o'clock",
        (-15, -5): "11 o'clock",
        (-5, 5): "12 o'clock",
        (5, 15): "1 o'clock",
        (15, 25): "1 o'clock",
        (25, 35): "2 o'clock",
    }

    def __init__(self, use_clock_positions: bool = False):
        self.use_clock_positions = use_clock_positions

    def format(
        self,
        fused: FusedResult,
        scene_graph: Optional[SceneGraph] = None,
    ) -> str:
        """
        Format fused result into micro-nav phrase.

        Returns concise phrase like:
        "2 objects. Chair 1.5m left. Step right."
        """
        if not fused.obstacles:
            return "Path clear ahead."

        # Check for uncertain/low confidence
        safety_prefix = fused.generate_safety_prefix()

        # Get primary obstacle (closest)
        primary = fused.get_closest()
        critical = fused.get_critical()

        # Format primary obstacle
        primary_str = self._format_obstacle(primary)

        # Determine action
        if critical:
            action = self._format_critical_action(critical[0])
        elif primary:
            action = self._format_action(primary)
        else:
            action = "Proceed with caution"

        return PromptTemplates.format_micronav(
            count=len(fused.obstacles),
            primary=primary_str,
            action=action,
            safety_prefix=safety_prefix,
        )

    def _format_obstacle(self, obs: FusedObstacle) -> str:
        """Format single obstacle."""
        distance = self._format_distance(obs.depth_m)
        direction = self._format_direction(obs.bbox.center[0], 640)  # Assume 640px width
        return f"{obs.class_name} {distance} {direction}"

    def _format_distance(self, depth_m: float) -> str:
        """Format distance for speech."""
        if depth_m < 0.5:
            return "very close"
        elif depth_m < 1.0:
            return "half meter"
        elif depth_m == float('inf') or depth_m != depth_m:
            return "unknown distance"
        elif depth_m < 2.0:
            return f"{depth_m:.1f}m"
        else:
            return f"{int(round(depth_m))}m"

    def _format_direction(self, center_x: int, img_width: int) -> str:
        """Format direction from image position."""
        normalized = (center_x - img_width / 2) / (img_width / 2)
        angle = normalized * 35  # Assume 70 deg FOV

        if self.use_clock_positions:
            for (min_a, max_a), clock in self.CLOCK_POSITIONS.items():
                if min_a <= angle < max_a:
                    return clock
            return "ahead"

        if angle < -15:
            return "left"
        elif angle < -5:
            return "slightly left"
        elif angle < 5:
            return "ahead"
        elif angle < 15:
            return "slightly right"
        else:
            return "right"

    def _format_critical_action(self, obs: FusedObstacle) -> str:
        """Format action for critical obstacle."""
        cx = obs.bbox.center[0]
        if cx < 213:  # Left third
            return "Stop, step right"
        elif cx > 427:  # Right third
            return "Stop, step left"
        else:
            return "Stop and reassess"

    def _format_action(self, obs: FusedObstacle) -> str:
        """Format action for non-critical obstacle."""
        priority = obs.get_priority()
        cx = obs.bbox.center[0]

        if priority == Priority.NEAR_HAZARD:
            prefix = "Caution, "
        else:
            prefix = ""

        if cx < 213:
            return f"{prefix}step right"
        elif cx > 427:
            return f"{prefix}step left"
        return f"{prefix}proceed carefully"


# ============================================================================
# VQA Request/Response
# ============================================================================

@dataclass
class VQARequest:
    """Request for VQA reasoning."""
    question: str
    image: Optional[Image.Image] = None
    scene_graph: Optional[SceneGraph] = None
    fused_result: Optional[FusedResult] = None
    use_image: bool = True
    max_tokens: int = 150
    temperature: float = 0.2


@dataclass
class VQAResponse:
    """Response from VQA reasoning."""
    answer: str
    confidence: float
    processing_time_ms: float
    tokens_used: int = 0
    source: str = "llm"  # "llm", "cache", "fallback"
    safety_prefix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "confidence": round(self.confidence, 3),
            "processing_time_ms": round(self.processing_time_ms, 1),
            "tokens_used": self.tokens_used,
            "source": self.source,
            "safety_prefix": self.safety_prefix,
        }

    def get_full_answer(self) -> str:
        """Get answer with safety prefix if applicable."""
        if self.safety_prefix:
            return f"{self.safety_prefix}{self.answer}"
        return self.answer


# ============================================================================
# VQA Reasoner
# ============================================================================

class VQAReasoner:
    """
    Main VQA reasoning class.
    Integrates with qwen3-vl via OpenAI-compatible API.

    Usage:
        reasoner = VQAReasoner(llm_client=my_openai_client)
        response = await reasoner.answer(request)
    """

    def __init__(
        self,
        llm_client: Any = None,
        model: str = "qwen3.5:397b-cloud",
        api_base: str = "http://localhost:11434/v1",
        use_micronav_fallback: bool = True,
    ):
        """
        Initialize VQA reasoner.

        Args:
            llm_client: OpenAI-compatible async client (optional)
            model: Model name for VQA
            api_base: API base URL
            use_micronav_fallback: Fall back to MicroNav if LLM fails
        """
        self.model = model
        self.api_base = api_base
        self.use_micronav_fallback = use_micronav_fallback
        self._llm = llm_client
        self._micronav = MicroNavFormatter()
        self._cache: Dict[str, VQAResponse] = {}
        self._cache_ttl = 5.0  # seconds
        self._CACHE_MAX = 128  # bounded to prevent memory leak

        # Stats
        self._total_requests = 0
        self._cache_hits = 0
        self._avg_latency_ms = 0.0

    async def answer(self, request: VQARequest) -> VQAResponse:
        """
        Answer a VQA question using scene data and optionally the image.

        Args:
            request: VQA request with question and scene data

        Returns:
            VQAResponse with answer and metadata
        """
        start_time = time.time()
        self._total_requests += 1

        # Check cache
        cache_key = self._get_cache_key(request)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - (start_time - cached.processing_time_ms / 1000) < self._cache_ttl:
                self._cache_hits += 1
                return VQAResponse(
                    answer=cached.answer,
                    confidence=cached.confidence,
                    processing_time_ms=0.5,
                    source="cache",
                    safety_prefix=cached.safety_prefix,
                )

        # Determine safety prefix from fused result
        safety_prefix = ""
        if request.fused_result:
            safety_prefix = request.fused_result.generate_safety_prefix()

        # Try LLM-based reasoning
        try:
            if self._llm:
                response = await self._reason_with_llm(request)
                response.safety_prefix = safety_prefix

                # Update cache (bounded)
                if len(self._cache) >= self._CACHE_MAX:
                    oldest = next(iter(self._cache))
                    del self._cache[oldest]
                self._cache[cache_key] = response

                # Update stats
                elapsed = (time.time() - start_time) * 1000
                self._avg_latency_ms = (self._avg_latency_ms * 0.9) + (elapsed * 0.1)

                return response
        except Exception as e:
            logger.warning(f"LLM reasoning failed: {e}")

        # Fall back to MicroNav formatting
        if self.use_micronav_fallback and request.fused_result:
            answer = self._micronav.format(request.fused_result, request.scene_graph)
            elapsed = (time.time() - start_time) * 1000

            return VQAResponse(
                answer=answer,
                confidence=0.6,
                processing_time_ms=elapsed,
                source="fallback",
                safety_prefix=safety_prefix,
            )

        # Final fallback
        elapsed = (time.time() - start_time) * 1000
        return VQAResponse(
            answer="Unable to analyze the scene. Please try again.",
            confidence=0.0,
            processing_time_ms=elapsed,
            source="error",
        )

    async def _reason_with_llm(self, request: VQARequest) -> VQAResponse:
        """Use LLM for VQA reasoning."""
        start_time = time.time()

        # Build messages
        messages = [
            {"role": "system", "content": PromptTemplates.SYSTEM}
        ]

        # Build user content
        content = []

        # Add image if available and requested
        if request.use_image and request.image:
            img_b64 = self._encode_image(request.image)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        # Add scene context if available
        if request.scene_graph:
            scene_json = self._format_scene_for_prompt(request.scene_graph)
            text = PromptTemplates.format_spatial(scene_json, request.question)
        elif request.fused_result:
            obstacles_str = self._format_obstacles_for_prompt(request.fused_result.obstacles)
            text = PromptTemplates.format_identify(obstacles_str, request.question)
        else:
            text = request.question

        content.append({"type": "text", "text": text})
        messages.append({"role": "user", "content": content})

        # Call LLM
        response = await self._llm.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        answer = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else 0

        elapsed = (time.time() - start_time) * 1000

        return VQAResponse(
            answer=answer,
            confidence=0.85,
            processing_time_ms=elapsed,
            tokens_used=tokens_used,
            source="llm",
        )

    def _encode_image(self, image: Image.Image, max_size: int = 512) -> str:
        """Encode image to base64 for LLM."""
        # Resize if needed
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.BILINEAR)

        # Convert to RGB if needed
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Encode to base64
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=80)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _format_scene_for_prompt(self, scene: SceneGraph) -> str:
        """Format scene graph as compact JSON for prompt."""
        compact = []
        for obs in scene.obstacles[:5]:  # Limit to 5 obstacles
            compact.append({
                "obj": obs.class_name,
                "dist": f"{obs.distance_m:.1f}m",
                "dir": obs.direction.value,
                "priority": obs.priority.value,
            })

        import json
        return json.dumps(compact, separators=(',', ':'))

    def _format_obstacles_for_prompt(self, obstacles: List[FusedObstacle]) -> str:
        """Format obstacles as text for prompt."""
        lines = []
        for obs in obstacles[:5]:
            lines.append(f"- {obs.class_name}: {obs.depth_m:.1f}m")
        return "\n".join(lines)

    def _get_cache_key(self, request: VQARequest) -> str:
        """Generate cache key from request."""
        key_parts = [request.question.lower()[:50]]

        if request.fused_result:
            for obs in request.fused_result.obstacles[:3]:
                depth_val = obs.depth_m if not (obs.depth_m == float('inf') or obs.depth_m != obs.depth_m) else 999
                key_parts.append(f"{obs.class_name}:{int(depth_val*10)}")

        return "|".join(key_parts)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": self._cache_hits / max(1, self._total_requests),
            "avg_latency_ms": round(self._avg_latency_ms, 1),
        }


# ============================================================================
# Quick Navigation Answers
# ============================================================================

class QuickAnswers:
    """
    Pre-computed answers for common navigation queries.
    Bypasses LLM for sub-10ms response time.
    """

    PATTERNS = {
        "clear": [
            "what's ahead",
            "is path clear",
            "can i go",
            "anything in front",
        ],
        "obstacles": [
            "what obstacles",
            "what's blocking",
            "any hazards",
        ],
        "directions": [
            "which way",
            "where should i go",
            "how to avoid",
        ],
    }

    @classmethod
    def try_quick_answer(
        cls,
        question: str,
        fused: FusedResult,
    ) -> Optional[str]:
        """
        Try to generate quick answer without LLM.
        Returns None if question doesn't match patterns.
        """
        q_lower = question.lower()

        # Check "clear path" questions
        for pattern in cls.PATTERNS["clear"]:
            if pattern in q_lower:
                if not fused.obstacles:
                    return "Path clear ahead, safe to proceed."
                critical = fused.get_critical()
                if critical:
                    c = critical[0]
                    return f"Warning: {c.class_name} {c.depth_m:.1f}m ahead. Stop."
                closest = fused.get_closest()
                if closest:
                    return f"{closest.class_name} detected {closest.depth_m:.1f}m away. Proceed with caution."
                return None

        # Check "obstacles" questions
        for pattern in cls.PATTERNS["obstacles"]:
            if pattern in q_lower:
                if not fused.obstacles:
                    return "No obstacles detected."
                return f"{len(fused.obstacles)} object(s) detected nearby."

        return None
