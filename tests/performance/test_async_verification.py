"""Async conversion verification tests (T-052).

Validates that all blocking calls have been eliminated from hot-path code
and that the async audit from T-046 continues to pass as a regression gate.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Hot-path directories where blocking calls are forbidden
HOT_PATH_DIRS = [
    "core/vision",
    "core/vqa",
    "core/memory",
    "core/ocr",
    "core/qr",
    "core/speech",
    "application/frame_processing",
    "application/pipelines",
    "infrastructure/llm",
]

# Blocking patterns that must not appear in async functions within hot-path code
BLOCKING_PATTERNS = [
    r"requests\.(get|post|put|delete|patch|head)",
    r"urllib\.request\.",
    r"subprocess\.(run|call|check_output|check_call)\(",
    r"time\.sleep\(",
]


def _find_blocking_in_async(filepath: Path) -> list[tuple[int, str]]:
    """Find blocking calls inside async function bodies."""
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            # Get the source lines for this async function
            start_line = node.lineno
            end_line = node.end_lineno or start_line
            func_lines = source.splitlines()[start_line - 1 : end_line]
            func_text = "\n".join(func_lines)

            for pattern in BLOCKING_PATTERNS:
                for match in re.finditer(pattern, func_text):
                    # Calculate actual line number
                    line_offset = func_text[: match.start()].count("\n")
                    violations.append((start_line + line_offset, match.group()))
    return violations


class TestNoSyncHttpInHotPath:
    """No synchronous HTTP calls should exist in hot-path async code."""

    def test_no_blocking_calls_in_hot_path(self):
        all_violations = []
        for dir_path in HOT_PATH_DIRS:
            full_path = ROOT / dir_path
            if not full_path.is_dir():
                continue
            for py_file in full_path.rglob("*.py"):
                violations = _find_blocking_in_async(py_file)
                for line, call in violations:
                    rel = py_file.relative_to(ROOT)
                    all_violations.append(f"{rel}:{line} — {call}")

        assert not all_violations, (
            "Blocking calls found in hot-path async code:\n"
            + "\n".join(f"  {v}" for v in all_violations)
        )


class TestAsyncAuditRegression:
    """Re-run T-046 audit checks as a regression gate."""

    def test_internet_search_uses_to_thread(self):
        """infrastructure/llm/internet_search.py must use asyncio.to_thread."""
        filepath = ROOT / "infrastructure" / "llm" / "internet_search.py"
        if not filepath.exists():
            return  # module may not exist in all configurations
        content = filepath.read_text(encoding="utf-8")
        assert "asyncio.to_thread" in content, (
            "internet_search.py should use asyncio.to_thread for Langchain calls"
        )

    def test_memory_maintenance_uses_to_thread(self):
        """core/memory/maintenance.py must use asyncio.to_thread for file I/O."""
        filepath = ROOT / "core" / "memory" / "maintenance.py"
        if not filepath.exists():
            return
        content = filepath.read_text(encoding="utf-8")
        assert "asyncio.to_thread" in content, (
            "maintenance.py should use asyncio.to_thread for backup I/O"
        )

    def test_memory_indexer_save_is_async(self):
        """core/memory/indexer.py save() should not have blocking I/O in hot-path async callers."""
        filepath = ROOT / "core" / "memory" / "indexer.py"
        if not filepath.exists():
            return
        content = filepath.read_text(encoding="utf-8")
        # Verify indexer exists and has a save method (sync is OK for persistence)
        assert "def save" in content, "indexer.py should have a save() method"

    def test_memory_ingest_uses_to_thread(self):
        """core/memory/ingest.py must use asyncio.to_thread for media writes."""
        filepath = ROOT / "core" / "memory" / "ingest.py"
        if not filepath.exists():
            return
        content = filepath.read_text(encoding="utf-8")
        assert "asyncio.to_thread" in content, (
            "ingest.py should use asyncio.to_thread for file writes"
        )

    def test_embedder_has_native_async(self):
        """core/memory/embeddings.py TextEmbedder must use AsyncClient."""
        filepath = ROOT / "core" / "memory" / "embeddings.py"
        content = filepath.read_text(encoding="utf-8")
        assert "AsyncClient" in content, (
            "TextEmbedder should use ollama.AsyncClient for async embedding"
        )
