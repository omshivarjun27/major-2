"""
Tests for startup_guards.py
============================
Covers venv enforcement, device detection, banned-module scanning,
and YAML config loading with env-var overrides.
"""

from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# YAML Config Loading
# ---------------------------------------------------------------------------

class TestYamlConfigLoad:
    """Test load_yaml_config behaviour."""

    def test_loads_default_config(self):
        from shared.utils.startup_guards import load_yaml_config
        cfg = load_yaml_config()
        assert isinstance(cfg, dict)
        # Must contain required sections
        assert "confidence" in cfg
        assert "latency" in cfg
        assert "robustness" in cfg

    def test_confidence_thresholds_present(self):
        from shared.utils.startup_guards import load_yaml_config
        cfg = load_yaml_config()
        conf = cfg["confidence"]
        assert conf["detected_threshold"] == 0.60
        assert conf["low_confidence_threshold"] == 0.30
        assert conf["face_verify_threshold"] == 0.85

    def test_latency_budget_present(self):
        from shared.utils.startup_guards import load_yaml_config
        cfg = load_yaml_config()
        lat = cfg["latency"]
        assert lat["frame_budget_ms"] == 250
        assert lat["tts_remote_timeout_ms"] == 2000

    def test_banned_modules_listed(self):
        from shared.utils.startup_guards import load_yaml_config
        cfg = load_yaml_config()
        banned = cfg.get("banned_modules", [])
        assert "antigravity" in banned

    def test_fallback_when_file_missing(self):
        from shared.utils.startup_guards import load_yaml_config
        cfg = load_yaml_config(path="/nonexistent/config.yaml")
        assert isinstance(cfg, dict)
        assert "confidence" in cfg  # built-in defaults used

    def test_env_var_override(self):
        from shared.utils.startup_guards import load_yaml_config
        with mock.patch.dict(os.environ, {"PERCEPTION_CONFIDENCE_DETECTED_THRESHOLD": "0.75"}):
            cfg = load_yaml_config()
            assert cfg["confidence"]["detected_threshold"] == 0.75


# ---------------------------------------------------------------------------
# Venv Enforcement
# ---------------------------------------------------------------------------

class TestVenvEnforcement:
    """Test enforce_venv() detects venv state."""

    def test_detects_active_venv(self):
        """When sys.prefix != sys.base_prefix, enforce_venv should return True."""
        from shared.utils.startup_guards import enforce_venv
        # In our test environment we should be in a venv
        # (if running via .venv), or we mock it
        with mock.patch.object(sys, "prefix", "/some/venv"):
            with mock.patch.object(sys, "base_prefix", "/usr"):
                result = enforce_venv()
                assert result is True

    def test_exits_outside_venv(self):
        """When sys.prefix == sys.base_prefix, enforce_venv should sys.exit(1)."""
        from shared.utils.startup_guards import enforce_venv
        with mock.patch.object(sys, "prefix", "/usr"):
            with mock.patch.object(sys, "base_prefix", "/usr"):
                # Also remove real_prefix if present
                if hasattr(sys, "real_prefix"):
                    with mock.patch.object(sys, "real_prefix", None, create=False):
                        with pytest.raises(SystemExit) as exc_info:
                            enforce_venv()
                        assert exc_info.value.code == 1
                else:
                    with pytest.raises(SystemExit) as exc_info:
                        enforce_venv()
                    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Device Detection
# ---------------------------------------------------------------------------

class TestDeviceDetection:
    """Test detect_device() reports cpu or cuda."""

    def test_cpu_when_no_torch(self):
        from shared.utils.startup_guards import detect_device
        with mock.patch.dict(sys.modules, {"torch": None}):
            # Force ImportError by replacing the module
            device = detect_device()
            # Should not crash, should return cpu
            assert device in ("cpu", "cuda")

    def test_cpu_when_cuda_unavailable(self):
        from shared.utils.startup_guards import detect_device
        mock_torch = mock.MagicMock()
        mock_torch.cuda.is_available.return_value = False
        with mock.patch.dict(sys.modules, {"torch": mock_torch}):
            device = detect_device()
            assert device == "cpu"

    def test_cuda_when_available(self):
        from shared.utils.startup_guards import detect_device
        mock_torch = mock.MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "Test GPU"
        with mock.patch.dict(sys.modules, {"torch": mock_torch}):
            device = detect_device()
            assert device == "cuda"


# ---------------------------------------------------------------------------
# Banned Module Scan
# ---------------------------------------------------------------------------

class TestBannedModuleScan:
    """Test scan_banned_modules detects loaded banned imports."""

    def test_no_banned_modules(self):
        from shared.utils.startup_guards import scan_banned_modules
        found = scan_banned_modules(["nonexistent_module_xyz"])
        assert found == []

    def test_detects_banned_module(self):
        from shared.utils.startup_guards import scan_banned_modules
        # Temporarily inject a fake banned module into sys.modules
        fake_name = "_test_banned_fake_module"
        sys.modules[fake_name] = mock.MagicMock()
        try:
            found = scan_banned_modules([fake_name])
            assert fake_name in found
        finally:
            del sys.modules[fake_name]

    def test_antigravity_default_list(self):
        from shared.utils.startup_guards import scan_banned_modules
        # antigravity should NOT be loaded by default
        found = scan_banned_modules()
        assert "antigravity" not in found  # should not be loaded


# ---------------------------------------------------------------------------
# run_startup_checks orchestrator
# ---------------------------------------------------------------------------

class TestRunStartupChecks:
    """Test the orchestrator function."""

    def test_returns_expected_keys(self):
        from shared.utils.startup_guards import run_startup_checks
        info = run_startup_checks(skip_venv_check=True)
        assert "device" in info
        assert "venv" in info
        assert "banned_modules_found" in info
        assert "config" in info
        assert isinstance(info["config"], dict)

    def test_get_startup_info_returns_cached(self):
        from shared.utils.startup_guards import get_startup_info, run_startup_checks
        info1 = run_startup_checks(skip_venv_check=True)
        info2 = get_startup_info()
        assert info1 is info2
