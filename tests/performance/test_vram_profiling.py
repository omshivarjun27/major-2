"""P4: VRAM Profiling Tests (T-077).

Tests for VRAM profiling utilities and analysis tools.
"""

from __future__ import annotations

import gc
import os
import sys
import time
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------

class TestVRAMProfilerImports:
    """Test VRAM profiler module imports."""
    
    def test_vram_profiler_import(self):
        """vram_profiler module should import correctly."""
        from shared.utils.vram_profiler import (
            VRAMProfiler,
            VRAMSnapshot,
            VRAMProfile,
            ComponentVRAMUsage,
            get_vram_profiler,
            is_cuda_available,
        )
        
        assert VRAMProfiler is not None
        assert VRAMSnapshot is not None
        assert VRAMProfile is not None
        assert ComponentVRAMUsage is not None
    
    def test_profile_script_import(self):
        """profile_vram script should import correctly."""
        from scripts.profile_vram import (
            ComponentProfile,
            generate_vram_report,
            generate_markdown_report,
        )
        
        assert ComponentProfile is not None
        assert generate_vram_report is not None
        assert generate_markdown_report is not None


# ---------------------------------------------------------------------------
# Data Structure Tests
# ---------------------------------------------------------------------------

class TestVRAMSnapshot:
    """Test VRAMSnapshot data structure."""
    
    def test_snapshot_creation(self):
        """Should create snapshot with correct values."""
        from shared.utils.vram_profiler import VRAMSnapshot
        
        snapshot = VRAMSnapshot(
            timestamp=time.time(),
            allocated_mb=1024.0,
            reserved_mb=2048.0,
            peak_mb=1500.0,
            label="test_snapshot",
        )
        
        assert snapshot.allocated_mb == 1024.0
        assert snapshot.reserved_mb == 2048.0
        assert snapshot.peak_mb == 1500.0
        assert snapshot.label == "test_snapshot"
    
    def test_snapshot_str(self):
        """Should have readable string representation."""
        from shared.utils.vram_profiler import VRAMSnapshot
        
        snapshot = VRAMSnapshot(
            timestamp=time.time(),
            allocated_mb=1024.0,
            reserved_mb=2048.0,
            peak_mb=1500.0,
            label="test",
        )
        
        assert "test" in str(snapshot)
        assert "1024" in str(snapshot)


class TestVRAMProfile:
    """Test VRAMProfile data structure."""
    
    def test_profile_delta_calculation(self):
        """Should calculate delta correctly."""
        from shared.utils.vram_profiler import VRAMProfile
        
        profile = VRAMProfile(
            name="test_op",
            start_allocated_mb=100.0,
            end_allocated_mb=250.0,
            peak_allocated_mb=300.0,
        )
        
        assert profile.delta_allocated_mb == 150.0
    
    def test_profile_to_dict(self):
        """Should serialize to dict correctly."""
        from shared.utils.vram_profiler import VRAMProfile
        
        profile = VRAMProfile(
            name="test_op",
            start_allocated_mb=100.0,
            end_allocated_mb=250.0,
            peak_allocated_mb=300.0,
            duration_ms=50.5,
        )
        
        d = profile.to_dict()
        assert d["name"] == "test_op"
        assert d["delta_allocated_mb"] == 150.0
        assert d["duration_ms"] == 50.5


class TestComponentVRAMUsage:
    """Test ComponentVRAMUsage data structure."""
    
    def test_component_average(self):
        """Should calculate average correctly."""
        from shared.utils.vram_profiler import ComponentVRAMUsage
        
        usage = ComponentVRAMUsage(
            component="yolo",
            idle_mb=500.0,
            active_mb=800.0,
            peak_mb=1000.0,
        )
        
        assert usage.average_mb == 650.0
    
    def test_component_to_dict(self):
        """Should serialize correctly."""
        from shared.utils.vram_profiler import ComponentVRAMUsage
        
        usage = ComponentVRAMUsage(
            component="yolo",
            idle_mb=500.0,
            active_mb=800.0,
            peak_mb=1000.0,
        )
        
        d = usage.to_dict()
        assert d["component"] == "yolo"
        assert d["peak_mb"] == 1000.0


# ---------------------------------------------------------------------------
# Profiler Tests
# ---------------------------------------------------------------------------

class TestVRAMProfiler:
    """Test VRAMProfiler class."""
    
    def test_profiler_creation(self):
        """Should create profiler instance."""
        from shared.utils.vram_profiler import VRAMProfiler
        
        profiler = VRAMProfiler(enabled=True)
        assert profiler is not None
    
    def test_profiler_track_context_manager(self):
        """Track context manager should work without CUDA."""
        from shared.utils.vram_profiler import VRAMProfiler
        
        profiler = VRAMProfiler(enabled=False)
        
        with profiler.track("test_op"):
            time.sleep(0.01)
        
        # Should not crash, but won't record without CUDA
        # This is acceptable behavior
    
    def test_profiler_register_component(self):
        """Should register component usage."""
        from shared.utils.vram_profiler import VRAMProfiler
        
        profiler = VRAMProfiler(enabled=False)
        profiler.register_component(
            component="test_component",
            idle_mb=100.0,
            active_mb=200.0,
            peak_mb=250.0,
        )
        
        assert "test_component" in profiler.component_usage
        assert profiler.component_usage["test_component"].peak_mb == 250.0
    
    def test_profiler_get_top_consumers(self):
        """Should return top consumers sorted by peak."""
        from shared.utils.vram_profiler import VRAMProfiler
        
        profiler = VRAMProfiler(enabled=False)
        profiler.register_component("small", 10, 20, 30)
        profiler.register_component("large", 100, 200, 300)
        profiler.register_component("medium", 50, 100, 150)
        
        top = profiler.get_top_consumers(3)
        
        assert len(top) == 3
        assert top[0][0] == "large"
        assert top[0][1] == 300
    
    def test_profiler_get_summary(self):
        """Should return complete summary."""
        from shared.utils.vram_profiler import VRAMProfiler
        
        profiler = VRAMProfiler(enabled=False)
        profiler.register_component("test", 100, 200, 250)
        
        summary = profiler.get_summary()
        
        assert "cuda_available" in summary
        assert "components" in summary
        assert "top_consumers" in summary
    
    def test_profiler_reset(self):
        """Should reset all data."""
        from shared.utils.vram_profiler import VRAMProfiler
        
        profiler = VRAMProfiler(enabled=False)
        profiler.register_component("test", 100, 200, 250)
        
        assert len(profiler.component_usage) == 1
        
        profiler.reset()
        
        assert len(profiler.component_usage) == 0


class TestGlobalProfiler:
    """Test global profiler singleton."""
    
    def test_get_vram_profiler(self):
        """Should return global profiler instance."""
        from shared.utils.vram_profiler import get_vram_profiler, reset_vram_profiler
        
        reset_vram_profiler()
        
        profiler1 = get_vram_profiler()
        profiler2 = get_vram_profiler()
        
        assert profiler1 is profiler2
    
    def test_reset_vram_profiler(self):
        """Should reset global profiler."""
        from shared.utils.vram_profiler import get_vram_profiler, reset_vram_profiler
        
        profiler1 = get_vram_profiler()
        reset_vram_profiler()
        profiler2 = get_vram_profiler()
        
        assert profiler1 is not profiler2


# ---------------------------------------------------------------------------
# CUDA Detection Tests
# ---------------------------------------------------------------------------

class TestCUDADetection:
    """Test CUDA detection utilities."""
    
    def test_is_cuda_available(self):
        """Should return boolean for CUDA availability."""
        from shared.utils.vram_profiler import is_cuda_available
        
        result = is_cuda_available()
        assert isinstance(result, bool)
    
    def test_get_current_vram_usage(self):
        """Should return tuple of floats."""
        from shared.utils.vram_profiler import get_current_vram_usage
        
        allocated, reserved, peak = get_current_vram_usage()
        
        assert isinstance(allocated, float)
        assert isinstance(reserved, float)
        assert isinstance(peak, float)
        assert allocated >= 0
        assert reserved >= 0
        assert peak >= 0
    
    def test_empty_cuda_cache(self):
        """Should not crash when emptying cache."""
        from shared.utils.vram_profiler import empty_cuda_cache
        
        # Should not raise exception
        empty_cuda_cache()


# ---------------------------------------------------------------------------
# Component Profile Tests
# ---------------------------------------------------------------------------

class TestComponentProfile:
    """Test ComponentProfile data structure."""
    
    def test_profile_creation(self):
        """Should create profile with all fields."""
        from scripts.profile_vram import ComponentProfile
        
        profile = ComponentProfile(
            name="Test Component",
            load_time_ms=100.0,
            idle_vram_mb=500.0,
            active_vram_mb=800.0,
            peak_vram_mb=1000.0,
            inference_time_ms=50.0,
        )
        
        assert profile.name == "Test Component"
        assert profile.available is True
    
    def test_profile_unavailable(self):
        """Should handle unavailable components."""
        from scripts.profile_vram import ComponentProfile
        
        profile = ComponentProfile(
            name="Missing Component",
            load_time_ms=0,
            idle_vram_mb=0,
            active_vram_mb=0,
            peak_vram_mb=0,
            inference_time_ms=0,
            available=False,
            error="Module not found",
        )
        
        assert profile.available is False
        assert profile.error == "Module not found"


# ---------------------------------------------------------------------------
# Report Generation Tests
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Test report generation functions."""
    
    def test_generate_vram_report(self):
        """Should generate valid report structure."""
        from scripts.profile_vram import ComponentProfile, generate_vram_report
        
        profiles = [
            ComponentProfile(
                name="Component A",
                load_time_ms=100,
                idle_vram_mb=500,
                active_vram_mb=800,
                peak_vram_mb=1000,
                inference_time_ms=50,
            ),
            ComponentProfile(
                name="Component B",
                load_time_ms=200,
                idle_vram_mb=300,
                active_vram_mb=600,
                peak_vram_mb=700,
                inference_time_ms=30,
            ),
        ]
        
        report = generate_vram_report(profiles)
        
        assert "timestamp" in report
        assert "summary" in report
        assert "components" in report
        assert "top_consumers" in report
        assert report["summary"]["components_profiled"] == 2
    
    def test_generate_markdown_report(self):
        """Should generate valid markdown."""
        from scripts.profile_vram import ComponentProfile, generate_vram_report, generate_markdown_report
        
        profiles = [
            ComponentProfile(
                name="Test Component",
                load_time_ms=100,
                idle_vram_mb=500,
                active_vram_mb=800,
                peak_vram_mb=1000,
                inference_time_ms=50,
            ),
        ]
        
        report = generate_vram_report(profiles)
        md = generate_markdown_report(report)
        
        assert "# VRAM Profiling Analysis" in md
        assert "Test Component" in md
        assert "Summary" in md
    
    def test_budget_check(self):
        """Should correctly check against 8GB budget."""
        from scripts.profile_vram import ComponentProfile, generate_vram_report
        
        # Within budget
        profiles_ok = [
            ComponentProfile("A", 0, 0, 0, 4000, 0),
        ]
        report_ok = generate_vram_report(profiles_ok)
        assert report_ok["summary"]["within_budget"] is True
        
        # Over budget
        profiles_over = [
            ComponentProfile("B", 0, 0, 0, 9000, 0),
        ]
        report_over = generate_vram_report(profiles_over)
        assert report_over["summary"]["within_budget"] is False


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestVRAMProfilingIntegration:
    """Integration tests for VRAM profiling."""
    
    def test_full_profiling_workflow(self):
        """Test complete profiling workflow."""
        from shared.utils.vram_profiler import VRAMProfiler, reset_vram_profiler
        from scripts.profile_vram import ComponentProfile, generate_vram_report, generate_markdown_report
        
        reset_vram_profiler()
        
        # Create profiler and register components
        profiler = VRAMProfiler(enabled=False)
        profiler.register_component("model_a", 100, 200, 300)
        profiler.register_component("model_b", 200, 400, 500)
        
        # Generate report from component profiles
        profiles = [
            ComponentProfile("Model A", 50, 100, 200, 300, 10),
            ComponentProfile("Model B", 100, 200, 400, 500, 20),
        ]
        
        report = generate_vram_report(profiles)
        md = generate_markdown_report(report)
        
        assert len(report["components"]) == 2
        assert "Model A" in md
        assert "Model B" in md
    
    def test_recommendations_generation(self):
        """Should generate recommendations for high VRAM usage."""
        from scripts.profile_vram import ComponentProfile, generate_vram_report
        
        # High VRAM usage should trigger recommendations
        profiles = [
            ComponentProfile("Heavy Model", 1000, 5000, 6500, 7000, 100),
        ]
        
        report = generate_vram_report(profiles)
        
        assert len(report["recommendations"]) > 0
        assert any("INT8" in r or "optimization" in r for r in report["recommendations"])
