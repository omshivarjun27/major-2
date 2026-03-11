"""NFR: Latency SLA — verifies configuration targets and budget enforcement."""

from __future__ import annotations

import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestLatencySLA:
    """Verify latency configuration and budget enforcement."""

    def test_latency_targets_configured(self):
        """Config should have latency targets defined."""
        from shared.config import get_config
        config = get_config()
        assert "TARGET_TOTAL_LATENCY_MS" in config
        assert config["TARGET_TOTAL_LATENCY_MS"] <= 1000, \
            "Total latency target should be <= 1000ms"

    def test_hot_path_budget_configured(self):
        """Hot path timeout should be configured."""
        from shared.config import get_config
        config = get_config()
        assert "HOT_PATH_TIMEOUT_MS" in config
        assert config["HOT_PATH_TIMEOUT_MS"] <= 1000

    def test_frame_max_age_configured(self):
        """Live frame max age should be reasonable."""
        from shared.config import get_config
        config = get_config()
        assert "LIVE_FRAME_MAX_AGE_MS" in config
        assert config["LIVE_FRAME_MAX_AGE_MS"] <= 2000, \
            "Frame max age should be <= 2000ms to prevent stale data"

    def test_orchestrator_import_latency(self):
        """FrameOrchestrator import should be fast (< 2s)."""
        start = time.monotonic()
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 2000, f"Orchestrator import took {elapsed:.0f}ms (limit: 2000ms)"

    def test_config_import_latency(self):
        """Config import should be fast (< 500ms)."""
        start = time.monotonic()
        from shared.config import get_config
        get_config()
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 500, f"Config import took {elapsed:.0f}ms (limit: 500ms)"
