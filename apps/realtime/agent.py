"""Real-time vision assistant — coordinator module.

This file is the LiveKit agent entrypoint. It wires together session_manager,
vision_controller, voice_controller, and tool_router. No business logic lives
here — only thin @function_tool wrappers and the session lifecycle.

Extracted prompts → prompts.py, UserData → user_data.py (T-042).
"""

import logging
import os
from typing import Annotated

from livekit.agents import JobContext
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext
from livekit.plugins import deepgram, elevenlabs, silero, tavus  # noqa: F401 — used by session_manager
from pydantic import Field

# ── Extracted modules (T-041, T-042) ─────────────────────────────────────
from apps.realtime.prompts import VISION_SYSTEM_PROMPT
from apps.realtime.tool_router import validate_detail_level, validate_query
from apps.realtime.user_data import UserData
from shared.config import get_config
from shared.utils.timing import get_profiler, time_end, time_start

# ── Live-frame & freshness infrastructure ─────────────────────────────────
try:
    from application.frame_processing.freshness import is_frame_fresh  # noqa: F401 — probe
    LIVE_INFRA_AVAILABLE = True
except ImportError as _live_err:
    LIVE_INFRA_AVAILABLE = False
    logger = logging.getLogger("ally-vision-agent")
    logger.warning(f"Live-frame infrastructure not available: {_live_err}")

# ── Model name from config (single source of truth) ──────────────────────
_CFG = get_config()
LLM_MODEL = _CFG.get("OLLAMA_VL_MODEL_ID", "qwen3.5:397b-cloud")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", _CFG.get("LLM_BASE_URL", "http://localhost:11434/v1"))
LLM_API_KEY = os.environ.get("LLM_API_KEY", _CFG.get("LLM_API_KEY", "ollama"))

# ── Optional dependency probes ────────────────────────────────────────────
try:
    import core.vqa  # noqa: F401
    VQA_ENGINE_AVAILABLE = True
except ImportError:
    VQA_ENGINE_AVAILABLE = False

try:
    import core.qr  # noqa: F401
    QR_ENGINE_AVAILABLE = True
except ImportError:
    QR_ENGINE_AVAILABLE = False

try:
    import core.speech.voice_router  # noqa: F401
    VOICE_ROUTER_AVAILABLE = True
except ImportError:
    VOICE_ROUTER_AVAILABLE = False

try:
    import core.ocr  # noqa: F401
    OCR_ENGINE_AVAILABLE = True
except ImportError:
    OCR_ENGINE_AVAILABLE = False

try:
    import apps.cli.session_logger  # noqa: F401
    SESSION_LOGGER_AVAILABLE = True
except ImportError:
    SESSION_LOGGER_AVAILABLE = False

# ── Logger ────────────────────────────────────────────────────────────────
logger = logging.getLogger("ally-vision-agent")

RunContext_T = RunContext[UserData]


# ==========================================================================
# Agent class — pure coordinator, no business logic
# ==========================================================================

class AllyVisionAgent(Agent):
    """
    REAL-TIME Vision & Navigation Assistant.
    Consistent, contextual, non-trigger-happy.
    Target: <500ms end-to-end.
    """

    def __init__(self) -> None:
        super().__init__(instructions=VISION_SYSTEM_PROMPT)

    async def on_enter(self) -> None:
        """Called when the agent is first started."""
        logger.info("Entering AllyVisionAgent")
        logger.info("Agent ready and waiting for user input")

    async def on_message(self, text: str) -> None:
        """Override on_message to log user queries and track timing.

        FRESH-CONTEXT ENFORCEMENT: every incoming message flushes all
        cached perception / spatial state so that subsequent tool calls
        always start from a clean slate with a new camera frame.
        """
        profiler = get_profiler()
        profiler.start_request(f"msg_{text[:15]}")
        msg_start = time_start()

        logger.info(f"USER QUERY: {text}")
        userdata: UserData = self.session.userdata
        userdata.last_query = text

        # ── FRESH-CONTEXT: wipe all cached perception state ──
        userdata.clear_perception_cache()

        # ── Watchdog heartbeat (proves event loop is alive) ──
        if userdata._watchdog is not None:
            userdata._watchdog.heartbeat("orchestrator")

        # Reset to general mode for each new query unless overridden by a tool
        userdata.current_tool = "general"

        await super().on_message(text)
        time_end(msg_start, "total_message_processing")

    # ── Function tools (thin wrappers delegating to controllers) ──────────

    @function_tool()
    async def search_internet(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Search query for the web")]
    ) -> str:
        """Search for up-to-date information on the web. Provides results with source links."""
        from apps.realtime import voice_controller as voc
        return await voc.search_internet(context.userdata, validate_query(query))

    async def _run_ollama_analysis(self, userdata, analysis_llm, visual_ctx):
        """Delegate to vision_controller.run_ollama_analysis."""
        from apps.realtime import vision_controller as vc
        await vc.run_ollama_analysis(userdata, analysis_llm, visual_ctx)

    @function_tool()
    async def analyze_vision(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Query about the visual scene")]
    ) -> str:
        """FAST visual scene analysis with freshness gate and failsafe."""
        from apps.realtime import vision_controller as vc
        return await vc.analyze_vision(
            context.userdata,
            validate_query(query),
            llm_model=LLM_MODEL,
            llm_base_url=LLM_BASE_URL,
            llm_api_key=LLM_API_KEY,
        )

    @function_tool()
    async def detect_obstacles(
        self,
        context: RunContext_T,
        detail_level: Annotated[str, Field(description="'quick' or 'detailed'")] = "quick"
    ) -> str:
        """ULTRA-FAST obstacle detection with freshness gate. Target: <200ms."""
        from apps.realtime import vision_controller as vc
        return await vc.detect_obstacles(context.userdata, validate_detail_level(detail_level))

    @function_tool()
    async def analyze_spatial_scene(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Spatial/navigation question")] = "What obstacles?"
    ) -> str:
        """ULTRA-FAST spatial analysis with freshness gate. Target: <200ms."""
        from apps.realtime import vision_controller as vc
        return await vc.analyze_spatial_scene(context.userdata, validate_query(query))

    @function_tool()
    async def ask_visual_question(
        self,
        context: RunContext_T,
        question: Annotated[str, Field(description="Visual question about the scene")]
    ) -> str:
        """Answer any visual question using VQA reasoning. Target: <500ms total."""
        from apps.realtime import vision_controller as vc
        return await vc.ask_visual_question(context.userdata, validate_query(question))

    @function_tool()
    async def get_navigation_cue(
        self,
        context: RunContext_T
    ) -> str:
        """Get a quick navigation cue from a FRESH camera frame. Never returns cached results."""
        from apps.realtime import vision_controller as vc
        return await vc.get_navigation_cue(context.userdata)

    @function_tool()
    async def scan_qr_code(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Optional context about the scan request")] = "scan"
    ) -> str:
        """Scan for QR codes or AR tags using the camera. Returns contextual spoken message."""
        from apps.realtime import voice_controller as voc
        return await voc.scan_qr_code(context.userdata, validate_query(query))

    @function_tool()
    async def read_text(
        self,
        context: RunContext_T,
        query: Annotated[str, Field(description="Optional context for the OCR request")] = "read text"
    ) -> str:
        """Read text from the camera using OCR."""
        from apps.realtime import vision_controller as vc
        return await vc.read_text(context.userdata, validate_query(query))

    # ── LLM node (stream delegation) ─────────────────────────────────────

    async def _process_stream(self, chat_ctx, tools, userdata):
        """Delegate stream processing to voice_controller."""
        from apps.realtime import voice_controller as voc
        async for chunk in voc.process_stream(
            chat_ctx, tools, userdata,
            llm_model=LLM_MODEL, llm_base_url=LLM_BASE_URL, llm_api_key=LLM_API_KEY,
        ):
            yield chunk

    async def llm_node(self, chat_ctx, tools, model_settings=None):
        """FAST LLM node."""
        userdata = self.session.userdata
        async for chunk in self._process_stream(chat_ctx, tools, userdata):
            yield chunk


# ==========================================================================
# Entrypoint — session lifecycle
# ==========================================================================

async def entrypoint(ctx: JobContext):
    """Set up and start the voice agent with all required tools.

    Delegates session lifecycle to session_manager (T-038 extraction).
    """
    from apps.realtime.session_manager import (
        _warmup_vqa,
        connect_with_retry,
        create_agent_session,
        initialize_components,
        run_diagnostics,
        setup_avatar,
        start_agent_session,
        start_continuous_processing,
        wire_watchdog_tts,
    )

    try:
        # 1. Connect to LiveKit room with retry
        await connect_with_retry(ctx)

        # 2. Create UserData and bootstrap all components
        userdata = UserData()
        await initialize_components(userdata, ctx)

        # 3. VQA warm-up (pre-fill caches)
        await _warmup_vqa(userdata)

        # 4. Runtime diagnostics (TTS & VQA preflight)
        await run_diagnostics(userdata, ctx)

        # 5. Create agent and session
        agent = AllyVisionAgent()
        agent_session, _ = create_agent_session(userdata, agent)

        # 6. Optional avatar
        avatar = await setup_avatar(agent_session, ctx)

        # 7. Start agent session
        await start_agent_session(agent_session, agent, ctx, avatar)

        # 8. Wire watchdog TTS alerts to session
        wire_watchdog_tts(userdata, agent_session)

        # 9. Launch continuous frame processing (background)
        await start_continuous_processing(userdata, ctx, agent_session)

    except Exception as e:
        logger.error("Agent startup failed: %s", e)
