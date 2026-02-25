"""Per-session state for the real-time vision assistant.

Extracted from agent.py (T-042) to keep the coordinator under 500 LOC.
"""

import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from livekit.agents import JobContext

from core.vision.spatial import NavigationOutput, ObstacleRecord
from core.vision.visual import VisualProcessor
from infrastructure.llm.internet_search import InternetSearch
from infrastructure.llm.ollama.handler import OllamaHandler


@dataclass
class UserData:
    """Mutable per-session state bag passed through tool calls and controllers."""

    # Core settings
    current_tool: str = "general"
    last_query: str = ""
    last_response: str = ""
    room_ctx: Optional[JobContext] = None

    # Tool instances
    visual_processor: VisualProcessor = None
    internet_search: InternetSearch = None
    ollama_handler: Optional[OllamaHandler] = None

    # Vision processing state
    _model_choice: Optional[str] = None
    _ollama_analysis: Optional[str] = None
    _ollama_chunks: List[str] = field(default_factory=list)
    _analysis_complete: bool = False
    _add_chunk_callback = None

    # Spatial perception state
    _spatial_enabled: bool = True
    _last_nav_output: Optional[NavigationOutput] = None
    _last_obstacles: List[ObstacleRecord] = field(default_factory=list)
    _pending_spatial_warning: Optional[str] = None

    # VQA Engine state
    _vqa_pipeline: Optional[Any] = None
    _vqa_fuser: Optional[Any] = None
    _vqa_reasoner: Optional[Any] = None
    _vqa_memory: Optional[Any] = None
    _vqa_session_id: Optional[str] = None

    # QR / AR scanning state
    _qr_scanner: Optional[Any] = None
    _qr_decoder: Optional[Any] = None
    _ar_handler: Optional[Any] = None
    _qr_cache: Optional[Any] = None
    _qr_enabled: bool = False

    # ── Voice Router (speech_vqa_bridge) ──
    _voice_router: Optional[Any] = None

    # ── OCR Engine ──
    _ocr_pipeline: Optional[Any] = None

    # ── Session Logger ──
    _session_logger: Optional[Any] = None
    _session_id: Optional[str] = None

    # ── Output debounce state ──
    _last_spoken_cue: str = ""
    _last_cue_time: float = 0.0
    _debounce_window_s: float = 7.0
    _last_distance_m: Optional[float] = None

    # ── Live-frame infrastructure ──
    _live_frame_mgr: Optional[Any] = None
    _debouncer: Optional[Any] = None
    _watchdog: Optional[Any] = None
    _live_infra_ready: bool = False

    # ── Proactive / always-on mode ──
    _proactive_enabled: bool = False
    _proactive_last_announce_time: float = 0.0
    _proactive_cadence_s: float = 2.0

    def clear_perception_cache(self):
        """Flush ALL cached spatial / vision state so the next query starts fresh."""
        self._model_choice = None
        self._ollama_analysis = None
        self._ollama_chunks.clear()
        self._analysis_complete = False
        self._add_chunk_callback = None
        self._last_nav_output = None
        self._last_obstacles.clear()
        self._pending_spatial_warning = None

    # ── Debounce helpers ──────────────────────────────────────────────
    def should_debounce(self, cue: str, distance_m: Optional[float] = None,
                        scene_graph_hash: str = "") -> bool:
        """Return True if this cue should be suppressed (duplicate within window).

        Delegates to the advanced Debouncer when live-frame infra is active.
        Falls back to simple time-window logic otherwise.
        """
        if self._debouncer is not None:
            return not self._debouncer.should_speak(
                cue, scene_graph_hash=scene_graph_hash, distance_m=distance_m
            )
        # Legacy path
        now = time.time()
        if cue == self._last_spoken_cue and (now - self._last_cue_time) < self._debounce_window_s:
            if distance_m is not None and self._last_distance_m is not None:
                if abs(distance_m - self._last_distance_m) > 0.5:
                    return False
            return True
        return False

    def record_cue(self, cue: str, distance_m: Optional[float] = None) -> None:
        """Record a spoken cue for debounce tracking.

        When the advanced Debouncer is active the record is already handled
        inside should_debounce → should_speak, but we keep the legacy fields
        up to date for backward compat.
        """
        self._last_spoken_cue = cue
        self._last_cue_time = time.time()
        self._last_distance_m = distance_m
