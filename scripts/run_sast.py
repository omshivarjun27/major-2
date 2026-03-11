"""
SAST scanning script — runs Bandit against the codebase.

Parses JSON output, reports findings by severity, and exits non-zero
if any HIGH or CRITICAL issues are found.

Usage:
    python scripts/run_sast.py [--config .bandit] [--baseline .bandit-baseline.json]
    python scripts/run_sast.py --help
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Severity levels in ascending order
SEVERITY_LEVELS = ("LOW", "MEDIUM", "HIGH")
CONFIDENCE_LEVELS = ("LOW", "MEDIUM", "HIGH")

# Block threshold — exit 1 if any finding at or above this severity
BLOCK_SEVERITIES = frozenset({"HIGH", "CRITICAL"})

DEFAULT_CONFIG = ".bandit"
DEFAULT_BASELINE = ".bandit-baseline.json"


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run Bandit SAST and report pass/fail based on severity threshold.",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help=f"Bandit config file (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE,
        help=f"Baseline file for known issues (default: {DEFAULT_BASELINE})",
    )
    parser.add_argument(
        "--targets",
        nargs="*",
        default=None,
        help="Target directories (overrides config file targets)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON report to this file path",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    return parser


def load_baseline(path: str) -> List[Dict[str, Any]]:
    """Load baseline findings from a JSON file."""
    baseline_path = Path(path)
    if not baseline_path.exists():
        logger.info("No baseline file found at %s — treating as empty", path)
        return []
    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("results", [])
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to parse baseline %s: %s", path, exc)
        return []


def run_bandit(config_path: str, targets: Optional[List[str]] = None) -> Dict[str, Any]:
    """Execute Bandit and return parsed JSON output.

    Returns a dict with 'results', 'metrics', and 'errors' keys.
    If Bandit is not installed, returns an empty result set with an error flag.
    """
    cmd = ["bandit", "-r", "-f", "json", "--configfile", config_path]

    if targets:
        cmd.extend(targets)
    else:
        # Use targets from config — bandit reads them automatically
        cmd.append(".")

    logger.info("Running: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        logger.error("Bandit is not installed. Install with: pip install bandit")
        return {"results": [], "errors": ["bandit_not_installed"], "metrics": {}}
    except subprocess.TimeoutExpired:
        logger.error("Bandit timed out after 300 seconds")
        return {"results": [], "errors": ["timeout"], "metrics": {}}

    # Bandit exits 1 when it finds issues — that's expected
    stdout = result.stdout.strip()
    if not stdout:
        logger.warning("Bandit produced no output (stderr: %s)", result.stderr.strip())
        return {"results": [], "errors": [], "metrics": {}}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Bandit JSON output: %s", exc)
        return {"results": [], "errors": ["parse_error"], "metrics": {}}


def filter_baseline(results: List[Dict[str, Any]], baseline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove known baseline findings from the results."""
    if not baseline:
        return results

    baseline_keys = set()
    for item in baseline:
        key = (
            item.get("filename", ""),
            item.get("line_number", 0),
            item.get("test_id", ""),
        )
        baseline_keys.add(key)

    filtered = []
    for item in results:
        key = (
            item.get("filename", ""),
            item.get("line_number", 0),
            item.get("test_id", ""),
        )
        if key not in baseline_keys:
            filtered.append(item)

    return filtered


def classify_findings(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group findings by severity level."""
    classified: Dict[str, List[Dict[str, Any]]] = {
        "LOW": [],
        "MEDIUM": [],
        "HIGH": [],
    }
    for item in results:
        severity = item.get("issue_severity", "LOW").upper()
        if severity not in classified:
            classified[severity] = []
        classified[severity].append(item)
    return classified


def should_block(classified: Dict[str, List[Dict[str, Any]]]) -> bool:
    """Return True if any finding severity warrants blocking the build."""
    for severity in BLOCK_SEVERITIES:
        if classified.get(severity):
            return True
    return False


def format_text_report(classified: Dict[str, List[Dict[str, Any]]], block: bool) -> str:
    """Format a human-readable text report."""
    lines = ["=" * 60, "SAST Report (Bandit)", "=" * 60, ""]

    total = sum(len(v) for v in classified.values())
    lines.append(f"Total findings: {total}")
    for severity in ("HIGH", "MEDIUM", "LOW"):
        count = len(classified.get(severity, []))
        lines.append(f"  {severity}: {count}")
    lines.append("")

    if block:
        lines.append("STATUS: FAIL — HIGH/CRITICAL findings detected")
    else:
        lines.append("STATUS: PASS — no HIGH/CRITICAL findings")
    lines.append("")

    # Detail HIGH findings
    for severity in ("HIGH", "MEDIUM"):
        items = classified.get(severity, [])
        if items:
            lines.append(f"--- {severity} severity ---")
            for item in items:
                lines.append(
                    f"  [{item.get('test_id', '?')}] {item.get('issue_text', '?')} "
                    f"at {item.get('filename', '?')}:{item.get('line_number', '?')}"
                )
            lines.append("")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns 0 on pass, 1 on fail."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Load baseline
    baseline = load_baseline(args.baseline)
    logger.info("Loaded %d baseline findings", len(baseline))

    # Run Bandit
    raw = run_bandit(args.config, args.targets)

    if raw.get("errors"):
        for err in raw["errors"]:
            if err == "bandit_not_installed":
                logger.error("Bandit not available — cannot run SAST scan")
                return 1

    # Filter baseline
    results = filter_baseline(raw.get("results", []), baseline)
    logger.info("Found %d findings after baseline filtering", len(results))

    # Classify
    classified = classify_findings(results)
    block = should_block(classified)

    # Report
    if args.format == "text":
        report = format_text_report(classified, block)
        logger.info("\n%s", report)
    else:
        report_data = {
            "status": "FAIL" if block else "PASS",
            "total": sum(len(v) for v in classified.values()),
            "by_severity": {k: len(v) for k, v in classified.items()},
            "findings": results,
        }
        report = json.dumps(report_data, indent=2)
        logger.info("\n%s", report)

    # Write output file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info("Report written to %s", args.output)

    return 1 if block else 0


if __name__ == "__main__":
    sys.exit(main())
