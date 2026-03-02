#!/usr/bin/env python3
"""Smoke test runner — post-deployment validation (T-147).

Usage:
    python scripts/run_smoke.py [--base-url URL] [--timeout SECONDS]

Exit codes:
    0  All smoke tests passed
    1  One or more tests failed
    2  Runner error (bad arguments, import failure)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run post-deployment smoke tests")
    p.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the deployed service (default: http://localhost:8000)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-test timeout in seconds (default: 30)",
    )
    p.add_argument(
        "--junit-xml",
        default=None,
        help="Optional path for JUnit XML report (e.g. reports/smoke.xml)",
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
    smoke_dir = repo_root / "tests" / "smoke"

    if not smoke_dir.exists():
        print(f"[run_smoke] ERROR: smoke test directory not found: {smoke_dir}", file=sys.stderr)
        return 2

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(smoke_dir),
        f"--timeout={args.timeout}",
        "-q",
        "--tb=short",
    ]
    if args.verbose:
        cmd.append("-v")
    if args.junit_xml:
        cmd += [f"--junit-xml={args.junit_xml}"]

    # Pass base URL to tests via env var
    import os

    env = os.environ.copy()
    env["SMOKE_BASE_URL"] = args.base_url

    print(f"[run_smoke] Running smoke tests against {args.base_url} ...")
    t0 = time.monotonic()
    result = subprocess.run(cmd, env=env, cwd=repo_root)
    elapsed = time.monotonic() - t0

    status = "PASSED" if result.returncode == 0 else "FAILED"
    print(f"[run_smoke] {status} in {elapsed:.1f}s (exit={result.returncode})")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
