"""Canary metrics analysis for Voice-Vision Assistant (T-139).

Compares error rate, P95 latency, and CPU between canary and stable services.
Auto-rollback thresholds:
  - error_rate > 2x stable
  - p95_latency_ms > 1.5x stable
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("canary-analysis")


@dataclass
class ServiceMetrics:
    """Snapshot of service health metrics."""
    service_name: str
    error_rate: float = 0.0          # fraction 0.0..1.0
    p95_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    request_count: int = 0
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ComparisonResult:
    """Result of comparing canary vs stable metrics."""
    canary: ServiceMetrics
    stable: ServiceMetrics
    error_rate_ratio: float = 1.0     # canary / stable (1.0 = equal)
    p95_ratio: float = 1.0
    cpu_ratio: float = 1.0
    verdict: str = "healthy"          # "healthy" | "degraded" | "unknown"
    reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Metric collection
# ---------------------------------------------------------------------------

def collect_metrics(service_name: str, prometheus_url: Optional[str] = None) -> ServiceMetrics:
    """Collect service metrics from Prometheus or environment stubs.

    In production, this queries the Prometheus API. In test/CI environments
    without Prometheus, it returns stub metrics or reads from env vars.
    """
    # Allow test injection via environment variables
    prefix = f"CANARY_METRICS_{service_name.upper().replace('-', '_')}_"
    error_rate = float(os.environ.get(f"{prefix}ERROR_RATE", "0.01"))
    p95_ms = float(os.environ.get(f"{prefix}P95_MS", "150.0"))
    p50_ms = float(os.environ.get(f"{prefix}P50_MS", "80.0"))
    cpu_pct = float(os.environ.get(f"{prefix}CPU_PCT", "25.0"))
    mem_mb = float(os.environ.get(f"{prefix}MEM_MB", "512.0"))
    req_count = int(os.environ.get(f"{prefix}REQ_COUNT", "1000"))

    if prometheus_url:
        try:
            metrics = _query_prometheus(prometheus_url, service_name)
            return ServiceMetrics(service_name=service_name, **metrics)
        except Exception as exc:
            logger.warning("Prometheus query failed (%s), using env stubs", exc)

    return ServiceMetrics(
        service_name=service_name,
        error_rate=error_rate,
        p95_latency_ms=p95_ms,
        p50_latency_ms=p50_ms,
        cpu_percent=cpu_pct,
        memory_mb=mem_mb,
        request_count=req_count,
    )


def _query_prometheus(base_url: str, service: str) -> Dict[str, Any]:
    """Query Prometheus for service metrics. Returns metric dict."""
    import urllib.request
    import urllib.parse

    def _instant(query: str) -> float:
        params = urllib.parse.urlencode({"query": query})
        url = f"{base_url}/api/v1/query?{params}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        results = data.get("data", {}).get("result", [])
        if not results:
            return 0.0
        return float(results[0]["value"][1])

    return {
        "error_rate": _instant(f'rate(http_requests_total{{job="{service}",status=~"5.."}}[2m])'),
        "p95_latency_ms": _instant(
            f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{job="{service}"}}[2m])) * 1000'
        ),
        "p50_latency_ms": _instant(
            f'histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{{job="{service}"}}[2m])) * 1000'
        ),
        "cpu_percent": _instant(f'rate(process_cpu_seconds_total{{job="{service}"}}[2m]) * 100'),
        "memory_mb": _instant(f'process_resident_memory_bytes{{job="{service}"}} / 1048576'),
        "request_count": int(_instant(f'increase(http_requests_total{{job="{service}"}}[2m])')),
    }


# ---------------------------------------------------------------------------
# Metric comparison
# ---------------------------------------------------------------------------

def compare_metrics(
    stable: ServiceMetrics,
    canary: ServiceMetrics,
    error_rate_threshold: float = 2.0,
    p95_threshold: float = 1.5,
) -> ComparisonResult:
    """Compare canary vs stable metrics and compute ratios.

    Args:
        stable: Baseline stable service metrics.
        canary: Canary service metrics.
        error_rate_threshold: Ratio at which error rate is considered degraded.
        p95_threshold: Ratio at which P95 latency is considered degraded.

    Returns:
        ComparisonResult with verdict and reasons.
    """
    reasons: list[str] = []
    verdict = "healthy"

    # Error rate comparison
    if stable.error_rate > 0:
        error_ratio = canary.error_rate / stable.error_rate
    elif canary.error_rate > 0.05:  # >5% absolute threshold when stable=0
        error_ratio = error_rate_threshold + 1
    else:
        error_ratio = 1.0

    # P95 latency comparison
    if stable.p95_latency_ms > 0:
        p95_ratio = canary.p95_latency_ms / stable.p95_latency_ms
    elif canary.p95_latency_ms > 1000:  # >1s absolute threshold
        p95_ratio = p95_threshold + 1
    else:
        p95_ratio = 1.0

    # CPU comparison
    if stable.cpu_percent > 0:
        cpu_ratio = canary.cpu_percent / stable.cpu_percent
    else:
        cpu_ratio = 1.0

    # Evaluate thresholds
    if error_ratio >= error_rate_threshold:
        verdict = "degraded"
        reasons.append(
            f"error_rate degraded: canary={canary.error_rate:.3f} "
            f"stable={stable.error_rate:.3f} ratio={error_ratio:.2f}x"
        )

    if p95_ratio >= p95_threshold:
        verdict = "degraded"
        reasons.append(
            f"p95_latency degraded: canary={canary.p95_latency_ms:.0f}ms "
            f"stable={stable.p95_latency_ms:.0f}ms ratio={p95_ratio:.2f}x"
        )

    if canary.cpu_percent > 85.0:
        verdict = "degraded"
        reasons.append(f"cpu_percent critical: canary={canary.cpu_percent:.1f}%")

    return ComparisonResult(
        canary=canary,
        stable=stable,
        error_rate_ratio=error_ratio,
        p95_ratio=p95_ratio,
        cpu_ratio=cpu_ratio,
        verdict=verdict,
        reasons=reasons,
    )


def should_rollback(comparison: ComparisonResult) -> bool:
    """Return True if the canary should be rolled back."""
    return comparison.verdict == "degraded"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(comparison: ComparisonResult) -> Dict[str, Any]:
    """Generate a structured report dict from a ComparisonResult."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": comparison.verdict,
        "should_rollback": should_rollback(comparison),
        "reasons": comparison.reasons,
        "metrics": {
            "stable": {
                "service": comparison.stable.service_name,
                "error_rate": comparison.stable.error_rate,
                "p95_latency_ms": comparison.stable.p95_latency_ms,
                "p50_latency_ms": comparison.stable.p50_latency_ms,
                "cpu_percent": comparison.stable.cpu_percent,
                "memory_mb": comparison.stable.memory_mb,
                "request_count": comparison.stable.request_count,
            },
            "canary": {
                "service": comparison.canary.service_name,
                "error_rate": comparison.canary.error_rate,
                "p95_latency_ms": comparison.canary.p95_latency_ms,
                "p50_latency_ms": comparison.canary.p50_latency_ms,
                "cpu_percent": comparison.canary.cpu_percent,
                "memory_mb": comparison.canary.memory_mb,
                "request_count": comparison.canary.request_count,
            },
        },
        "ratios": {
            "error_rate_ratio": comparison.error_rate_ratio,
            "p95_ratio": comparison.p95_ratio,
            "cpu_ratio": comparison.cpu_ratio,
        },
    }
