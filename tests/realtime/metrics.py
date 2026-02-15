"""
Metrics Collection System for Spatial Perception Pipeline
==========================================================

Collects, aggregates, and reports performance and accuracy metrics
for the spatial perception pipeline.

Usage:
    from tests.realtime.metrics import MetricsCollector, MetricsReporter
    
    collector = MetricsCollector()
    collector.record_frame(latency_ms, detections, navigation_cue)
    
    reporter = MetricsReporter(collector)
    reporter.print_summary()
    reporter.export_json("metrics.json")

Author: Ally Vision Team
"""

import json
import logging
import statistics
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from collections import deque

logger = logging.getLogger("metrics")


# =============================================================================
# METRIC THRESHOLDS
# =============================================================================

@dataclass
class PerformanceThresholds:
    """Thresholds for pass/fail determination"""
    # Latency thresholds (milliseconds)
    latency_target_ms: float = 500.0
    latency_warning_ms: float = 800.0
    latency_critical_ms: float = 1000.0
    
    # FPS thresholds
    fps_target: float = 15.0
    fps_warning: float = 10.0
    fps_critical: float = 5.0
    
    # Memory thresholds (MB)
    memory_warning_mb: float = 500.0
    memory_critical_mb: float = 1000.0
    
    # Stability thresholds
    max_cue_changes_per_second: float = 2.0
    max_consecutive_failures: int = 3
    
    # Accuracy thresholds
    min_detection_confidence: float = 0.5
    max_distance_error_m: float = 1.0


DEFAULT_THRESHOLDS = PerformanceThresholds()


# =============================================================================
# METRIC DATA STRUCTURES
# =============================================================================

@dataclass
class FrameMetrics:
    """Metrics for a single frame"""
    timestamp: float
    latency_ms: float
    fps: float
    detection_count: int
    critical_detected: bool
    navigation_cue: str
    memory_mb: float = 0.0
    
    def is_latency_ok(self, threshold: float = 500.0) -> bool:
        return self.latency_ms <= threshold


@dataclass
class WindowMetrics:
    """Aggregated metrics over a time window"""
    window_start: float
    window_end: float
    frame_count: int
    
    # Latency stats
    latency_mean: float
    latency_std: float
    latency_min: float
    latency_max: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    
    # FPS stats
    fps_mean: float
    fps_min: float
    
    # Detection stats
    detection_mean: float
    critical_frame_count: int
    
    # Stability
    cue_changes: int
    cue_changes_per_second: float
    
    # Pass/fail
    meets_latency_target: bool
    meets_fps_target: bool


@dataclass
class SessionMetrics:
    """Complete session metrics"""
    session_id: str
    start_time: str
    end_time: str = ""
    duration_seconds: float = 0.0
    
    # Frame counts
    total_frames: int = 0
    dropped_frames: int = 0
    error_frames: int = 0
    
    # Performance
    latency_mean: float = 0.0
    latency_p95: float = 0.0
    fps_mean: float = 0.0
    
    # Detection
    total_detections: int = 0
    critical_frames: int = 0
    
    # Stability
    cue_changes: int = 0
    max_consecutive_high_latency: int = 0
    
    # Quality
    meets_targets: bool = False
    quality_score: float = 0.0  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# METRICS COLLECTOR
# =============================================================================

class MetricsCollector:
    """
    Collects and aggregates metrics in real-time.
    
    Features:
    - Rolling window statistics
    - Threshold monitoring
    - Alert callbacks
    - Efficient memory usage
    """
    
    def __init__(
        self,
        window_size: int = 100,
        thresholds: Optional[PerformanceThresholds] = None
    ):
        self.window_size = window_size
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        
        # Rolling windows
        self._latencies: deque = deque(maxlen=window_size)
        self._fps_values: deque = deque(maxlen=window_size)
        self._detection_counts: deque = deque(maxlen=window_size)
        self._timestamps: deque = deque(maxlen=window_size)
        self._cues: deque = deque(maxlen=window_size)
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()
        self.frame_count = 0
        self.error_count = 0
        self.total_detections = 0
        self.critical_count = 0
        self.cue_changes = 0
        self._last_cue = ""
        self._consecutive_high_latency = 0
        self._max_consecutive_high_latency = 0
        
        # Callbacks
        self._alert_callbacks: List[Callable] = []
        
        # Full history (optional, for analysis)
        self._full_history: List[FrameMetrics] = []
        self.keep_full_history = False
    
    def record_frame(
        self,
        latency_ms: float,
        fps: float,
        detection_count: int,
        critical_detected: bool,
        navigation_cue: str,
        memory_mb: float = 0.0
    ):
        """Record metrics for a single frame"""
        self.frame_count += 1
        timestamp = time.time()
        
        # Update rolling windows
        self._latencies.append(latency_ms)
        self._fps_values.append(fps)
        self._detection_counts.append(detection_count)
        self._timestamps.append(timestamp)
        self._cues.append(navigation_cue)
        
        # Track totals
        self.total_detections += detection_count
        if critical_detected:
            self.critical_count += 1
        
        # Track cue changes
        if navigation_cue != self._last_cue:
            self.cue_changes += 1
            self._last_cue = navigation_cue
        
        # Track consecutive high latency
        if latency_ms > self.thresholds.latency_target_ms:
            self._consecutive_high_latency += 1
            self._max_consecutive_high_latency = max(
                self._max_consecutive_high_latency,
                self._consecutive_high_latency
            )
        else:
            self._consecutive_high_latency = 0
        
        # Check for alerts
        self._check_alerts(latency_ms, fps, memory_mb)
        
        # Store full history if enabled
        if self.keep_full_history:
            metrics = FrameMetrics(
                timestamp=timestamp,
                latency_ms=latency_ms,
                fps=fps,
                detection_count=detection_count,
                critical_detected=critical_detected,
                navigation_cue=navigation_cue,
                memory_mb=memory_mb
            )
            self._full_history.append(metrics)
    
    def record_error(self):
        """Record a frame processing error"""
        self.error_count += 1
        self._check_alerts(0, 0, 0, is_error=True)
    
    def _check_alerts(
        self,
        latency_ms: float,
        fps: float,
        memory_mb: float,
        is_error: bool = False
    ):
        """Check thresholds and trigger alerts"""
        alerts = []
        
        if is_error:
            alerts.append(("ERROR", "Frame processing error"))
        
        if latency_ms > self.thresholds.latency_critical_ms:
            alerts.append(("CRITICAL", f"Latency {latency_ms:.0f}ms exceeds critical threshold"))
        elif latency_ms > self.thresholds.latency_warning_ms:
            alerts.append(("WARNING", f"Latency {latency_ms:.0f}ms exceeds warning threshold"))
        
        if fps < self.thresholds.fps_critical:
            alerts.append(("CRITICAL", f"FPS {fps:.1f} below critical threshold"))
        elif fps < self.thresholds.fps_warning:
            alerts.append(("WARNING", f"FPS {fps:.1f} below warning threshold"))
        
        if memory_mb > self.thresholds.memory_critical_mb:
            alerts.append(("CRITICAL", f"Memory {memory_mb:.0f}MB exceeds critical threshold"))
        elif memory_mb > self.thresholds.memory_warning_mb:
            alerts.append(("WARNING", f"Memory {memory_mb:.0f}MB exceeds warning threshold"))
        
        if self._consecutive_high_latency >= self.thresholds.max_consecutive_failures:
            alerts.append(("CRITICAL", f"{self._consecutive_high_latency} consecutive high-latency frames"))
        
        # Trigger callbacks
        for alert in alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alert[0], alert[1])
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
    
    def add_alert_callback(self, callback: Callable[[str, str], None]):
        """Add alert callback function(severity, message)"""
        self._alert_callbacks.append(callback)
    
    def get_window_metrics(self) -> Optional[WindowMetrics]:
        """Get aggregated metrics for current window"""
        if len(self._latencies) < 2:
            return None
        
        latencies = list(self._latencies)
        fps_values = list(self._fps_values)
        detection_counts = list(self._detection_counts)
        timestamps = list(self._timestamps)
        cues = list(self._cues)
        
        # Calculate latency stats
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        
        # Count cue changes in window
        window_cue_changes = sum(1 for i in range(1, len(cues)) if cues[i] != cues[i-1])
        window_duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 1
        
        return WindowMetrics(
            window_start=timestamps[0],
            window_end=timestamps[-1],
            frame_count=len(latencies),
            latency_mean=statistics.mean(latencies),
            latency_std=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            latency_min=min(latencies),
            latency_max=max(latencies),
            latency_p50=sorted_latencies[n // 2],
            latency_p95=sorted_latencies[int(n * 0.95)],
            latency_p99=sorted_latencies[int(n * 0.99)],
            fps_mean=statistics.mean(fps_values),
            fps_min=min(fps_values),
            detection_mean=statistics.mean(detection_counts),
            critical_frame_count=self.critical_count,
            cue_changes=window_cue_changes,
            cue_changes_per_second=window_cue_changes / window_duration if window_duration > 0 else 0,
            meets_latency_target=statistics.mean(latencies) <= self.thresholds.latency_target_ms,
            meets_fps_target=statistics.mean(fps_values) >= self.thresholds.fps_target
        )
    
    def get_session_metrics(self) -> SessionMetrics:
        """Get complete session metrics"""
        latencies = list(self._latencies)
        fps_values = list(self._fps_values)
        
        duration = time.time() - self.start_time
        
        # Calculate quality score (0-100)
        quality = 100.0
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            if avg_latency > self.thresholds.latency_target_ms:
                quality -= min(30, (avg_latency - self.thresholds.latency_target_ms) / 10)
        
        if fps_values:
            avg_fps = statistics.mean(fps_values)
            if avg_fps < self.thresholds.fps_target:
                quality -= min(30, (self.thresholds.fps_target - avg_fps) * 2)
        
        if self.error_count > 0:
            quality -= min(20, self.error_count * 2)
        
        quality = max(0, quality)
        
        sorted_latencies = sorted(latencies) if latencies else [0]
        
        return SessionMetrics(
            session_id=self.session_id,
            start_time=datetime.fromtimestamp(self.start_time).isoformat(),
            end_time=datetime.now().isoformat(),
            duration_seconds=duration,
            total_frames=self.frame_count,
            dropped_frames=0,
            error_frames=self.error_count,
            latency_mean=statistics.mean(latencies) if latencies else 0,
            latency_p95=sorted_latencies[int(len(sorted_latencies) * 0.95)] if latencies else 0,
            fps_mean=statistics.mean(fps_values) if fps_values else 0,
            total_detections=self.total_detections,
            critical_frames=self.critical_count,
            cue_changes=self.cue_changes,
            max_consecutive_high_latency=self._max_consecutive_high_latency,
            meets_targets=(
                (statistics.mean(latencies) <= self.thresholds.latency_target_ms if latencies else True) and
                (statistics.mean(fps_values) >= self.thresholds.fps_target if fps_values else True)
            ),
            quality_score=quality
        )
    
    def reset(self):
        """Reset all metrics"""
        self._latencies.clear()
        self._fps_values.clear()
        self._detection_counts.clear()
        self._timestamps.clear()
        self._cues.clear()
        self._full_history.clear()
        
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = time.time()
        self.frame_count = 0
        self.error_count = 0
        self.total_detections = 0
        self.critical_count = 0
        self.cue_changes = 0
        self._last_cue = ""
        self._consecutive_high_latency = 0
        self._max_consecutive_high_latency = 0


# =============================================================================
# METRICS REPORTER
# =============================================================================

class MetricsReporter:
    """
    Reports and exports collected metrics.
    
    Features:
    - Console output formatting
    - JSON export
    - CSV export
    - HTML report generation
    """
    
    def __init__(self, collector: MetricsCollector):
        self.collector = collector
    
    def print_summary(self):
        """Print summary to console"""
        metrics = self.collector.get_session_metrics()
        window = self.collector.get_window_metrics()
        
        print("\n" + "=" * 60)
        print("METRICS SUMMARY")
        print("=" * 60)
        
        print(f"\nSession: {metrics.session_id}")
        print(f"Duration: {metrics.duration_seconds:.1f} seconds")
        print(f"Frames: {metrics.total_frames}")
        
        print(f"\nPerformance:")
        print(f"  Avg Latency: {metrics.latency_mean:.1f} ms")
        print(f"  P95 Latency: {metrics.latency_p95:.1f} ms")
        print(f"  Avg FPS: {metrics.fps_mean:.1f}")
        
        if window:
            print(f"\nRecent Window ({window.frame_count} frames):")
            print(f"  Latency: {window.latency_mean:.1f} ± {window.latency_std:.1f} ms")
            print(f"  FPS: {window.fps_mean:.1f}")
            print(f"  Cue changes/sec: {window.cue_changes_per_second:.2f}")
        
        print(f"\nDetection:")
        print(f"  Total detections: {metrics.total_detections}")
        print(f"  Critical frames: {metrics.critical_frames}")
        
        print(f"\nQuality:")
        print(f"  Score: {metrics.quality_score:.0f}/100")
        print(f"  Meets targets: {'✓ YES' if metrics.meets_targets else '✗ NO'}")
        
        print("=" * 60)
    
    def print_realtime(self):
        """Print single-line realtime status"""
        window = self.collector.get_window_metrics()
        if not window:
            return
        
        status = "✓" if window.meets_latency_target and window.meets_fps_target else "✗"
        print(f"\r[{status}] FPS: {window.fps_mean:.1f} | "
              f"Latency: {window.latency_mean:.0f}ms | "
              f"Frames: {self.collector.frame_count}", end="")
    
    def export_json(self, filepath: str):
        """Export metrics to JSON"""
        metrics = self.collector.get_session_metrics()
        
        data = {
            "session": metrics.to_dict(),
            "thresholds": asdict(self.collector.thresholds)
        }
        
        # Include window metrics
        window = self.collector.get_window_metrics()
        if window:
            data["window"] = asdict(window)
        
        # Include full history if available
        if self.collector.keep_full_history:
            data["history"] = [asdict(f) for f in self.collector._full_history]
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Metrics exported to: {filepath}")
    
    def export_csv(self, filepath: str):
        """Export frame history to CSV"""
        if not self.collector.keep_full_history:
            logger.warning("Full history not enabled - no data to export")
            return
        
        import csv
        
        with open(filepath, "w", newline="") as f:
            if self.collector._full_history:
                fieldnames = list(asdict(self.collector._full_history[0]).keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for frame in self.collector._full_history:
                    writer.writerow(asdict(frame))
        
        logger.info(f"History exported to: {filepath}")
    
    def generate_html_report(self, filepath: str):
        """Generate HTML report"""
        metrics = self.collector.get_session_metrics()
        window = self.collector.get_window_metrics()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Metrics Report - {metrics.session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .metric {{ 
            display: inline-block; 
            background: #f5f5f5; 
            padding: 20px; 
            margin: 10px;
            border-radius: 8px;
            min-width: 150px;
        }}
        .metric-value {{ font-size: 32px; font-weight: bold; }}
        .metric-label {{ color: #666; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        table {{ border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Spatial Perception Metrics Report</h1>
    <p>Session: {metrics.session_id}</p>
    <p>Duration: {metrics.duration_seconds:.1f} seconds</p>
    
    <h2>Key Metrics</h2>
    <div class="metric">
        <div class="metric-value">{metrics.latency_mean:.0f}ms</div>
        <div class="metric-label">Avg Latency</div>
    </div>
    <div class="metric">
        <div class="metric-value">{metrics.fps_mean:.1f}</div>
        <div class="metric-label">Avg FPS</div>
    </div>
    <div class="metric">
        <div class="metric-value">{metrics.total_frames}</div>
        <div class="metric-label">Total Frames</div>
    </div>
    <div class="metric">
        <div class="metric-value">{metrics.quality_score:.0f}</div>
        <div class="metric-label">Quality Score</div>
    </div>
    
    <h2>Performance</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr>
        <tr>
            <td>Average Latency</td>
            <td>{metrics.latency_mean:.1f} ms</td>
            <td>< {self.collector.thresholds.latency_target_ms} ms</td>
            <td class="{'pass' if metrics.latency_mean <= self.collector.thresholds.latency_target_ms else 'fail'}">
                {'PASS' if metrics.latency_mean <= self.collector.thresholds.latency_target_ms else 'FAIL'}
            </td>
        </tr>
        <tr>
            <td>Average FPS</td>
            <td>{metrics.fps_mean:.1f}</td>
            <td>>= {self.collector.thresholds.fps_target}</td>
            <td class="{'pass' if metrics.fps_mean >= self.collector.thresholds.fps_target else 'fail'}">
                {'PASS' if metrics.fps_mean >= self.collector.thresholds.fps_target else 'FAIL'}
            </td>
        </tr>
    </table>
    
    <h2>Detection Stats</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Total Detections</td><td>{metrics.total_detections}</td></tr>
        <tr><td>Critical Frames</td><td>{metrics.critical_frames}</td></tr>
        <tr><td>Cue Changes</td><td>{metrics.cue_changes}</td></tr>
    </table>
    
    <p><em>Generated: {datetime.now().isoformat()}</em></p>
</body>
</html>
"""
        
        with open(filepath, "w") as f:
            f.write(html)
        
        logger.info(f"Report generated: {filepath}")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_default_collector() -> MetricsCollector:
    """Create a metrics collector with default settings"""
    return MetricsCollector(window_size=100, thresholds=DEFAULT_THRESHOLDS)


def quick_benchmark(frames: int = 100) -> SessionMetrics:
    """Run a quick benchmark and return metrics"""
    collector = MetricsCollector()
    
    import random
    
    for i in range(frames):
        latency = random.uniform(30, 100)
        fps = 1000 / latency
        detections = random.randint(0, 5)
        critical = random.random() < 0.1
        cue = random.choice(["Clear path", "Person ahead", "Chair on left"])
        
        collector.record_frame(latency, fps, detections, critical, cue)
    
    return collector.get_session_metrics()


if __name__ == "__main__":
    # Demo
    collector = MetricsCollector()
    collector.keep_full_history = True
    
    # Add some demo data
    import random
    
    for i in range(200):
        latency = random.uniform(30, 80) + (20 if random.random() < 0.1 else 0)
        fps = 1000 / latency
        detections = random.randint(0, 4)
        critical = random.random() < 0.05
        cue = random.choice(["Clear path ahead", "Person 2 meters", "Chair on right"])
        
        collector.record_frame(latency, fps, detections, critical, cue)
    
    reporter = MetricsReporter(collector)
    reporter.print_summary()
    reporter.export_json("demo_metrics.json")
    reporter.generate_html_report("demo_report.html")
