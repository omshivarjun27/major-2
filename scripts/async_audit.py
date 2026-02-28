#!/usr/bin/env python3
"""Async audit sweep — scans core/ and application/ for blocking patterns.

This script is the deliverable for T-046. It searches for synchronous
blocking calls that could stall the event loop:
  - requests.get/post/put/delete/patch/head
  - urllib.request.urlopen
  - subprocess.run/call/check_output/check_call/Popen
  - time.sleep
  - import requests (library-level)

Run as:  python -m scripts.async_audit
Or:      python scripts/async_audit.py

Exit code 0 if zero hot-path violations; 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# ── Patterns to detect ──────────────────────────────────────────────────

PATTERNS = [
    ("requests_call", re.compile(r"requests\.(get|post|put|delete|patch|head)\(")),
    ("urllib_urlopen", re.compile(r"urllib\.request\.urlopen\(")),
    ("subprocess_sync", re.compile(r"subprocess\.(run|call|check_output|check_call|Popen)\(")),
    ("time_sleep", re.compile(r"time\.sleep\(")),
    ("import_requests", re.compile(r"^import requests\s*$|^from requests ")),
]

# Directories in the hot path (violations here are fatal)
HOT_PATH_DIRS = {"core/vqa", "core/vision", "core/memory", "application/frame_processing", "application/pipelines"}

# Directories to scan (non-hot-path findings are warnings)
SCAN_DIRS = ["core", "application", "infrastructure"]

# Files to skip (test harnesses, stubs)
SKIP_PATTERNS = {"__pycache__", ".pyc", "test_", "conftest"}

# Files that are startup-only (model downloads, config loading) — NOT hot path
STARTUP_ONLY_FILES = {"model_download.py", "__init__.py"}


@dataclass
class Finding:
    """One blocking-call finding."""

    file: str
    line_no: int
    pattern_name: str
    line_text: str
    hot_path: bool
    severity: str = ""

    def __post_init__(self):
        self.severity = "ERROR" if self.hot_path else "WARNING"


@dataclass
class AuditReport:
    """Summary of the async audit sweep."""

    findings: List[Finding] = field(default_factory=list)
    files_scanned: int = 0
    hot_path_violations: int = 0
    warnings: int = 0

    @property
    def clean(self) -> bool:
        return self.hot_path_violations == 0

    def summary(self) -> str:
        lines = [
            "=" * 72,
            "ASYNC AUDIT SWEEP REPORT",
            "=" * 72,
            f"Files scanned:        {self.files_scanned}",
            f"Hot-path violations:  {self.hot_path_violations}",
            f"Non-hot-path warns:   {self.warnings}",
            f"Total findings:       {len(self.findings)}",
            f"Status:               {'PASS' if self.clean else 'FAIL'}",
            "-" * 72,
        ]
        if self.findings:
            lines.append("")
            for f in self.findings:
                lines.append(f"  [{f.severity}] {f.file}:{f.line_no}  ({f.pattern_name})")
                lines.append(f"    > {f.line_text.strip()}")
            lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)


def _is_hot_path(filepath: str) -> bool:
    """Return True if the file is inside a hot-path directory and not startup-only."""
    normalized = filepath.replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]
    if basename in STARTUP_ONLY_FILES:
        return False
    return any(normalized.startswith(hp) or f"/{hp}" in normalized for hp in HOT_PATH_DIRS)


def _should_skip(filepath: str) -> bool:
    """Return True if file should be skipped."""
    return any(skip in filepath for skip in SKIP_PATTERNS)


def scan_file(filepath: Path, root: Path) -> List[Finding]:
    """Scan a single Python file for blocking patterns."""
    findings: List[Finding] = []
    rel = str(filepath.relative_to(root))

    if _should_skip(rel):
        return findings

    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    hot = _is_hot_path(rel)
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern_name, regex in PATTERNS:
            if regex.search(stripped):
                findings.append(Finding(
                    file=rel,
                    line_no=line_no,
                    pattern_name=pattern_name,
                    line_text=line,
                    hot_path=hot,
                ))
    return findings


def run_audit(project_root: Path | None = None) -> AuditReport:
    """Execute the full async audit sweep and return a report."""
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    report = AuditReport()

    for scan_dir in SCAN_DIRS:
        target = project_root / scan_dir
        if not target.is_dir():
            continue
        for py_file in sorted(target.rglob("*.py")):
            report.files_scanned += 1
            for finding in scan_file(py_file, project_root):
                report.findings.append(finding)
                if finding.hot_path:
                    report.hot_path_violations += 1
                else:
                    report.warnings += 1

    return report


def main() -> int:
    """CLI entry point."""
    report = run_audit()
    print(report.summary())
    return 0 if report.clean else 1


if __name__ == "__main__":
    sys.exit(main())
