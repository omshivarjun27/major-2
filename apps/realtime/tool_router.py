# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Tool router — query classification and capability dispatch (T-041).

Classifies incoming queries by type (visual, spatial, search, QR/AR, OCR,
VQA, navigation, general) and dispatches to the appropriate controller
function in ``vision_controller`` or ``voice_controller``.  All function-call
definitions, parameter validation, and tool error handling are consolidated
here so that ``agent.py`` retains only thin ``@function_tool`` wrappers.
"""

import enum
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional, Sequence

logger = logging.getLogger("ally-tool-router")


# ---------------------------------------------------------------------------
# Query type classification
# ---------------------------------------------------------------------------

class QueryType(enum.Enum):
    """High-level intent bucket for an incoming user query."""

    VISUAL = "visual"
    SPATIAL = "spatial"
    SEARCH = "search"
    QR_AR = "qr_ar"
    OCR = "ocr"
    VQA = "vqa"
    NAVIGATION = "navigation"
    GENERAL = "general"


# Spatial trigger phrases — consolidated from agent.py
SPATIAL_TRIGGER_PHRASES: List[str] = [
    # Detection triggers
    "detect", "detect objects", "what objects", "identify", "recognize",
    # Navigation triggers
    "what is in front", "what's in front", "in front of me",
    "describe surroundings", "describe my surroundings", "describe the room",
    "obstacles", "obstacle", "any obstacles", "obstacles nearby",
    "path clear", "is the path clear", "can i walk", "safe to walk",
    "guide me", "navigation", "navigate", "help me navigate",
    "what is ahead", "what's ahead", "ahead of me",
    "can i go", "should i move", "where should i", "where can i",
    "what do you see", "what is there", "what's there", "what can you see",
    "distance", "how far", "direction", "which way",
    # Scene understanding
    "scene", "environment", "around me", "nearby",
]

# QR/AR trigger phrases
QR_TRIGGER_PHRASES: List[str] = [
    "scan qr", "qr code", "read code", "scan code", "barcode",
    "ar tag", "ar marker", "aruco", "scan tag",
    "what does this code say", "what does this qr say",
]

# OCR trigger phrases
OCR_TRIGGER_PHRASES: List[str] = [
    "read text", "read this", "what does this say", "what does it say",
    "read the sign", "read the label", "ocr", "text recognition",
    "what is written", "what's written",
]

# Search trigger phrases
SEARCH_TRIGGER_PHRASES: List[str] = [
    "search", "look up", "find out", "google", "search for",
    "what is the latest", "news about", "tell me about",
]

# Vision trigger phrases (general visual analysis)
VISION_TRIGGER_PHRASES: List[str] = [
    "what do you see", "describe", "look at", "show me",
    "analyze", "what is this", "what's this", "tell me what",
    "can you see", "identify this",
]

# Pre-compiled patterns for faster matching
_SPATIAL_PATTERN: Optional[re.Pattern[str]] = None
_QR_PATTERN: Optional[re.Pattern[str]] = None
_OCR_PATTERN: Optional[re.Pattern[str]] = None
_SEARCH_PATTERN: Optional[re.Pattern[str]] = None


def _compile_pattern(phrases: Sequence[str]) -> re.Pattern[str]:
    """Compile a list of trigger phrases into a single regex pattern."""
    escaped = [re.escape(p) for p in sorted(phrases, key=len, reverse=True)]
    return re.compile(r"(?:" + "|".join(escaped) + r")", re.IGNORECASE)


def _get_spatial_pattern() -> re.Pattern[str]:
    global _SPATIAL_PATTERN
    if _SPATIAL_PATTERN is None:
        _SPATIAL_PATTERN = _compile_pattern(SPATIAL_TRIGGER_PHRASES)
    return _SPATIAL_PATTERN


def _get_qr_pattern() -> re.Pattern[str]:
    global _QR_PATTERN
    if _QR_PATTERN is None:
        _QR_PATTERN = _compile_pattern(QR_TRIGGER_PHRASES)
    return _QR_PATTERN


def _get_ocr_pattern() -> re.Pattern[str]:
    global _OCR_PATTERN
    if _OCR_PATTERN is None:
        _OCR_PATTERN = _compile_pattern(OCR_TRIGGER_PHRASES)
    return _OCR_PATTERN


def _get_search_pattern() -> re.Pattern[str]:
    global _SEARCH_PATTERN
    if _SEARCH_PATTERN is None:
        _SEARCH_PATTERN = _compile_pattern(SEARCH_TRIGGER_PHRASES)
    return _SEARCH_PATTERN


def classify_query(query: str) -> QueryType:
    """Classify a user query into a ``QueryType``.

    Priority order (first match wins):
      1. QR/AR  (explicit scan requests)
      2. OCR    (explicit read-text requests)
      3. Search (explicit web search requests)
      4. Spatial/Navigation (obstacle & direction queries)
      5. Visual  (general scene description)
      6. General (fallback)
    """
    q = query.strip()
    if not q:
        return QueryType.GENERAL

    if _get_qr_pattern().search(q):
        return QueryType.QR_AR
    if _get_ocr_pattern().search(q):
        return QueryType.OCR
    if _get_search_pattern().search(q):
        return QueryType.SEARCH
    if _get_spatial_pattern().search(q):
        return QueryType.SPATIAL
    # Visual is intentionally broad — anything with a "see/describe/look" flavour
    # but we only check after more specific types have been ruled out.
    for phrase in VISION_TRIGGER_PHRASES:
        if phrase.lower() in q.lower():
            return QueryType.VISUAL
    return QueryType.GENERAL


# ---------------------------------------------------------------------------
# Tool capability handler — async callable signature
# ---------------------------------------------------------------------------

ToolHandler = Callable[..., Coroutine[Any, Any, str]]


@dataclass
class ToolEntry:
    """Metadata for a registered tool handler."""

    name: str
    query_type: QueryType
    handler: ToolHandler
    description: str = ""
    sla_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Registry mapping tool names to handler functions.

    Populated at import time with the known set of controllers from
    ``vision_controller`` and ``voice_controller``.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolEntry] = {}
        self._type_map: Dict[QueryType, List[ToolEntry]] = {}

    def register(
        self,
        name: str,
        query_type: QueryType,
        handler: ToolHandler,
        description: str = "",
        sla_ms: Optional[int] = None,
    ) -> None:
        """Register a tool handler."""
        entry = ToolEntry(
            name=name,
            query_type=query_type,
            handler=handler,
            description=description,
            sla_ms=sla_ms,
        )
        self._tools[name] = entry
        self._type_map.setdefault(query_type, []).append(entry)
        logger.debug("Registered tool %s → %s", name, query_type.value)

    def get(self, name: str) -> Optional[ToolEntry]:
        """Retrieve a tool entry by name."""
        return self._tools.get(name)

    def get_for_type(self, query_type: QueryType) -> List[ToolEntry]:
        """Get all tool entries for a given query type."""
        return self._type_map.get(query_type, [])

    @property
    def tool_names(self) -> List[str]:
        """All registered tool names."""
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)


# Module-level singleton registry
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Return the module-level tool registry singleton."""
    return _registry


# ---------------------------------------------------------------------------
# Tool registration — wires vision_controller + voice_controller functions
# ---------------------------------------------------------------------------

def _register_default_tools() -> None:
    """Populate the registry with the standard set of controller functions.

    Called once at module import time.  The lazy import pattern avoids
    circular imports between agent ↔ controllers.
    """
    from apps.realtime import vision_controller as vc
    from apps.realtime import voice_controller as voc

    _registry.register(
        name="analyze_vision",
        query_type=QueryType.VISUAL,
        handler=vc.analyze_vision,
        description="Visual scene analysis with freshness gate and failsafe.",
        sla_ms=500,
    )
    _registry.register(
        name="detect_obstacles",
        query_type=QueryType.SPATIAL,
        handler=vc.detect_obstacles,
        description="Ultra-fast obstacle detection. Target: <200ms.",
        sla_ms=200,
    )
    _registry.register(
        name="analyze_spatial_scene",
        query_type=QueryType.SPATIAL,
        handler=vc.analyze_spatial_scene,
        description="Spatial analysis with VQA fallback. Target: <200ms.",
        sla_ms=200,
    )
    _registry.register(
        name="ask_visual_question",
        query_type=QueryType.VQA,
        handler=vc.ask_visual_question,
        description="Answer visual questions using VQA reasoning. Target: <500ms.",
        sla_ms=500,
    )
    _registry.register(
        name="get_navigation_cue",
        query_type=QueryType.NAVIGATION,
        handler=vc.get_navigation_cue,
        description="Quick navigation cue from a fresh camera frame.",
        sla_ms=500,
    )
    _registry.register(
        name="read_text",
        query_type=QueryType.OCR,
        handler=vc.read_text,
        description="Read text from the camera using OCR.",
        sla_ms=2000,
    )
    _registry.register(
        name="search_internet",
        query_type=QueryType.SEARCH,
        handler=voc.search_internet,
        description="Search for up-to-date information on the web.",
    )
    _registry.register(
        name="scan_qr_code",
        query_type=QueryType.QR_AR,
        handler=voc.scan_qr_code,
        description="Scan for QR codes or AR tags using the camera.",
    )


# Auto-register at import time
_register_default_tools()


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

@dataclass
class DispatchResult:
    """Result of dispatching a query through the tool router."""

    tool_name: str
    query_type: QueryType
    response: str
    error: Optional[str] = None


async def dispatch(
    tool_name: str,
    userdata: Any,
    **kwargs: Any,
) -> DispatchResult:
    """Dispatch a tool call to the appropriate controller function.

    Parameters
    ----------
    tool_name:
        Registered tool name (e.g. ``"analyze_vision"``).
    userdata:
        The session ``UserData`` instance.
    **kwargs:
        Extra arguments forwarded to the handler (e.g. ``query=...``).

    Returns
    -------
    DispatchResult with the response string or error detail.
    """
    entry = _registry.get(tool_name)
    if entry is None:
        msg = f"Unknown tool: {tool_name}"
        logger.error(msg)
        return DispatchResult(
            tool_name=tool_name,
            query_type=QueryType.GENERAL,
            response=msg,
            error=msg,
        )

    try:
        response = await entry.handler(userdata, **kwargs)
        return DispatchResult(
            tool_name=tool_name,
            query_type=entry.query_type,
            response=response,
        )
    except Exception as exc:
        error_msg = f"Tool {tool_name} failed: {exc}"
        logger.error(error_msg, exc_info=True)
        return DispatchResult(
            tool_name=tool_name,
            query_type=entry.query_type,
            response=_failsafe_for_type(entry.query_type),
            error=error_msg,
        )


def _failsafe_for_type(query_type: QueryType) -> str:
    """Return a safe fallback message based on query type."""
    failsafes: Dict[QueryType, str] = {
        QueryType.VISUAL: "I can't see clearly right now — proceed with caution.",
        QueryType.SPATIAL: "I can't see clearly right now — proceed with caution.",
        QueryType.NAVIGATION: "I can't see clearly right now — proceed with caution.",
        QueryType.VQA: "I can't see clearly right now — proceed with caution.",
        QueryType.OCR: "I can't read the text clearly right now.",
        QueryType.QR_AR: "Error scanning QR code.",
        QueryType.SEARCH: "I encountered an error while searching.",
        QueryType.GENERAL: "Something went wrong. Please try again.",
    }
    return failsafes.get(query_type, failsafes[QueryType.GENERAL])


# ---------------------------------------------------------------------------
# Auto-dispatch: classify + dispatch in one call
# ---------------------------------------------------------------------------

async def auto_dispatch(
    query: str,
    userdata: Any,
    **kwargs: Any,
) -> DispatchResult:
    """Classify a free-text query and dispatch to the best matching tool.

    Uses ``classify_query`` to determine query type, then selects the
    primary handler for that type from the registry.

    Falls back to ``QueryType.GENERAL`` if no handler is registered for
    the classified type.
    """
    query_type = classify_query(query)
    entries = _registry.get_for_type(query_type)
    if not entries:
        return DispatchResult(
            tool_name="none",
            query_type=query_type,
            response=_failsafe_for_type(query_type),
            error=f"No handler registered for {query_type.value}",
        )

    # Use first (primary) handler for the type
    entry = entries[0]
    return await dispatch(entry.name, userdata, **kwargs)


# ---------------------------------------------------------------------------
# Parameter validation helpers
# ---------------------------------------------------------------------------

def validate_detail_level(detail_level: str) -> str:
    """Normalise and validate the detail_level parameter.

    Returns ``"quick"`` or ``"detailed"``.  Invalid values are silently
    coerced to ``"quick"`` with a log warning.
    """
    normalised = detail_level.strip().lower()
    if normalised in ("quick", "detailed"):
        return normalised
    logger.warning("Invalid detail_level '%s', defaulting to 'quick'", detail_level)
    return "quick"


def validate_query(query: str, *, max_length: int = 2000) -> str:
    """Sanitise an incoming query string.

    * Strips leading/trailing whitespace.
    * Truncates to *max_length* characters.
    * Returns ``"general query"`` if empty.
    """
    q = query.strip()
    if not q:
        return "general query"
    if len(q) > max_length:
        logger.warning("Query truncated from %d to %d chars", len(q), max_length)
        q = q[:max_length]
    return q
