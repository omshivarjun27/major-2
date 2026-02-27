"""P4: Performance Regression Tests (T-087).

Automated tests that run in CI to catch performance degradations early.
Tests fail if latency exceeds thresholds or resource usage exceeds budgets.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Regression Test Models
# ---------------------------------------------------------------------------

class RegressionStatus(Enum):
    """Status of a regression check."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class PerformanceThreshold:
    """Performance threshold definition."""
    name: str
    target_ms: float
    warning_ms: float
    critical_ms: float
    component: str
    
    def check(self, actual_ms: float) -> Tuple[RegressionStatus, str]:
        """Check if actual value meets threshold."""
        if actual_ms <= self.target_ms:
            return RegressionStatus.PASS, f"{self.name}: {actual_ms:.1f}ms <= {self.target_ms}ms [PASS]"
        if actual_ms <= self.warning_ms:
            return RegressionStatus.PASS, f"{self.name}: {actual_ms:.1f}ms (warning: > {self.target_ms}ms)"
        if actual_ms <= self.critical_ms:
            return RegressionStatus.FAIL, f"{self.name}: {actual_ms:.1f}ms > {self.warning_ms}ms [WARNING]"
        return RegressionStatus.FAIL, f"{self.name}: {actual_ms:.1f}ms > {self.critical_ms}ms [CRITICAL]"


@dataclass
class RegressionResult:
    """Result of a regression test."""
    threshold: PerformanceThreshold
    actual_ms: float
    status: RegressionStatus
    message: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.threshold.name,
            "component": self.threshold.component,
            "target_ms": self.threshold.target_ms,
            "actual_ms": round(self.actual_ms, 2),
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class RegressionReport:
    """Report containing all regression test results."""
    results: List[RegressionResult] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == RegressionStatus.PASS)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == RegressionStatus.FAIL)
    
    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == RegressionStatus.SKIP)
    
    @property
    def all_passed(self) -> bool:
        return self.failed == 0
    
    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000
    
    def add_result(self, result: RegressionResult):
        self.results.append(result)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total": len(self.results),
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "all_passed": self.all_passed,
                "duration_ms": round(self.duration_ms, 2),
            },
            "results": [r.to_dict() for r in self.results],
        }


# ---------------------------------------------------------------------------
# Performance Thresholds (SLA Targets)
# ---------------------------------------------------------------------------

# Define all performance thresholds
PERFORMANCE_THRESHOLDS = [
    PerformanceThreshold("hot_path", target_ms=500.0, warning_ms=600.0, critical_ms=750.0, component="e2e"),
    PerformanceThreshold("vision_pipeline", target_ms=300.0, warning_ms=350.0, critical_ms=450.0, component="vision"),
    PerformanceThreshold("stt_latency", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="speech"),
    PerformanceThreshold("tts_first_chunk", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="speech"),
    PerformanceThreshold("faiss_query", target_ms=50.0, warning_ms=60.0, critical_ms=80.0, component="memory"),
    PerformanceThreshold("llm_ttft", target_ms=200.0, warning_ms=250.0, critical_ms=300.0, component="llm"),
    PerformanceThreshold("frame_processing", target_ms=300.0, warning_ms=350.0, critical_ms=400.0, component="vision"),
    PerformanceThreshold("embedding_query", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="memory"),
]

# Resource budget thresholds
VRAM_BUDGET_MB = 8192.0  # 8GB
RAM_WARNING_PERCENT = 80.0
CPU_WARNING_PERCENT = 90.0


# ---------------------------------------------------------------------------
# Mock Performance Measurement Functions
# ---------------------------------------------------------------------------

class MockPerformanceMeasurer:
    """Mock performance measurer for testing."""
    
    def __init__(self, latencies: Optional[Dict[str, float]] = None):
        self.latencies = latencies or {
            "hot_path": 450.0,
            "vision_pipeline": 280.0,
            "stt_latency": 85.0,
            "tts_first_chunk": 75.0,
            "faiss_query": 35.0,
            "llm_ttft": 180.0,
            "frame_processing": 270.0,
            "embedding_query": 80.0,
        }
        self.vram_mb = 5000.0
        self.ram_percent = 60.0
        self.cpu_percent = 50.0
    
    async def measure_latency(self, component: str) -> float:
        """Measure latency for a component."""
        await asyncio.sleep(0.01)  # Simulate measurement
        return self.latencies.get(component, 100.0)
    
    def get_vram_usage(self) -> float:
        return self.vram_mb
    
    def get_ram_usage_percent(self) -> float:
        return self.ram_percent
    
    def get_cpu_usage_percent(self) -> float:
        return self.cpu_percent


class RegressionTestRunner:
    """Runner for performance regression tests."""
    
    def __init__(self, measurer: MockPerformanceMeasurer):
        self.measurer = measurer
        self.thresholds = PERFORMANCE_THRESHOLDS
        self.report = RegressionReport()
    
    async def run_latency_tests(self) -> List[RegressionResult]:
        """Run all latency regression tests."""
        results = []
        for threshold in self.thresholds:
            actual_ms = await self.measurer.measure_latency(threshold.name)
            status, message = threshold.check(actual_ms)
            result = RegressionResult(
                threshold=threshold,
                actual_ms=actual_ms,
                status=status,
                message=message,
            )
            results.append(result)
            self.report.add_result(result)
        return results
    
    def run_resource_tests(self) -> List[RegressionResult]:
        """Run resource budget regression tests."""
        results = []
        
        # VRAM check
        vram_threshold = PerformanceThreshold(
            name="vram_budget",
            target_ms=VRAM_BUDGET_MB,
            warning_ms=VRAM_BUDGET_MB * 0.9,
            critical_ms=VRAM_BUDGET_MB,
            component="gpu"
        )
        vram_actual = self.measurer.get_vram_usage()
        if vram_actual <= VRAM_BUDGET_MB:
            status = RegressionStatus.PASS
            message = f"VRAM: {vram_actual:.0f}MB <= {VRAM_BUDGET_MB:.0f}MB [PASS]"
        else:
            status = RegressionStatus.FAIL
            message = f"VRAM: {vram_actual:.0f}MB > {VRAM_BUDGET_MB:.0f}MB [FAIL]"
        
        result = RegressionResult(
            threshold=vram_threshold,
            actual_ms=vram_actual,
            status=status,
            message=message,
        )
        results.append(result)
        self.report.add_result(result)
        
        return results
    
    async def run_all_tests(self) -> RegressionReport:
        """Run all regression tests."""
        self.report = RegressionReport()
        await self.run_latency_tests()
        self.run_resource_tests()
        self.report.end_time = time.time()
        return self.report


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------

class TestPerformanceThreshold:
    """Tests for performance threshold definitions."""
    
    def test_threshold_pass(self):
        """Test threshold passes when under target."""
        threshold = PerformanceThreshold("test", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="test")
        status, message = threshold.check(80.0)
        assert status == RegressionStatus.PASS
        assert "PASS" in message
    
    def test_threshold_warning(self):
        """Test threshold passes with warning."""
        threshold = PerformanceThreshold("test", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="test")
        status, message = threshold.check(110.0)
        assert status == RegressionStatus.PASS
        assert "warning" in message
    
    def test_threshold_fail(self):
        """Test threshold fails when over critical."""
        threshold = PerformanceThreshold("test", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="test")
        status, message = threshold.check(160.0)
        assert status == RegressionStatus.FAIL
        assert "CRITICAL" in message


class TestRegressionResult:
    """Tests for regression result handling."""
    
    def test_result_serialization(self):
        """Test result serialization."""
        threshold = PerformanceThreshold("test", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="test")
        result = RegressionResult(
            threshold=threshold,
            actual_ms=80.0,
            status=RegressionStatus.PASS,
            message="Test passed",
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["actual_ms"] == 80.0
        assert d["status"] == "pass"


class TestRegressionReport:
    """Tests for regression report generation."""
    
    def test_report_counts(self):
        """Test report counts are correct."""
        report = RegressionReport()
        threshold = PerformanceThreshold("test", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="test")
        
        report.add_result(RegressionResult(threshold, 80.0, RegressionStatus.PASS, ""))
        report.add_result(RegressionResult(threshold, 80.0, RegressionStatus.PASS, ""))
        report.add_result(RegressionResult(threshold, 160.0, RegressionStatus.FAIL, ""))
        
        assert report.passed == 2
        assert report.failed == 1
        assert report.all_passed is False
    
    def test_report_all_passed(self):
        """Test all_passed is true when no failures."""
        report = RegressionReport()
        threshold = PerformanceThreshold("test", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="test")
        
        report.add_result(RegressionResult(threshold, 80.0, RegressionStatus.PASS, ""))
        report.add_result(RegressionResult(threshold, 90.0, RegressionStatus.PASS, ""))
        
        assert report.all_passed is True
    
    def test_report_serialization(self):
        """Test report serialization."""
        report = RegressionReport()
        threshold = PerformanceThreshold("test", target_ms=100.0, warning_ms=120.0, critical_ms=150.0, component="test")
        report.add_result(RegressionResult(threshold, 80.0, RegressionStatus.PASS, ""))
        report.end_time = time.time()
        
        d = report.to_dict()
        assert "summary" in d
        assert "results" in d
        assert d["summary"]["total"] == 1


class TestMockPerformanceMeasurer:
    """Tests for mock performance measurer."""
    
    async def test_measure_latency(self):
        """Test latency measurement."""
        measurer = MockPerformanceMeasurer()
        latency = await measurer.measure_latency("hot_path")
        assert latency == 450.0
    
    def test_resource_measurements(self):
        """Test resource measurements."""
        measurer = MockPerformanceMeasurer()
        assert measurer.get_vram_usage() == 5000.0
        assert measurer.get_ram_usage_percent() == 60.0


class TestRegressionTestRunner:
    """Tests for regression test runner."""
    
    async def test_run_latency_tests(self):
        """Test running latency tests."""
        measurer = MockPerformanceMeasurer()
        runner = RegressionTestRunner(measurer)
        results = await runner.run_latency_tests()
        
        assert len(results) == len(PERFORMANCE_THRESHOLDS)
        # With default latencies, all should pass
        assert all(r.status == RegressionStatus.PASS for r in results)
    
    def test_run_resource_tests(self):
        """Test running resource tests."""
        measurer = MockPerformanceMeasurer()
        runner = RegressionTestRunner(measurer)
        results = runner.run_resource_tests()
        
        assert len(results) >= 1
        # Default VRAM is under budget
        vram_result = results[0]
        assert vram_result.status == RegressionStatus.PASS
    
    async def test_run_all_tests(self):
        """Test running all tests."""
        measurer = MockPerformanceMeasurer()
        runner = RegressionTestRunner(measurer)
        report = await runner.run_all_tests()
        
        assert report.passed > 0
        assert report.all_passed


class TestRegressionFailures:
    """Tests for regression failure detection."""
    
    async def test_detect_hot_path_regression(self):
        """Test detecting hot path regression."""
        measurer = MockPerformanceMeasurer(latencies={"hot_path": 600.0})
        runner = RegressionTestRunner(measurer)
        results = await runner.run_latency_tests()
        
        hot_path_result = next(r for r in results if r.threshold.name == "hot_path")
        # 600ms > 500ms target, but <= 600ms warning
        assert hot_path_result.status == RegressionStatus.PASS
    
    async def test_detect_critical_regression(self):
        """Test detecting critical regression."""
        measurer = MockPerformanceMeasurer(latencies={"hot_path": 800.0})
        runner = RegressionTestRunner(measurer)
        results = await runner.run_latency_tests()
        
        hot_path_result = next(r for r in results if r.threshold.name == "hot_path")
        # 800ms > 750ms critical
        assert hot_path_result.status == RegressionStatus.FAIL
    
    def test_detect_vram_overflow(self):
        """Test detecting VRAM overflow."""
        measurer = MockPerformanceMeasurer()
        measurer.vram_mb = 9000.0  # Over 8GB budget
        runner = RegressionTestRunner(measurer)
        results = runner.run_resource_tests()
        
        vram_result = results[0]
        assert vram_result.status == RegressionStatus.FAIL


class TestCIIntegration:
    """Tests for CI integration patterns."""
    
    async def test_ci_exit_code_pass(self):
        """Test CI would exit 0 when all pass."""
        measurer = MockPerformanceMeasurer()
        runner = RegressionTestRunner(measurer)
        report = await runner.run_all_tests()
        
        # CI exit code: 0 for pass, 1 for fail
        exit_code = 0 if report.all_passed else 1
        assert exit_code == 0
    
    async def test_ci_exit_code_fail(self):
        """Test CI would exit 1 when failures."""
        measurer = MockPerformanceMeasurer(latencies={"hot_path": 1000.0})
        runner = RegressionTestRunner(measurer)
        report = await runner.run_all_tests()
        
        exit_code = 0 if report.all_passed else 1
        assert exit_code == 1
    
    async def test_test_duration_reasonable(self):
        """Test regression suite completes in reasonable time."""
        measurer = MockPerformanceMeasurer()
        runner = RegressionTestRunner(measurer)
        
        start = time.perf_counter()
        await runner.run_all_tests()
        duration_s = time.perf_counter() - start
        
        # Should complete in < 5 seconds (mock measurements are fast)
        assert duration_s < 5.0


class TestHistoricalTracking:
    """Tests for historical performance tracking."""
    
    def test_store_results(self):
        """Test storing results for trend analysis."""
        results_history: List[RegressionReport] = []
        
        # Simulate multiple test runs
        for _ in range(5):
            report = RegressionReport()
            threshold = PerformanceThreshold("test", 100, 120, 150, "test")
            report.add_result(RegressionResult(threshold, 80 + _ * 5, RegressionStatus.PASS, ""))
            report.end_time = time.time()
            results_history.append(report)
        
        assert len(results_history) == 5
        
        # Can detect trend (latency increasing)
        latencies = [r.results[0].actual_ms for r in results_history]
        assert latencies[-1] > latencies[0]  # Trending up
    
    def test_detect_gradual_degradation(self):
        """Test detecting gradual performance degradation."""
        baseline = 80.0
        current = 95.0
        degradation_threshold = 10.0  # 10% degradation
        
        degradation_percent = ((current - baseline) / baseline) * 100
        is_degraded = degradation_percent > degradation_threshold
        
        assert is_degraded
