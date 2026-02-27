"""Regression tests to prevent reintroduction of blocking calls in async code.

These tests use static analysis (AST + grep) to verify that known blocking
patterns are not present inside async functions in hot-path modules.
"""

import ast
import re
from pathlib import Path

# Directories to scan
SOURCE_DIRS = [
    Path("core"),
    Path("application"),
    Path("infrastructure"),
]

# Hot-path modules where blocking is critical
HOT_PATH_MODULES = [
    "core/vision/spatial.py",
    "core/vision/visual.py",
    "core/vqa/perception.py",
    "core/vqa/orchestrator.py",
    "core/speech/tts_handler.py",
    "core/speech/speech_handler.py",
    "core/ocr/engine.py",
    "core/memory/retriever.py",
    "infrastructure/llm/ollama/handler.py",
    "infrastructure/llm/internet_search.py",
]


def _get_python_files(dirs):
    """Collect all .py files from given directories."""
    files = []
    for d in dirs:
        if d.exists():
            files.extend(d.rglob("*.py"))
    return files


def _find_async_functions(tree: ast.AST):
    """Yield all async function definitions in an AST."""
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            yield node


def _contains_call(node, func_names):
    """Check if an AST node contains a call to any of the given function names."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            # Check for attribute calls like time.sleep, requests.get
            if isinstance(child.func, ast.Attribute):
                full_name = f"{_get_attr_base(child.func)}.{child.func.attr}"
                if any(fn in full_name for fn in func_names):
                    return True, full_name
            # Check for simple name calls
            if isinstance(child.func, ast.Name):
                if child.func.id in func_names:
                    return True, child.func.id
    return False, ""


def _get_attr_base(node):
    """Get the base name of an attribute chain."""
    if isinstance(node, ast.Attribute):
        return _get_attr_base(node.value)
    if isinstance(node, ast.Name):
        return node.id
    return ""


class TestNoBlockingInAsyncFunctions:
    """Verify no blocking patterns exist inside async functions."""

    def test_no_time_sleep_in_async(self):
        """time.sleep() must not appear in any async function."""
        violations = []
        for py_file in _get_python_files(SOURCE_DIRS):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for func in _find_async_functions(tree):
                found, name = _contains_call(func, ["time.sleep"])
                if found:
                    violations.append(f"{py_file}:{func.lineno} {func.name}() calls {name}")
        assert not violations, "Blocking time.sleep in async functions:\n" + "\n".join(violations)

    def test_no_sync_requests_in_async(self):
        """requests.get/post/etc must not appear in any async function."""
        violations = []
        blocked = ["requests.get", "requests.post", "requests.put", "requests.delete", "requests.patch"]
        for py_file in _get_python_files(SOURCE_DIRS):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for func in _find_async_functions(tree):
                found, name = _contains_call(func, blocked)
                if found:
                    violations.append(f"{py_file}:{func.lineno} {func.name}() calls {name}")
        assert not violations, "Sync requests in async functions:\n" + "\n".join(violations)

    def test_no_bare_open_in_hot_path_async(self):
        """Bare open() calls should not appear in async functions of hot-path modules."""
        violations = []
        for module_path in HOT_PATH_MODULES:
            py_file = Path(module_path)
            if not py_file.exists():
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for func in _find_async_functions(tree):
                # Look for 'open(' calls that aren't inside asyncio.to_thread/run_in_executor
                for child in ast.walk(func):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == "open":
                        violations.append(f"{py_file}:{func.lineno} {func.name}() has bare open()")
        assert not violations, "Bare open() in hot-path async functions:\n" + "\n".join(violations)

    def test_no_subprocess_run_in_async(self):
        """subprocess.run/call must not appear in any async function."""
        violations = []
        blocked = ["subprocess.run", "subprocess.call", "subprocess.Popen"]
        for py_file in _get_python_files(SOURCE_DIRS):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for func in _find_async_functions(tree):
                found, name = _contains_call(func, blocked)
                if found:
                    violations.append(f"{py_file}:{func.lineno} {func.name}() calls {name}")
        assert not violations, "Sync subprocess in async functions:\n" + "\n".join(violations)

    def test_no_requests_import_in_hot_path(self):
        """The 'requests' library must not be imported in hot-path modules."""
        violations = []
        for module_path in HOT_PATH_MODULES:
            py_file = Path(module_path)
            if not py_file.exists():
                continue
            source = py_file.read_text(encoding="utf-8")
            if re.search(r"^import requests\b|^from requests\b", source, re.MULTILINE):
                violations.append(str(py_file))
        assert not violations, "'requests' imported in hot-path modules:\n" + "\n".join(violations)

    def test_no_bare_langchain_invoke_in_async(self):
        """Langchain .invoke() must be wrapped with asyncio.to_thread in async functions."""
        violations = []
        for py_file in _get_python_files(SOURCE_DIRS):
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for func in _find_async_functions(tree):
                # Check for .invoke() calls that are NOT inside asyncio.to_thread
                for child in ast.walk(func):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                        if child.func.attr == "invoke":
                            # Check if this is inside an asyncio.to_thread call
                            # Simple heuristic: if the parent is an Await, it's wrapped
                            source_lines = source.split("\n")
                            if child.lineno <= len(source_lines):
                                line = source_lines[child.lineno - 1]
                                if "asyncio.to_thread" not in line and "await" not in line:
                                    violations.append(
                                        f"{py_file}:{child.lineno} {func.name}() has bare .invoke()"
                                    )
        assert not violations, "Bare .invoke() in async functions:\n" + "\n".join(violations)
