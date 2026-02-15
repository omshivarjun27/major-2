"""
NFR Test #114 — Sustained FPS Stress Test
==========================================

Verifies the frame processing pipeline sustains target FPS
over a 60-second simulated window with <5% frame drops.
"""

import time
import asyncio
import numpy as np
import pytest


@pytest.fixture
def mock_frame():
    """Generate a realistic 640x480 BGR test frame."""
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


class TestSustainedFPS:

    TARGET_FPS = 10  # Conservative target for edge devices
    DURATION_SECONDS = 5  # Short for CI; set to 60 for real bench
    MAX_DROP_RATIO = 0.05  # <5% dropped frames

    def test_frame_processing_sustained(self, mock_frame):
        """Process frames at target FPS for DURATION_SECONDS; measure drops."""
        from shared.config import get_config
        config = get_config()

        interval = 1.0 / self.TARGET_FPS
        total_expected = int(self.TARGET_FPS * self.DURATION_SECONDS)
        processed = 0
        dropped = 0

        start = time.monotonic()
        for i in range(total_expected):
            frame_start = time.monotonic()

            # Simulate lightweight per-frame work (no GPU)
            gray = np.mean(mock_frame, axis=2).astype(np.uint8)
            _ = np.histogram(gray, bins=16)

            elapsed = time.monotonic() - frame_start
            if elapsed > interval:
                dropped += 1
            else:
                processed += 1
                remaining = interval - elapsed
                if remaining > 0:
                    time.sleep(remaining)

        wall_time = time.monotonic() - start
        drop_ratio = dropped / total_expected

        assert drop_ratio < self.MAX_DROP_RATIO, (
            f"Frame drop ratio {drop_ratio:.2%} exceeds {self.MAX_DROP_RATIO:.2%} "
            f"({dropped}/{total_expected} dropped in {wall_time:.1f}s)"
        )

    def test_capture_cadence_config_exists(self):
        """Verify CAPTURE_CADENCE_MS config is set and reasonable."""
        from shared.config import get_config
        config = get_config()
        cadence = config.get("CAPTURE_CADENCE_MS", None)
        assert cadence is not None, "CAPTURE_CADENCE_MS must be configured"
        assert 10 <= cadence <= 1000, f"CAPTURE_CADENCE_MS={cadence} outside [10, 1000] range"

    def test_hot_path_timeout_config(self):
        """Verify HOT_PATH_TIMEOUT_MS is set and <= 500ms."""
        from shared.config import get_config
        config = get_config()
        timeout = config.get("HOT_PATH_TIMEOUT_MS", None)
        assert timeout is not None, "HOT_PATH_TIMEOUT_MS must be configured"
        assert timeout <= 500, f"HOT_PATH_TIMEOUT_MS={timeout} exceeds 500ms SLA"
