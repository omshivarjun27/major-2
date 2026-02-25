"""
Tests for Reasoning Engine MVP (T-032)
=======================================

Tests for QueryClassifier, ReasoningEngine, and create_reasoning_engine
in core/reasoning/engine.py. All subsystems are mocked.
"""

from unittest.mock import AsyncMock, MagicMock

from core.reasoning.engine import QueryClassifier, ReasoningEngine, create_reasoning_engine
from shared.schemas import ReasoningResult

# ============================================================================
# Helpers
# ============================================================================


def _mock_vqa_reasoner(answer: str = "I see a chair."):
    """Build a mock VQA reasoner that returns a canned response."""
    response = MagicMock()
    response.get_full_answer = MagicMock(return_value=answer)
    response.confidence = 0.85
    response.tokens_used = 30
    response.source = "llm"

    reasoner = MagicMock()
    reasoner.answer = AsyncMock(return_value=response)
    return reasoner


def _mock_ocr_reader(text: str = "Exit door ahead"):
    """Build a mock OCR reader (async callable returning OCRResult-like)."""
    result = MagicMock()
    result.full_text = text
    result.confidence = 0.9
    result.backend = "easyocr"
    return AsyncMock(return_value=result)


def _mock_memory_retriever(results=None):
    """Build a mock memory retriever with search()."""
    if results is None:
        results = [{"summary": "Keys on the kitchen table", "score": 0.8}]
    retriever = MagicMock()
    retriever.search = AsyncMock(return_value=results)
    return retriever


# ============================================================================
# QueryClassifier Tests
# ============================================================================


class TestQueryClassifier:
    """Tests for QueryClassifier routing."""

    def test_classify_visual_question(self):
        """Visual questions with image route to VQA."""
        c = QueryClassifier()
        assert c.classify("what do you see?", has_image=True) == "vqa"
        assert c.classify("describe the scene", has_image=True) == "vqa"
        assert c.classify("how many people are there?", has_image=True) == "vqa"

    def test_classify_text_question(self):
        """Text-reading questions with image route to OCR."""
        c = QueryClassifier()
        assert c.classify("read the sign", has_image=True) == "ocr"
        assert c.classify("what does it say on the label?", has_image=True) == "ocr"

    def test_classify_recall_question(self):
        """Recall questions route to Memory regardless of image."""
        c = QueryClassifier()
        assert c.classify("what did I see earlier?", has_image=False) == "memory"
        assert c.classify("do you remember the keys?", has_image=True) == "memory"
        assert c.classify("what happened last time?", has_image=False) == "memory"


# ============================================================================
# ReasoningEngine Tests
# ============================================================================


class TestReasoningEngine:
    """Tests for ReasoningEngine routing and fallback."""

    async def test_reason_vqa_route(self):
        """Engine calls VQA reasoner for visual questions with image."""
        vqa = _mock_vqa_reasoner("There is a chair 2m ahead.")
        engine = ReasoningEngine(vqa_reasoner=vqa)

        result = await engine.reason("What do you see?", image="fake_image")

        assert isinstance(result, ReasoningResult)
        assert result.source == "vqa"
        assert result.confidence > 0
        assert "chair" in result.answer.lower()
        vqa.answer.assert_called_once()

    async def test_reason_fallback_on_failure(self):
        """Engine falls back to generic response when all subsystems fail."""
        # VQA that raises
        vqa = MagicMock()
        vqa.answer = AsyncMock(side_effect=RuntimeError("LLM down"))

        engine = ReasoningEngine(vqa_reasoner=vqa)
        result = await engine.reason("What do you see?", image="fake_image")

        assert result.source == "fallback"
        assert result.confidence == 0.0
        assert "unable" in result.answer.lower() or "try again" in result.answer.lower()


# ============================================================================
# Factory Tests
# ============================================================================


class TestFactory:
    """Tests for create_reasoning_engine factory."""

    def test_factory_creates_engine(self):
        """create_reasoning_engine returns configured ReasoningEngine."""
        vqa = _mock_vqa_reasoner()
        ocr = _mock_ocr_reader()
        mem = _mock_memory_retriever()

        engine = create_reasoning_engine(
            vqa_reasoner=vqa,
            ocr_reader=ocr,
            memory_retriever=mem,
        )

        assert isinstance(engine, ReasoningEngine)
        assert engine._vqa is vqa
        assert engine._ocr is ocr
        assert engine._memory is mem

    def test_factory_graceful_degradation(self):
        """Factory works with None subsystems (graceful degradation)."""
        engine = create_reasoning_engine()
        assert isinstance(engine, ReasoningEngine)
        assert engine._vqa is None
        assert engine._ocr is None
        assert engine._memory is None
