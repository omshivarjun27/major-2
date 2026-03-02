"""Reasoning engine edge cases: ambiguous inputs, contradictory data, fallback chains."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from core.reasoning.engine import QueryClassifier, ReasoningEngine, create_reasoning_engine
from shared.schemas import ReasoningResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_vqa(answer: str = "A chair.", confidence: float = 0.85):
    """Build a mock VQA reasoner."""
    response = MagicMock()
    response.get_full_answer = MagicMock(return_value=answer)
    response.confidence = confidence
    response.tokens_used = 20
    response.source = "llm"
    reasoner = MagicMock()
    reasoner.answer = AsyncMock(return_value=response)
    return reasoner


def _mock_ocr(text: str = "Exit sign", confidence: float = 0.9):
    """Build a mock OCR reader."""
    result = MagicMock()
    result.full_text = text
    result.confidence = confidence
    result.backend = "easyocr"
    return AsyncMock(return_value=result)


def _mock_memory(results=None):
    """Build a mock memory retriever."""
    if results is None:
        results = [{"summary": "Keys on table", "score": 0.8}]
    mem = MagicMock()
    mem.search = AsyncMock(return_value=results)
    return mem


def _failing_vqa():
    """VQA that always raises."""
    reasoner = MagicMock()
    reasoner.answer = AsyncMock(side_effect=RuntimeError("VQA offline"))
    return reasoner


def _failing_ocr():
    """OCR that always raises."""
    return AsyncMock(side_effect=RuntimeError("OCR crashed"))


def _failing_memory():
    """Memory retriever that always raises."""
    mem = MagicMock()
    mem.search = AsyncMock(side_effect=RuntimeError("DB unavailable"))
    return mem


# ===========================================================================
# QueryClassifier edge cases
# ===========================================================================


class TestQueryClassifierEdgeCases:
    """Edge cases for query classification with ambiguous inputs."""

    def test_empty_question_defaults_to_memory(self):
        """Empty string with no image should route to memory."""
        c = QueryClassifier()
        assert c.classify("", has_image=False) == "memory"

    def test_empty_question_with_image_routes_vqa(self):
        """Empty string with image should route to VQA."""
        c = QueryClassifier()
        assert c.classify("", has_image=True) == "vqa"

    def test_whitespace_only_question(self):
        """Whitespace-only question defaults based on image presence."""
        c = QueryClassifier()
        assert c.classify("   \t\n", has_image=False) == "memory"
        assert c.classify("   ", has_image=True) == "vqa"

    def test_mixed_signals_text_and_visual(self):
        """Question with both visual and text patterns — text patterns checked first."""
        c = QueryClassifier()
        # 'read' matches TEXT_PATTERNS, checked first
        result = c.classify("read what do you see on the sign", has_image=True)
        assert result == "ocr"

    def test_mixed_signals_recall_and_visual(self):
        """Question with recall and visual keywords — recall patterns checked first."""
        c = QueryClassifier()
        result = c.classify("do you remember what I saw earlier?", has_image=True)
        assert result == "memory"

    def test_case_insensitivity(self):
        """Classification should be case-insensitive."""
        c = QueryClassifier()
        assert c.classify("DESCRIBE the scene", has_image=True) == "vqa"
        assert c.classify("READ THE SIGN", has_image=True) == "ocr"

    def test_unknown_question_with_image(self):
        """Unrecognized question with image defaults to VQA."""
        c = QueryClassifier()
        assert c.classify("xyzzy foobar baz", has_image=True) == "vqa"

    def test_unknown_question_without_image(self):
        """Unrecognized question without image defaults to memory."""
        c = QueryClassifier()
        assert c.classify("xyzzy foobar baz", has_image=False) == "memory"

    def test_text_pattern_without_image_routes_memory(self):
        """Text pattern (read/sign) without image routes to memory."""
        c = QueryClassifier()
        assert c.classify("read the sign for me", has_image=False) == "memory"

    def test_visual_pattern_without_image_routes_memory(self):
        """Visual pattern (describe) without image routes to memory."""
        c = QueryClassifier()
        assert c.classify("describe what you see", has_image=False) == "memory"


# ===========================================================================
# ReasoningEngine edge cases
# ===========================================================================


class TestReasoningEngineEdgeCases:
    """Edge cases for ReasoningEngine routing and fallback."""

    async def test_all_subsystems_none_returns_fallback(self):
        """Engine with no subsystems should return fallback answer."""
        engine = ReasoningEngine()
        result = await engine.reason("What do you see?", image=MagicMock())
        assert result.source == "fallback"
        assert result.confidence == 0.0

    async def test_vqa_failure_falls_back_to_ocr(self):
        """When VQA fails, engine should try OCR next (if image present)."""
        engine = ReasoningEngine(
            vqa_reasoner=_failing_vqa(),
            ocr_reader=_mock_ocr("Emergency exit"),
        )
        result = await engine.reason("What do you see?", image=MagicMock())
        assert result.source == "ocr"
        assert "Emergency exit" in result.answer

    async def test_vqa_failure_falls_back_to_memory(self):
        """When VQA fails and no OCR, engine should try memory."""
        engine = ReasoningEngine(
            vqa_reasoner=_failing_vqa(),
            memory_retriever=_mock_memory(),
        )
        result = await engine.reason("What do you see?", image=MagicMock())
        assert result.source == "memory"

    async def test_all_subsystems_fail_returns_fallback(self):
        """When all subsystems fail, engine returns fallback."""
        engine = ReasoningEngine(
            vqa_reasoner=_failing_vqa(),
            ocr_reader=_failing_ocr(),
            memory_retriever=_failing_memory(),
        )
        result = await engine.reason("anything", image=MagicMock())
        assert result.source == "fallback"
        assert result.confidence == 0.0

    async def test_memory_returns_empty_results(self):
        """Memory search returning empty list should give low-confidence answer."""
        engine = ReasoningEngine(memory_retriever=_mock_memory(results=[]))
        result = await engine.reason("do you remember my keys?")
        assert result.source == "memory"
        assert result.confidence < 0.5

    async def test_ocr_result_with_no_full_text_attr(self):
        """OCR result without full_text attribute should be stringified."""
        ocr_result = "plain string result"
        engine = ReasoningEngine(ocr_reader=AsyncMock(return_value=ocr_result))
        result = await engine.reason("read the text", image=MagicMock())
        assert result.source == "ocr"
        assert "plain string result" in result.answer

    async def test_reason_latency_is_positive(self):
        """Latency in result should always be a positive number."""
        engine = ReasoningEngine(vqa_reasoner=_mock_vqa())
        result = await engine.reason("describe this", image=MagicMock())
        assert result.latency_ms > 0

    async def test_reason_with_none_image_routes_to_memory(self):
        """No image should route to memory subsystem."""
        engine = ReasoningEngine(
            vqa_reasoner=_mock_vqa(),
            memory_retriever=_mock_memory(),
        )
        result = await engine.reason("tell me about the room")
        assert result.source == "memory"


# ===========================================================================
# create_reasoning_engine factory edge cases
# ===========================================================================


class TestCreateReasoningEngineEdgeCases:
    """Edge cases for the factory function."""

    def test_factory_all_none(self):
        """Factory with all None should still return an engine."""
        engine = create_reasoning_engine()
        assert isinstance(engine, ReasoningEngine)

    def test_factory_partial_subsystems(self):
        """Factory with only memory should work."""
        engine = create_reasoning_engine(memory_retriever=_mock_memory())
        assert isinstance(engine, ReasoningEngine)

    async def test_factory_engine_routes_correctly(self):
        """Engine from factory should route VQA questions correctly."""
        engine = create_reasoning_engine(vqa_reasoner=_mock_vqa("I see a dog"))
        result = await engine.reason("what do you see?", image=MagicMock())
        assert "dog" in result.answer
        assert result.source == "vqa"

    def test_factory_with_all_subsystems(self):
        """Factory with all subsystems should not raise."""
        engine = create_reasoning_engine(
            vqa_reasoner=_mock_vqa(),
            ocr_reader=_mock_ocr(),
            memory_retriever=_mock_memory(),
        )
        assert isinstance(engine, ReasoningEngine)


# ===========================================================================
# ReasoningResult edge cases
# ===========================================================================


class TestReasoningResultEdgeCases:
    """Edge cases for ReasoningResult schema."""

    def test_result_with_empty_answer(self):
        """ReasoningResult should accept empty string answer."""
        r = ReasoningResult(answer="", source="test", confidence=0.0, latency_ms=1.0)
        assert r.answer == ""

    def test_result_metadata_defaults_to_none_or_empty(self):
        """Metadata should have a sensible default."""
        r = ReasoningResult(answer="ok", source="test", confidence=1.0, latency_ms=0.5)
        assert r.metadata is None or isinstance(r.metadata, dict)

    def test_result_confidence_bounds(self):
        """Confidence 0.0 and 1.0 should both be valid."""
        r0 = ReasoningResult(answer="a", source="s", confidence=0.0, latency_ms=1.0)
        r1 = ReasoningResult(answer="a", source="s", confidence=1.0, latency_ms=1.0)
        assert r0.confidence == 0.0
        assert r1.confidence == 1.0
