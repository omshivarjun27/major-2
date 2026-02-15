"""
Real-Time Testing Framework for Spatial Perception Pipeline
============================================================

This package provides comprehensive tools for testing, benchmarking,
and validating the spatial perception pipeline in real-time scenarios.

Components:
-----------
- realtime_test.py   : Live camera testing with debug overlays
- benchmark.py       : Performance benchmarking across configurations
- session_logger.py  : Frame-by-frame telemetry logging
- replay_tool.py     : Offline session replay and analysis
- calibrate_depth.py : Depth estimation calibration tools
- metrics.py         : Metrics collection and reporting
- TEST_PLAN.md       : Staged testing methodology
- SAFETY_PROTOCOLS.md: Safety requirements and protocols

Usage:
------
    # Run real-time test with debug overlay
    python -m tests.realtime.realtime_test --debug
    
    # Run benchmarks
    python -m tests.realtime.benchmark --config yolo-simple
    
    # Replay a session
    python -m tests.realtime.replay_tool logs/sessions/SESSION_NAME

Quick Start:
------------
    from tests.realtime.metrics import MetricsCollector, MetricsReporter
    from tests.realtime.session_logger import SessionRecorder, SessionLoader
    from tests.realtime.benchmark import BenchmarkRunner, PRESET_CONFIGS
    
    # Collect metrics
    collector = MetricsCollector()
    collector.record_frame(latency_ms=45, fps=22, detection_count=3, 
                          critical_detected=False, navigation_cue="Clear path")
    
    # Generate report
    reporter = MetricsReporter(collector)
    reporter.print_summary()

Author: Ally Vision Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Ally Vision Team"

# Lazy imports for convenience
def get_metrics_collector():
    """Get a new MetricsCollector instance"""
    from .metrics import MetricsCollector
    return MetricsCollector()

def get_session_recorder(session_name=None):
    """Get a new SessionRecorder instance"""
    from .session_logger import SessionRecorder
    return SessionRecorder(session_name)

def get_benchmark_runner(**kwargs):
    """Get a new BenchmarkRunner instance"""
    from .benchmark import BenchmarkRunner
    return BenchmarkRunner(**kwargs)

__all__ = [
    "get_metrics_collector",
    "get_session_recorder", 
    "get_benchmark_runner",
]
