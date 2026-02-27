"""Tech debt compliance checks (T-050).

Ensures key tech debt resolutions remain in effect:
- TD-001: agent.py stays under 500 LOC
- TD-003: TextEmbedder uses async patterns
- TD-010: shared/__init__.py has minimal, intentional re-exports
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REALTIME_DIR = ROOT / "apps" / "realtime"


class TestAgentLOCCompliance:
    """TD-001: agent.py must stay under 500 LOC."""

    MAX_COORDINATOR_LOC = 500

    def test_agent_under_500_loc(self):
        agent_py = REALTIME_DIR / "agent.py"
        loc = sum(1 for _ in agent_py.open(encoding="utf-8"))
        assert loc <= self.MAX_COORDINATOR_LOC, (
            f"agent.py has {loc} LOC (limit: {self.MAX_COORDINATOR_LOC}). "
            "Extract logic to a controller module."
        )

    def test_no_file_exceeds_800_loc_in_realtime(self):
        """No single module in apps/realtime/ should exceed 800 LOC."""
        limit = 800
        over = []
        for py_file in REALTIME_DIR.glob("*.py"):
            loc = sum(1 for _ in py_file.open(encoding="utf-8"))
            if loc > limit:
                over.append(f"{py_file.name}: {loc} LOC")
        assert not over, (
            f"File(s) exceed {limit} LOC in apps/realtime/:\n"
            + "\n".join(f"  {v}" for v in over)
        )


class TestEmbedderAsync:
    """TD-003: TextEmbedder must use async patterns (not sync HTTP)."""

    def test_embedder_has_async_client(self):
        """TextEmbedder should reference AsyncClient for native async embedding."""
        embeddings_py = ROOT / "core" / "memory" / "embeddings.py"
        content = embeddings_py.read_text(encoding="utf-8")
        assert "AsyncClient" in content, (
            "core/memory/embeddings.py does not reference AsyncClient. "
            "TextEmbedder should use ollama.AsyncClient for async embedding."
        )

    def test_embedder_has_async_embed_method(self):
        """TextEmbedder should have an async embed method."""
        embeddings_py = ROOT / "core" / "memory" / "embeddings.py"
        tree = ast.parse(embeddings_py.read_text(encoding="utf-8"))
        async_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and "embed" in node.name.lower():
                async_methods.append(node.name)
        assert async_methods, (
            "No async embed methods found in core/memory/embeddings.py. "
            "TextEmbedder must have async def embed_*() methods."
        )


class TestSharedInitMinimal:
    """TD-010: shared/__init__.py should have minimal, intentional re-exports."""

    MAX_EXPORTS = 25  # reasonable ceiling for canonical shared types

    def test_shared_init_export_count(self):
        """shared/__init__.py should not have excessive re-exports."""
        init_py = ROOT / "shared" / "__init__.py"
        tree = ast.parse(init_py.read_text(encoding="utf-8"))
        # Count items in __all__ if it exists
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            count = len(node.value.elts)
                            assert count <= self.MAX_EXPORTS, (
                                f"shared/__init__.py exports {count} symbols "
                                f"(limit: {self.MAX_EXPORTS}). "
                                "Consider importing directly from submodules."
                            )
                            return
        # If no __all__, count import statements
        imports = sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        )
        assert imports <= self.MAX_EXPORTS, (
            f"shared/__init__.py has {imports} import statements "
            f"(limit: {self.MAX_EXPORTS})"
        )

    def test_shared_init_only_imports_from_schemas(self):
        """shared/__init__.py should only re-export from shared.schemas."""
        init_py = ROOT / "shared" / "__init__.py"
        tree = ast.parse(init_py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.startswith("shared."), (
                    f"shared/__init__.py imports from {node.module} — "
                    "should only re-export from shared.schemas or shared submodules"
                )
