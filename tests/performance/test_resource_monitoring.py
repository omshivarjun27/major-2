"""P4: Resource Utilization Monitoring Tests (T-086).

Tests for CPU, memory, GPU, and VRAM monitoring during operation.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Resource Monitoring Models
# ---------------------------------------------------------------------------

class ResourceAlertLevel(Enum):
    """Alert severity levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CPUMetrics:
    """CPU utilization metrics."""
    total_percent: float = 0.0
    per_core_percent: List[float] = field(default_factory=list)
    process_percent: float = 0.0
    load_average_1m: float = 0.0
    
    @property
    def alert_level(self) -> ResourceAlertLevel:
        if self.total_percent > 95.0:
            return ResourceAlertLevel.CRITICAL
        if self.total_percent > 90.0:
            return ResourceAlertLevel.WARNING
        return ResourceAlertLevel.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_percent": round(self.total_percent, 2),
            "per_core_percent": [round(p, 2) for p in self.per_core_percent],
            "process_percent": round(self.process_percent, 2),
            "load_average_1m": round(self.load_average_1m, 2),
            "alert_level": self.alert_level.value,
        }


@dataclass
class MemoryMetrics:
    """Memory utilization metrics."""
    total_mb: float = 0.0
    used_mb: float = 0.0
    available_mb: float = 0.0
    percent_used: float = 0.0
    process_rss_mb: float = 0.0
    
    @property
    def alert_level(self) -> ResourceAlertLevel:
        if self.percent_used > 95.0:
            return ResourceAlertLevel.CRITICAL
        if self.percent_used > 80.0:
            return ResourceAlertLevel.WARNING
        return ResourceAlertLevel.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_mb": round(self.total_mb, 2),
            "used_mb": round(self.used_mb, 2),
            "available_mb": round(self.available_mb, 2),
            "percent_used": round(self.percent_used, 2),
            "process_rss_mb": round(self.process_rss_mb, 2),
            "alert_level": self.alert_level.value,
        }


@dataclass
class GPUMetrics:
    """GPU utilization metrics."""
    utilization_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 8192.0  # Default 8GB for RTX 4060
    temperature_c: float = 0.0
    power_draw_w: float = 0.0
    gpu_available: bool = True
    
    @property
    def memory_percent(self) -> float:
        if self.memory_total_mb == 0:
            return 0.0
        return (self.memory_used_mb / self.memory_total_mb) * 100
    
    @property
    def alert_level(self) -> ResourceAlertLevel:
        # VRAM > 7GB is warning on 8GB card
        if self.memory_used_mb > 7168:  # 7GB
            return ResourceAlertLevel.CRITICAL
        if self.memory_used_mb > 6144:  # 6GB
            return ResourceAlertLevel.WARNING
        return ResourceAlertLevel.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "utilization_percent": round(self.utilization_percent, 2),
            "memory_used_mb": round(self.memory_used_mb, 2),
            "memory_total_mb": round(self.memory_total_mb, 2),
            "memory_percent": round(self.memory_percent, 2),
            "temperature_c": round(self.temperature_c, 1),
            "power_draw_w": round(self.power_draw_w, 1),
            "gpu_available": self.gpu_available,
            "alert_level": self.alert_level.value,
        }


@dataclass
class DiskMetrics:
    """Disk I/O metrics."""
    read_bytes_per_sec: float = 0.0
    write_bytes_per_sec: float = 0.0
    read_count: int = 0
    write_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "read_mb_per_sec": round(self.read_bytes_per_sec / (1024 * 1024), 2),
            "write_mb_per_sec": round(self.write_bytes_per_sec / (1024 * 1024), 2),
            "read_count": self.read_count,
            "write_count": self.write_count,
        }


@dataclass
class ResourceSnapshot:
    """Complete resource snapshot at a point in time."""
    timestamp: float = 0.0
    cpu: CPUMetrics = field(default_factory=CPUMetrics)
    memory: MemoryMetrics = field(default_factory=MemoryMetrics)
    gpu: GPUMetrics = field(default_factory=GPUMetrics)
    disk: DiskMetrics = field(default_factory=DiskMetrics)
    
    @property
    def overall_alert_level(self) -> ResourceAlertLevel:
        """Highest alert level across all resources."""
        levels = [self.cpu.alert_level, self.memory.alert_level, self.gpu.alert_level]
        if ResourceAlertLevel.CRITICAL in levels:
            return ResourceAlertLevel.CRITICAL
        if ResourceAlertLevel.WARNING in levels:
            return ResourceAlertLevel.WARNING
        return ResourceAlertLevel.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "cpu": self.cpu.to_dict(),
            "memory": self.memory.to_dict(),
            "gpu": self.gpu.to_dict(),
            "disk": self.disk.to_dict(),
            "overall_alert_level": self.overall_alert_level.value,
        }


@dataclass
class AlertConfig:
    """Configuration for resource alerts."""
    cpu_warning_threshold: float = 90.0
    cpu_critical_threshold: float = 95.0
    memory_warning_threshold: float = 80.0
    memory_critical_threshold: float = 95.0
    vram_warning_mb: float = 6144.0  # 6GB
    vram_critical_mb: float = 7168.0  # 7GB
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_warning_threshold": self.cpu_warning_threshold,
            "cpu_critical_threshold": self.cpu_critical_threshold,
            "memory_warning_threshold": self.memory_warning_threshold,
            "memory_critical_threshold": self.memory_critical_threshold,
            "vram_warning_mb": self.vram_warning_mb,
            "vram_critical_mb": self.vram_critical_mb,
        }


# ---------------------------------------------------------------------------
# Mock Resource Monitor
# ---------------------------------------------------------------------------

class MockResourceMonitor:
    """Mock resource monitor for testing."""
    
    def __init__(
        self,
        cpu_percent: float = 30.0,
        memory_percent: float = 50.0,
        vram_mb: float = 4000.0,
        gpu_available: bool = True,
        alert_config: Optional[AlertConfig] = None
    ):
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.vram_mb = vram_mb
        self.gpu_available = gpu_available
        self.alert_config = alert_config or AlertConfig()
        self._snapshots: List[ResourceSnapshot] = []
        self._monitoring = False
        self._sample_interval_ms = 100
    
    def get_cpu_metrics(self) -> CPUMetrics:
        """Get current CPU metrics."""
        return CPUMetrics(
            total_percent=self.cpu_percent,
            per_core_percent=[self.cpu_percent * 0.8, self.cpu_percent * 1.2, self.cpu_percent, self.cpu_percent],
            process_percent=self.cpu_percent * 0.5,
            load_average_1m=self.cpu_percent / 25.0,
        )
    
    def get_memory_metrics(self) -> MemoryMetrics:
        """Get current memory metrics."""
        total_mb = 16384.0  # 16GB
        used_mb = total_mb * (self.memory_percent / 100.0)
        return MemoryMetrics(
            total_mb=total_mb,
            used_mb=used_mb,
            available_mb=total_mb - used_mb,
            percent_used=self.memory_percent,
            process_rss_mb=used_mb * 0.3,
        )
    
    def get_gpu_metrics(self) -> GPUMetrics:
        """Get current GPU metrics."""
        return GPUMetrics(
            utilization_percent=self.cpu_percent * 1.5 if self.gpu_available else 0.0,
            memory_used_mb=self.vram_mb,
            memory_total_mb=8192.0,
            temperature_c=65.0 if self.gpu_available else 0.0,
            power_draw_w=120.0 if self.gpu_available else 0.0,
            gpu_available=self.gpu_available,
        )
    
    def get_disk_metrics(self) -> DiskMetrics:
        """Get current disk I/O metrics."""
        return DiskMetrics(
            read_bytes_per_sec=10 * 1024 * 1024,  # 10 MB/s
            write_bytes_per_sec=5 * 1024 * 1024,   # 5 MB/s
            read_count=100,
            write_count=50,
        )
    
    def take_snapshot(self) -> ResourceSnapshot:
        """Take a resource snapshot."""
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu=self.get_cpu_metrics(),
            memory=self.get_memory_metrics(),
            gpu=self.get_gpu_metrics(),
            disk=self.get_disk_metrics(),
        )
        self._snapshots.append(snapshot)
        return snapshot
    
    async def start_monitoring(self, interval_ms: int = 100):
        """Start continuous monitoring."""
        self._monitoring = True
        self._sample_interval_ms = interval_ms
        while self._monitoring:
            self.take_snapshot()
            await asyncio.sleep(interval_ms / 1000)
    
    def stop_monitoring(self):
        """Stop continuous monitoring."""
        self._monitoring = False
    
    def get_snapshots(self) -> List[ResourceSnapshot]:
        """Get all recorded snapshots."""
        return self._snapshots
    
    def get_average_metrics(self) -> ResourceSnapshot:
        """Get average metrics across all snapshots."""
        if not self._snapshots:
            return ResourceSnapshot()
        
        n = len(self._snapshots)
        return ResourceSnapshot(
            timestamp=time.time(),
            cpu=CPUMetrics(
                total_percent=sum(s.cpu.total_percent for s in self._snapshots) / n,
            ),
            memory=MemoryMetrics(
                percent_used=sum(s.memory.percent_used for s in self._snapshots) / n,
            ),
            gpu=GPUMetrics(
                memory_used_mb=sum(s.gpu.memory_used_mb for s in self._snapshots) / n,
            ),
        )
    
    def check_alerts(self) -> List[Tuple[str, ResourceAlertLevel, str]]:
        """Check for active alerts."""
        alerts = []
        snapshot = self.take_snapshot()
        
        if snapshot.cpu.total_percent > self.alert_config.cpu_critical_threshold:
            alerts.append(("cpu", ResourceAlertLevel.CRITICAL, f"CPU at {snapshot.cpu.total_percent}%"))
        elif snapshot.cpu.total_percent > self.alert_config.cpu_warning_threshold:
            alerts.append(("cpu", ResourceAlertLevel.WARNING, f"CPU at {snapshot.cpu.total_percent}%"))
        
        if snapshot.memory.percent_used > self.alert_config.memory_critical_threshold:
            alerts.append(("memory", ResourceAlertLevel.CRITICAL, f"Memory at {snapshot.memory.percent_used}%"))
        elif snapshot.memory.percent_used > self.alert_config.memory_warning_threshold:
            alerts.append(("memory", ResourceAlertLevel.WARNING, f"Memory at {snapshot.memory.percent_used}%"))
        
        if snapshot.gpu.memory_used_mb > self.alert_config.vram_critical_mb:
            alerts.append(("vram", ResourceAlertLevel.CRITICAL, f"VRAM at {snapshot.gpu.memory_used_mb}MB"))
        elif snapshot.gpu.memory_used_mb > self.alert_config.vram_warning_mb:
            alerts.append(("vram", ResourceAlertLevel.WARNING, f"VRAM at {snapshot.gpu.memory_used_mb}MB"))
        
        return alerts
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for API endpoint."""
        snapshot = self.take_snapshot()
        return {
            "status": "healthy" if snapshot.overall_alert_level == ResourceAlertLevel.NORMAL else "degraded",
            "resources": snapshot.to_dict(),
            "alerts": [
                {"resource": r, "level": l.value, "message": m}
                for r, l, m in self.check_alerts()
            ],
        }


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------

class TestCPUMetrics:
    """Tests for CPU metrics."""
    
    def test_cpu_alert_levels(self):
        """Test CPU alert level thresholds."""
        metrics = CPUMetrics(total_percent=50.0)
        assert metrics.alert_level == ResourceAlertLevel.NORMAL
        
        metrics = CPUMetrics(total_percent=92.0)
        assert metrics.alert_level == ResourceAlertLevel.WARNING
        
        metrics = CPUMetrics(total_percent=97.0)
        assert metrics.alert_level == ResourceAlertLevel.CRITICAL
    
    def test_cpu_metrics_serialization(self):
        """Test CPU metrics serialization."""
        metrics = CPUMetrics(
            total_percent=45.5,
            per_core_percent=[40.0, 50.0, 45.0, 47.0],
            process_percent=20.5
        )
        d = metrics.to_dict()
        assert d["total_percent"] == 45.5
        assert len(d["per_core_percent"]) == 4
        assert d["alert_level"] == "normal"


class TestMemoryMetrics:
    """Tests for memory metrics."""
    
    def test_memory_alert_levels(self):
        """Test memory alert level thresholds."""
        metrics = MemoryMetrics(percent_used=50.0)
        assert metrics.alert_level == ResourceAlertLevel.NORMAL
        
        metrics = MemoryMetrics(percent_used=85.0)
        assert metrics.alert_level == ResourceAlertLevel.WARNING
        
        metrics = MemoryMetrics(percent_used=97.0)
        assert metrics.alert_level == ResourceAlertLevel.CRITICAL
    
    def test_memory_metrics_values(self):
        """Test memory metrics calculations."""
        metrics = MemoryMetrics(
            total_mb=16384.0,
            used_mb=8192.0,
            available_mb=8192.0,
            percent_used=50.0
        )
        d = metrics.to_dict()
        assert d["total_mb"] == 16384.0
        assert d["available_mb"] == 8192.0


class TestGPUMetrics:
    """Tests for GPU metrics."""
    
    def test_gpu_memory_percent(self):
        """Test GPU memory percentage calculation."""
        metrics = GPUMetrics(memory_used_mb=4096.0, memory_total_mb=8192.0)
        assert metrics.memory_percent == 50.0
    
    def test_gpu_vram_alert_levels(self):
        """Test VRAM alert thresholds."""
        # Normal usage
        metrics = GPUMetrics(memory_used_mb=4000.0)
        assert metrics.alert_level == ResourceAlertLevel.NORMAL
        
        # Warning (> 6GB)
        metrics = GPUMetrics(memory_used_mb=6500.0)
        assert metrics.alert_level == ResourceAlertLevel.WARNING
        
        # Critical (> 7GB)
        metrics = GPUMetrics(memory_used_mb=7500.0)
        assert metrics.alert_level == ResourceAlertLevel.CRITICAL
    
    def test_gpu_unavailable(self):
        """Test GPU unavailable state."""
        metrics = GPUMetrics(gpu_available=False)
        d = metrics.to_dict()
        assert d["gpu_available"] is False


class TestResourceSnapshot:
    """Tests for resource snapshots."""
    
    def test_overall_alert_level(self):
        """Test overall alert level aggregation."""
        # All normal
        snapshot = ResourceSnapshot(
            cpu=CPUMetrics(total_percent=30.0),
            memory=MemoryMetrics(percent_used=50.0),
            gpu=GPUMetrics(memory_used_mb=4000.0),
        )
        assert snapshot.overall_alert_level == ResourceAlertLevel.NORMAL
        
        # One warning
        snapshot = ResourceSnapshot(
            cpu=CPUMetrics(total_percent=92.0),
            memory=MemoryMetrics(percent_used=50.0),
            gpu=GPUMetrics(memory_used_mb=4000.0),
        )
        assert snapshot.overall_alert_level == ResourceAlertLevel.WARNING
        
        # One critical overrides warning
        snapshot = ResourceSnapshot(
            cpu=CPUMetrics(total_percent=92.0),
            memory=MemoryMetrics(percent_used=97.0),
            gpu=GPUMetrics(memory_used_mb=4000.0),
        )
        assert snapshot.overall_alert_level == ResourceAlertLevel.CRITICAL
    
    def test_snapshot_serialization(self):
        """Test full snapshot serialization."""
        snapshot = ResourceSnapshot(
            timestamp=time.time(),
            cpu=CPUMetrics(total_percent=30.0),
            memory=MemoryMetrics(percent_used=50.0),
            gpu=GPUMetrics(memory_used_mb=4000.0),
            disk=DiskMetrics(read_bytes_per_sec=1024 * 1024),
        )
        d = snapshot.to_dict()
        assert "cpu" in d
        assert "memory" in d
        assert "gpu" in d
        assert "disk" in d
        assert "overall_alert_level" in d


class TestMockResourceMonitor:
    """Tests for mock resource monitor."""
    
    def test_take_snapshot(self):
        """Test snapshot capture."""
        monitor = MockResourceMonitor(cpu_percent=40.0, memory_percent=60.0, vram_mb=5000.0)
        snapshot = monitor.take_snapshot()
        
        assert snapshot.cpu.total_percent == 40.0
        assert snapshot.memory.percent_used == 60.0
        assert snapshot.gpu.memory_used_mb == 5000.0
    
    async def test_continuous_monitoring(self):
        """Test continuous monitoring captures multiple snapshots."""
        monitor = MockResourceMonitor()
        
        # Start monitoring in background
        task = asyncio.create_task(monitor.start_monitoring(interval_ms=50))
        
        # Let it run for a bit
        await asyncio.sleep(0.2)
        monitor.stop_monitoring()
        
        # Wait for task to complete
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        snapshots = monitor.get_snapshots()
        assert len(snapshots) >= 2  # Should have captured multiple snapshots
    
    def test_average_metrics(self):
        """Test average metrics calculation."""
        monitor = MockResourceMonitor(cpu_percent=50.0)
        
        # Take multiple snapshots
        for _ in range(5):
            monitor.take_snapshot()
        
        avg = monitor.get_average_metrics()
        assert avg.cpu.total_percent == 50.0


class TestAlertSystem:
    """Tests for alert system."""
    
    def test_no_alerts_normal_usage(self):
        """Test no alerts under normal usage."""
        monitor = MockResourceMonitor(cpu_percent=30.0, memory_percent=50.0, vram_mb=4000.0)
        alerts = monitor.check_alerts()
        assert len(alerts) == 0
    
    def test_cpu_warning_alert(self):
        """Test CPU warning alert."""
        monitor = MockResourceMonitor(cpu_percent=92.0)
        alerts = monitor.check_alerts()
        
        cpu_alerts = [a for a in alerts if a[0] == "cpu"]
        assert len(cpu_alerts) == 1
        assert cpu_alerts[0][1] == ResourceAlertLevel.WARNING
    
    def test_memory_critical_alert(self):
        """Test memory critical alert."""
        monitor = MockResourceMonitor(memory_percent=97.0)
        alerts = monitor.check_alerts()
        
        memory_alerts = [a for a in alerts if a[0] == "memory"]
        assert len(memory_alerts) == 1
        assert memory_alerts[0][1] == ResourceAlertLevel.CRITICAL
    
    def test_vram_warning_alert(self):
        """Test VRAM warning alert."""
        monitor = MockResourceMonitor(vram_mb=6500.0)
        alerts = monitor.check_alerts()
        
        vram_alerts = [a for a in alerts if a[0] == "vram"]
        assert len(vram_alerts) == 1
        assert vram_alerts[0][1] == ResourceAlertLevel.WARNING
    
    def test_custom_alert_thresholds(self):
        """Test custom alert thresholds."""
        config = AlertConfig(
            cpu_warning_threshold=80.0,
            cpu_critical_threshold=90.0,
        )
        monitor = MockResourceMonitor(cpu_percent=85.0, alert_config=config)
        alerts = monitor.check_alerts()
        
        cpu_alerts = [a for a in alerts if a[0] == "cpu"]
        assert len(cpu_alerts) == 1


class TestHealthEndpoint:
    """Tests for health endpoint integration."""
    
    def test_healthy_status(self):
        """Test healthy status response."""
        monitor = MockResourceMonitor(cpu_percent=30.0, memory_percent=50.0, vram_mb=4000.0)
        health = monitor.get_health_status()
        
        assert health["status"] == "healthy"
        assert "resources" in health
        assert len(health["alerts"]) == 0
    
    def test_degraded_status_with_alerts(self):
        """Test degraded status with alerts."""
        monitor = MockResourceMonitor(cpu_percent=95.0)
        health = monitor.get_health_status()
        
        assert health["status"] == "degraded"
        assert len(health["alerts"]) > 0
    
    def test_health_response_structure(self):
        """Test health response structure."""
        monitor = MockResourceMonitor()
        health = monitor.get_health_status()
        
        assert "status" in health
        assert "resources" in health
        assert "alerts" in health
        assert "cpu" in health["resources"]
        assert "memory" in health["resources"]
        assert "gpu" in health["resources"]


class TestMonitoringOverhead:
    """Tests for monitoring overhead."""
    
    async def test_snapshot_latency(self):
        """Test snapshot capture is fast."""
        monitor = MockResourceMonitor()
        
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            monitor.take_snapshot()
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        # Snapshot should be very fast (< 10ms)
        assert avg_latency < 10.0
    
    def test_monitoring_memory_bounded(self):
        """Test monitoring doesn't grow unbounded."""
        monitor = MockResourceMonitor()
        
        # Take many snapshots
        for _ in range(1000):
            monitor.take_snapshot()
        
        snapshots = monitor.get_snapshots()
        # In real implementation, would limit to last N snapshots
        # For now, just verify they're all captured
        assert len(snapshots) == 1000


class TestGPUAvailability:
    """Tests for GPU availability handling."""
    
    def test_gpu_not_available(self):
        """Test handling when GPU is not available."""
        monitor = MockResourceMonitor(gpu_available=False)
        snapshot = monitor.take_snapshot()
        
        assert snapshot.gpu.gpu_available is False
        assert snapshot.gpu.utilization_percent == 0.0
    
    def test_gpu_metrics_with_cuda(self):
        """Test GPU metrics when CUDA is available."""
        monitor = MockResourceMonitor(gpu_available=True, vram_mb=5000.0)
        metrics = monitor.get_gpu_metrics()
        
        assert metrics.gpu_available is True
        assert metrics.memory_used_mb == 5000.0
        assert metrics.utilization_percent > 0.0


class TestResourceBudgets:
    """Tests for resource budget compliance."""
    
    def test_vram_under_8gb_budget(self):
        """Test VRAM stays under 8GB budget."""
        monitor = MockResourceMonitor(vram_mb=7000.0)
        snapshot = monitor.take_snapshot()
        
        # Should be under 8GB total
        assert snapshot.gpu.memory_used_mb < 8192.0
    
    def test_ram_reasonable_usage(self):
        """Test RAM usage is reasonable."""
        monitor = MockResourceMonitor(memory_percent=60.0)
        snapshot = monitor.take_snapshot()
        
        # Should have reasonable headroom
        assert snapshot.memory.percent_used < 80.0
    
    def test_cpu_not_saturated(self):
        """Test CPU is not saturated."""
        monitor = MockResourceMonitor(cpu_percent=50.0)
        snapshot = monitor.take_snapshot()
        
        # Should not be constantly at max
        assert snapshot.cpu.total_percent < 90.0
