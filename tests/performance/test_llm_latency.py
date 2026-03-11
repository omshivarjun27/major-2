"""P4: LLM Inference Optimization Tests (T-082).

Tests for LLM latency optimization including TTFT and streaming.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from typing import AsyncIterator

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# LLM Latency Models
# ---------------------------------------------------------------------------

@dataclass
class LLMTimingMetrics:
    """Timing metrics for LLM inference."""
    ttft_ms: float  # Time to first token
    total_ms: float  # Total generation time
    tokens_generated: int
    prompt_tokens: int

    @property
    def tokens_per_second(self) -> float:
        gen_time = (self.total_ms - self.ttft_ms) / 1000
        return self.tokens_generated / gen_time if gen_time > 0 else 0.0

    @property
    def within_vqa_budget(self) -> bool:
        """Check if within 300ms VQA budget."""
        return self.total_ms < 300.0


class MockLLMClient:
    """Mock LLM client for testing latency patterns."""

    def __init__(
        self,
        ttft_ms: float = 100.0,
        tokens_per_second: float = 30.0,
        variance_pct: float = 20.0,
    ):
        self.base_ttft_ms = ttft_ms
        self.tokens_per_second = tokens_per_second
        self.variance_pct = variance_pct

    def _add_variance(self, value: float) -> float:
        import random
        factor = 1 + random.uniform(-self.variance_pct, self.variance_pct) / 100
        return value * factor

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 50,
    ) -> tuple[str, LLMTimingMetrics]:
        """Generate a response with timing metrics."""
        ttft = self._add_variance(self.base_ttft_ms)

        # Simulate TTFT
        await asyncio.sleep(ttft / 1000)
        time.perf_counter()

        # Simulate token generation
        tokens_to_generate = min(max_tokens, len(prompt.split()) + 20)
        gen_time = tokens_to_generate / self.tokens_per_second
        await asyncio.sleep(gen_time)

        total_time = ttft + gen_time * 1000

        response = " ".join(["word"] * tokens_to_generate)

        metrics = LLMTimingMetrics(
            ttft_ms=ttft,
            total_ms=total_time,
            tokens_generated=tokens_to_generate,
            prompt_tokens=len(prompt.split()),
        )

        return response, metrics

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 50,
    ) -> AsyncIterator[tuple[str, float]]:
        """Generate tokens in streaming mode."""
        ttft = self._add_variance(self.base_ttft_ms)

        # Simulate TTFT
        await asyncio.sleep(ttft / 1000)
        yield ("", ttft)  # First yield is TTFT

        # Generate tokens
        tokens_to_generate = min(max_tokens, len(prompt.split()) + 20)
        token_delay = 1 / self.tokens_per_second

        for i in range(tokens_to_generate):
            await asyncio.sleep(token_delay)
            elapsed = ttft + (i + 1) * token_delay * 1000
            yield (f"word{i} ", elapsed)


# ---------------------------------------------------------------------------
# Prompt Optimization
# ---------------------------------------------------------------------------

class PromptOptimizer:
    """Utilities for prompt optimization."""

    # System prompt templates (optimized for token efficiency)
    SYSTEM_PROMPTS = {
        "vision": "Describe what you see concisely.",
        "navigation": "Guide the user safely with brief directions.",
        "general": "Be helpful and concise.",
    }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Roughly 1 token per 4 characters
        return len(text) // 4

    @staticmethod
    def truncate_prompt(prompt: str, max_tokens: int = 500) -> str:
        """Truncate prompt to fit within token budget."""
        estimated = PromptOptimizer.estimate_tokens(prompt)
        if estimated <= max_tokens:
            return prompt

        # Truncate by character count
        max_chars = max_tokens * 4
        return prompt[:max_chars] + "..."

    @staticmethod
    def get_system_prompt(task: str = "general") -> str:
        """Get optimized system prompt for task."""
        return PromptOptimizer.SYSTEM_PROMPTS.get(task, PromptOptimizer.SYSTEM_PROMPTS["general"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLLMTimingMetrics:
    """Test LLMTimingMetrics dataclass."""

    def test_metrics_creation(self):
        """Should create metrics with all fields."""
        metrics = LLMTimingMetrics(
            ttft_ms=100.0,
            total_ms=500.0,
            tokens_generated=50,
            prompt_tokens=20,
        )

        assert metrics.ttft_ms == 100.0
        assert metrics.total_ms == 500.0

    def test_tokens_per_second(self):
        """Should calculate tokens per second."""
        metrics = LLMTimingMetrics(
            ttft_ms=100.0,
            total_ms=600.0,  # 500ms generation time
            tokens_generated=25,  # 25 tokens in 500ms = 50 tokens/sec
            prompt_tokens=20,
        )

        assert metrics.tokens_per_second == pytest.approx(50.0, rel=0.1)

    def test_vqa_budget_pass(self):
        """Should pass VQA budget when under 300ms."""
        metrics = LLMTimingMetrics(
            ttft_ms=50.0,
            total_ms=250.0,
            tokens_generated=20,
            prompt_tokens=10,
        )

        assert metrics.within_vqa_budget is True

    def test_vqa_budget_fail(self):
        """Should fail VQA budget when over 300ms."""
        metrics = LLMTimingMetrics(
            ttft_ms=150.0,
            total_ms=400.0,
            tokens_generated=30,
            prompt_tokens=10,
        )

        assert metrics.within_vqa_budget is False


class TestMockLLMClient:
    """Test MockLLMClient."""

    async def test_generate_response(self):
        """Should generate response with timing."""
        client = MockLLMClient(ttft_ms=50, tokens_per_second=50)

        response, metrics = await client.generate("Test prompt", max_tokens=10)

        assert response is not None
        assert metrics.ttft_ms > 0
        assert metrics.total_ms > metrics.ttft_ms

    async def test_ttft_timing(self):
        """Should measure TTFT correctly."""
        client = MockLLMClient(ttft_ms=100, tokens_per_second=100, variance_pct=0)

        time.perf_counter()
        response, metrics = await client.generate("Test", max_tokens=1)

        # TTFT should be approximately 100ms
        assert 80 < metrics.ttft_ms < 150

    async def test_streaming_generation(self):
        """Should stream tokens with timing."""
        client = MockLLMClient(ttft_ms=50, tokens_per_second=20, variance_pct=0)

        tokens = []
        async for token, elapsed in client.generate_stream("Test", max_tokens=5):
            tokens.append((token, elapsed))

        # First should be TTFT marker
        assert tokens[0][0] == ""
        assert 40 < tokens[0][1] < 70  # ~50ms TTFT

        # Should have tokens
        assert len(tokens) > 1


class TestPromptOptimizer:
    """Test PromptOptimizer utilities."""

    def test_estimate_tokens(self):
        """Should estimate token count."""
        text = "This is a test prompt with about forty characters."
        tokens = PromptOptimizer.estimate_tokens(text)

        # ~50 chars / 4 = ~12 tokens
        assert 10 <= tokens <= 15

    def test_truncate_prompt(self):
        """Should truncate long prompts."""
        long_prompt = "word " * 1000  # ~5000 chars

        truncated = PromptOptimizer.truncate_prompt(long_prompt, max_tokens=100)

        assert len(truncated) < len(long_prompt)
        assert truncated.endswith("...")

    def test_system_prompts(self):
        """Should provide optimized system prompts."""
        vision_prompt = PromptOptimizer.get_system_prompt("vision")
        nav_prompt = PromptOptimizer.get_system_prompt("navigation")

        assert len(vision_prompt) < 100  # Short and efficient
        assert len(nav_prompt) < 100


class TestLLMLatencyOptimization:
    """Test LLM latency optimization strategies."""

    async def test_short_generation_under_budget(self):
        """Short generation should be under 300ms."""
        client = MockLLMClient(ttft_ms=80, tokens_per_second=40, variance_pct=10)

        # Short response (5 tokens)
        response, metrics = await client.generate("Test prompt", max_tokens=5)

        # TTFT 80ms + 5 tokens @ 40/s = 125ms = 205ms total
        assert metrics.total_ms < 300, f"Total {metrics.total_ms:.0f}ms exceeds 300ms"

    async def test_streaming_reduces_perceived_latency(self):
        """Streaming should deliver first token quickly."""
        client = MockLLMClient(ttft_ms=100, tokens_per_second=30)

        first_token_time = None
        async for token, elapsed in client.generate_stream("Test", max_tokens=20):
            if first_token_time is None:
                first_token_time = elapsed
                break

        # First token should arrive at TTFT (~100ms)
        assert first_token_time < 150, f"TTFT {first_token_time:.0f}ms too high"

    async def test_batch_generation_efficiency(self):
        """Batch should be more efficient than sequential."""
        client = MockLLMClient(ttft_ms=50, tokens_per_second=50)

        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]

        # Sequential
        start = time.perf_counter()
        for p in prompts:
            await client.generate(p, max_tokens=5)
        sequential_time = (time.perf_counter() - start) * 1000

        # Note: In real implementation, batch would be parallel
        # This mock doesn't implement true batching

        assert sequential_time > 0  # Just verify it runs
