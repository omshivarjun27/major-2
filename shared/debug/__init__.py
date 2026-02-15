"""
Debug Tools — Cross-cutting Visualization & Session Logging
============================================================

Provides debug visualization tools and structured session logging
used across multiple architectural layers.

Canonical location: ``shared/debug/``
"""

from .visualizer import (
    DebugVisualizer,
    VisualizerConfig,
    DebugVisualizerResult,
    render_debug_image,
    annotate_image,
)
from .session_logger import SessionLogger, SessionEvent

__all__ = [
    "DebugVisualizer",
    "VisualizerConfig",
    "DebugVisualizerResult",
    "render_debug_image",
    "annotate_image",
    "SessionLogger",
    "SessionEvent",
]
