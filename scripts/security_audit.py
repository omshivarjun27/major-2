"""
Security hardening audit — automated checks for common security issues.

Checks for plaintext API keys, Docker non-root, PII scrubbing, encryption,
HTTPS enforcement, input validation, rate limiting, and CORS configuration.

Usage:
    python scripts/security_audit.py [--project-root .]
    python scripts/security_audit.py --help
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_ROOT = "."
DEFAULT_REPORT_PATH = "reports/security_audit.json"

# Patterns that indicate hardcoded API keys or secrets
SECRET_PATTERNS = [
    re.compile(r"""(?:API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)\s*=\s*["'][A-Za-z0-9+/=_\-]{8,}["']""", re.IGNORECASE),
    re.compile(r"""(?:api_key|secret|token|password)\s*=\s*["'][A-Za-z0-9+/=_\-]{8,}["']"""),
    re.compile(r"""Bearer\s+[A-Za-z0-9+/=_\-]{20,}"""),
    re.compile(r"""sk-[A-Za-z0-9]{20,}"""),
]

# Files/dirs to skip when scanning for secrets
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".ruff_cache", ".pytest_cache", "data", "models"}
SKIP_FILES = {".env", ".env.example", ".bandit-baseline.json"}

# Allowed extensions for source scanning
SOURCE_EXTENSIONS = {".py", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".json"}


class AuditCheck:
    """Represents a single audit check result."""

    def __init__(self, name: str, description: str, severity: str = "HIGH"):
        self.name = name
        self.description = description
        self.severity = severity
        self.passed: Optional[bool] = None
        self.evidence: List[str] = []

    def pass_check(self, evidence: str = "") -> None:
        """Mark the check as passed."""
        self.passed = True
        if evidence:
            self.evidence.append(evidence)

    def fail_check(self, evidence: str = "") -> None:
        """Mark the check as failed."""
        self.passed = False
        if evidence:
            self.evidence.append(evidence)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "passed": self.passed,
            "evidence": self.evidence,
        }


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run security hardening audit against the project.",
    )
    parser.add_argument(
        "--project-root",
        default=DEFAULT_PROJECT_ROOT,
        help=f"Project root directory (default: {DEFAULT_PROJECT_ROOT})",
    )
    parser.add_argument(
        "--report-output",
        default=DEFAULT_REPORT_PATH,
        help=f"Report output path (default: {DEFAULT_REPORT_PATH})",
    )
    return parser


def _iter_source_files(root: Path) -> List[Path]:
    """Iterate over source files, skipping excluded directories."""
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in SOURCE_EXTENSIONS and fpath.name not in SKIP_FILES:
                files.append(fpath)
    return files


def check_no_plaintext_keys(root: Path) -> AuditCheck:
    """Check 1: No plaintext API keys in source code."""
    check = AuditCheck(
        name="no_plaintext_keys",
        description="No hardcoded API keys, secrets, or tokens in source code",
        severity="CRITICAL",
    )

    violations: List[str] = []
    for fpath in _iter_source_files(root):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        for line_no, line in enumerate(content.splitlines(), 1):
            # Skip comments and test fixtures
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            # Skip lines that are env var lookups
            if "os.environ" in line or "os.getenv" in line or "dotenv" in line:
                continue
            # Skip common test patterns
            if "test" in str(fpath).lower() and ("mock" in line.lower() or "fake" in line.lower()):
                continue

            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    # Check if it's a placeholder value
                    match = pattern.search(line)
                    if match:
                        value = match.group()
                        # Skip obvious placeholders
                        if any(ph in value.lower() for ph in [
                            "your_", "example", "placeholder", "change_me",
                            "xxx", "todo", "replace", "dummy",
                        ]):
                            continue
                        violations.append(f"{fpath}:{line_no}")

    if violations:
        check.fail_check(f"Found {len(violations)} potential hardcoded secrets: {violations[:5]}")
    else:
        check.pass_check("No hardcoded secrets found in source files")

    return check


def check_docker_nonroot(root: Path) -> AuditCheck:
    """Check 2: Docker containers run as non-root."""
    check = AuditCheck(
        name="docker_nonroot",
        description="Docker containers configured to run as non-root user",
        severity="HIGH",
    )

    dockerfiles = list(root.glob("**/Dockerfile")) + list(root.glob("**/Dockerfile.*"))
    if not dockerfiles:
        check.pass_check("No Dockerfiles found — N/A")
        return check

    all_nonroot = True
    for df in dockerfiles:
        try:
            content = df.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        has_user = bool(re.search(r"^\s*USER\s+(?!root)", content, re.MULTILINE))
        if has_user:
            check.evidence.append(f"{df}: USER directive found (non-root)")
        else:
            all_nonroot = False
            check.evidence.append(f"{df}: no non-root USER directive")

    if all_nonroot:
        check.pass_check()
    else:
        check.fail_check()

    return check


def check_pii_scrubbing(root: Path) -> AuditCheck:
    """Check 3: PII scrubbed from logs (PIIScrubFilter usage)."""
    check = AuditCheck(
        name="pii_scrubbing",
        description="PII scrubbing filter is configured in logging pipeline",
        severity="HIGH",
    )

    # Look for PIIScrubFilter usage
    found_definition = False
    found_usage = False

    for fpath in _iter_source_files(root):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        if "class PIIScrubFilter" in content:
            found_definition = True
            check.evidence.append(f"PIIScrubFilter defined in {fpath}")
        if "PIIScrubFilter" in content and ("addFilter" in content or "add_filter" in content):
            found_usage = True
            check.evidence.append(f"PIIScrubFilter used in {fpath}")

    if found_definition and found_usage:
        check.pass_check("PIIScrubFilter is defined and wired into logging")
    elif found_definition:
        check.fail_check("PIIScrubFilter defined but not wired into logging handlers")
    else:
        check.fail_check("PIIScrubFilter not found in codebase")

    return check


def check_encryption_present(root: Path) -> AuditCheck:
    """Check 4: Encryption present for consent/sensitive data."""
    check = AuditCheck(
        name="encryption_present",
        description="Encryption utilities present for sensitive data handling",
        severity="HIGH",
    )

    found_crypto = False
    for fpath in _iter_source_files(root):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        if any(term in content for term in ["cryptography", "Fernet", "encrypt", "AES", "cipher"]):
            if "encryption" in str(fpath).lower() or "utils" in str(fpath).lower():
                found_crypto = True
                check.evidence.append(f"Encryption utilities found in {fpath}")

    if found_crypto:
        check.pass_check("Encryption module found in shared utilities")
    else:
        check.fail_check("No encryption utilities found for sensitive data")

    return check


def check_https_enforced(root: Path) -> AuditCheck:
    """Check 5: HTTPS enforced for external calls."""
    check = AuditCheck(
        name="https_enforced",
        description="External HTTP calls use HTTPS",
        severity="MEDIUM",
    )

    http_violations: List[str] = []
    http_pattern = re.compile(r"""(?:httpx|requests|urllib).*["']http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)""")

    for fpath in _iter_source_files(root):
        if fpath.suffix != ".py":
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        for line_no, line in enumerate(content.splitlines(), 1):
            if http_pattern.search(line):
                http_violations.append(f"{fpath}:{line_no}")

    if http_violations:
        check.fail_check(f"Found {len(http_violations)} non-HTTPS external calls: {http_violations[:5]}")
    else:
        check.pass_check("No plaintext HTTP calls to external hosts found")

    return check


def check_input_validation(root: Path) -> AuditCheck:
    """Check 6: Input validation on API endpoints."""
    check = AuditCheck(
        name="input_validation",
        description="API endpoints use input validation (Pydantic/Query/Body)",
        severity="MEDIUM",
    )

    # Check for Pydantic models or FastAPI validation
    found_validation = False
    for fpath in _iter_source_files(root):
        if fpath.suffix != ".py":
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        if "server" in fpath.name.lower() or "api" in str(fpath).lower():
            if any(v in content for v in ["BaseModel", "Query(", "Body(", "Depends(", "HTTPException"]):
                found_validation = True
                check.evidence.append(f"Input validation found in {fpath}")

    if found_validation:
        check.pass_check("FastAPI validation decorators found in API layer")
    else:
        check.fail_check("No input validation patterns found in API endpoints")

    return check


def check_rate_limiting(root: Path) -> AuditCheck:
    """Check 7: Rate limiting configured."""
    check = AuditCheck(
        name="rate_limiting",
        description="Rate limiting is configured for API endpoints",
        severity="MEDIUM",
    )

    found_rate_limit = False
    for fpath in _iter_source_files(root):
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        if any(term in content for term in [
            "RateLimiter", "rate_limit", "slowapi", "throttle",
            "RateLimit", "limiter", "Limiter",
        ]):
            found_rate_limit = True
            check.evidence.append(f"Rate limiting reference in {fpath}")

    if found_rate_limit:
        check.pass_check("Rate limiting configuration found")
    else:
        check.fail_check("No rate limiting configuration found")

    return check


def check_cors_configured(root: Path) -> AuditCheck:
    """Check 8: CORS properly configured."""
    check = AuditCheck(
        name="cors_configured",
        description="CORS middleware is configured (not wildcard in production)",
        severity="MEDIUM",
    )

    found_cors = False
    wildcard_cors = False

    for fpath in _iter_source_files(root):
        if fpath.suffix != ".py":
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue

        if "CORSMiddleware" in content or "cors" in content.lower():
            found_cors = True
            check.evidence.append(f"CORS configuration in {fpath}")
            if 'allow_origins=["*"]' in content or "allow_origins=['*']" in content:
                wildcard_cors = True
                check.evidence.append(f"WARNING: Wildcard CORS in {fpath}")

    if found_cors and not wildcard_cors:
        check.pass_check("CORS configured without wildcard")
    elif found_cors and wildcard_cors:
        check.fail_check("CORS uses wildcard allow_origins — restrict in production")
    else:
        # No CORS means API doesn't serve browsers — acceptable
        check.pass_check("No CORS middleware found (API-only — acceptable)")

    return check


def run_all_checks(root: Path) -> List[AuditCheck]:
    """Run all security audit checks."""
    checks = [
        check_no_plaintext_keys(root),
        check_docker_nonroot(root),
        check_pii_scrubbing(root),
        check_encryption_present(root),
        check_https_enforced(root),
        check_input_validation(root),
        check_rate_limiting(root),
        check_cors_configured(root),
    ]
    return checks


def generate_report(checks: List[AuditCheck]) -> Dict[str, Any]:
    """Generate audit report from check results."""
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    failed = sum(1 for c in checks if c.passed is False)
    critical_fails = sum(1 for c in checks if c.passed is False and c.severity == "CRITICAL")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "critical_failures": critical_fails,
        },
        "status": "FAIL" if critical_fails > 0 else "PASS",
        "checks": [c.to_dict() for c in checks],
    }


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns 0 if all pass, 1 if any CRITICAL fails."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    logger.info("Running security audit on %s", root)

    checks = run_all_checks(root)
    report = generate_report(checks)

    # Write report
    out = Path(args.report_output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Audit report written to %s", args.report_output)

    # Log summary
    summary = report["summary"]
    logger.info(
        "Audit complete: %d/%d passed, %d failed (%d critical)",
        summary["passed"],
        summary["total_checks"],
        summary["failed"],
        summary["critical_failures"],
    )

    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        logger.info("  [%s] %s: %s", status, check.name, check.description)

    if report["status"] == "FAIL":
        logger.error("AUDIT FAIL: %d critical failures", summary["critical_failures"])
        return 1

    logger.info("AUDIT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
