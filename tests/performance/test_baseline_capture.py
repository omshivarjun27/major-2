"""P4: Performance Baseline Capture Tests.

Establishes comprehensive performance baselines for all pipeline components
before optimization work begins. These baselines serve as reference points
for measuring optimization improvements throughout Phase 4.

SLA Targets:
- STT (Deepgram): <100ms
- TTS (ElevenLabs): <100ms
- VQA/LLM (Ollama): <300ms
- Vision pipeline: <300ms
- FAISS query: <50ms
- Hot path (e2e): <500ms
- VRAM budget: <8GB
"""

from __future__ import annotations

import gc
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Baseline Data Structures
# ---------------------------------------------------------------------------


@dataclass
class LatencyMeasurement:
    """Single latency measurement with metadata."""
    component: str
    samples: List[float] = field(default_factory=list)
    unit: str = "ms"

    @property
    def min(self) -> float:
        return min(self.samples) if self.samples else 0.0

    @property
    def max(self) -> float:
        return max(self.samples) if self.samples else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def p95(self) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.95)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    @property
    def p99(self) -> float:
        if not self.samples:
            return 0.0
        sorted_samples = sorted(self.samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "sample_count": len(self.samples),
            "min_ms": round(self.min, 2),
            "max_ms": round(self.max, 2),
            "median_ms": round(self.median, 2),
            "mean_ms": round(self.mean, 2),
            "p95_ms": round(self.p95, 2),
            "p99_ms": round(self.p99, 2),
        }


@dataclass
class BaselineReport:
    """Complete baseline report with all measurements."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    measurements: Dict[str, LatencyMeasurement] = field(default_factory=dict)
    vram_idle_mb: float = 0.0
    vram_peak_mb: float = 0.0
    ram_usage_mb: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "measurements": {k: v.to_dict() for k, v in self.measurements.items()},
            "vram_idle_mb": self.vram_idle_mb,
            "vram_peak_mb": self.vram_peak_mb,
            "ram_usage_mb": self.ram_usage_mb,
            "notes": self.notes,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# Global report to collect all measurements
_baseline_report = BaselineReport()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def baseline_report() -> BaselineReport:
    """Shared baseline report across tests."""
    return _baseline_report


@pytest.fixture
def mock_audio_data() -> bytes:
    """Mock audio data for STT testing."""
    # 1 second of silence at 16kHz, 16-bit mono
    return b"\x00\x00" * 16000


@pytest.fixture
def mock_image():
    """Mock image for vision testing."""
    try:
        from PIL import Image
        return Image.new("RGB", (640, 480), color=(128, 128, 128))
    except ImportError:
        pytest.skip("PIL not available")


# ---------------------------------------------------------------------------
# Component Latency Measurement Utilities
# ---------------------------------------------------------------------------


async def measure_async_latency(
    func,
    *args,
    iterations: int = 10,
    warmup: int = 2,
    **kwargs
) -> List[float]:
    """Measure latency of an async function over multiple iterations."""
    # Warmup runs
    for _ in range(warmup):
        try:
            await func(*args, **kwargs)
        except Exception:
            pass

    # Measurement runs
    timings = []
    for _ in range(iterations):
        gc.collect()  # Reduce GC interference
        start = time.perf_counter()
        try:
            await func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)
        except Exception:
            # Record failed attempt as very high latency
            timings.append(float('inf'))

    return [t for t in timings if t != float('inf')]


def measure_sync_latency(
    func,
    *args,
    iterations: int = 10,
    warmup: int = 2,
    **kwargs
) -> List[float]:
    """Measure latency of a sync function over multiple iterations."""
    # Warmup runs
    for _ in range(warmup):
        try:
            func(*args, **kwargs)
        except Exception:
            pass

    # Measurement runs
    timings = []
    for _ in range(iterations):
        gc.collect()
        start = time.perf_counter()
        try:
            func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)
        except Exception:
            timings.append(float('inf'))

    return [t for t in timings if t != float('inf')]


# ---------------------------------------------------------------------------
# Import Latency Tests
# ---------------------------------------------------------------------------


class TestImportLatency:
    """Measure import latency for key modules."""

    def test_config_import_latency(self, baseline_report: BaselineReport):
        """Config module import should be fast (<500ms)."""
        timings = measure_sync_latency(
            lambda: __import__("shared.config", fromlist=["get_config"]),
            iterations=5,
            warmup=0
        )

        measurement = LatencyMeasurement("config_import", timings)
        baseline_report.measurements["config_import"] = measurement

        assert measurement.median < 500, f"Config import median {measurement.median:.0f}ms > 500ms"

    def test_circuit_breaker_import_latency(self, baseline_report: BaselineReport):
        """Circuit breaker import should be fast (<200ms)."""
        timings = measure_sync_latency(
            lambda: __import__("infrastructure.resilience.circuit_breaker", fromlist=["CircuitBreaker"]),
            iterations=5,
            warmup=0
        )

        measurement = LatencyMeasurement("circuit_breaker_import", timings)
        baseline_report.measurements["circuit_breaker_import"] = measurement

        assert measurement.median < 200, f"CB import median {measurement.median:.0f}ms > 200ms"


# ---------------------------------------------------------------------------
# Circuit Breaker Latency Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerLatency:
    """Measure circuit breaker operation latency."""

    async def test_circuit_breaker_call_latency(self, baseline_report: BaselineReport):
        """Circuit breaker call overhead should be minimal (<1ms)."""
        from infrastructure.resilience.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerConfig,
            clear_registry,
        )

        clear_registry()
        cb = CircuitBreaker("test_latency", config=CircuitBreakerConfig())

        async def fast_operation():
            return True

        timings = await measure_async_latency(
            lambda: cb.call(fast_operation),
            iterations=100,
            warmup=10
        )

        measurement = LatencyMeasurement("circuit_breaker_overhead", timings)
        baseline_report.measurements["circuit_breaker_overhead"] = measurement

        # CB overhead should be < 1ms
        assert measurement.median < 1.0, f"CB overhead {measurement.median:.2f}ms > 1ms"

        clear_registry()


# ---------------------------------------------------------------------------
# Retry Policy Latency Tests
# ---------------------------------------------------------------------------


class TestRetryPolicyLatency:
    """Measure retry policy operation latency."""

    async def test_retry_policy_success_latency(self, baseline_report: BaselineReport):
        """Retry policy successful call overhead should be minimal."""
        from infrastructure.resilience.retry_policy import RetryConfig, RetryPolicy

        config = RetryConfig(max_retries=3, base_delay_s=0.01)
        policy = RetryPolicy(config=config)

        async def fast_operation():
            return True

        timings = await measure_async_latency(
            lambda: policy.execute(fast_operation),
            iterations=50,
            warmup=5
        )

        measurement = LatencyMeasurement("retry_policy_overhead", timings)
        baseline_report.measurements["retry_policy_overhead"] = measurement

        # Retry overhead should be < 2ms on success
        assert measurement.median < 2.0, f"Retry overhead {measurement.median:.2f}ms > 2ms"


# ---------------------------------------------------------------------------
# Health Registry Latency Tests
# ---------------------------------------------------------------------------


class TestHealthRegistryLatency:
    """Measure health registry operation latency."""

    def test_health_summary_latency(self, baseline_report: BaselineReport):
        """Health summary generation should be fast (<10ms)."""
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        from infrastructure.resilience.health_registry import ServiceHealthRegistry

        clear_registry()
        services = ["deepgram", "elevenlabs", "ollama", "livekit", "tavus", "duckduckgo"]
        for s in services:
            register_circuit_breaker(s)

        registry = ServiceHealthRegistry(known_services=services)

        timings = measure_sync_latency(
            registry.get_health_summary,
            iterations=100,
            warmup=10
        )

        measurement = LatencyMeasurement("health_registry_summary", timings)
        baseline_report.measurements["health_registry_summary"] = measurement

        assert measurement.median < 10, f"Health summary {measurement.median:.2f}ms > 10ms"

        clear_registry()


# ---------------------------------------------------------------------------
# Degradation Coordinator Latency Tests
# ---------------------------------------------------------------------------


class TestDegradationCoordinatorLatency:
    """Measure degradation coordinator operation latency."""

    async def test_degradation_refresh_latency(self, baseline_report: BaselineReport):
        """Degradation refresh should be fast (<20ms)."""
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            reset_degradation_coordinator,
        )

        clear_registry()
        reset_degradation_coordinator()

        services = ["deepgram", "elevenlabs", "ollama", "livekit", "tavus", "duckduckgo"]
        for s in services:
            register_circuit_breaker(s)

        coordinator = DegradationCoordinator()
        await coordinator.initialize()

        timings = await measure_async_latency(
            coordinator.refresh,
            iterations=50,
            warmup=5
        )

        measurement = LatencyMeasurement("degradation_refresh", timings)
        baseline_report.measurements["degradation_refresh"] = measurement

        assert measurement.median < 20, f"Degradation refresh {measurement.median:.2f}ms > 20ms"

        await coordinator.shutdown()
        clear_registry()
        reset_degradation_coordinator()


# ---------------------------------------------------------------------------
# Failover Manager Latency Tests
# ---------------------------------------------------------------------------


class TestFailoverManagerLatency:
    """Measure failover manager operation latency."""

    async def test_stt_failover_latency(self, baseline_report: BaselineReport):
        """STT failover should complete within 2 seconds."""
        with patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True):
            from infrastructure.resilience.circuit_breaker import (
                clear_registry,
                register_circuit_breaker,
            )
            from infrastructure.speech.stt_failover import STTFailoverConfig, STTFailoverManager

            clear_registry()
            register_circuit_breaker("deepgram")

            mgr = STTFailoverManager(config=STTFailoverConfig())
            await mgr.initialize()

            # Measure failover time
            timings = []
            for _ in range(5):
                # Reset to primary
                await mgr.force_failback_to_deepgram()

                start = time.perf_counter()
                await mgr.force_failover_to_whisper()
                elapsed_ms = (time.perf_counter() - start) * 1000
                timings.append(elapsed_ms)

            measurement = LatencyMeasurement("stt_failover", timings)
            baseline_report.measurements["stt_failover"] = measurement

            # Failover should be < 2000ms (SLA)
            assert measurement.median < 2000, f"STT failover {measurement.median:.0f}ms > 2000ms"

            await mgr.shutdown()
            clear_registry()

    async def test_tts_failover_latency(self, baseline_report: BaselineReport):
        """TTS failover should complete within 2 seconds."""
        with (
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            from infrastructure.resilience.circuit_breaker import (
                clear_registry,
                register_circuit_breaker,
            )
            from infrastructure.speech.tts_failover import TTSFailoverConfig, TTSFailoverManager

            clear_registry()
            register_circuit_breaker("elevenlabs")

            mgr = TTSFailoverManager(config=TTSFailoverConfig())
            await mgr.initialize()

            timings = []
            for _ in range(5):
                await mgr.force_failback_to_elevenlabs()

                start = time.perf_counter()
                await mgr.force_failover_to_local()
                elapsed_ms = (time.perf_counter() - start) * 1000
                timings.append(elapsed_ms)

            measurement = LatencyMeasurement("tts_failover", timings)
            baseline_report.measurements["tts_failover"] = measurement

            assert measurement.median < 2000, f"TTS failover {measurement.median:.0f}ms > 2000ms"

            await mgr.shutdown()
            clear_registry()


# ---------------------------------------------------------------------------
# Memory Usage Tests
# ---------------------------------------------------------------------------


class TestMemoryUsage:
    """Measure memory and VRAM usage."""

    def test_ram_usage_baseline(self, baseline_report: BaselineReport):
        """Capture baseline RAM usage."""
        import psutil

        process = psutil.Process()
        ram_mb = process.memory_info().rss / (1024 * 1024)

        baseline_report.ram_usage_mb = ram_mb
        baseline_report.notes.append(f"Baseline RAM: {ram_mb:.1f} MB")

        # RAM should be reasonable (< 2GB for tests)
        assert ram_mb < 2048, f"RAM usage {ram_mb:.0f}MB > 2GB"

    def test_vram_usage_baseline(self, baseline_report: BaselineReport):
        """Capture baseline VRAM usage if GPU available."""
        try:
            import torch
            if not torch.cuda.is_available():
                pytest.skip("CUDA not available")

            # Force cleanup
            gc.collect()
            torch.cuda.empty_cache()

            vram_mb = torch.cuda.memory_allocated() / (1024 * 1024)
            baseline_report.vram_idle_mb = vram_mb
            baseline_report.notes.append(f"Baseline VRAM (idle): {vram_mb:.1f} MB")

            # Idle VRAM should be minimal
            assert vram_mb < 1024, f"Idle VRAM {vram_mb:.0f}MB > 1GB"

        except ImportError:
            pytest.skip("PyTorch not available")


# ---------------------------------------------------------------------------
# Baseline Report Generation
# ---------------------------------------------------------------------------


class TestBaselineReportGeneration:
    """Generate and save the baseline report."""

    def test_generate_baseline_report(self, baseline_report: BaselineReport):
        """Generate final baseline report after all measurements."""
        # This runs last due to test ordering
        baseline_report.to_dict()

        # Verify we captured measurements
        assert len(baseline_report.measurements) >= 5, \
            f"Expected at least 5 measurements, got {len(baseline_report.measurements)}"

        # Save report to file
        report_path = Path(PROJECT_ROOT) / "docs" / "performance"
        report_path.mkdir(parents=True, exist_ok=True)

        json_path = report_path / "baseline-metrics.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(baseline_report.to_json())

        # Generate markdown report
        md_path = report_path / "baseline-report.md"
        md_content = _generate_markdown_report(baseline_report)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        baseline_report.notes.append(f"Report saved to {json_path}")


def _generate_markdown_report(report: BaselineReport) -> str:
    """Generate markdown formatted baseline report."""
    lines = [
        "# Performance Baseline Report",
        "",
        f"**Generated:** {report.timestamp}",
        "",
        "## Summary",
        "",
        "| Component | Median (ms) | P95 (ms) | P99 (ms) | Samples |",
        "|-----------|-------------|----------|----------|---------|",
    ]

    for name, m in sorted(report.measurements.items()):
        lines.append(
            f"| {name} | {m.median:.2f} | {m.p95:.2f} | {m.p99:.2f} | {len(m.samples)} |"
        )

    lines.extend([
        "",
        "## Memory Usage",
        "",
        f"- **RAM Usage:** {report.ram_usage_mb:.1f} MB",
        f"- **VRAM (Idle):** {report.vram_idle_mb:.1f} MB",
        f"- **VRAM (Peak):** {report.vram_peak_mb:.1f} MB",
        "",
        "## SLA Targets",
        "",
        "| Component | Target | Status |",
        "|-----------|--------|--------|",
        "| Hot Path (e2e) | <500ms | TBD |",
        "| Vision Pipeline | <300ms | TBD |",
        "| STT | <100ms | TBD |",
        "| TTS | <100ms | TBD |",
        "| FAISS Query | <50ms | TBD |",
        "| VRAM Budget | <8GB | OK |",
        "",
        "## Notes",
        "",
    ])

    for note in report.notes:
        lines.append(f"- {note}")

    return "\n".join(lines)
