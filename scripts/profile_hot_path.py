"""Hot-path profiling harness for P4 performance analysis.

Profiles the end-to-end voice interaction loop (STT → LLM/VQA → TTS)
to identify bottlenecks. Generates timing reports and optionally
flame graphs using cProfile + snakeviz.

Usage:
    python scripts/profile_hot_path.py --iterations 10
    python scripts/profile_hot_path.py --profile  # Generate cProfile output
    python scripts/profile_hot_path.py --flamegraph  # Generate flame graph
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import gc
import io
import json
import logging
import os
import pstats
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.utils.timing import PipelineProfiler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("hot_path_profiler")


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class HotPathTiming:
    """Timing for a single hot-path execution."""
    iteration: int
    stt_ms: float = 0.0
    llm_ms: float = 0.0
    tts_ms: float = 0.0
    overhead_ms: float = 0.0  # Pipeline orchestration overhead
    total_ms: float = 0.0

    @property
    def is_within_sla(self) -> bool:
        """Check if total is within 500ms SLA."""
        return self.total_ms < 500.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BottleneckInfo:
    """Information about an identified bottleneck."""
    component: str
    avg_ms: float
    max_ms: float
    percentage: float  # Percentage of total time
    file_location: str
    function_name: str
    recommendation: str


@dataclass
class HotPathReport:
    """Complete hot-path profiling report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    iterations: int = 0
    timings: List[HotPathTiming] = field(default_factory=list)
    bottlenecks: List[BottleneckInfo] = field(default_factory=list)
    cprofile_stats: Optional[str] = None

    @property
    def avg_total_ms(self) -> float:
        if not self.timings:
            return 0.0
        return sum(t.total_ms for t in self.timings) / len(self.timings)

    @property
    def p95_total_ms(self) -> float:
        if not self.timings:
            return 0.0
        sorted_totals = sorted(t.total_ms for t in self.timings)
        idx = int(len(sorted_totals) * 0.95)
        return sorted_totals[min(idx, len(sorted_totals) - 1)]

    @property
    def sla_pass_rate(self) -> float:
        if not self.timings:
            return 0.0
        passing = sum(1 for t in self.timings if t.is_within_sla)
        return (passing / len(self.timings)) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "iterations": self.iterations,
            "summary": {
                "avg_total_ms": round(self.avg_total_ms, 2),
                "p95_total_ms": round(self.p95_total_ms, 2),
                "sla_pass_rate_pct": round(self.sla_pass_rate, 1),
                "sla_target_ms": 500,
            },
            "timings": [t.to_dict() for t in self.timings],
            "bottlenecks": [asdict(b) for b in self.bottlenecks],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ---------------------------------------------------------------------------
# Mock Components for Profiling
# ---------------------------------------------------------------------------

class MockSTTProcessor:
    """Mock STT processor simulating Deepgram latency."""

    def __init__(self, latency_ms: float = 80.0, variance_ms: float = 20.0):
        self.latency_ms = latency_ms
        self.variance_ms = variance_ms

    async def transcribe(self, audio: bytes) -> str:
        """Simulate STT transcription with realistic latency."""
        import random
        delay = (self.latency_ms + random.uniform(-self.variance_ms, self.variance_ms)) / 1000
        await asyncio.sleep(delay)
        return "What do you see in front of me?"


class MockLLMProcessor:
    """Mock LLM processor simulating Ollama/VQA latency."""

    def __init__(self, latency_ms: float = 200.0, variance_ms: float = 50.0):
        self.latency_ms = latency_ms
        self.variance_ms = variance_ms

    async def generate(self, prompt: str, image: Optional[bytes] = None) -> str:
        """Simulate LLM generation with realistic latency."""
        import random
        delay = (self.latency_ms + random.uniform(-self.variance_ms, self.variance_ms)) / 1000
        await asyncio.sleep(delay)
        return "I can see a chair approximately 2 meters ahead and slightly to your left."


class MockTTSProcessor:
    """Mock TTS processor simulating ElevenLabs latency."""

    def __init__(self, latency_ms: float = 80.0, variance_ms: float = 20.0):
        self.latency_ms = latency_ms
        self.variance_ms = variance_ms

    async def synthesize(self, text: str) -> bytes:
        """Simulate TTS synthesis with realistic latency."""
        import random
        delay = (self.latency_ms + random.uniform(-self.variance_ms, self.variance_ms)) / 1000
        await asyncio.sleep(delay)
        return b"\x00\x00" * 16000  # 1 second of silence


# ---------------------------------------------------------------------------
# Hot Path Profiler
# ---------------------------------------------------------------------------

class HotPathProfiler:
    """Profiles the complete voice interaction hot path."""

    def __init__(
        self,
        stt: Optional[MockSTTProcessor] = None,
        llm: Optional[MockLLMProcessor] = None,
        tts: Optional[MockTTSProcessor] = None,
    ):
        self.stt = stt or MockSTTProcessor()
        self.llm = llm or MockLLMProcessor()
        self.tts = tts or MockTTSProcessor()
        self.profiler = PipelineProfiler(enabled=True)

    async def run_hot_path(self, iteration: int) -> HotPathTiming:
        """Execute a single hot-path iteration with timing."""
        timing = HotPathTiming(iteration=iteration)

        total_start = time.perf_counter()

        # STT Phase
        stt_start = time.perf_counter()
        async with self.profiler.measure_async("stt"):
            transcript = await self.stt.transcribe(b"mock_audio")
        timing.stt_ms = (time.perf_counter() - stt_start) * 1000

        # LLM/VQA Phase
        llm_start = time.perf_counter()
        async with self.profiler.measure_async("llm"):
            response = await self.llm.generate(transcript)
        timing.llm_ms = (time.perf_counter() - llm_start) * 1000

        # TTS Phase
        tts_start = time.perf_counter()
        async with self.profiler.measure_async("tts"):
            await self.tts.synthesize(response)
        timing.tts_ms = (time.perf_counter() - tts_start) * 1000

        timing.total_ms = (time.perf_counter() - total_start) * 1000
        timing.overhead_ms = timing.total_ms - (timing.stt_ms + timing.llm_ms + timing.tts_ms)

        return timing

    async def profile(self, iterations: int = 10, warmup: int = 2) -> HotPathReport:
        """Run multiple iterations and generate a report."""
        report = HotPathReport(iterations=iterations)

        # Warmup runs (not recorded)
        logger.info(f"Running {warmup} warmup iterations...")
        for i in range(warmup):
            await self.run_hot_path(i)
            gc.collect()

        # Measurement runs
        logger.info(f"Running {iterations} measurement iterations...")
        for i in range(iterations):
            gc.collect()
            timing = await self.run_hot_path(i)
            report.timings.append(timing)

            status = "PASS" if timing.is_within_sla else "FAIL"
            logger.info(f"  [{i+1}/{iterations}] Total: {timing.total_ms:.1f}ms [{status}]")

        # Analyze bottlenecks
        report.bottlenecks = self._analyze_bottlenecks(report.timings)

        return report

    def _analyze_bottlenecks(self, timings: List[HotPathTiming]) -> List[BottleneckInfo]:
        """Analyze timings to identify top bottlenecks."""
        if not timings:
            return []

        # Aggregate by component
        components = {
            "stt": {
                "times": [t.stt_ms for t in timings],
                "file": "infrastructure/speech/deepgram_stt.py",
                "function": "transcribe()",
            },
            "llm": {
                "times": [t.llm_ms for t in timings],
                "file": "infrastructure/llm/ollama_client.py",
                "function": "generate()",
            },
            "tts": {
                "times": [t.tts_ms for t in timings],
                "file": "infrastructure/speech/elevenlabs_tts.py",
                "function": "synthesize()",
            },
            "overhead": {
                "times": [t.overhead_ms for t in timings],
                "file": "application/pipelines/voice_pipeline.py",
                "function": "orchestrate()",
            },
        }

        total_avg = sum(sum(c["times"]) / len(c["times"]) for c in components.values())

        bottlenecks = []
        for name, data in components.items():
            times = data["times"]
            avg_ms = sum(times) / len(times)
            max_ms = max(times)
            pct = (avg_ms / total_avg * 100) if total_avg > 0 else 0

            # Generate recommendation based on component
            recommendation = self._get_recommendation(name, avg_ms)

            bottlenecks.append(BottleneckInfo(
                component=name,
                avg_ms=round(avg_ms, 2),
                max_ms=round(max_ms, 2),
                percentage=round(pct, 1),
                file_location=data["file"],
                function_name=data["function"],
                recommendation=recommendation,
            ))

        # Sort by percentage (highest first)
        bottlenecks.sort(key=lambda b: b.percentage, reverse=True)
        return bottlenecks[:5]  # Top 5

    def _get_recommendation(self, component: str, avg_ms: float) -> str:
        """Generate optimization recommendation for a component."""
        recommendations = {
            "stt": {
                "high": "Consider streaming STT or local Whisper fallback",
                "medium": "Optimize audio preprocessing or batch size",
                "low": "STT is within acceptable range",
            },
            "llm": {
                "high": "Consider INT8 quantization or smaller model",
                "medium": "Enable KV cache, optimize prompt length",
                "low": "LLM latency is within acceptable range",
            },
            "tts": {
                "high": "Consider streaming TTS or local engine fallback",
                "medium": "Optimize text chunking or voice selection",
                "low": "TTS is within acceptable range",
            },
            "overhead": {
                "high": "Profile pipeline orchestration, reduce async overhead",
                "medium": "Optimize task scheduling and context switches",
                "low": "Orchestration overhead is acceptable",
            },
        }

        thresholds = {"stt": 100, "llm": 300, "tts": 100, "overhead": 50}
        threshold = thresholds.get(component, 100)

        if avg_ms > threshold * 1.5:
            return recommendations.get(component, {}).get("high", "Optimize this component")
        elif avg_ms > threshold:
            return recommendations.get(component, {}).get("medium", "Minor optimization possible")
        else:
            return recommendations.get(component, {}).get("low", "No optimization needed")


# ---------------------------------------------------------------------------
# cProfile Integration
# ---------------------------------------------------------------------------

def profile_with_cprofile(func, *args, **kwargs):
    """Run a function with cProfile and return stats."""
    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args, **kwargs)

    profiler.disable()

    # Get stats as string
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(50)  # Top 50 functions

    return result, stream.getvalue()


async def run_profiled_hot_path(iterations: int = 10) -> Tuple[HotPathReport, str]:
    """Run hot path profiling with cProfile instrumentation."""
    profiler = HotPathProfiler()

    # Wrap async function for cProfile
    def sync_wrapper():
        return asyncio.run(profiler.profile(iterations=iterations))

    report, cprofile_output = profile_with_cprofile(sync_wrapper)
    report.cprofile_stats = cprofile_output

    return report, cprofile_output


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def generate_markdown_report(report: HotPathReport) -> str:
    """Generate markdown formatted hot-path analysis report."""
    lines = [
        "# Hot-Path Profiling Report",
        "",
        f"**Generated:** {report.timestamp}",
        f"**Iterations:** {report.iterations}",
        "",
        "## Summary",
        "",
        "| Metric | Value | Target | Status |",
        "|--------|-------|--------|--------|",
        f"| Average Latency | {report.avg_total_ms:.1f}ms | <500ms | {'OK' if report.avg_total_ms < 500 else 'FAIL'} |",
        f"| P95 Latency | {report.p95_total_ms:.1f}ms | <500ms | {'OK' if report.p95_total_ms < 500 else 'FAIL'} |",
        f"| SLA Pass Rate | {report.sla_pass_rate:.1f}% | 100% | {'OK' if report.sla_pass_rate >= 95 else 'WARN'} |",
        "",
        "## Top Bottlenecks",
        "",
        "| Rank | Component | Avg (ms) | Max (ms) | % of Total | Location |",
        "|------|-----------|----------|----------|------------|----------|",
    ]

    for i, b in enumerate(report.bottlenecks, 1):
        lines.append(
            f"| {i} | {b.component} | {b.avg_ms:.1f} | {b.max_ms:.1f} | {b.percentage:.1f}% | {b.file_location} |"
        )

    lines.extend([
        "",
        "## Optimization Recommendations",
        "",
    ])

    for i, b in enumerate(report.bottlenecks, 1):
        lines.append(f"{i}. **{b.component}** ({b.function_name}): {b.recommendation}")

    lines.extend([
        "",
        "## Iteration Details",
        "",
        "| # | STT (ms) | LLM (ms) | TTS (ms) | Overhead | Total | Status |",
        "|---|----------|----------|----------|----------|-------|--------|",
    ])

    for t in report.timings[:20]:  # First 20 iterations
        status = "OK" if t.is_within_sla else "FAIL"
        lines.append(
            f"| {t.iteration + 1} | {t.stt_ms:.1f} | {t.llm_ms:.1f} | {t.tts_ms:.1f} | {t.overhead_ms:.1f} | {t.total_ms:.1f} | {status} |"
        )

    if len(report.timings) > 20:
        lines.append("| ... | ... | ... | ... | ... | ... | ... |")
        lines.append(f"| (showing first 20 of {len(report.timings)} iterations) |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Profile voice interaction hot path")
    parser.add_argument("--iterations", type=int, default=10, help="Number of iterations")
    parser.add_argument("--profile", action="store_true", help="Enable cProfile")
    parser.add_argument("--output", type=str, default="docs/performance", help="Output directory")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("HOT-PATH PROFILER")
    logger.info("=" * 60)
    logger.info(f"Iterations: {args.iterations}")
    logger.info(f"cProfile: {'enabled' if args.profile else 'disabled'}")
    logger.info("")

    if args.profile:
        report, cprofile_output = await run_profiled_hot_path(args.iterations)
        logger.info("\n--- cProfile Output (top 50 functions) ---")
        print(cprofile_output)
    else:
        profiler = HotPathProfiler()
        report = await profiler.profile(iterations=args.iterations)

    # Generate reports
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = output_dir / "hot-path-metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.to_json())
    logger.info(f"\nJSON report: {json_path}")

    # Markdown report
    md_path = output_dir / "hot-path-analysis.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(report))
    logger.info(f"Markdown report: {md_path}")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Average Latency: {report.avg_total_ms:.1f}ms (target: <500ms)")
    logger.info(f"P95 Latency: {report.p95_total_ms:.1f}ms")
    logger.info(f"SLA Pass Rate: {report.sla_pass_rate:.1f}%")
    logger.info("")
    logger.info("Top 3 Bottlenecks:")
    for i, b in enumerate(report.bottlenecks[:3], 1):
        logger.info(f"  {i}. {b.component}: {b.avg_ms:.1f}ms ({b.percentage:.1f}%)")

    return report


if __name__ == "__main__":
    asyncio.run(main())
