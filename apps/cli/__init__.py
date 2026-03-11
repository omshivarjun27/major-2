"""
Debug Tools — CLI Entrypoint
=============================

Re-exports from ``shared.debug`` for backward compatibility.
Canonical location: ``shared/debug/``
"""

from shared.debug import (
    DebugVisualizer,
    DebugVisualizerResult,
    SessionEvent,
    SessionLogger,
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
