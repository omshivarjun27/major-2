"""Tests for canary deployment scripts (T-139)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.canary_analysis import (
    ServiceMetrics,
    collect_metrics,
    compare_metrics,
    generate_report,
    should_rollback,
)
from scripts.canary_deploy import (
    _load_state,
    _save_state,
    build_parser,
)

# ---------------------------------------------------------------------------
# canary_analysis tests
# ---------------------------------------------------------------------------

class TestServiceMetrics:
    """ServiceMetrics construction edge cases."""

    def test_default_metrics(self) -> None:
        """ServiceMetrics has sensible defaults."""
        m = ServiceMetrics(service_name="test")
        assert m.error_rate == 0.0
        assert m.p95_latency_ms == 0.0
        assert m.request_count == 0

    def test_custom_metrics(self) -> None:
        """Custom metrics are stored correctly."""
        m = ServiceMetrics(service_name="svc", error_rate=0.05, p95_latency_ms=250.0)
        assert m.error_rate == pytest.approx(0.05)
        assert m.p95_latency_ms == pytest.approx(250.0)


class TestCollectMetrics:
    """collect_metrics uses env var overrides."""

    def test_collect_uses_env_vars(self) -> None:
        """Metrics are read from environment variables."""
        env = {
            "CANARY_METRICS_APP_STABLE_ERROR_RATE": "0.02",
            "CANARY_METRICS_APP_STABLE_P95_MS": "200.0",
        }
        with patch.dict(os.environ, env):
            m = collect_metrics("app-stable")
        assert m.error_rate == pytest.approx(0.02)
        assert m.p95_latency_ms == pytest.approx(200.0)
        assert m.service_name == "app-stable"

    def test_collect_defaults_without_env(self) -> None:
        """collect_metrics returns defaults when no env vars set."""
        clean = {k: v for k, v in os.environ.items()
                 if not k.startswith("CANARY_METRICS_")}
        with patch.dict(os.environ, clean, clear=True):
            m = collect_metrics("unknown-service")
        assert isinstance(m.error_rate, float)
        assert m.request_count >= 0


class TestCompareMetrics:
    """compare_metrics threshold logic."""

    def _stable(self, error_rate: float = 0.01, p95: float = 150.0) -> ServiceMetrics:
        return ServiceMetrics(service_name="stable", error_rate=error_rate,
                               p95_latency_ms=p95, cpu_percent=20.0)

    def _canary(self, error_rate: float = 0.01, p95: float = 150.0,
                cpu: float = 20.0) -> ServiceMetrics:
        return ServiceMetrics(service_name="canary", error_rate=error_rate,
                               p95_latency_ms=p95, cpu_percent=cpu)

    def test_equal_metrics_healthy(self) -> None:
        """Equal metrics produce healthy verdict."""
        result = compare_metrics(self._stable(), self._canary())
        assert result.verdict == "healthy"
        assert not should_rollback(result)

    def test_error_rate_2x_triggers_rollback(self) -> None:
        """Error rate at 2x stable triggers degraded verdict."""
        stable = self._stable(error_rate=0.01)
        canary = self._canary(error_rate=0.02)
        result = compare_metrics(stable, canary, error_rate_threshold=2.0)
        assert result.verdict == "degraded"
        assert should_rollback(result)

    def test_error_rate_below_threshold_healthy(self) -> None:
        """Error rate below 2x threshold stays healthy."""
        stable = self._stable(error_rate=0.01)
        canary = self._canary(error_rate=0.015)  # 1.5x — under 2x threshold
        result = compare_metrics(stable, canary, error_rate_threshold=2.0)
        assert result.verdict == "healthy"

    def test_p95_latency_1_5x_triggers_rollback(self) -> None:
        """P95 latency at 1.5x stable triggers degraded verdict."""
        stable = self._stable(p95=100.0)
        canary = self._canary(p95=150.0)  # exactly 1.5x
        result = compare_metrics(stable, canary, p95_threshold=1.5)
        assert result.verdict == "degraded"

    def test_high_cpu_triggers_degraded(self) -> None:
        """Canary CPU above 85% triggers degraded verdict."""
        result = compare_metrics(self._stable(), self._canary(cpu=90.0))
        assert result.verdict == "degraded"

    def test_zero_stable_metrics_no_crash(self) -> None:
        """Zero stable metrics don't cause division by zero."""
        stable = ServiceMetrics(service_name="stable", error_rate=0.0, p95_latency_ms=0.0)
        canary = ServiceMetrics(service_name="canary", error_rate=0.01, p95_latency_ms=100.0)
        result = compare_metrics(stable, canary)
        assert result is not None
        assert result.verdict in ("healthy", "degraded")

    def test_comparison_result_contains_reasons(self) -> None:
        """Degraded result includes human-readable reason strings."""
        stable = self._stable(error_rate=0.01)
        canary = self._canary(error_rate=0.05)
        result = compare_metrics(stable, canary, error_rate_threshold=2.0)
        assert any("error_rate" in r for r in result.reasons)


class TestGenerateReport:
    """generate_report output structure."""

    def test_report_is_dict(self) -> None:
        """generate_report returns a dict."""
        stable = ServiceMetrics(service_name="stable")
        canary = ServiceMetrics(service_name="canary")
        result = compare_metrics(stable, canary)
        report = generate_report(result)
        assert isinstance(report, dict)

    def test_report_has_required_keys(self) -> None:
        """Report contains verdict, metrics, ratios, should_rollback."""
        stable = ServiceMetrics(service_name="stable")
        canary = ServiceMetrics(service_name="canary")
        result = compare_metrics(stable, canary)
        report = generate_report(result)
        for key in ("verdict", "should_rollback", "metrics", "ratios", "generated_at"):
            assert key in report, f"Missing key: {key}"

    def test_report_is_json_serializable(self) -> None:
        """Report can be serialized to JSON."""
        stable = ServiceMetrics(service_name="stable", error_rate=0.01, p95_latency_ms=120.0)
        canary = ServiceMetrics(service_name="canary", error_rate=0.03, p95_latency_ms=180.0)
        result = compare_metrics(stable, canary)
        report = generate_report(result)
        json_str = json.dumps(report)
        assert json_str


# ---------------------------------------------------------------------------
# canary_deploy state management tests
# ---------------------------------------------------------------------------

class TestCanaryDeployState:
    """State persistence tests for canary_deploy."""

    def test_load_state_when_no_file(self, tmp_path: Path) -> None:
        """Loading state when file absent returns inactive state."""
        with patch("scripts.canary_deploy.STATE_FILE", tmp_path / "state.json"):
            state = _load_state()
        assert state["active"] is False
        assert state["canary_image"] is None

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        """State saved then loaded is identical."""
        state_file = tmp_path / "state.json"
        data = {"active": True, "canary_image": "v2.1.0", "traffic_pct": 10}
        with patch("scripts.canary_deploy.STATE_FILE", state_file):
            _save_state(data)
            loaded = _load_state()
        assert loaded["active"] is True
        assert loaded["canary_image"] == "v2.1.0"

    def test_save_corrupted_file_handled(self, tmp_path: Path) -> None:
        """Corrupted state file returns default state."""
        state_file = tmp_path / "state.json"
        state_file.write_text("NOT JSON", encoding="utf-8")
        with patch("scripts.canary_deploy.STATE_FILE", state_file):
            state = _load_state()
        assert state["active"] is False


class TestCanaryDeployParser:
    """Argument parser edge cases."""

    def test_parser_constructs(self) -> None:
        """build_parser returns a valid ArgumentParser."""
        parser = build_parser()
        assert parser is not None

    def test_deploy_requires_image(self) -> None:
        """deploy subcommand requires --image argument."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["deploy"])

    def test_deploy_with_image_parses(self) -> None:
        """deploy subcommand with --image parses correctly."""
        parser = build_parser()
        args = parser.parse_args(["deploy", "--image", "v2.1.0"])
        assert args.command == "deploy"
        assert args.image == "v2.1.0"
        assert args.traffic == 10  # default

    def test_deploy_custom_traffic(self) -> None:
        """deploy --traffic sets custom percentage."""
        parser = build_parser()
        args = parser.parse_args(["deploy", "--image", "v2.1.0", "--traffic", "20"])
        assert args.traffic == 20

    def test_promote_subcommand(self) -> None:
        """promote subcommand parses correctly."""
        parser = build_parser()
        args = parser.parse_args(["promote"])
        assert args.command == "promote"

    def test_rollback_subcommand(self) -> None:
        """rollback subcommand parses correctly."""
        parser = build_parser()
        args = parser.parse_args(["rollback"])
        assert args.command == "rollback"

    def test_status_subcommand(self) -> None:
        """status subcommand parses correctly."""
        parser = build_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"
