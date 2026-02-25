# T-012: p0-baseline-metrics-capture

> Phase: P0 | Cluster: CL-OPS | Risk: Critical | State: not_started

## Objective

Record measurable baseline metrics before Phase 1 begins. Produce a structured JSON
artifact for regression tracking in subsequent phases.

## Current State (Codebase Audit 2026-02-25)

### Existing Benchmark Infrastructure
- `tests/performance/test_benchmark_report.py` (103 LOC) — generates JSON with p50/p95/p99 latencies
- `tests/performance/test_latency_sla.py` (54 LOC) — config validation + import timing
- `tests/performance/test_sustained_fps.py` (76 LOC) — FPS and frame drop ratio
- `tests/performance/conftest.py` — `project_root()` and `env_overrides()` fixtures

### What We Can Measure (No GPU Required)
1. **Import latency**: Time to import key modules (shared.config, core.vqa, application)
2. **Test pass rate**: Run pytest --collect-only, count total/pass/fail/skip
3. **LOC per module**: Count lines in shared/, core/, application/, infrastructure/, apps/
4. **Stub inventory**: Count functions/classes with stub/placeholder/TODO markers
5. **Config variable count**: Count os.environ.get calls in settings.py
6. **Dependency count**: Count packages in requirements.txt

### What We Cannot Measure (Requires GPU)
- VRAM usage (needs nvidia-smi or torch.cuda)
- GPU inference latency
- Model load time with GPU acceleration

## Implementation Plan

### Step 1: Create baseline metrics script

Create `scripts/capture_baseline.py`:

```python
"""Capture P0 baseline metrics for regression tracking."""
import json
import os
import re
import subprocess
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
                total += sum(1 for _ in py_file.open())
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
                content = py_file.read_text(errors="ignore")
                for pattern in patterns:
                    count += len(re.findall(pattern, content, re.IGNORECASE))
        results[module] = count
    return results


def count_config_vars() -> int:
    """Count os.environ.get calls in settings.py."""
    settings = Path("shared/config/settings.py")
    if settings.exists():
        content = settings.read_text()
        return len(re.findall(r"os\.environ\.get", content))
    return 0


def count_dependencies() -> dict:
    """Count packages in requirements files."""
    results = {}
    for req_file in ["requirements.txt", "requirements-extras.txt"]:
        path = Path(req_file)
        if path.exists():
            lines = [l.strip() for l in path.read_text().splitlines()
                     if l.strip() and not l.strip().startswith("#")]
            results[req_file] = len(lines)
    return results


def capture_test_stats() -> dict:
    """Run pytest --collect-only to get test counts."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "--collect-only", "-q", "--timeout=30"],
            capture_output=True, text=True, timeout=60,
        )
        # Parse output: "X tests collected"
        output = result.stdout
        match = re.search(r"(\d+) tests? collected", output)
        collected = int(match.group(1)) if match else 0
        return {"collected": collected, "output": output[:500]}
    except Exception as e:
        return {"collected": 0, "error": str(e)}


def main():
    metrics = {
        "schema_version": "1.0.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "phase": "P0_baseline",
        "git_commit": subprocess.getoutput("git rev-parse --short HEAD").strip(),
        "metrics": {
            "import_latency": measure_import_latency(),
            "loc_per_module": count_loc(),
            "stub_inventory": count_stubs(),
            "config_var_count": count_config_vars(),
            "dependency_count": count_dependencies(),
            "test_stats": capture_test_stats(),
        },
        "vram_usage": {
            "note": "Manual measurement required — GPU hardware not available in CI",
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
```

### Step 2: Create pytest wrapper

Create `tests/performance/test_p0_baseline.py`:

```python
"""Verify P0 baseline metrics are capturable and within expected ranges."""

class TestP0BaselineMetrics:
    def test_import_latency_under_limits(self):
        """Key module imports complete within acceptable time."""
        # Config should import in < 500ms
        # Core modules in < 2000ms
        ...

    def test_loc_counts_nonzero(self):
        """All source modules have nonzero LOC."""
        ...

    def test_config_var_count_matches_expected(self):
        """settings.py has approximately 82 env var lookups."""
        ...

    def test_baseline_json_schema(self):
        """Generated baseline JSON matches expected schema."""
        ...
```

### Step 3: Run and commit baseline

```bash
python scripts/capture_baseline.py
# Review docs/baselines/p0_metrics.json
git add docs/baselines/p0_metrics.json
git commit -m "docs: capture P0 baseline metrics for regression tracking"
```

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/capture_baseline.py` | Baseline metrics capture script |
| `docs/baselines/p0_metrics.json` | Generated baseline artifact |
| `tests/performance/test_p0_baseline.py` | Validation tests for metrics |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/performance/test_p0_baseline.py` | |
| | Import latency under limits (config < 500ms, core < 2s) |
| | All modules have nonzero LOC |
| | Config var count approximately 82 |
| | Test count >= 840 |
| | Baseline JSON has required schema fields |

## Acceptance Criteria

- [ ] capture_baseline.py runs successfully and produces JSON
- [ ] docs/baselines/p0_metrics.json committed with all metrics
- [ ] Metrics include: import_latency, loc_per_module, stub_inventory, config_var_count, dependency_count, test_stats
- [ ] VRAM field present as null with explanatory note
- [ ] Validation tests pass
- [ ] All existing tests pass
- [ ] ruff check clean

## Upstream Dependencies

T-011 (all P0 tasks complete — this is the final checkpoint)

## Downstream Unblocks

None (terminal task in P0). Phase 1 uses this baseline for regression comparison.

## Estimated Scope

- scripts/capture_baseline.py: ~120 LOC
- tests/performance/test_p0_baseline.py: ~60 LOC
- Risk: Low (measurement only, no production code changes)
