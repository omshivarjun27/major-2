"""
Action Recognition Engine — Short-clip temporal analysis for intent recognition.

Provides action/activity classification from short video clips and
generates user-oriented cues for blind navigation assistance.
"""

from .action_recognizer import (
    ActionRecognizer,
    ActionResult,
    ActionConfig,
    ActionType,
    ClipBuffer,
)

__all__ = [
    "ActionRecognizer",
    "ActionResult",
    "ActionConfig",
    "ActionType",
    "ClipBuffer",
]
