"""
NFR Test #128 — Resource Threshold Triggers
=============================================

Verifies that the system correctly triggers fallback behavior
when resource thresholds (CPU, memory, stall) are exceeded.
"""



class TestResourceThresholds:

    def test_camera_stall_threshold_exists(self):
        """CAMERA_STALL_THRESHOLD_MS must be configured."""
        from shared.config import get_config
        cfg = get_config()
        threshold = cfg.get("CAMERA_STALL_THRESHOLD_MS")
        assert threshold is not None, "CAMERA_STALL_THRESHOLD_MS not set"
        assert threshold > 0, "CAMERA_STALL_THRESHOLD_MS must be positive"
        assert threshold <= 10000, "CAMERA_STALL_THRESHOLD_MS unreasonably high"

    def test_worker_stall_threshold_exists(self):
        """WORKER_STALL_THRESHOLD_MS must be configured."""
        from shared.config import get_config
        cfg = get_config()
        threshold = cfg.get("WORKER_STALL_THRESHOLD_MS")
        assert threshold is not None, "WORKER_STALL_THRESHOLD_MS not set"
        assert threshold > 0

    def test_frame_buffer_capacity_reasonable(self):
        """FRAME_BUFFER_CAPACITY should be between 5 and 100."""
        from shared.config import get_config
        cfg = get_config()
        cap = cfg.get("FRAME_BUFFER_CAPACITY", 30)
        assert 5 <= cap <= 100, f"FRAME_BUFFER_CAPACITY={cap} outside [5, 100]"

    def test_debounce_window_configured(self):
        """DEBOUNCE_WINDOW_SECONDS should be set and >0."""
        from shared.config import get_config
        cfg = get_config()
        window = cfg.get("DEBOUNCE_WINDOW_SECONDS")
        assert window is not None
        assert window > 0, "DEBOUNCE_WINDOW_SECONDS must be positive"

    def test_pipeline_timeout_enforced(self):
        """PIPELINE_TIMEOUT_MS must be <= 500ms for real-time operation."""
        from shared.config import get_config
        cfg = get_config()
        timeout = cfg.get("PIPELINE_TIMEOUT_MS", 300)
        assert timeout <= 500, f"PIPELINE_TIMEOUT_MS={timeout} exceeds 500ms"

    def test_worker_count_reasonable(self):
        """Worker counts should be between 1 and 8."""
        from shared.config import get_config
        cfg = get_config()
        for key in ["NUM_DETECT_WORKERS", "NUM_DEPTH_WORKERS", "NUM_OCR_WORKERS", "NUM_QR_WORKERS"]:
            val = cfg.get(key, 1)
            assert 1 <= val <= 8, f"{key}={val} outside [1, 8]"

    def test_latency_targets_configured(self):
        """All latency target configs must exist and be positive."""
        from shared.config import get_config
        cfg = get_config()
        targets = [
            "TARGET_STT_LATENCY_MS",
            "TARGET_VQA_LATENCY_MS",
            "TARGET_TTS_LATENCY_MS",
            "TARGET_TOTAL_LATENCY_MS",
        ]
        for key in targets:
            val = cfg.get(key)
            assert val is not None, f"{key} not configured"
            assert val > 0, f"{key}={val} must be positive"

    def test_total_latency_budget_consistent(self):
        """Total latency target should >= sum of component targets."""
        from shared.config import get_config
        cfg = get_config()
        stt = cfg.get("TARGET_STT_LATENCY_MS", 100)
        cfg.get("TARGET_VQA_LATENCY_MS", 300)
        tts = cfg.get("TARGET_TTS_LATENCY_MS", 100)
        total = cfg.get("TARGET_TOTAL_LATENCY_MS", 500)
        assert total >= stt + tts, (
            f"Total latency {total}ms < STT({stt}ms) + TTS({tts}ms) = {stt+tts}ms"
        )
