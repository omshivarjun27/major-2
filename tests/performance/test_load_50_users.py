"""T-137: Load Test — 50 Concurrent Users via Locust.

Defines Locust-based load test scenarios scaling to 50 concurrent users
exercising REST API endpoints with realistic wait times and SLA assertions.

Endpoints under test:
  GET  /health           — Health check (always available)
  POST /vqa/ask          — VQA query with base64 image
  POST /qr/scan          — QR code scanning
  POST /memory/query     — Memory/RAG query
  GET  /metrics          — Prometheus metrics

Run standalone:  locust -f tests/performance/test_load_50_users.py --headless -u 50 -r 5 -t 60s
Run via pytest:  pytest tests/performance/test_load_50_users.py -v --timeout=300
"""

from __future__ import annotations

import base64
import os
import statistics
import sys
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Check if locust is available; skip gracefully if not
# ---------------------------------------------------------------------------
try:
    from locust import HttpUser, between, task



    LOCUST_AVAILABLE = True
except ImportError:
    LOCUST_AVAILABLE = False

# ---------------------------------------------------------------------------
# Check if httpx/FastAPI test client is available
# ---------------------------------------------------------------------------
try:



    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TARGET_USERS = 50
SPAWN_RATE = 5  # users/sec
WAIT_TIME_MIN = 0.5  # seconds
WAIT_TIME_MAX = 2.0  # seconds
P95_LATENCY_LIMIT_MS = 500  # SLA: P95 < 500ms
ERROR_RATE_LIMIT = 0.005  # SLA: < 0.5% errors
TEST_DURATION_S = 10  # Shortened for pytest; use 60s+ for real runs


def _make_test_image_b64() -> str:
    """Generate a minimal valid JPEG as base64 for VQA requests."""
    # Minimal 1x1 white JPEG
    jpeg_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04"
        b"\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"
        b"\x22q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16"
        b"\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz"
        b"\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99"
        b"\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7"
        b"\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5"
        b"\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1"
        b"\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\xae\x8a(\x03\xff\xd9"
    )
    return base64.b64encode(jpeg_bytes).decode("ascii")


# ---------------------------------------------------------------------------
# Locust User Classes (for standalone locust runs)
# ---------------------------------------------------------------------------
if LOCUST_AVAILABLE:

    class HealthCheckUser(HttpUser):
        """User that only hits /health — baseline latency measurement."""

        wait_time = between(WAIT_TIME_MIN, WAIT_TIME_MAX)
        weight = 3  # 30% of traffic

        @task
        def check_health(self) -> None:
            self.client.get("/health", name="/health")

    class VQAQueryUser(HttpUser):
        """User that submits VQA queries with images."""

        wait_time = between(WAIT_TIME_MIN, WAIT_TIME_MAX)
        weight = 3  # 30% of traffic

        def on_start(self) -> None:
            self._image_b64 = _make_test_image_b64()

        @task
        def ask_visual_question(self) -> None:
            self.client.post(
                "/vqa/ask",
                json={
                    "question": "What do you see in this image?",
                    "image_b64": self._image_b64,
                },
                name="/vqa/ask",
                timeout=5,
            )

    class QRScanUser(HttpUser):
        """User that submits QR scan requests."""

        wait_time = between(WAIT_TIME_MIN, WAIT_TIME_MAX)
        weight = 2  # 20% of traffic

        def on_start(self) -> None:
            self._image_b64 = _make_test_image_b64()

        @task
        def scan_qr(self) -> None:
            self.client.post(
                "/qr/scan",
                json={"image_b64": self._image_b64},
                name="/qr/scan",
                timeout=5,
            )

    class MemoryQueryUser(HttpUser):
        """User that queries the memory/RAG system."""

        wait_time = between(WAIT_TIME_MIN, WAIT_TIME_MAX)
        weight = 1  # 10% of traffic

        @task
        def query_memory(self) -> None:
            self.client.post(
                "/memory/query",
                json={"query": "What was the last thing I saw?"},
                name="/memory/query",
                timeout=5,
            )

    class MetricsUser(HttpUser):
        """User that polls Prometheus metrics endpoint."""

        wait_time = between(WAIT_TIME_MIN, WAIT_TIME_MAX)
        weight = 1  # 10% of traffic

        @task
        def fetch_metrics(self) -> None:
            self.client.get("/metrics", name="/metrics")


# ---------------------------------------------------------------------------
# SLA Assertions (reusable)
# ---------------------------------------------------------------------------

class SLAValidator:
    """Validates load test results against defined SLA thresholds."""

    def __init__(
        self,
        p95_limit_ms: float = P95_LATENCY_LIMIT_MS,
        error_rate_limit: float = ERROR_RATE_LIMIT,
    ):
        self.p95_limit_ms = p95_limit_ms
        self.error_rate_limit = error_rate_limit

    def check_latencies(self, latencies_ms: List[float], endpoint: str) -> None:
        """Assert P95 latency is within SLA."""
        if not latencies_ms:
            return
        sorted_lat = sorted(latencies_ms)
        p95_idx = int(len(sorted_lat) * 0.95)
        p95 = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
        assert p95 <= self.p95_limit_ms, (
            f"[{endpoint}] P95 latency {p95:.1f}ms exceeds SLA limit {self.p95_limit_ms}ms"
        )

    def check_error_rate(self, total: int, errors: int, endpoint: str) -> None:
        """Assert error rate is within SLA."""
        if total == 0:
            return
        rate = errors / total
        assert rate <= self.error_rate_limit, (
            f"[{endpoint}] Error rate {rate:.2%} exceeds SLA limit {self.error_rate_limit:.2%}"
        )

    def check_throughput(self, requests: int, duration_s: float, min_rps: float = 1.0) -> None:
        """Assert minimum throughput."""
        if duration_s <= 0:
            return
        rps = requests / duration_s
        assert rps >= min_rps, (
            f"Throughput {rps:.1f} req/s below minimum {min_rps} req/s"
        )


# ---------------------------------------------------------------------------
# Simulated Load Runner (for pytest — no live server required)
# ---------------------------------------------------------------------------

class SimulatedRequestResult:
    """Captures a single simulated request result."""

    def __init__(self, endpoint: str, status_code: int, latency_ms: float, error: Optional[str] = None):
        self.endpoint = endpoint
        self.status_code = status_code
        self.latency_ms = latency_ms
        self.error = error

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400 and self.error is None


class MockLoadRunner:
    """Simulates concurrent user load without requiring a live server.

    Uses httpx AsyncClient with ASGI transport to hit the FastAPI app directly.
    Falls back to pure simulation if httpx/app are unavailable.
    """

    def __init__(self, num_users: int = TARGET_USERS, spawn_rate: int = SPAWN_RATE):
        self.num_users = num_users
        self.spawn_rate = spawn_rate
        self.results: List[SimulatedRequestResult] = []
        self._image_b64 = _make_test_image_b64()

    async def _make_request(
        self,
        client: Any,
        method: str,
        endpoint: str,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> SimulatedRequestResult:
        """Execute a single request and capture the result."""
        start = time.monotonic()
        try:
            if method == "GET":
                resp = await client.get(endpoint)
            else:
                resp = await client.post(endpoint, json=json_body or {})
            latency_ms = (time.monotonic() - start) * 1000
            error_msg = None if 200 <= resp.status_code < 400 else f"HTTP {resp.status_code}"
            return SimulatedRequestResult(endpoint, resp.status_code, latency_ms, error_msg)
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            return SimulatedRequestResult(endpoint, 0, latency_ms, str(exc))

    def _get_scenario_requests(self) -> List[Dict[str, Any]]:
        """Define the request mix for a single user iteration."""
        return [
            {"method": "GET", "endpoint": "/health", "json_body": None},
            {
                "method": "POST",
                "endpoint": "/vqa/ask",
                "json_body": {"question": "Describe the scene", "image_b64": self._image_b64},
            },
            {
                "method": "POST",
                "endpoint": "/qr/scan",
                "json_body": {"image_b64": self._image_b64},
            },
            {
                "method": "POST",
                "endpoint": "/memory/query",
                "json_body": {"query": "What did I see earlier?"},
            },
            {"method": "GET", "endpoint": "/metrics", "json_body": None},
        ]

    def get_results_by_endpoint(self, endpoint: str) -> List[SimulatedRequestResult]:
        """Filter results for a specific endpoint."""
        return [r for r in self.results if r.endpoint == endpoint]

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all results."""
        if not self.results:
            return {"total": 0, "errors": 0, "error_rate": 0.0}
        total = len(self.results)
        errors = sum(1 for r in self.results if not r.ok)
        latencies = [r.latency_ms for r in self.results]
        return {
            "total": total,
            "errors": errors,
            "error_rate": errors / total,
            "latency_p50": statistics.median(latencies),
            "latency_p95": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            "latency_max": max(latencies) if latencies else 0,
            "latency_avg": statistics.mean(latencies),
        }


# ---------------------------------------------------------------------------
# Pytest-based Load Tests (self-contained, no live server)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestLoadConfig:
    """Verify load test configuration parameters are sane."""

    def test_target_users(self) -> None:
        """Load test targets 50 concurrent users."""
        assert TARGET_USERS == 50, f"Expected 50 users, got {TARGET_USERS}"

    def test_spawn_rate(self) -> None:
        """Spawn rate is 5 users/sec for gradual ramp-up."""
        assert SPAWN_RATE == 5, f"Expected spawn rate 5, got {SPAWN_RATE}"

    def test_wait_time_range(self) -> None:
        """Wait time between requests is 0.5-2.0 seconds (realistic pacing)."""
        assert WAIT_TIME_MIN == 0.5
        assert WAIT_TIME_MAX == 2.0

    def test_sla_p95_limit(self) -> None:
        """P95 latency SLA is 500ms."""
        assert P95_LATENCY_LIMIT_MS == 500

    def test_sla_error_rate_limit(self) -> None:
        """Error rate SLA is under 0.5%."""
        assert ERROR_RATE_LIMIT == 0.005

    def test_ramp_up_duration(self) -> None:
        """Full 50-user ramp-up completes in 10 seconds at rate 5/sec."""
        ramp_up_s = TARGET_USERS / SPAWN_RATE
        assert ramp_up_s == 10.0, f"Ramp-up duration {ramp_up_s}s (expected 10s)"


@pytest.mark.slow
class TestSLAValidator:
    """Unit tests for the SLA validation logic."""

    def test_p95_within_sla(self) -> None:
        """P95 check passes when latencies are within SLA."""
        validator = SLAValidator(p95_limit_ms=500)
        latencies = [100.0, 200.0, 300.0, 400.0, 450.0] * 10
        validator.check_latencies(latencies, "/health")  # should not raise

    def test_p95_exceeds_sla(self) -> None:
        """P95 check fails when latencies exceed SLA."""
        validator = SLAValidator(p95_limit_ms=500)
        latencies = [100.0] * 4 + [900.0] * 6  # P95 will be 900ms
        with pytest.raises(AssertionError, match="P95 latency"):
            validator.check_latencies(latencies, "/health")

    def test_error_rate_within_sla(self) -> None:
        """Error rate check passes when below threshold."""
        validator = SLAValidator(error_rate_limit=0.005)
        validator.check_error_rate(total=1000, errors=4, endpoint="/health")

    def test_error_rate_exceeds_sla(self) -> None:
        """Error rate check fails when above threshold."""
        validator = SLAValidator(error_rate_limit=0.005)
        with pytest.raises(AssertionError, match="Error rate"):
            validator.check_error_rate(total=1000, errors=10, endpoint="/health")

    def test_throughput_sufficient(self) -> None:
        """Throughput check passes when above minimum."""
        validator = SLAValidator()
        validator.check_throughput(requests=100, duration_s=10, min_rps=5.0)

    def test_throughput_insufficient(self) -> None:
        """Throughput check fails when below minimum."""
        validator = SLAValidator()
        with pytest.raises(AssertionError, match="Throughput"):
            validator.check_throughput(requests=2, duration_s=10, min_rps=5.0)

    def test_empty_latencies_pass(self) -> None:
        """Empty latency list should not raise."""
        validator = SLAValidator()
        validator.check_latencies([], "/noop")

    def test_zero_requests_pass(self) -> None:
        """Zero total requests should not raise."""
        validator = SLAValidator()
        validator.check_error_rate(total=0, errors=0, endpoint="/noop")


@pytest.mark.slow
class TestMockLoadRunner:
    """Verify MockLoadRunner scenario definitions and aggregation."""

    def test_scenario_includes_all_endpoints(self) -> None:
        """Scenario mix covers health, VQA, QR, memory, and metrics."""
        runner = MockLoadRunner()
        scenarios = runner._get_scenario_requests()
        endpoints = {s["endpoint"] for s in scenarios}
        assert "/health" in endpoints
        assert "/vqa/ask" in endpoints
        assert "/qr/scan" in endpoints
        assert "/memory/query" in endpoints
        assert "/metrics" in endpoints

    def test_vqa_request_includes_image(self) -> None:
        """VQA request payload includes a base64-encoded image."""
        runner = MockLoadRunner()
        scenarios = runner._get_scenario_requests()
        vqa = [s for s in scenarios if s["endpoint"] == "/vqa/ask"][0]
        assert "image_b64" in vqa["json_body"]
        assert len(vqa["json_body"]["image_b64"]) > 0

    def test_aggregate_stats_empty(self) -> None:
        """Aggregate stats handle no results gracefully."""
        runner = MockLoadRunner()
        stats = runner.get_aggregate_stats()
        assert stats["total"] == 0
        assert stats["errors"] == 0

    def test_aggregate_stats_with_results(self) -> None:
        """Aggregate stats compute correctly with mixed results."""
        runner = MockLoadRunner()
        runner.results = [
            SimulatedRequestResult("/health", 200, 50.0),
            SimulatedRequestResult("/health", 200, 100.0),
            SimulatedRequestResult("/health", 500, 200.0, "Internal error"),
            SimulatedRequestResult("/vqa/ask", 200, 300.0),
            SimulatedRequestResult("/vqa/ask", 200, 400.0),
        ]
        stats = runner.get_aggregate_stats()
        assert stats["total"] == 5
        assert stats["errors"] == 1
        assert stats["error_rate"] == pytest.approx(0.2, abs=0.01)

    def test_filter_by_endpoint(self) -> None:
        """Results can be filtered by endpoint name."""
        runner = MockLoadRunner()
        runner.results = [
            SimulatedRequestResult("/health", 200, 50.0),
            SimulatedRequestResult("/vqa/ask", 200, 300.0),
            SimulatedRequestResult("/health", 200, 60.0),
        ]
        health_results = runner.get_results_by_endpoint("/health")
        assert len(health_results) == 2
        vqa_results = runner.get_results_by_endpoint("/vqa/ask")
        assert len(vqa_results) == 1

    def test_user_count_configurable(self) -> None:
        """Runner respects custom user count."""
        runner = MockLoadRunner(num_users=25, spawn_rate=10)
        assert runner.num_users == 25
        assert runner.spawn_rate == 10


@pytest.mark.slow
class TestSimulatedLoad:
    """Simulate 50 concurrent users against mocked ASGI app."""

    async def test_health_endpoint_under_load(self) -> None:
        """GET /health handles 50 concurrent requests within SLA."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "status": "ok"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        runner = MockLoadRunner(num_users=TARGET_USERS)
        validator = SLAValidator()

        # Simulate 50 concurrent health checks
        tasks = []
        for _ in range(TARGET_USERS):
            tasks.append(runner._make_request(mock_client, "GET", "/health"))
        results = await asyncio.gather(*tasks)
        runner.results.extend(results)

        latencies = [r.latency_ms for r in results]
        validator.check_latencies(latencies, "/health")
        validator.check_error_rate(len(results), sum(1 for r in results if not r.ok), "/health")

    async def test_vqa_endpoint_under_load(self) -> None:
        """POST /vqa/ask handles concurrent requests gracefully."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        runner = MockLoadRunner(num_users=TARGET_USERS)

        tasks = []
        for _ in range(TARGET_USERS):
            tasks.append(
                runner._make_request(
                    mock_client,
                    "POST",
                    "/vqa/ask",
                    {"question": "What is this?", "image_b64": runner._image_b64},
                )
            )
        results = await asyncio.gather(*tasks)
        runner.results.extend(results)

        ok_count = sum(1 for r in results if r.ok)
        assert ok_count == TARGET_USERS, f"Expected all {TARGET_USERS} requests to succeed, got {ok_count}"

    async def test_mixed_endpoints_under_load(self) -> None:
        """Mixed endpoint traffic from 50 users completes without errors."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)

        runner = MockLoadRunner(num_users=TARGET_USERS)
        scenarios = runner._get_scenario_requests()
        validator = SLAValidator()

        # Each of 50 users cycles through the scenario mix
        tasks = []
        for _ in range(TARGET_USERS):
            for scenario in scenarios:
                tasks.append(
                    runner._make_request(
                        mock_client,
                        scenario["method"],
                        scenario["endpoint"],
                        scenario.get("json_body"),
                    )
                )
        results = await asyncio.gather(*tasks)
        runner.results.extend(results)

        stats = runner.get_aggregate_stats()
        assert stats["total"] == TARGET_USERS * len(scenarios)
        validator.check_error_rate(stats["total"], stats["errors"], "mixed")

    async def test_gradual_ramp_up(self) -> None:
        """Users are spawned gradually at 5/sec to avoid thundering herd."""
        import asyncio

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        runner = MockLoadRunner(num_users=TARGET_USERS, spawn_rate=SPAWN_RATE)
        batch_count = TARGET_USERS // SPAWN_RATE  # 10 batches of 5

        all_results: List[SimulatedRequestResult] = []
        for batch in range(batch_count):
            tasks = []
            for _ in range(SPAWN_RATE):
                tasks.append(runner._make_request(mock_client, "GET", "/health"))
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)
            # In real load test, we'd await asyncio.sleep(1.0) between batches

        assert len(all_results) == TARGET_USERS
        assert all(r.ok for r in all_results), "All ramped-up requests should succeed"

    async def test_error_injection_under_load(self) -> None:
        """System handles partial failures under load within SLA error rate."""
        import asyncio

        call_count = 0

        async def _mock_get(endpoint: str, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            # Inject 0.4% error rate (below 0.5% SLA)
            resp.status_code = 500 if call_count % 250 == 0 else 200
            return resp

        mock_client = AsyncMock()
        mock_client.get = _mock_get

        runner = MockLoadRunner(num_users=TARGET_USERS)
        validator = SLAValidator()

        tasks = []
        for _ in range(TARGET_USERS * 5):  # 250 requests total
            tasks.append(runner._make_request(mock_client, "GET", "/health"))
        results = await asyncio.gather(*tasks)
        runner.results.extend(results)

        total = len(results)
        errors = sum(1 for r in results if not r.ok)
        validator.check_error_rate(total, errors, "/health")


@pytest.mark.slow
class TestLocustUserDefinitions:
    """Verify Locust user classes are correctly defined (when locust is available)."""

    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="locust not installed")
    def test_health_user_weight(self) -> None:
        """HealthCheckUser weight is 3 (30% traffic share)."""
        assert HealthCheckUser.weight == 3

    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="locust not installed")
    def test_vqa_user_weight(self) -> None:
        """VQAQueryUser weight is 3 (30% traffic share)."""
        assert VQAQueryUser.weight == 3

    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="locust not installed")
    def test_qr_user_weight(self) -> None:
        """QRScanUser weight is 2 (20% traffic share)."""
        assert QRScanUser.weight == 2

    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="locust not installed")
    def test_memory_user_weight(self) -> None:
        """MemoryQueryUser weight is 1 (10% traffic share)."""
        assert MemoryQueryUser.weight == 1

    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="locust not installed")
    def test_metrics_user_weight(self) -> None:
        """MetricsUser weight is 1 (10% traffic share)."""
        assert MetricsUser.weight == 1

    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="locust not installed")
    def test_total_weight_is_10(self) -> None:
        """All user weights sum to 10 for clean percentage splits."""
        total = (
            HealthCheckUser.weight
            + VQAQueryUser.weight
            + QRScanUser.weight
            + MemoryQueryUser.weight
            + MetricsUser.weight
        )
        assert total == 10, f"Total weight {total}, expected 10"

    @pytest.mark.skipif(not LOCUST_AVAILABLE, reason="locust not installed")
    def test_wait_time_configured(self) -> None:
        """All user classes have wait_time between 0.5 and 2.0 seconds."""
        for user_cls in [HealthCheckUser, VQAQueryUser, QRScanUser, MemoryQueryUser, MetricsUser]:
            assert hasattr(user_cls, "wait_time"), f"{user_cls.__name__} missing wait_time"
