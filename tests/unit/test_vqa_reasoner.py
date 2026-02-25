"""
Tests for VQA Reasoner Module (T-025)
======================================

Tests for VQAReasoner, QuickAnswers, and MicroNavFormatter in
core/vqa/vqa_reasoner.py. All LLM calls are mocked.
"""

import time
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from core.vqa.spatial_fuser import FusedObstacle, FusedResult
from core.vqa.vqa_reasoner import (
    MicroNavFormatter,
    QuickAnswers,
    VQAReasoner,
    VQARequest,
    VQAResponse,
)
from shared.schemas import BoundingBox, DepthMap, PerceptionResult

# ============================================================================
# Test Helpers
# ============================================================================


def _make_obstacle(
    class_name: str = "chair",
    depth_m: float = 2.0,
    cx: int = 320,
    confidence: float = 0.8,
    is_uncertain: bool = False,
) -> FusedObstacle:
    """Build a FusedObstacle with sensible defaults."""
    half = 40
    return FusedObstacle(
        id=f"obs_{class_name}",
        class_name=class_name,
        bbox=BoundingBox(cx - half, 200, cx + half, 300),
        depth_m=depth_m,
        depth_variance=0.1,
        fused_confidence=confidence,
        mask_confidence=confidence,
        is_uncertain=is_uncertain,
    )


def _make_fused(obstacles: Optional[List[FusedObstacle]] = None) -> FusedResult:
    """Build a FusedResult with given obstacles (empty PerceptionResult)."""
    depth_arr = np.full((120, 160), 5.0, dtype=np.float32)
    perception = PerceptionResult(
        detections=[],
        masks=[],
        depth_map=DepthMap(
            depth_array=depth_arr,
            min_depth=5.0,
            max_depth=5.0,
            is_metric=False,
        ),
        image_size=(640, 480),
        latency_ms=10.0,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )
    return FusedResult(
        obstacles=obstacles or [],
        tracks=[],
        frame_dt=0.033,
        timestamp=time.time(),
        perception=perception,
    )


def _make_mock_llm(answer_text: str = "I see a chair ahead.") -> MagicMock:
    """Build a mock OpenAI-compatible async LLM client."""
    usage = MagicMock()
    usage.total_tokens = 42

    message = MagicMock()
    message.content = answer_text

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage

    completions = AsyncMock()
    completions.create = AsyncMock(return_value=response)

    chat = MagicMock()
    chat.completions = completions

    client = MagicMock()
    client.chat = chat
    return client


# ============================================================================
# QuickAnswers Tests
# ============================================================================


class TestQuickAnswers:
    """Tests for QuickAnswers pattern matching."""

    def test_clear_path_patterns(self):
        """Clear-path questions with empty obstacles return 'Path clear'."""
        fused = _make_fused([])
        answer = QuickAnswers.try_quick_answer("what's ahead of me?", fused)
        assert answer is not None
        assert "clear" in answer.lower(), f"Expected 'clear' in: {answer}"

        # With critical obstacle
        critical = _make_obstacle("person", depth_m=0.5, cx=320)
        fused_crit = _make_fused([critical])
        answer_crit = QuickAnswers.try_quick_answer("is path clear?", fused_crit)
        assert answer_crit is not None
        assert "warning" in answer_crit.lower() or "stop" in answer_crit.lower()

        # With non-critical closest obstacle
        far = _make_obstacle("table", depth_m=3.0)
        fused_far = _make_fused([far])
        answer_far = QuickAnswers.try_quick_answer("can i go forward?", fused_far)
        assert answer_far is not None
        assert "table" in answer_far.lower()

    def test_obstacle_patterns(self):
        """Obstacle questions return counts or 'No obstacles'."""
        # No obstacles
        fused_empty = _make_fused([])
        answer = QuickAnswers.try_quick_answer("what obstacles are there?", fused_empty)
        assert answer is not None
        assert "no obstacles" in answer.lower()

        # Multiple obstacles
        obs = [_make_obstacle("chair", 2.0), _make_obstacle("table", 3.0)]
        fused_full = _make_fused(obs)
        answer = QuickAnswers.try_quick_answer("what obstacles are around?", fused_full)
        assert answer is not None
        assert "2" in answer

    def test_nonmatching_returns_none(self):
        """Questions not matching any pattern return None."""
        fused = _make_fused([_make_obstacle()])
        assert QuickAnswers.try_quick_answer("what color is the sky?", fused) is None
        assert QuickAnswers.try_quick_answer("tell me a joke", fused) is None


# ============================================================================
# MicroNavFormatter Tests
# ============================================================================


class TestMicroNavFormatter:
    """Tests for MicroNavFormatter output."""

    def test_format_with_obstacles(self):
        """Formatter produces obstacle description with count and action."""
        obs = [
            _make_obstacle("chair", depth_m=1.5, cx=200),
            _make_obstacle("table", depth_m=3.0, cx=500),
        ]
        fused = _make_fused(obs)
        formatter = MicroNavFormatter()
        result = formatter.format(fused)

        assert "2 object" in result, f"Expected '2 object' in: {result}"
        assert "chair" in result.lower(), f"Expected 'chair' in: {result}"

    def test_format_empty_scene(self):
        """Empty obstacles produce 'Path clear ahead.'."""
        fused = _make_fused([])
        formatter = MicroNavFormatter()
        result = formatter.format(fused)
        assert result == "Path clear ahead."


# ============================================================================
# VQAReasoner Tests
# ============================================================================


class TestVQAReasoner:
    """Tests for VQAReasoner with mock LLM."""

    async def test_answer_with_mock_llm(self):
        """Reasoner returns LLM answer with correct source and metadata."""
        mock_llm = _make_mock_llm("There is a chair 2 meters ahead.")
        reasoner = VQAReasoner(llm_client=mock_llm)

        fused = _make_fused([_make_obstacle("chair", 2.0)])
        request = VQARequest(
            question="What do you see?",
            fused_result=fused,
        )
        response = await reasoner.answer(request)

        assert isinstance(response, VQAResponse)
        assert response.source == "llm"
        assert response.confidence > 0
        assert "chair" in response.answer.lower()
        assert response.tokens_used == 42

    async def test_cache_hit_on_repeat(self):
        """Second identical request returns source='cache'."""
        mock_llm = _make_mock_llm("A table nearby.")
        reasoner = VQAReasoner(llm_client=mock_llm)

        fused = _make_fused([_make_obstacle("table", 1.8)])
        request = VQARequest(question="What is near me?", fused_result=fused)

        first = await reasoner.answer(request)
        assert first.source == "llm"

        second = await reasoner.answer(request)
        assert second.source == "cache", f"Expected 'cache', got '{second.source}'"
        assert second.processing_time_ms == pytest.approx(0.5, abs=0.1)

    async def test_safety_prefix_critical(self):
        """Critical obstacle produces safety prefix and get_full_answer includes it."""
        mock_llm = _make_mock_llm("Be careful, chair very close.")
        reasoner = VQAReasoner(llm_client=mock_llm)

        # Uncertain obstacle triggers "Possible: " prefix
        critical = _make_obstacle("person", depth_m=0.5, is_uncertain=True)
        fused = _make_fused([critical])
        request = VQARequest(question="Is it safe?", fused_result=fused)

        response = await reasoner.answer(request)
        assert response.safety_prefix != "", "Expected non-empty safety_prefix for uncertain obstacle"

        full = response.get_full_answer()
        assert full.startswith(response.safety_prefix)
        assert len(full) > len(response.answer)

    async def test_stats_tracking(self):
        """Stats correctly track total_requests, cache_hits, and cache_hit_rate."""
        mock_llm = _make_mock_llm("Answer.")
        reasoner = VQAReasoner(llm_client=mock_llm)

        # 3 unique questions
        for i in range(3):
            fused = _make_fused([_make_obstacle(f"obj{i}", float(i + 1))])
            req = VQARequest(question=f"Question {i}?", fused_result=fused)
            await reasoner.answer(req)

        # 2 cache hits (repeat questions 0 and 1)
        for i in range(2):
            fused = _make_fused([_make_obstacle(f"obj{i}", float(i + 1))])
            req = VQARequest(question=f"Question {i}?", fused_result=fused)
            await reasoner.answer(req)

        stats = reasoner.get_stats()
        assert stats["total_requests"] == 5
        assert stats["cache_hits"] == 2
        assert stats["cache_hit_rate"] == pytest.approx(0.4, abs=0.01)
