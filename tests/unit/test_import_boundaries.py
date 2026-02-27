"""Import boundary regression tests (T-048).

Validates the 5-layer architecture is respected via both AST-level
import scanning and programmatic lint-imports invocation.  These tests
run entirely offline — no external services or heavy dependencies.
"""

import ast
import subprocess
import sys
from pathlib import Path

# ── Helpers ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[2]  # repo root

PROJECT_PACKAGES = {"core", "application", "infrastructure", "shared", "apps"}

# Allowed imports per layer (layer -> set of allowed project-package imports)
LAYER_RULES = {
    "shared": set(),  # stdlib only
    "core": {"shared"},
    "application": {"core", "shared"},
    "infrastructure": {"shared"},
    "apps": {"core", "application", "infrastructure", "shared"},
}


def _collect_project_imports(layer: str) -> list[tuple[str, int, str]]:
    """Return list of (filepath, lineno, imported_package) for project imports."""
    violations: list[tuple[str, int, str]] = []
    layer_dir = ROOT / layer
    if not layer_dir.is_dir():
        return violations
    for py_file in layer_dir.rglob("*.py"):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            top_pkg = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_pkg = alias.name.split(".")[0]
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_pkg = node.module.split(".")[0]
            if top_pkg and top_pkg in PROJECT_PACKAGES and top_pkg != layer:
                violations.append((str(py_file.relative_to(ROOT)), node.lineno, top_pkg))
    return violations


# ── Tests ────────────────────────────────────────────────────────────────


class TestLintImportsClean:
    """Run lint-imports programmatically and assert all contracts pass."""

    def test_lint_imports_zero_violations(self):
        """lint-imports must report 0 broken contracts."""
        result = subprocess.run(
            [str(ROOT / ".venv" / "Scripts" / "lint-imports")],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=120,
        )
        # Fallback: if lint-imports.exe is not at the expected path, try via python -m
        if result.returncode != 0 and "not found" in (result.stderr or "").lower():
            result = subprocess.run(
                [sys.executable, "-c", "from importlinter.cli import lint_imports_command; lint_imports_command()"],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                timeout=120,
            )
        assert "0 broken" in result.stdout, (
            f"lint-imports reported broken contracts:\n{result.stdout}\n{result.stderr}"
        )
        assert result.returncode == 0, f"lint-imports exited with code {result.returncode}"


class TestSharedNoUpwardImports:
    """shared/ must not import from any other project package."""

    def test_shared_only_imports_stdlib(self):
        violations = _collect_project_imports("shared")
        forbidden = [(f, ln, pkg) for f, ln, pkg in violations if pkg not in LAYER_RULES["shared"]]
        assert not forbidden, (
            f"shared/ has {len(forbidden)} forbidden import(s):\n"
            + "\n".join(f"  {f}:{ln} imports {pkg}" for f, ln, pkg in forbidden)
        )


class TestCoreOnlyImportsShared:
    """core/ must only import from shared/ (no application, infrastructure, apps)."""

    def test_core_respects_boundary(self):
        violations = _collect_project_imports("core")
        forbidden = [(f, ln, pkg) for f, ln, pkg in violations if pkg not in LAYER_RULES["core"]]
        assert not forbidden, (
            f"core/ has {len(forbidden)} forbidden import(s):\n"
            + "\n".join(f"  {f}:{ln} imports {pkg}" for f, ln, pkg in forbidden)
        )


class TestInfrastructureOnlyImportsShared:
    """infrastructure/ must only import from shared/."""

    def test_infrastructure_respects_boundary(self):
        violations = _collect_project_imports("infrastructure")
        forbidden = [(f, ln, pkg) for f, ln, pkg in violations if pkg not in LAYER_RULES["infrastructure"]]
        assert not forbidden, (
            f"infrastructure/ has {len(forbidden)} forbidden import(s):\n"
            + "\n".join(f"  {f}:{ln} imports {pkg}" for f, ln, pkg in forbidden)
        )


class TestApplicationRespectsLayers:
    """application/ must only import from core/ and shared/."""

    def test_application_respects_boundary(self):
        violations = _collect_project_imports("application")
        forbidden = [(f, ln, pkg) for f, ln, pkg in violations if pkg not in LAYER_RULES["application"]]
        assert not forbidden, (
            f"application/ has {len(forbidden)} forbidden import(s):\n"
            + "\n".join(f"  {f}:{ln} imports {pkg}" for f, ln, pkg in forbidden)
        )


class TestNoCircularDepsInRealtime:
    """Extracted apps/realtime/ modules must form a DAG (no circular imports)."""

    REALTIME_MODULES = [
        "agent",
        "session_manager",
        "vision_controller",
        "voice_controller",
        "tool_router",
        "prompts",
        "user_data",
        "entrypoint",
    ]

    def _build_import_graph(self) -> dict[str, list[str]]:
        base = ROOT / "apps" / "realtime"
        graph: dict[str, list[str]] = {}
        for mod in self.REALTIME_MODULES:
            fpath = base / (mod + ".py")
            if not fpath.exists():
                continue
            graph[mod] = []
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                module_name = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        parts = alias.name.split(".")
                        if len(parts) >= 3 and parts[0] == "apps" and parts[1] == "realtime":
                            module_name = parts[2]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    parts = node.module.split(".")
                    if len(parts) >= 3 and parts[0] == "apps" and parts[1] == "realtime":
                        module_name = parts[2]
                if module_name and module_name in self.REALTIME_MODULES and module_name != mod:
                    graph[mod].append(module_name)
        return graph

    def _has_cycle(self, graph: dict[str, list[str]]) -> list[str]:
        """DFS cycle detection. Returns cycle path or empty list."""
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[str] = []

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor in rec_stack:
                    idx = path.index(neighbor) if neighbor in path else len(path)
                    cycles.append(" -> ".join(path[idx:] + [neighbor]))
                elif neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
            rec_stack.discard(node)

        for node in graph:
            if node not in visited:
                dfs(node, [node])
        return cycles

    def test_no_circular_imports(self):
        graph = self._build_import_graph()
        cycles = self._has_cycle(graph)
        assert not cycles, (
            "Circular import(s) found in apps/realtime/:\n"
            + "\n".join(f"  {c}" for c in cycles)
        )


class TestExtractedModulesRespectLayer:
    """Each extracted realtime module must only import from allowed project layers (apps rule)."""

    EXTRACTED_MODULES = [
        "session_manager.py",
        "vision_controller.py",
        "voice_controller.py",
        "tool_router.py",
        "user_data.py",
        "prompts.py",
    ]

    def test_each_module_respects_apps_layer(self):
        allowed = LAYER_RULES["apps"]
        base = ROOT / "apps" / "realtime"
        violations = []
        for fname in self.EXTRACTED_MODULES:
            fpath = base / fname
            if not fpath.exists():
                continue
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                top_pkg = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top_pkg = node.module.split(".")[0]
                if top_pkg and top_pkg in PROJECT_PACKAGES and top_pkg != "apps" and top_pkg not in allowed:
                    violations.append(f"{fname}:{node.lineno} imports {top_pkg}")
        assert not violations, (
            "Extracted module(s) violate apps layer rules:\n"
            + "\n".join(f"  {v}" for v in violations)
        )
