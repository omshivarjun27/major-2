"""
NFR Test #115 — Memory Leak Detection
=======================================

Processes a large number of frames and asserts that RSS growth
stays below acceptable thresholds, detecting memory leaks.
"""

import gc
import os
import numpy as np
import pytest


def _rss_mb():
    """Get current process RSS in MB (cross-platform)."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        # Fallback for Windows without psutil
        try:
            import ctypes
            import ctypes.wintypes
            kernel32 = ctypes.windll.kernel32
            process = kernel32.GetCurrentProcess()

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.wintypes.DWORD),
                    ("PageFaultCount", ctypes.wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(pmc)
            ctypes.windll.psapi.GetProcessMemoryInfo(
                process, ctypes.byref(pmc), pmc.cb
            )
            return pmc.WorkingSetSize / (1024 * 1024)
        except Exception:
            return 0.0


class TestMemoryLeak:

    NUM_FRAMES = 500  # Reduced for CI; use 5000 for real bench
    MAX_GROWTH_MB = 50

    def test_frame_processing_no_leak(self):
        """Process many frames and check RSS doesn't grow excessively."""
        gc.collect()
        baseline = _rss_mb()
        if baseline == 0:
            pytest.skip("Cannot measure RSS on this platform")

        for i in range(self.NUM_FRAMES):
            # Simulate frame processing: alloc, compute, release
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            gray = np.mean(frame, axis=2).astype(np.uint8)
            _ = np.histogram(gray, bins=16)
            del frame, gray

            # Periodic GC
            if i % 100 == 0:
                gc.collect()

        gc.collect()
        final = _rss_mb()
        growth = final - baseline

        assert growth < self.MAX_GROWTH_MB, (
            f"RSS grew {growth:.1f} MB after {self.NUM_FRAMES} frames "
            f"(baseline={baseline:.1f} MB, final={final:.1f} MB). "
            f"Limit: {self.MAX_GROWTH_MB} MB"
        )

    def test_config_lists_no_leak(self):
        """Loading config repeatedly shouldn't leak."""
        gc.collect()
        baseline = _rss_mb()
        if baseline == 0:
            pytest.skip("Cannot measure RSS on this platform")

        from shared.config import get_config
        for _ in range(100):
            _ = get_config()

        gc.collect()
        final = _rss_mb()
        growth = final - baseline
        assert growth < 5, f"Config loading leaked {growth:.1f} MB"
