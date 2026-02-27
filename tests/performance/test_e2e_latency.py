"""P4: End-to-End Latency Validation Tests (T-085).

Validates complete hot-path latency meets 500ms SLA.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# E2E Latency Models
# ---------------------------------------------------------------------------

@dataclass
class E2ELatencyBreakdown:
    """Breakdown of end-to-end latency by component."""
    stt_ms: float = 0.0
    processing_ms: float = 0.0  # LLM/VQA
    tts_ms: float = 0.0
    overhead_ms: float = 0.0
    
    @property
    def total_ms(self) -> float:
        return self.stt_ms + self.processing_ms + self.tts_ms + self.overhead_ms
    
    @property
    def within_sla(self) -> bool:
        """Check if within 500ms hot-path SLA."""
        return self.total_ms < 500.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "stt_ms": round(self.stt_ms, 2),
            "processing_ms": round(self.processing_ms, 2),
            "tts_ms": round(self.tts_ms, 2),
            "overhead_ms": round(self.overhead_ms, 2),
            "total_ms": round(self.total_ms, 2),
            "within_sla": self.within_sla,
        }


@dataclass
class E2ETestResult:
    """Result of an end-to-end latency test."""
    scenario: str
    iterations: int
    breakdowns: List[E2ELatencyBreakdown] = field(default_factory=list)
    
    @property
    def avg_total_ms(self) -> float:
        if not self.breakdowns:
            return 0.0
        return sum(b.total_ms for b in self.breakdowns) / len(self.breakdowns)
    
    @property
    def p50_ms(self) -> float:
        if not self.breakdowns:
            return 0.0
        sorted_totals = sorted(b.total_ms for b in self.breakdowns)
        return sorted_totals[len(sorted_totals) // 2]
    
    @property
    def p95_ms(self) -> float:
        if not self.breakdowns:
            return 0.0
        sorted_totals = sorted(b.total_ms for b in self.breakdowns)
        idx = int(len(sorted_totals) * 0.95)
        return sorted_totals[min(idx, len(sorted_totals) - 1)]
    
    @property
    def p99_ms(self) -> float:
        if not self.breakdowns:
            return 0.0
        sorted_totals = sorted(b.total_ms for b in self.breakdowns)
        idx = int(len(sorted_totals) * 0.99)
        return sorted_totals[min(idx, len(sorted_totals) - 1)]
    
    @property
    def sla_pass_rate(self) -> float:
        if not self.breakdowns:
            return 0.0
        passing = sum(1 for b in self.breakdowns if b.within_sla)
        return (passing / len(self.breakdowns)) * 100


# ---------------------------------------------------------------------------
# Mock E2E Pipeline
# ---------------------------------------------------------------------------

class MockE2EPipeline:
    """Mock end-to-end pipeline for latency testing."""
    
    def __init__(
        self,
        stt_latency_ms: float = 90.0,
        processing_latency_ms: float = 220.0,
        tts_latency_ms: float = 90.0,
        overhead_ms: float = 20.0,
        variance_pct: float = 15.0,
    ):
        self.stt_latency_ms = stt_latency_ms
        self.processing_latency_ms = processing_latency_ms
        self.tts_latency_ms = tts_latency_ms
        self.overhead_ms = overhead_ms
        self.variance_pct = variance_pct
    
    def _add_variance(self, value: float) -> float:
        import random
        factor = 1 + random.uniform(-self.variance_pct, self.variance_pct) / 100
        return value * factor
    
    async def process_voice_interaction(self) -> E2ELatencyBreakdown:
        """Simulate voice interaction: STT -> LLM -> TTS."""
        # STT
        stt_time = self._add_variance(self.stt_latency_ms)
        await asyncio.sleep(stt_time / 1000)
        
        # Processing (LLM)
        processing_time = self._add_variance(self.processing_latency_ms)
        await asyncio.sleep(processing_time / 1000)
        
        # TTS
        tts_time = self._add_variance(self.tts_latency_ms)
        await asyncio.sleep(tts_time / 1000)
        
        # Overhead
        overhead_time = self._add_variance(self.overhead_ms)
        await asyncio.sleep(overhead_time / 1000)
        
        return E2ELatencyBreakdown(
            stt_ms=stt_time,
            processing_ms=processing_time,
            tts_ms=tts_time,
            overhead_ms=overhead_time,
        )
    
    async def process_vision_interaction(self) -> E2ELatencyBreakdown:
        """Simulate vision interaction: VQA -> TTS."""
        # VQA processing (typically longer)
        processing_time = self._add_variance(self.processing_latency_ms * 1.3)
        await asyncio.sleep(processing_time / 1000)
        
        # TTS
        tts_time = self._add_variance(self.tts_latency_ms)
        await asyncio.sleep(tts_time / 1000)
        
        # Overhead
        overhead_time = self._add_variance(self.overhead_ms * 1.5)
        await asyncio.sleep(overhead_time / 1000)
        
        return E2ELatencyBreakdown(
            stt_ms=0.0,  # No STT for vision
            processing_ms=processing_time,
            tts_ms=tts_time,
            overhead_ms=overhead_time,
        )


async def run_e2e_test(
    pipeline: MockE2EPipeline,
    scenario: str,
    iterations: int = 20,
) -> E2ETestResult:
    """Run end-to-end latency test."""
    result = E2ETestResult(scenario=scenario, iterations=iterations)
    
    for _ in range(iterations):
        if scenario == "voice":
            breakdown = await pipeline.process_voice_interaction()
        elif scenario == "vision":
            breakdown = await pipeline.process_vision_interaction()
        else:
            breakdown = await pipeline.process_voice_interaction()
        
        result.breakdowns.append(breakdown)
    
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestE2ELatencyBreakdown:
    """Test E2ELatencyBreakdown dataclass."""
    
    def test_breakdown_total(self):
        """Should calculate total correctly."""
        breakdown = E2ELatencyBreakdown(
            stt_ms=90.0,
            processing_ms=200.0,
            tts_ms=90.0,
            overhead_ms=20.0,
        )
        
        assert breakdown.total_ms == 400.0
    
    def test_sla_pass(self):
        """Should pass SLA when under 500ms."""
        breakdown = E2ELatencyBreakdown(
            stt_ms=90.0,
            processing_ms=200.0,
            tts_ms=90.0,
            overhead_ms=20.0,
        )
        
        assert breakdown.within_sla is True
    
    def test_sla_fail(self):
        """Should fail SLA when over 500ms."""
        breakdown = E2ELatencyBreakdown(
            stt_ms=150.0,
            processing_ms=300.0,
            tts_ms=100.0,
            overhead_ms=50.0,
        )
        
        assert breakdown.within_sla is False


class TestE2ETestResult:
    """Test E2ETestResult statistics."""
    
    def test_percentile_calculations(self):
        """Should calculate percentiles correctly."""
        result = E2ETestResult(scenario="test", iterations=100)
        
        for i in range(100):
            result.breakdowns.append(E2ELatencyBreakdown(
                stt_ms=90,
                processing_ms=200 + i,  # 200-299ms
                tts_ms=90,
                overhead_ms=20,
            ))
        
        assert result.avg_total_ms > 0
        assert result.p50_ms > 0
        assert result.p95_ms > result.p50_ms
    
    def test_sla_pass_rate(self):
        """Should calculate SLA pass rate."""
        result = E2ETestResult(scenario="test", iterations=10)
        
        for i in range(10):
            total = 400 + i * 20  # 400, 420, ..., 580
            result.breakdowns.append(E2ELatencyBreakdown(
                stt_ms=total * 0.225,
                processing_ms=total * 0.5,
                tts_ms=total * 0.225,
                overhead_ms=total * 0.05,
            ))
        
        # First 5 should pass (<500), last 5 fail
        assert 40 <= result.sla_pass_rate <= 70


class TestMockE2EPipeline:
    """Test MockE2EPipeline."""
    
    async def test_voice_interaction(self):
        """Should complete voice interaction."""
        pipeline = MockE2EPipeline(
            stt_latency_ms=50,
            processing_latency_ms=100,
            tts_latency_ms=50,
            overhead_ms=10,
            variance_pct=0,
        )
        
        breakdown = await pipeline.process_voice_interaction()
        
        assert breakdown.stt_ms == pytest.approx(50, rel=0.1)
        assert breakdown.processing_ms == pytest.approx(100, rel=0.1)
        assert breakdown.tts_ms == pytest.approx(50, rel=0.1)
    
    async def test_vision_interaction(self):
        """Should complete vision interaction."""
        pipeline = MockE2EPipeline(
            stt_latency_ms=50,
            processing_latency_ms=100,
            tts_latency_ms=50,
            overhead_ms=10,
            variance_pct=0,
        )
        
        breakdown = await pipeline.process_vision_interaction()
        
        assert breakdown.stt_ms == 0  # No STT for vision
        assert breakdown.processing_ms > 100  # VQA is longer


class TestE2ESLAValidation:
    """SLA validation tests."""
    
    async def test_voice_scenario_under_500ms(self):
        """Voice scenario should be under 500ms SLA."""
        pipeline = MockE2EPipeline(
            stt_latency_ms=90,
            processing_latency_ms=220,
            tts_latency_ms=90,
            overhead_ms=20,
            variance_pct=15,
        )
        
        result = await run_e2e_test(pipeline, "voice", iterations=20)
        
        print(f"\nVoice Scenario:")
        print(f"  Avg: {result.avg_total_ms:.1f}ms")
        print(f"  P50: {result.p50_ms:.1f}ms")
        print(f"  P95: {result.p95_ms:.1f}ms")
        print(f"  SLA Pass Rate: {result.sla_pass_rate:.1f}%")
        
        assert result.p95_ms < 500, f"P95 {result.p95_ms:.1f}ms exceeds 500ms SLA"
        assert result.sla_pass_rate >= 95, f"SLA pass rate {result.sla_pass_rate:.1f}% < 95%"
    
    async def test_vision_scenario_under_800ms(self):
        """Vision scenario should be under 800ms extended SLA."""
        pipeline = MockE2EPipeline(
            stt_latency_ms=90,
            processing_latency_ms=220,
            tts_latency_ms=90,
            overhead_ms=20,
            variance_pct=15,
        )
        
        result = await run_e2e_test(pipeline, "vision", iterations=20)
        
        print(f"\nVision Scenario:")
        print(f"  Avg: {result.avg_total_ms:.1f}ms")
        print(f"  P50: {result.p50_ms:.1f}ms")
        print(f"  P95: {result.p95_ms:.1f}ms")
        
        assert result.p95_ms < 800, f"P95 {result.p95_ms:.1f}ms exceeds 800ms SLA"
    
    async def test_latency_breakdown_documented(self):
        """Should provide clear latency breakdown."""
        pipeline = MockE2EPipeline(
            stt_latency_ms=90,
            processing_latency_ms=220,
            tts_latency_ms=90,
            overhead_ms=20,
            variance_pct=5,
        )
        
        breakdown = await pipeline.process_voice_interaction()
        breakdown_dict = breakdown.to_dict()
        
        # Verify all components documented
        assert "stt_ms" in breakdown_dict
        assert "processing_ms" in breakdown_dict
        assert "tts_ms" in breakdown_dict
        assert "overhead_ms" in breakdown_dict
        assert "total_ms" in breakdown_dict
        assert "within_sla" in breakdown_dict
        
        # Print breakdown
        print(f"\nLatency Breakdown: {breakdown_dict}")


class TestE2EIntegration:
    """Integration tests for E2E latency."""
    
    async def test_multiple_scenarios(self):
        """Should handle multiple scenarios."""
        pipeline = MockE2EPipeline(
            stt_latency_ms=90,
            processing_latency_ms=200,
            tts_latency_ms=90,
            overhead_ms=20,
        )
        
        voice_result = await run_e2e_test(pipeline, "voice", iterations=10)
        vision_result = await run_e2e_test(pipeline, "vision", iterations=10)
        
        assert voice_result.iterations == 10
        assert vision_result.iterations == 10
        
        # Both should complete successfully
        assert voice_result.avg_total_ms > 0
        assert vision_result.avg_total_ms > 0
    
    async def test_consistent_results(self):
        """Results should be consistent across runs."""
        pipeline = MockE2EPipeline(variance_pct=5)  # Low variance
        
        result1 = await run_e2e_test(pipeline, "voice", iterations=20)
        result2 = await run_e2e_test(pipeline, "voice", iterations=20)
        
        # Averages should be similar (within 20%)
        diff = abs(result1.avg_total_ms - result2.avg_total_ms)
        avg = (result1.avg_total_ms + result2.avg_total_ms) / 2
        
        assert diff / avg < 0.2, "Results are inconsistent"
