"""
Dependency vulnerability scanning — runs pip-audit or safety check.

Generates SBOM in CycloneDX JSON format and reports pass/fail
based on severity threshold.

Usage:
    python scripts/run_dep_scan.py [--requirements requirements.txt]
    python scripts/run_dep_scan.py --help
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_REQUIREMENTS = ["requirements.txt", "requirements-extras.txt"]
DEFAULT_SBOM_PATH = "reports/sbom.json"
DEFAULT_REPORT_PATH = "reports/dep_scan.json"

BLOCK_SEVERITIES = frozenset({"CRITICAL", "HIGH"})


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Scan dependencies for known vulnerabilities and generate SBOM.",
    )
    parser.add_argument(
        "--requirements",
        nargs="*",
        default=DEFAULT_REQUIREMENTS,
        help=f"Requirements files to scan (default: {DEFAULT_REQUIREMENTS})",
    )
    parser.add_argument(
        "--sbom-output",
        default=DEFAULT_SBOM_PATH,
        help=f"SBOM output path (default: {DEFAULT_SBOM_PATH})",
    )
    parser.add_argument(
        "--report-output",
        default=DEFAULT_REPORT_PATH,
        help=f"Scan report output path (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--tool",
        choices=["pip-audit", "safety", "auto"],
        default="auto",
        help="Scanning tool to use (default: auto-detect)",
    )
    return parser


def parse_requirements(req_path: str) -> List[Dict[str, str]]:
    """Parse a requirements file into a list of {name, version} dicts."""
    components: List[Dict[str, str]] = []
    path = Path(req_path)
    if not path.exists():
        logger.warning("Requirements file not found: %s", req_path)
        return components

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Handle extras like package[extra]>=1.0
            name = line
            version = ""

            for op in (">=", "==", "<=", "!=", "~=", ">", "<"):
                if op in line:
                    parts = line.split(op, 1)
                    name = parts[0].strip()
                    version = parts[1].strip().rstrip(",")
                    break

            # Strip extras bracket
            if "[" in name:
                name = name.split("[")[0]

            if name:
                components.append({"name": name, "version": version})

    return components


def generate_sbom(req_files: List[str], output_path: str) -> Dict[str, Any]:
    """Generate a CycloneDX SBOM in JSON format."""
    all_components: List[Dict[str, str]] = []
    for req_file in req_files:
        all_components.extend(parse_requirements(req_file))

    # Deduplicate by name
    seen = set()
    unique: List[Dict[str, str]] = []
    for comp in all_components:
        if comp["name"].lower() not in seen:
            seen.add(comp["name"].lower())
            unique.append(comp)

    sbom: Dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "serialNumber": f"urn:uuid:{uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [
                {
                    "vendor": "voice-vision-assistant",
                    "name": "run_dep_scan",
                    "version": "1.0.0",
                }
            ],
            "component": {
                "type": "application",
                "name": "voice-vision-assistant",
                "version": "1.0.0",
            },
        },
        "components": [
            {
                "type": "library",
                "name": comp["name"],
                "version": comp["version"] or "unspecified",
                "purl": f"pkg:pypi/{comp['name'].lower()}@{comp['version'] or 'unspecified'}",
            }
            for comp in unique
        ],
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(sbom, f, indent=2)
    logger.info("SBOM written to %s with %d components", output_path, len(unique))

    return sbom


def run_pip_audit(req_files: List[str]) -> Dict[str, Any]:
    """Run pip-audit against requirements files."""
    all_vulns: List[Dict[str, Any]] = []

    for req_file in req_files:
        if not Path(req_file).exists():
            logger.warning("Skipping missing file: %s", req_file)
            continue

        cmd = ["pip-audit", "-r", req_file, "-f", "json", "--progress-spinner=off"]
        logger.info("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            logger.warning("pip-audit not installed")
            return {"tool": "pip-audit", "available": False, "vulnerabilities": []}
        except subprocess.TimeoutExpired:
            logger.error("pip-audit timed out")
            return {"tool": "pip-audit", "available": True, "vulnerabilities": [], "error": "timeout"}

        stdout = result.stdout.strip()
        if stdout:
            try:
                data = json.loads(stdout)
                if isinstance(data, dict):
                    all_vulns.extend(data.get("dependencies", []))
                elif isinstance(data, list):
                    all_vulns.extend(data)
            except json.JSONDecodeError:
                logger.warning("Could not parse pip-audit output for %s", req_file)

    return {"tool": "pip-audit", "available": True, "vulnerabilities": all_vulns}


def run_safety(req_files: List[str]) -> Dict[str, Any]:
    """Run safety check against requirements files."""
    all_vulns: List[Dict[str, Any]] = []

    for req_file in req_files:
        if not Path(req_file).exists():
            continue

        cmd = ["safety", "check", "-r", req_file, "--json"]
        logger.info("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            logger.warning("safety not installed")
            return {"tool": "safety", "available": False, "vulnerabilities": []}
        except subprocess.TimeoutExpired:
            logger.error("safety timed out")
            return {"tool": "safety", "available": True, "vulnerabilities": [], "error": "timeout"}

        stdout = result.stdout.strip()
        if stdout:
            try:
                data = json.loads(stdout)
                if isinstance(data, list):
                    all_vulns.extend(data)
                elif isinstance(data, dict):
                    all_vulns.extend(data.get("vulnerabilities", []))
            except json.JSONDecodeError:
                logger.warning("Could not parse safety output for %s", req_file)

    return {"tool": "safety", "available": True, "vulnerabilities": all_vulns}


def classify_vulnerabilities(scan_result: Dict[str, Any]) -> Dict[str, int]:
    """Classify vulnerabilities by severity."""
    counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for vuln in scan_result.get("vulnerabilities", []):
        # Different tools use different keys
        severity = (
            vuln.get("severity", "")
            or vuln.get("vulnerability", {}).get("severity", "")
            or "UNKNOWN"
        ).upper()
        if severity in counts:
            counts[severity] += 1
    return counts


def should_block(counts: Dict[str, int]) -> bool:
    """Return True if any blocking-severity vulnerabilities found."""
    for severity in BLOCK_SEVERITIES:
        if counts.get(severity, 0) > 0:
            return True
    return False


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns 0 on pass, 1 on fail."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Generate SBOM
    sbom = generate_sbom(args.requirements, args.sbom_output)
    logger.info("SBOM generated with %d components", len(sbom.get("components", [])))

    # Run vulnerability scan
    scan_result: Dict[str, Any] = {"tool": "none", "available": False, "vulnerabilities": []}

    if args.tool in ("pip-audit", "auto"):
        scan_result = run_pip_audit(args.requirements)

    if not scan_result.get("available") and args.tool in ("safety", "auto"):
        scan_result = run_safety(args.requirements)

    if not scan_result.get("available"):
        logger.warning("No scanning tool available (pip-audit or safety). Install one.")
        logger.info("SBOM was still generated. Scan skipped.")
        # Write empty report
        report = {
            "status": "SKIPPED",
            "tool": "none",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vulnerabilities": [],
            "counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        }
        out = Path(args.report_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return 0

    # Classify and decide
    counts = classify_vulnerabilities(scan_result)
    block = should_block(counts)

    report = {
        "status": "FAIL" if block else "PASS",
        "tool": scan_result.get("tool", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vulnerability_count": len(scan_result.get("vulnerabilities", [])),
        "counts": counts,
        "block": block,
    }

    out = Path(args.report_output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Scan report written to %s", args.report_output)

    if block:
        logger.error("DEP SCAN FAIL: %s", counts)
        return 1

    logger.info("DEP SCAN PASS: %s", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
