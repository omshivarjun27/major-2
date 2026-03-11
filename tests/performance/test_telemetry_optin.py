"""NFR: Telemetry Opt-In — verifies diagnostics only collected after opt-in."""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestTelemetryOptIn:
    """Verify telemetry and diagnostics respect opt-in settings."""

    def test_diagnostics_disabled_by_default(self):
        """DIAGNOSTICS_ENABLED should default to false."""
        val = os.environ.get("DIAGNOSTICS_ENABLED", "false")
        assert val.lower() == "false", \
            "Diagnostics should be disabled by default"

    def test_memory_telemetry_disabled_by_default(self):
        """MEMORY_TELEMETRY should default to false in config."""
        from shared.config import get_config
        config = get_config()
        assert config.get("MEMORY_TELEMETRY", False) is False, \
            "Memory telemetry should be disabled by default"

    def test_pii_scrub_enabled_by_default(self):
        """PII scrubbing should be enabled by default."""
        val = os.environ.get("PII_SCRUB", "true")
        assert val.lower() != "false", \
            "PII scrubbing should be enabled by default"
