"""
Action Recognition Engine — Short-clip temporal analysis for intent recognition.

Provides action/activity classification from short video clips and
generates user-oriented cues for blind navigation assistance.
"""

from .action_context import (
    ActionContextConfig,
    ActionContextIntegrator,
    ActionContextResult,
    SceneContext,
    create_action_context_integrator,
)
from .action_recognizer import (
    ActionConfig,
    ActionRecognizer,
    ActionResult,
    ActionType,
    ClipBuffer,
)
from .clip_recognizer import (
    CLIPActionRecognizer,
    CLIPActionResult,
    CLIPConfig,
    IndoorAction,
    create_clip_recognizer,
)

__all__ = [
    "ActionRecognizer",
    "ActionResult",
    "ActionConfig",
    "ActionType",
    "ClipBuffer",
    "CLIPActionRecognizer",
    "CLIPActionResult",
    "CLIPConfig",
    "IndoorAction",
    "create_clip_recognizer",
    "ActionContextConfig",
    "ActionContextIntegrator",
    "ActionContextResult",
    "SceneContext",
    "create_action_context_integrator",
]
