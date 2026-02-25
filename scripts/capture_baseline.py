"""Capture P0 baseline metrics for regression tracking.

Produces a structured JSON artifact at docs/baselines/p0_metrics.json
for use as the regression baseline in subsequent phases.
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def measure_import_latency() -> dict:
    """Measure import time for key modules."""
    results = {}
    modules = [
        ("shared.config.settings", "Config"),
        ("shared.schemas", "Schemas"),
        ("core.vqa", "VQA"),
        ("core.memory", "Memory"),
        ("application", "Application"),
    ]
    for module_path, label in modules:
        start = time.monotonic()
        try:
            __import__(module_path)
            elapsed = (time.monotonic() - start) * 1000
            results[label] = {"ms": round(elapsed, 1), "status": "ok"}
        except ImportError as e:
            results[label] = {"ms": 0, "status": f"import_error: {e}"}
    return results


def count_loc() -> dict:
    """Count lines of code per top-level module."""
    results = {}
    for module in ["shared", "core", "application", "infrastructure", "apps"]:
        total = 0
        module_path = Path(module)
        if module_path.exists():
            for py_file in module_path.rglob("*.py"):
                try:
                    total += sum(1 for _ in py_file.open(encoding="utf-8", errors="ignore"))
                except OSError:
                    pass
        results[module] = total
    return results


def count_stubs() -> dict:
    """Count stub/placeholder/TODO markers in source code."""
    patterns = [r"raise NotImplementedError", r"pass\s*#.*stub", r"# TODO", r"# STUB", r"placeholder"]
    results = {}
    for module in ["shared", "core", "application", "infrastructure", "apps"]:
        count = 0
        module_path = Path(module)
        if module_path.exists():
            for py_file in module_path.rglob("*.py"):
                try:
                    content = py_file.read_text(errors="ignore")
                    for pattern in patterns:
                        count += len(re.findall(pattern, content, re.IGNORECASE))
                except OSError:
                    pass
        results[module] = count
    return results


def count_config_vars() -> int:
    """Count os.environ.get calls in settings.py."""
    settings = Path("shared/config/settings.py")
    if settings.exists():
        content = settings.read_text(errors="ignore")
        return len(re.findall(r"os\.environ\.get", content))
    return 0


def count_dependencies() -> dict:
    """Count packages in requirements files."""
    results = {}
    for req_file in ["requirements.txt", "requirements-extras.txt"]:
        path = Path(req_file)
        if path.exists():
            lines = [
                line.strip()
                for line in path.read_text().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            results[req_file] = len(lines)
    return results


def capture_test_stats() -> dict:
    """Run pytest --collect-only to get test counts."""
    python = sys.executable
    try:
        result = subprocess.run(
            [python, "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout
        match = re.search(r"(\d+) tests? collected", output)
        collected = int(match.group(1)) if match else 0
        # Count errors
        error_match = re.search(r"(\d+) errors?", output)
        errors = int(error_match.group(1)) if error_match else 0
        return {"collected": collected, "errors": errors}
    except Exception as e:
        return {"collected": 0, "errors": 0, "error": str(e)}


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def main():
    """Capture all baseline metrics and write to JSON."""
    metrics = {
        "schema_version": "1.0.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "phase": "P0_baseline",
        "git_commit": get_git_commit(),
        "metrics": {
            "import_latency": measure_import_latency(),
            "loc_per_module": count_loc(),
            "stub_inventory": count_stubs(),
            "config_var_count": count_config_vars(),
            "dependency_count": count_dependencies(),
            "test_stats": capture_test_stats(),
        },
        "vram_usage": {
            "note": "Manual measurement required - GPU hardware not available in CI",
            "value_mb": None,
        },
    }

    output_dir = Path("docs/baselines")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "p0_metrics.json"
    output_path.write_text(json.dumps(metrics, indent=2))
    print(f"Baseline metrics written to {output_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
