"""VRAM profiling utilities for GPU memory analysis.

Provides tools for measuring GPU VRAM usage across different components
of the Voice-Vision Assistant pipeline.

Usage:
    from shared.utils.vram_profiler import VRAMProfiler, get_vram_profiler
    
    profiler = get_vram_profiler()
    
    with profiler.track("model_loading"):
        model = load_model()
    
    profiler.print_summary()
"""

from __future__ import annotations

import gc
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("vram-profiler")


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class VRAMSnapshot:
    """Single VRAM measurement snapshot."""
    timestamp: float
    allocated_mb: float
    reserved_mb: float
    peak_mb: float
    label: str = ""
    
    def __str__(self) -> str:
        return f"{self.label}: {self.allocated_mb:.1f}MB allocated, {self.peak_mb:.1f}MB peak"


@dataclass
class VRAMProfile:
    """VRAM profile for a tracked operation."""
    name: str
    start_allocated_mb: float = 0.0
    end_allocated_mb: float = 0.0
    peak_allocated_mb: float = 0.0
    start_reserved_mb: float = 0.0
    end_reserved_mb: float = 0.0
    duration_ms: float = 0.0
    
    @property
    def delta_allocated_mb(self) -> float:
        """Change in allocated VRAM."""
        return self.end_allocated_mb - self.start_allocated_mb
    
    @property
    def delta_reserved_mb(self) -> float:
        """Change in reserved VRAM."""
        return self.end_reserved_mb - self.start_reserved_mb
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_allocated_mb": round(self.start_allocated_mb, 2),
            "end_allocated_mb": round(self.end_allocated_mb, 2),
            "peak_allocated_mb": round(self.peak_allocated_mb, 2),
            "delta_allocated_mb": round(self.delta_allocated_mb, 2),
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class ComponentVRAMUsage:
    """VRAM usage summary for a component."""
    component: str
    idle_mb: float
    active_mb: float
    peak_mb: float
    samples: int = 1
    
    @property
    def average_mb(self) -> float:
        return (self.idle_mb + self.active_mb) / 2
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "idle_mb": round(self.idle_mb, 2),
            "active_mb": round(self.active_mb, 2),
            "peak_mb": round(self.peak_mb, 2),
            "samples": self.samples,
        }


# ---------------------------------------------------------------------------
# VRAM Detection
# ---------------------------------------------------------------------------

def is_cuda_available() -> bool:
    """Check if CUDA is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_cuda_device_info() -> Optional[Dict[str, Any]]:
    """Get CUDA device information."""
    if not is_cuda_available():
        return None
    
    try:
        import torch
        device = torch.cuda.current_device()
        props = torch.cuda.get_device_properties(device)
        return {
            "name": props.name,
            "total_memory_mb": props.total_memory / (1024 * 1024),
            "compute_capability": f"{props.major}.{props.minor}",
            "multi_processor_count": props.multi_processor_count,
        }
    except Exception as e:
        logger.warning(f"Failed to get CUDA device info: {e}")
        return None


def get_current_vram_usage() -> Tuple[float, float, float]:
    """Get current VRAM usage (allocated, reserved, peak) in MB.
    
    Returns (0, 0, 0) if CUDA is not available.
    """
    if not is_cuda_available():
        return (0.0, 0.0, 0.0)
    
    try:
        import torch
        allocated = torch.cuda.memory_allocated() / (1024 * 1024)
        reserved = torch.cuda.memory_reserved() / (1024 * 1024)
        peak = torch.cuda.max_memory_allocated() / (1024 * 1024)
        return (allocated, reserved, peak)
    except Exception:
        return (0.0, 0.0, 0.0)


def reset_peak_vram_stats():
    """Reset peak memory statistics."""
    if is_cuda_available():
        try:
            import torch
            torch.cuda.reset_peak_memory_stats()
        except Exception:
            pass


def empty_cuda_cache():
    """Empty CUDA cache and run garbage collection."""
    gc.collect()
    if is_cuda_available():
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# VRAM Profiler
# ---------------------------------------------------------------------------

class VRAMProfiler:
    """Profiles VRAM usage across components and operations."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled and is_cuda_available()
        self.profiles: Dict[str, List[VRAMProfile]] = {}
        self.snapshots: List[VRAMSnapshot] = []
        self.component_usage: Dict[str, ComponentVRAMUsage] = {}
        self._device_info = get_cuda_device_info() if self.enabled else None
    
    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._device_info
    
    @property
    def total_vram_mb(self) -> float:
        """Total VRAM available on the device."""
        if self._device_info:
            return self._device_info.get("total_memory_mb", 0.0)
        return 0.0
    
    def take_snapshot(self, label: str = "") -> VRAMSnapshot:
        """Take a VRAM snapshot."""
        allocated, reserved, peak = get_current_vram_usage()
        snapshot = VRAMSnapshot(
            timestamp=time.time(),
            allocated_mb=allocated,
            reserved_mb=reserved,
            peak_mb=peak,
            label=label,
        )
        self.snapshots.append(snapshot)
        return snapshot
    
    @contextmanager
    def track(self, name: str):
        """Context manager to track VRAM usage for an operation."""
        if not self.enabled:
            yield
            return
        
        # Prepare for measurement
        empty_cuda_cache()
        reset_peak_vram_stats()
        
        # Capture start state
        start_allocated, start_reserved, _ = get_current_vram_usage()
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            # Capture end state
            end_time = time.perf_counter()
            end_allocated, end_reserved, peak = get_current_vram_usage()
            
            # Create profile
            profile = VRAMProfile(
                name=name,
                start_allocated_mb=start_allocated,
                end_allocated_mb=end_allocated,
                peak_allocated_mb=peak,
                start_reserved_mb=start_reserved,
                end_reserved_mb=end_reserved,
                duration_ms=(end_time - start_time) * 1000,
            )
            
            # Store profile
            if name not in self.profiles:
                self.profiles[name] = []
            self.profiles[name].append(profile)
            
            # Log
            logger.info(
                f"[VRAM] {name}: {profile.delta_allocated_mb:+.1f}MB "
                f"(peak: {profile.peak_allocated_mb:.1f}MB, "
                f"time: {profile.duration_ms:.1f}ms)"
            )
    
    def register_component(
        self,
        component: str,
        idle_mb: float,
        active_mb: float,
        peak_mb: float,
    ):
        """Register VRAM usage for a component."""
        self.component_usage[component] = ComponentVRAMUsage(
            component=component,
            idle_mb=idle_mb,
            active_mb=active_mb,
            peak_mb=peak_mb,
        )
    
    def get_profile_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a profiled operation."""
        if name not in self.profiles:
            return None
        
        profiles = self.profiles[name]
        if not profiles:
            return None
        
        deltas = [p.delta_allocated_mb for p in profiles]
        peaks = [p.peak_allocated_mb for p in profiles]
        durations = [p.duration_ms for p in profiles]
        
        return {
            "name": name,
            "count": len(profiles),
            "avg_delta_mb": sum(deltas) / len(deltas),
            "max_delta_mb": max(deltas),
            "avg_peak_mb": sum(peaks) / len(peaks),
            "max_peak_mb": max(peaks),
            "avg_duration_ms": sum(durations) / len(durations),
        }
    
    def get_top_consumers(self, n: int = 5) -> List[Tuple[str, float]]:
        """Get top N VRAM consumers by peak usage."""
        consumers = []
        
        for name, profiles in self.profiles.items():
            if profiles:
                max_peak = max(p.peak_allocated_mb for p in profiles)
                consumers.append((name, max_peak))
        
        for name, usage in self.component_usage.items():
            consumers.append((name, usage.peak_mb))
        
        consumers.sort(key=lambda x: x[1], reverse=True)
        return consumers[:n]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete profiling summary."""
        return {
            "cuda_available": self.enabled,
            "device_info": self._device_info,
            "total_vram_mb": self.total_vram_mb,
            "current_usage": {
                "allocated_mb": get_current_vram_usage()[0],
                "reserved_mb": get_current_vram_usage()[1],
            },
            "profiles": {
                name: self.get_profile_stats(name)
                for name in self.profiles
            },
            "components": {
                name: usage.to_dict()
                for name, usage in self.component_usage.items()
            },
            "top_consumers": self.get_top_consumers(5),
        }
    
    def print_summary(self):
        """Print a formatted summary to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("VRAM PROFILING SUMMARY")
        print("=" * 60)
        
        if not self.enabled:
            print("CUDA not available - no GPU profiling data")
            return
        
        if self._device_info:
            print(f"Device: {self._device_info['name']}")
            print(f"Total VRAM: {self.total_vram_mb:.0f} MB")
        
        allocated, reserved, _ = get_current_vram_usage()
        print(f"Current Usage: {allocated:.1f} MB allocated, {reserved:.1f} MB reserved")
        
        print("\n--- Profiled Operations ---")
        for name, stats in summary["profiles"].items():
            if stats:
                print(f"  {name}:")
                print(f"    Avg Delta: {stats['avg_delta_mb']:+.1f} MB")
                print(f"    Max Peak:  {stats['max_peak_mb']:.1f} MB")
                print(f"    Samples:   {stats['count']}")
        
        print("\n--- Top VRAM Consumers ---")
        for i, (name, peak_mb) in enumerate(summary["top_consumers"], 1):
            pct = (peak_mb / self.total_vram_mb * 100) if self.total_vram_mb > 0 else 0
            print(f"  {i}. {name}: {peak_mb:.1f} MB ({pct:.1f}%)")
        
        print("=" * 60)
    
    def reset(self):
        """Reset all profiling data."""
        self.profiles.clear()
        self.snapshots.clear()
        self.component_usage.clear()
        reset_peak_vram_stats()
        empty_cuda_cache()


# ---------------------------------------------------------------------------
# Global Profiler
# ---------------------------------------------------------------------------

_vram_profiler: Optional[VRAMProfiler] = None


def get_vram_profiler() -> VRAMProfiler:
    """Get the global VRAM profiler instance."""
    global _vram_profiler
    if _vram_profiler is None:
        _vram_profiler = VRAMProfiler()
    return _vram_profiler


def reset_vram_profiler():
    """Reset the global VRAM profiler."""
    global _vram_profiler
    if _vram_profiler:
        _vram_profiler.reset()
    _vram_profiler = None
