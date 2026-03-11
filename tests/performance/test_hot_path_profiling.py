"""P4: Hot-Path Profiling Tests (T-074).

Tests for the hot-path profiling harness that identifies bottlenecks
in the voice interaction loop (STT -> LLM/VQA -> TTS).

SLA Target: <500ms end-to-end
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------

class TestHotPathImports:
    """Test that all hot-path profiling modules import correctly."""

    def test_timing_module_import(self):
        """shared.utils.timing should import quickly."""
        start = time.perf_counter()
        from shared.utils.timing import PipelineProfiler, get_profiler
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"Timing module import took {elapsed_ms:.0f}ms (limit: 500ms)"
        assert PipelineProfiler is not None
        assert get_profiler is not None

    def test_profile_script_import(self):
        """scripts.profile_hot_path should import without errors."""
        start = time.perf_counter()
        from scripts.profile_hot_path import (
            HotPathProfiler,
            HotPathTiming,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 1000, f"Profile script import took {elapsed_ms:.0f}ms"
        assert HotPathProfiler is not None
        assert HotPathTiming is not None


# ---------------------------------------------------------------------------
# Mock Component Tests
# ---------------------------------------------------------------------------

class TestMockComponents:
    """Test mock STT/LLM/TTS components for profiling."""

    async def test_mock_stt_latency(self):
        """Mock STT should have configurable latency."""
        from scripts.profile_hot_path import MockSTTProcessor

        # Test with 50ms base latency, low variance
        stt = MockSTTProcessor(latency_ms=50.0, variance_ms=5.0)

        timings = []
        for _ in range(5):
            start = time.perf_counter()
            result = await stt.transcribe(b"test_audio")
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        avg_latency = sum(timings) / len(timings)
        assert 40 < avg_latency < 70, f"Mock STT latency {avg_latency:.1f}ms outside expected range"
        assert result == "What do you see in front of me?"

    async def test_mock_llm_latency(self):
        """Mock LLM should have configurable latency."""
        from scripts.profile_hot_path import MockLLMProcessor

        llm = MockLLMProcessor(latency_ms=100.0, variance_ms=10.0)

        timings = []
        for _ in range(5):
            start = time.perf_counter()
            result = await llm.generate("test prompt")
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        avg_latency = sum(timings) / len(timings)
        assert 80 < avg_latency < 130, f"Mock LLM latency {avg_latency:.1f}ms outside expected range"
        assert "chair" in result.lower() or "see" in result.lower()

    async def test_mock_tts_latency(self):
        """Mock TTS should have configurable latency."""
        from scripts.profile_hot_path import MockTTSProcessor

        tts = MockTTSProcessor(latency_ms=50.0, variance_ms=5.0)

        timings = []
        for _ in range(5):
            start = time.perf_counter()
            result = await tts.synthesize("test text")
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        avg_latency = sum(timings) / len(timings)
        assert 40 < avg_latency < 70, f"Mock TTS latency {avg_latency:.1f}ms outside expected range"
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# Hot Path Profiler Tests
# ---------------------------------------------------------------------------

class TestHotPathProfiler:
    """Test the HotPathProfiler class."""

    async def test_single_hot_path_iteration(self):
        """Single hot-path iteration should produce valid timing."""
        from scripts.profile_hot_path import (
            HotPathProfiler,
            MockLLMProcessor,
            MockSTTProcessor,
            MockTTSProcessor,
        )

        # Use fast mocks for testing
        profiler = HotPathProfiler(
            stt=MockSTTProcessor(latency_ms=10.0, variance_ms=2.0),
            llm=MockLLMProcessor(latency_ms=20.0, variance_ms=5.0),
            tts=MockTTSProcessor(latency_ms=10.0, variance_ms=2.0),
        )

        timing = await profiler.run_hot_path(iteration=0)

        # Verify timing structure
        assert timing.iteration == 0
        assert timing.stt_ms > 0
        assert timing.llm_ms > 0
        assert timing.tts_ms > 0
        assert timing.total_ms > 0

        # Total should be >= sum of components
        component_sum = timing.stt_ms + timing.llm_ms + timing.tts_ms
        assert timing.total_ms >= component_sum * 0.95  # Allow small measurement variance

    async def test_profiler_multiple_iterations(self):
        """Profiler should run multiple iterations and generate report."""
        from scripts.profile_hot_path import (
            HotPathProfiler,
            MockLLMProcessor,
            MockSTTProcessor,
            MockTTSProcessor,
        )

        profiler = HotPathProfiler(
            stt=MockSTTProcessor(latency_ms=10.0, variance_ms=2.0),
            llm=MockLLMProcessor(latency_ms=20.0, variance_ms=5.0),
            tts=MockTTSProcessor(latency_ms=10.0, variance_ms=2.0),
        )

        report = await profiler.profile(iterations=5, warmup=1)

        # Verify report structure
        assert report.iterations == 5
        assert len(report.timings) == 5
        assert len(report.bottlenecks) > 0
        assert report.avg_total_ms > 0
        assert report.p95_total_ms > 0

    async def test_bottleneck_identification(self):
        """Profiler should correctly identify the slowest component."""
        from scripts.profile_hot_path import (
            HotPathProfiler,
            MockLLMProcessor,
            MockSTTProcessor,
            MockTTSProcessor,
        )

        # Make LLM the bottleneck (much slower than others)
        profiler = HotPathProfiler(
            stt=MockSTTProcessor(latency_ms=10.0, variance_ms=1.0),
            llm=MockLLMProcessor(latency_ms=100.0, variance_ms=5.0),  # Bottleneck
            tts=MockTTSProcessor(latency_ms=10.0, variance_ms=1.0),
        )

        report = await profiler.profile(iterations=5, warmup=1)

        # LLM should be the top bottleneck
        assert len(report.bottlenecks) > 0
        top_bottleneck = report.bottlenecks[0]
        assert top_bottleneck.component == "llm", f"Expected LLM bottleneck, got {top_bottleneck.component}"
        assert top_bottleneck.percentage > 50, "LLM should be >50% of total time"


# ---------------------------------------------------------------------------
# Timing Data Structure Tests
# ---------------------------------------------------------------------------

class TestHotPathTiming:
    """Test HotPathTiming data structure."""

    def test_timing_sla_check_pass(self):
        """Timing under 500ms should pass SLA check."""
        from scripts.profile_hot_path import HotPathTiming

        timing = HotPathTiming(
            iteration=0,
            stt_ms=80.0,
            llm_ms=200.0,
            tts_ms=80.0,
            overhead_ms=20.0,
            total_ms=380.0,
        )

        assert timing.is_within_sla is True

    def test_timing_sla_check_fail(self):
        """Timing over 500ms should fail SLA check."""
        from scripts.profile_hot_path import HotPathTiming

        timing = HotPathTiming(
            iteration=0,
            stt_ms=200.0,
            llm_ms=300.0,
            tts_ms=100.0,
            overhead_ms=50.0,
            total_ms=650.0,
        )

        assert timing.is_within_sla is False

    def test_timing_to_dict(self):
        """Timing should serialize to dict correctly."""
        from scripts.profile_hot_path import HotPathTiming

        timing = HotPathTiming(
            iteration=1,
            stt_ms=80.0,
            llm_ms=200.0,
            tts_ms=80.0,
            overhead_ms=10.0,
            total_ms=370.0,
        )

        d = timing.to_dict()
        assert d["iteration"] == 1
        assert d["stt_ms"] == 80.0
        assert d["llm_ms"] == 200.0
        assert d["tts_ms"] == 80.0
        assert d["total_ms"] == 370.0


# ---------------------------------------------------------------------------
# Report Generation Tests
# ---------------------------------------------------------------------------

class TestHotPathReport:
    """Test HotPathReport generation."""

    def test_report_summary_stats(self):
        """Report should calculate summary statistics correctly."""
        from scripts.profile_hot_path import HotPathReport, HotPathTiming

        timings = [
            HotPathTiming(iteration=i, total_ms=350.0 + i * 20)
            for i in range(10)
        ]

        report = HotPathReport(iterations=10, timings=timings)

        # Average should be around 440ms (350 + 90/2)
        assert 430 < report.avg_total_ms < 450

        # P95 should be near the higher values
        assert report.p95_total_ms > 500

        # Some should pass, some fail
        assert 0 < report.sla_pass_rate < 100

    def test_report_json_serialization(self):
        """Report should serialize to valid JSON."""
        import json

        from scripts.profile_hot_path import BottleneckInfo, HotPathReport, HotPathTiming

        report = HotPathReport(
            iterations=5,
            timings=[HotPathTiming(iteration=i, total_ms=400.0) for i in range(5)],
            bottlenecks=[
                BottleneckInfo(
                    component="llm",
                    avg_ms=200.0,
                    max_ms=250.0,
                    percentage=50.0,
                    file_location="infrastructure/llm/ollama_client.py",
                    function_name="generate()",
                    recommendation="Consider INT8 quantization",
                )
            ],
        )

        json_str = report.to_json()
        parsed = json.loads(json_str)

        assert parsed["iterations"] == 5
        assert len(parsed["timings"]) == 5
        assert len(parsed["bottlenecks"]) == 1
        assert "avg_total_ms" in parsed["summary"]


# ---------------------------------------------------------------------------
# Markdown Report Tests
# ---------------------------------------------------------------------------

class TestMarkdownReport:
    """Test markdown report generation."""

    def test_markdown_report_generation(self):
        """Markdown report should be well-formatted."""
        from scripts.profile_hot_path import (
            BottleneckInfo,
            HotPathReport,
            HotPathTiming,
            generate_markdown_report,
        )

        report = HotPathReport(
            iterations=5,
            timings=[HotPathTiming(iteration=i, stt_ms=80, llm_ms=200, tts_ms=80, total_ms=380) for i in range(5)],
            bottlenecks=[
                BottleneckInfo(
                    component="llm",
                    avg_ms=200.0,
                    max_ms=220.0,
                    percentage=52.6,
                    file_location="infrastructure/llm/ollama_client.py",
                    function_name="generate()",
                    recommendation="Consider INT8 quantization",
                )
            ],
        )

        md = generate_markdown_report(report)

        # Verify key sections exist
        assert "# Hot-Path Profiling Report" in md
        assert "## Summary" in md
        assert "## Top Bottlenecks" in md
        assert "## Optimization Recommendations" in md
        assert "llm" in md
        assert "INT8 quantization" in md


# ---------------------------------------------------------------------------
# Pipeline Profiler Integration Tests
# ---------------------------------------------------------------------------

class TestPipelineProfilerIntegration:
    """Test integration with shared.utils.timing.PipelineProfiler."""

    def test_profiler_context_manager(self):
        """PipelineProfiler context manager should measure sync operations."""
        from shared.utils.timing import PipelineProfiler

        profiler = PipelineProfiler(enabled=True)

        with profiler.measure("test_sync"):
            time.sleep(0.01)  # 10ms

        stats = profiler.get_stats("test_sync")
        assert stats["count"] == 1
        assert stats["avg_ms"] >= 8  # At least 8ms (allowing variance)

    async def test_profiler_async_context_manager(self):
        """PipelineProfiler should measure async operations."""
        from shared.utils.timing import PipelineProfiler

        profiler = PipelineProfiler(enabled=True)

        async with profiler.measure_async("test_async"):
            await asyncio.sleep(0.01)  # 10ms

        stats = profiler.get_stats("test_async")
        assert stats["count"] == 1
        assert stats["avg_ms"] >= 8


# ---------------------------------------------------------------------------
# cProfile Integration Tests
# ---------------------------------------------------------------------------

class TestCProfileIntegration:
    """Test cProfile integration for flame graph generation."""

    def test_cprofile_wrapper(self):
        """cProfile wrapper should capture function execution stats."""
        from scripts.profile_hot_path import profile_with_cprofile

        def slow_function():
            time.sleep(0.01)
            return "done"

        result, stats_output = profile_with_cprofile(slow_function)

        assert result == "done"
        assert "function calls" in stats_output.lower() or "cumulative" in stats_output.lower()
