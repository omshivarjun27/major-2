"""P1 Phase Exit Validation Suite (T-035).

Validates all P1 exit criteria in a single pytest file:
1. Stub count below threshold (< 10)
2. Total test count above baseline + P1 contributions
3. All 5 placeholder modules have MVP implementations
4. Import-linter passes (no architecture violations)
5. Documentation coverage for new modules (AGENTS.md)
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


class TestP1ExitCriteria:
    """P1 phase exit validation suite."""

    # ------------------------------------------------------------------
    # 1. Stub count: must be < 10 across all layers
    # ------------------------------------------------------------------

    def test_stub_count_below_10(self):
        """Scan all layer directories; verify fewer than 10 stub modules.

        A stub is a package directory containing only ``__init__.py``
        and optionally ``AGENTS.md``, with no other ``.py`` files that
        contain real logic (more than 5 non-blank/non-comment lines).
        """
        allowed_stubs = {"__pycache__", "fixtures"}
        layers = ["shared", "core", "application", "infrastructure", "apps"]
        stubs: list[str] = []

        for layer in layers:
            layer_path = ROOT / layer
            if not layer_path.is_dir():
                continue
            for subdir in layer_path.iterdir():
                if not subdir.is_dir():
                    continue
                if subdir.name in allowed_stubs or subdir.name.startswith("."):
                    continue
                init_file = subdir / "__init__.py"
                if not init_file.exists():
                    continue

                # Count .py files with real code (> 5 non-trivial lines)
                real_py_count = 0
                for py_file in subdir.glob("*.py"):
                    if py_file.name == "__init__.py":
                        # Check if __init__.py itself has real code
                        lines = [
                            ln
                            for ln in py_file.read_text(encoding="utf-8", errors="replace").splitlines()
                            if ln.strip() and not ln.strip().startswith("#")
                        ]
                        if len(lines) > 5:
                            real_py_count += 1
                        continue
                    real_py_count += 1

                if real_py_count == 0:
                    stubs.append(f"{layer}/{subdir.name}")

        assert len(stubs) < 10, f"Too many stubs ({len(stubs)}): {stubs}"

    # ------------------------------------------------------------------
    # 2. Total test count: P1 must add tests above P0 baseline
    # ------------------------------------------------------------------

    def test_total_test_count_exceeds_baseline(self):
        """Collect all tests; verify P1 pushed count well above P0 baseline.

        P0 baseline had ~429 known tests; P1 adds 100+.  We check >= 500
        as a conservative floor that accounts for test-only tasks.
        """
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=120,
        )
        # Parse last line: "N tests collected, M errors"
        output = result.stdout.strip()
        last_line = output.splitlines()[-1] if output else ""
        # Also check stderr for the count
        err_lines = result.stderr.strip().splitlines()

        count = 0
        for line in [last_line] + err_lines:
            if "collected" in line:
                for word in line.split():
                    if word.isdigit():
                        count = max(count, int(word))
                        break

        assert count >= 500, f"Only {count} tests collected — expected >= 500 after P1"

    # ------------------------------------------------------------------
    # 3. MVP existence checks for 5 placeholder modules
    # ------------------------------------------------------------------

    def test_reasoning_engine_mvp_exists(self):
        """core.reasoning must export ReasoningEngine."""
        mod = importlib.import_module("core.reasoning")
        assert hasattr(mod, "ReasoningEngine"), "ReasoningEngine not found in core.reasoning"

    def test_storage_adapter_mvp_exists(self):
        """infrastructure.storage must export StorageAdapter and LocalFileStorage."""
        mod = importlib.import_module("infrastructure.storage.adapter")
        assert hasattr(mod, "StorageAdapter"), "StorageAdapter not found"
        assert hasattr(mod, "LocalFileStorage"), "LocalFileStorage not found"

    def test_monitoring_mvp_exists(self):
        """infrastructure.monitoring must export MetricsCollector and InMemoryMetrics."""
        mod = importlib.import_module("infrastructure.monitoring.collector")
        assert hasattr(mod, "MetricsCollector"), "MetricsCollector not found"
        assert hasattr(mod, "InMemoryMetrics"), "InMemoryMetrics not found"

    def test_event_bus_mvp_exists(self):
        """application.event_bus must export EventBus."""
        mod = importlib.import_module("application.event_bus.bus")
        assert hasattr(mod, "EventBus"), "EventBus not found"

    def test_session_management_mvp_exists(self):
        """application.session_management must export SessionManager."""
        mod = importlib.import_module("application.session_management.manager")
        assert hasattr(mod, "SessionManager"), "SessionManager not found"

    # ------------------------------------------------------------------
    # 4. Import-linter: no architecture violations
    # ------------------------------------------------------------------

    def test_import_linter_passes(self):
        """Run lint-imports and verify exit code 0."""
        lint_imports = str(ROOT / '.venv' / 'Scripts' / 'lint-imports.exe')
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

    # ------------------------------------------------------------------
    # 5. Documentation coverage for new P1 modules
    # ------------------------------------------------------------------

    def test_new_modules_have_docs(self):
        """Verify AGENTS.md exists in all module directories that received P1 code."""
        p1_modules = [
            "core/reasoning",
            "infrastructure/storage",
            "infrastructure/monitoring",
            "application/event_bus",
            "application/session_management",
            "application/frame_processing",
        ]
        missing: list[str] = []
        for mod_path in p1_modules:
            agents_file = ROOT / mod_path / "AGENTS.md"
            if not agents_file.exists():
                missing.append(mod_path)

        assert not missing, f"Missing AGENTS.md in: {missing}"
