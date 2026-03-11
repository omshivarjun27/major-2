"""
Debug Tools — Cross-cutting Visualization & Session Logging
============================================================

Provides debug visualization tools and structured session logging
used across multiple architectural layers.

Canonical location: ``shared/debug/``
"""

from .session_logger import SessionEvent, SessionLogger
from .visualizer import (
    DebugVisualizer,
    DebugVisualizerResult,
    VisualizerConfig,
    annotate_image,
    render_debug_image,
)

__all__ = [
    "DebugVisualizer",
    "VisualizerConfig",
    "DebugVisualizerResult",
    "render_debug_image",
    "annotate_image",
    "SessionLogger",
    "SessionEvent",
]
