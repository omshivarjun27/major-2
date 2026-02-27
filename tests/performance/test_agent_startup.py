"""Agent startup time benchmark (T-051).

Measures the import-time cost of the decomposed agent module structure.
This establishes the P2 baseline and ensures decomposition did not
introduce excessive import overhead.
"""

import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestAgentStartup:
    """Measure startup time for the decomposed agent modules."""

    MAX_IMPORT_TIME_S = 30.0  # includes heavy ML deps (torch, FAISS, easyocr)

    def test_startup_time_within_budget(self):
        """Importing the full agent module chain should complete within budget."""
        import importlib
        import sys

        # Evict cached modules to measure fresh import cost
        modules_to_clear = [m for m in sys.modules if m.startswith("apps.realtime")]
        for m in modules_to_clear:
            del sys.modules[m]

        start = time.perf_counter()
        importlib.import_module("apps.realtime.agent")
        elapsed = time.perf_counter() - start

        assert elapsed < self.MAX_IMPORT_TIME_S, (
            f"Agent import took {elapsed:.2f}s (limit: {self.MAX_IMPORT_TIME_S}s)"
        )

    def test_tool_router_imports_fast(self):
        """tool_router.py should import very quickly (stdlib only)."""
        import importlib
        import sys

        modules_to_clear = [m for m in sys.modules if m.startswith("apps.realtime.tool_router")]
        for m in modules_to_clear:
            del sys.modules[m]

        start = time.perf_counter()
        importlib.import_module("apps.realtime.tool_router")
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, (
            f"tool_router import took {elapsed:.2f}s (limit: 2.0s)"
        )

    def test_no_file_exceeds_500_loc_coordinator(self):
        """The coordinator (agent.py) must stay under 500 LOC."""
        agent_py = ROOT / "apps" / "realtime" / "agent.py"
        loc = sum(1 for _ in agent_py.open(encoding="utf-8"))
        assert loc <= 500, f"agent.py has {loc} LOC (limit: 500)"
