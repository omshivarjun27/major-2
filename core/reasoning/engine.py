"""
Reasoning Engine — Unified query-response orchestrator.

Routes questions to VQA, OCR, or Memory subsystems based on
query classification, with fallback chain for resilience.
"""

import logging
import time
from typing import Any, Optional

from shared.schemas import ReasoningResult

logger = logging.getLogger("reasoning-engine")


class QueryClassifier:
    """Classify questions into routing targets (VQA, OCR, Memory)."""

    VISUAL_PATTERNS = [
        "what do you see",
        "describe",
        "how many",
        "is there",
        "what is",
        "what are",
        "look",
    ]
    TEXT_PATTERNS = [
        "read",
        "what does it say",
        "text on",
        "sign",
        "label",
        "writing",
        "ocr",
    ]
    RECALL_PATTERNS = [
        "remember",
        "earlier",
        "before",
        "last time",
        "did i see",
        "history",
        "recall",
    ]

    def classify(self, question: str, has_image: bool = False) -> str:
        """Classify a question into a routing target.

        Returns:
            One of "vqa", "ocr", "memory".
        """
        q = question.lower().strip()

        for pattern in self.TEXT_PATTERNS:
            if pattern in q:
                return "ocr" if has_image else "memory"

        for pattern in self.RECALL_PATTERNS:
            if pattern in q:
                return "memory"

        for pattern in self.VISUAL_PATTERNS:
            if pattern in q:
                return "vqa" if has_image else "memory"

        # Default: VQA if image present, else memory
        return "vqa" if has_image else "memory"


class ReasoningEngine:
    """Orchestrates VQA, OCR, and Memory into a unified query-response flow.

    Usage:
        engine = ReasoningEngine(vqa_reasoner=vqa, ocr_reader=ocr, memory_retriever=mem)
        result = await engine.reason("What do you see?", image=img)
    """

    def __init__(
        self,
        vqa_reasoner: Optional[Any] = None,
        ocr_reader: Optional[Any] = None,
        memory_retriever: Optional[Any] = None,
        classifier: Optional[QueryClassifier] = None,
    ):
        self._vqa = vqa_reasoner
        self._ocr = ocr_reader
        self._memory = memory_retriever
        self._classifier = classifier or QueryClassifier()

    async def reason(self, question: str, image: Optional[Any] = None) -> ReasoningResult:
        """Route a question to the appropriate subsystem and return a unified result.

        Args:
            question: Natural language question.
            image: Optional image (PIL Image or numpy array).

        Returns:
            ReasoningResult with answer, source, confidence, latency, metadata.
        """
        start = time.time()
        route = self._classifier.classify(question, has_image=image is not None)

        try:
            if route == "vqa":
                return await self._route_vqa(question, image, start)
            elif route == "ocr":
                return await self._route_ocr(image, start)
            elif route == "memory":
                return await self._route_memory(question, start)
        except Exception as e:
            logger.warning("Primary route '%s' failed: %s", route, e)

        # Fallback chain: try remaining routes
        for fallback_route in ["vqa", "ocr", "memory"]:
            if fallback_route == route:
                continue
            try:
                if fallback_route == "vqa" and self._vqa and image is not None:
                    return await self._route_vqa(question, image, start)
                elif fallback_route == "ocr" and self._ocr and image is not None:
                    return await self._route_ocr(image, start)
                elif fallback_route == "memory" and self._memory:
                    return await self._route_memory(question, start)
            except Exception:
                continue

        # Final fallback
        return ReasoningResult(
            answer="I'm unable to process your question right now. Please try again.",
            source="fallback",
            confidence=0.0,
            latency_ms=(time.time() - start) * 1000,
            metadata={"route": route, "error": "all subsystems failed"},
        )

    async def _route_vqa(self, question: str, image: Any, start: float) -> ReasoningResult:
        """Route to VQA subsystem."""
        if not self._vqa:
            raise RuntimeError("VQA reasoner not configured")

        # Import locally to avoid circular deps
        from core.vqa.vqa_reasoner import VQARequest

        request = VQARequest(question=question, image=image)
        response = await self._vqa.answer(request)
        return ReasoningResult(
            answer=response.get_full_answer(),
            source="vqa",
            confidence=response.confidence,
            latency_ms=(time.time() - start) * 1000,
            metadata={"tokens_used": response.tokens_used, "vqa_source": response.source},
        )

    async def _route_ocr(self, image: Any, start: float) -> ReasoningResult:
        """Route to OCR subsystem."""
        if not self._ocr:
            raise RuntimeError("OCR reader not configured")

        result = await self._ocr(image)
        text = result.full_text if hasattr(result, "full_text") else str(result)
        confidence = result.confidence if hasattr(result, "confidence") else 0.5
        return ReasoningResult(
            answer=text or "No text detected.",
            source="ocr",
            confidence=confidence,
            latency_ms=(time.time() - start) * 1000,
            metadata={"backend": getattr(result, "backend", "unknown")},
        )

    async def _route_memory(self, question: str, start: float) -> ReasoningResult:
        """Route to Memory retrieval subsystem."""
        if not self._memory:
            raise RuntimeError("Memory retriever not configured")

        results = await self._memory.search(question)
        if results:
            top = results[0]
            summary = top.get("summary", str(top)) if isinstance(top, dict) else str(top)
            return ReasoningResult(
                answer=summary,
                source="memory",
                confidence=0.7,
                latency_ms=(time.time() - start) * 1000,
                metadata={"hits": len(results)},
            )
        return ReasoningResult(
            answer="I don't have any relevant memories about that.",
            source="memory",
            confidence=0.1,
            latency_ms=(time.time() - start) * 1000,
            metadata={"hits": 0},
        )


def create_reasoning_engine(
    vqa_reasoner: Optional[Any] = None,
    ocr_reader: Optional[Any] = None,
    memory_retriever: Optional[Any] = None,
) -> ReasoningEngine:
    """Factory to assemble a ReasoningEngine with graceful degradation.

    Any subsystem can be None — the engine will skip unavailable routes.
    """
    engine = ReasoningEngine(
        vqa_reasoner=vqa_reasoner,
        ocr_reader=ocr_reader,
        memory_retriever=memory_retriever,
    )
    available = []
    if vqa_reasoner:
        available.append("vqa")
    if ocr_reader:
        available.append("ocr")
    if memory_retriever:
        available.append("memory")
    logger.info("ReasoningEngine created with subsystems: %s", available or ["none"])
    return engine
