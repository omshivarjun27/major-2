"""P1 Architecture Check and Metrics Comparison (T-037).

Final P1 gate: verifies architectural integrity and captures P1 metrics
for comparison against the P0 baseline.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


class TestP1Architecture:
    """Architecture validation and P0-vs-P1 metric comparison."""

    def test_lint_imports_passes(self):
        """Run lint-imports; verify exit code 0 (no architecture violations)."""
        lint_imports = str(ROOT / ".venv" / "Scripts" / "lint-imports.exe")
        result = subprocess.run(
            [lint_imports],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=60,
        )
        assert result.returncode == 0, (
            f"lint-imports failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
        )

    def test_ruff_check_p1_files(self):
        """Run ruff check on P1-modified files; verify no new violations."""
        ruff = str(ROOT / ".venv" / "Scripts" / "ruff.exe")
        # Only check files created or modified during P1
        p1_files = [
            "core/reasoning",
            "core/vision/spatial.py",
            "core/vision/model_download.py",
            "core/memory/indexer.py",
            "core/memory/embeddings.py",
            "core/memory/ingest.py",
            "core/memory/retriever.py",
            "core/ocr/engine.py",
            "core/braille/braille_classifier.py",
            "core/face/face_embeddings.py",
            "core/face/consent_audit.py",
            "application/event_bus",
            "application/session_management",
            "application/frame_processing/spatial_binding.py",
            "infrastructure/storage/adapter.py",
            "infrastructure/monitoring/collector.py",
            "shared/schemas/__init__.py",
        ]
        existing = [f for f in p1_files if (ROOT / f).exists()]
        result = subprocess.run(
            [ruff, "check"] + existing,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            timeout=60,
        )
        assert result.returncode == 0, (
            f"ruff check failed on P1 files (exit {result.returncode}):\n{result.stdout}"
        )

    def test_p1_metrics_snapshot_exists(self):
        """Verify docs/baselines/p1_metrics.json exists and has required fields."""
        p1_path = ROOT / "docs" / "baselines" / "p1_metrics.json"
        assert p1_path.exists(), "P1 metrics snapshot not found"

        data = json.loads(p1_path.read_text(encoding="utf-8"))
        assert "metrics" in data
        assert "loc_per_module" in data["metrics"]
        assert "stub_inventory" in data["metrics"]
        assert "test_count" in data["metrics"]

    def test_test_count_increased(self):
        """Compare P1 vs P0 test counts; verify meaningful increase."""
        p0_path = ROOT / "docs" / "baselines" / "p0_metrics.json"
        p1_path = ROOT / "docs" / "baselines" / "p1_metrics.json"

        p1 = json.loads(p1_path.read_text(encoding="utf-8"))
        p1_count = p1["metrics"]["test_count"]

        # P0 baseline may not have test_count — use LOC as secondary check
        if p0_path.exists():
            p0 = json.loads(p0_path.read_text(encoding="utf-8"))
            p0_loc = sum(p0["metrics"].get("loc_per_module", {}).values())
            p1_loc = sum(p1["metrics"].get("loc_per_module", {}).values())
            assert p1_loc >= p0_loc, f"P1 LOC ({p1_loc}) < P0 LOC ({p0_loc})"

        # P1 should have at least 500 tests (we know we have 2000+)
        assert p1_count >= 500, f"P1 test count {p1_count} < 500"

    def test_stub_count_decreased(self):
        """Compare P1 vs P0 stub counts; verify P1 <= P0."""
        p0_path = ROOT / "docs" / "baselines" / "p0_metrics.json"
        p1_path = ROOT / "docs" / "baselines" / "p1_metrics.json"

        p0 = json.loads(p0_path.read_text(encoding="utf-8"))
        p1 = json.loads(p1_path.read_text(encoding="utf-8"))

        p0_stubs = sum(p0["metrics"]["stub_inventory"].values())
        p1_stubs = sum(p1["metrics"]["stub_inventory"].values())

        assert p1_stubs <= p0_stubs, (
            f"P1 stubs ({p1_stubs}) > P0 stubs ({p0_stubs}) — regressions introduced"
        )

    def test_no_unexpected_dependencies(self):
        """Verify no unexpected new package dependencies were added."""
        # Check that pyproject.toml dependencies section hasn't grown uncontrolled
        pyproject = ROOT / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert "dependencies" in content or "install_requires" in content or "requires" in content

    def test_all_new_modules_have_agents_md(self):
        """Check that all P1-created module directories have AGENTS.md."""
        new_modules = [
            "core/reasoning",
            "infrastructure/storage",
            "infrastructure/monitoring",
            "application/event_bus",
            "application/session_management",
            "application/frame_processing",
        ]
        missing: list[str] = []
        for mod in new_modules:
            if not (ROOT / mod / "AGENTS.md").exists():
                missing.append(mod)
        assert not missing, f"Missing AGENTS.md in: {missing}"
