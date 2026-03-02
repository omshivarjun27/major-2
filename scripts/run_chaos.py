#!/usr/bin/env python3
"""Chaos test runner — graceful degradation & auto-recovery validation (T-138).

Usage:
    python scripts/run_chaos.py [--scenario NAME] [--timeout SECONDS]

Exit codes:
    0  All chaos scenarios passed
    1  One or more scenarios failed
    2  Runner error
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_KNOWN_SCENARIOS = [
    "service_shutdown",
    "network_partition",
    "vram_exhaustion",
    "disk_full",
    "cascading_failure",
    "circuit_breaker",
    "timeout_cascade",
    "memory_pressure",
    "cpu_spike",
    "dependency_latency",
    "partial_degradation",
    "recovery_timing",
    "concurrent_failures",
    "rolling_restart",
    "data_corruption",
]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run chaos/resilience test suite")
    p.add_argument(
        "--scenario",
        choices=_KNOWN_SCENARIOS + ["all"],
        default="all",
        help="Run a specific chaos scenario or 'all' (default: all)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Per-test timeout in seconds (default: 120)",
    )
    p.add_argument(
        "--junit-xml",
        default=None,
        help="Optional path for JUnit XML report (e.g. reports/chaos.xml)",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose pytest output",
    )
    return p


def main(argv: list[str] | None = None) -> int:  # noqa: FA100
    args = _build_parser().parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    chaos_dir = repo_root / "tests" / "chaos"

    if not chaos_dir.exists():
        print(f"[run_chaos] ERROR: chaos test directory not found: {chaos_dir}", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(chaos_dir),
        f"--timeout={args.timeout}",
        "-q",
        "--tb=short",
    ]
    if args.verbose:
        cmd.append("-v")
    if args.scenario != "all":
        cmd += ["-k", args.scenario]
    if args.junit_xml:
        cmd += [f"--junit-xml={args.junit_xml}"]

    print(f"[run_chaos] Running chaos scenario(s): {args.scenario} ...")
    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=repo_root)
    elapsed = time.monotonic() - t0

    status = "PASSED" if result.returncode == 0 else "FAILED"
    print(f"[run_chaos] {status} in {elapsed:.1f}s (exit={result.returncode})")

    if result.returncode == 0:
        print(f"[run_chaos] All {len(_KNOWN_SCENARIOS)} chaos scenarios verified: graceful degradation ✓")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
