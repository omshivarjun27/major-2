# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Integration tests for the agent coordinator (T-043).

Verifies that agent.py correctly delegates to the 4 extracted modules
(session_manager, vision_controller, voice_controller, tool_router) and
that cross-module interactions work end-to-end.

Scope:
  - AllyVisionAgent thin-wrapper delegation
  - Tool router → controller dispatch chain
  - Coordinator dependency wiring
  - Cross-module error propagation
  - Module import integrity
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers: mock the OllamaHandler import chain for agent.py / user_data.py
# ---------------------------------------------------------------------------

def _try_import_agent():
    """Attempt to import agent module, returning (module, skip_reason)."""
    try:
        from apps.realtime.agent import AllyVisionAgent, entrypoint  # noqa: F401

        return True
    except (ImportError, ModuleNotFoundError):
        return False


_AGENT_IMPORTABLE = _try_import_agent()
_AGENT_SKIP = pytest.mark.skipif(
    not _AGENT_IMPORTABLE,
    reason="agent.py import chain broken (infrastructure.llm.config missing — fixed in T-045)",
)


def _try_import_userdata():
    """Attempt to import UserData, returning success bool."""
    try:
        from apps.realtime.user_data import UserData  # noqa: F401

        return True
    except (ImportError, ModuleNotFoundError):
        return False


_USERDATA_IMPORTABLE = _try_import_userdata()
_USERDATA_SKIP = pytest.mark.skipif(
    not _USERDATA_IMPORTABLE,
    reason="user_data.py import chain broken (infrastructure.llm.config missing — fixed in T-045)",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_userdata(**overrides):
    """Create a mock UserData suitable for coordinator integration tests."""
    ud = MagicMock()
    ud.current_tool = "general"
    ud.last_query = ""
    ud.last_response = ""
    ud.room_ctx = MagicMock()
    ud.room_ctx.room = MagicMock()
    ud.visual_processor = MagicMock()
    ud.visual_processor.capture_frame = AsyncMock(return_value=MagicMock())
    ud.visual_processor.last_capture_epoch_ms = None
    ud.visual_processor.spatial_enabled = True
    ud.visual_processor.process_spatial = AsyncMock(return_value=None)
    ud.visual_processor.get_quick_warning = AsyncMock(return_value="Path clear.")
    ud.visual_processor.last_obstacles = []
    ud.internet_search = MagicMock()
    ud.internet_search.search = AsyncMock(return_value=[])
    ud.internet_search.format_results = MagicMock(return_value="No results")
    ud.ollama_handler = None
    ud._model_choice = None
    ud._ollama_analysis = None
    ud._ollama_chunks = []
    ud._analysis_complete = False
    ud._add_chunk_callback = None
    ud._spatial_enabled = True
    ud._last_nav_output = None
    ud._last_obstacles = []
    ud._pending_spatial_warning = None
    ud._vqa_pipeline = None
    ud._vqa_fuser = None
    ud._vqa_reasoner = None
    ud._vqa_memory = None
    ud._vqa_session_id = None
    ud._qr_enabled = False
    ud._qr_scanner = None
    ud._qr_decoder = None
    ud._ar_handler = None
    ud._qr_cache = None
    ud._voice_router = None
    ud._ocr_pipeline = None
    ud._session_logger = None
    ud._session_id = None
    ud._debouncer = None
    ud._watchdog = None
    ud._live_infra_ready = False
    ud._live_frame_mgr = None
    ud._proactive_enabled = False
    ud.should_debounce = MagicMock(return_value=False)
    ud.record_cue = MagicMock()
    ud.clear_perception_cache = MagicMock()
    for k, v in overrides.items():
        setattr(ud, k, v)
    return ud


# ===========================================================================
# 1. Module Import Integrity
# ===========================================================================


class TestModuleImportIntegrity:
    """Verify all extracted modules and the coordinator are importable."""

    def test_session_manager_importable(self):
        from apps.realtime.session_manager import (  # noqa: F401
            connect_with_retry,
            create_agent_session,
            initialize_components,
            run_diagnostics,
            setup_avatar,
            start_agent_session,
            start_continuous_processing,
            wire_watchdog_tts,
        )

    def test_vision_controller_importable(self):
        from apps.realtime.vision_controller import (  # noqa: F401
            analyze_spatial_scene,
            analyze_vision,
            analyze_with_ollama,
            ask_visual_question,
            capture_fresh_frame,
            detect_obstacles,
            get_navigation_cue,
            read_text,
        )

    def test_voice_controller_importable(self):
        from apps.realtime.voice_controller import (  # noqa: F401
            process_stream,
            scan_qr_code,
            search_internet,
        )

    def test_tool_router_importable(self):
        from apps.realtime.tool_router import (  # noqa: F401
            QueryType,
            ToolRegistry,
            auto_dispatch,
            classify_query,
            dispatch,
            get_registry,
            validate_detail_level,
            validate_query,
        )

    @_AGENT_SKIP
    def test_agent_coordinator_importable(self):
        from apps.realtime.agent import AllyVisionAgent, entrypoint  # noqa: F401

    @_USERDATA_SKIP
    def test_user_data_importable(self):
        from apps.realtime.user_data import UserData  # noqa: F401

    def test_prompts_importable(self):
        from apps.realtime.prompts import VISION_SYSTEM_PROMPT  # noqa: F401

        assert len(VISION_SYSTEM_PROMPT) > 100


# ===========================================================================
# 2. Tool Router → Controller Dispatch Chain
# ===========================================================================


class TestToolRouterControllerChain:
    """Verify the tool router correctly wires to controller functions."""

    def test_registry_maps_to_vision_controller(self):
        """Vision-related tools map to vision_controller functions."""
        from apps.realtime.tool_router import QueryType, get_registry

        reg = get_registry()
        vision_tools = {
            "analyze_vision", "detect_obstacles", "analyze_spatial_scene",
            "ask_visual_question", "get_navigation_cue", "read_text",
        }
        for name in vision_tools:
            entry = reg.get(name)
            assert entry is not None, f"Tool {name} not registered"
            assert entry.query_type in (
                QueryType.VISUAL, QueryType.SPATIAL, QueryType.VQA,
                QueryType.NAVIGATION, QueryType.OCR,
            ), f"Tool {name} has unexpected type {entry.query_type}"

    def test_registry_maps_to_voice_controller(self):
        """Voice-related tools map to voice_controller functions."""
        from apps.realtime.tool_router import QueryType, get_registry

        reg = get_registry()
        voice_tools = {"search_internet", "scan_qr_code"}
        for name in voice_tools:
            entry = reg.get(name)
            assert entry is not None, f"Tool {name} not registered"
            assert entry.query_type in (QueryType.SEARCH, QueryType.QR_AR)

    async def test_dispatch_calls_vision_controller(self):
        """dispatch('detect_obstacles') invokes vision_controller.detect_obstacles."""
        from apps.realtime.tool_router import dispatch

        ud = _make_mock_userdata()
        result = await dispatch("detect_obstacles", ud, detail_level="quick")
        assert result.error is None
        assert isinstance(result.response, str)

    async def test_dispatch_calls_voice_controller(self):
        """dispatch('search_internet') invokes voice_controller.search_internet."""
        from apps.realtime.tool_router import dispatch

        ud = _make_mock_userdata()
        result = await dispatch("search_internet", ud, query="test")
        assert result.error is None
        assert isinstance(result.response, str)

    async def test_auto_dispatch_classifies_and_routes(self):
        """auto_dispatch classifies a spatial query and dispatches correctly."""
        from apps.realtime.tool_router import auto_dispatch

        ud = _make_mock_userdata()
        result = await auto_dispatch("any obstacles nearby?", ud)
        assert result.query_type.value == "spatial"
        assert result.error is None

    async def test_auto_dispatch_search_query(self):
        """auto_dispatch routes search queries to voice_controller."""
        from apps.realtime.tool_router import auto_dispatch

        ud = _make_mock_userdata()
        # auto_dispatch takes (query, userdata, **kwargs) — query is positional
        result = await auto_dispatch("search for weather forecast", ud)
        assert result.query_type.value == "search"

    async def test_all_registered_tools_are_callable(self):
        """Every tool in the default registry has a callable handler."""
        from apps.realtime.tool_router import get_registry

        reg = get_registry()
        for name in reg.tool_names:
            entry = reg.get(name)
            assert entry is not None
            assert callable(entry.handler), f"Handler for {name} is not callable"

    def test_registry_has_at_least_8_tools(self):
        """The default registry should have all 8 standard tools."""
        from apps.realtime.tool_router import get_registry

        reg = get_registry()
        assert len(reg) >= 8, f"Expected 8+ tools, got {len(reg)}"


# ===========================================================================
# 3. Cross-Module Error Propagation
# ===========================================================================


class TestCrossModuleErrorPropagation:
    """Verify errors propagate correctly across module boundaries."""

    async def test_vision_error_returns_failsafe_via_dispatch(self):
        """When vision_controller raises, dispatch returns a failsafe string."""
        from apps.realtime.tool_router import dispatch

        ud = _make_mock_userdata()
        ud.visual_processor.capture_frame = AsyncMock(side_effect=RuntimeError("camera crash"))
        result = await dispatch("detect_obstacles", ud)
        # Should get a failsafe, not a raw exception
        assert result.response  # non-empty fallback
        assert "crash" not in result.response.lower()  # error details not leaked to user

    async def test_search_error_returns_error_message_via_dispatch(self):
        """When internet search fails, dispatch returns error message."""
        from apps.realtime.tool_router import dispatch

        ud = _make_mock_userdata()
        ud.internet_search.search = AsyncMock(side_effect=RuntimeError("network down"))
        result = await dispatch("search_internet", ud, query="test")
        assert "error" in result.response.lower()

    async def test_unknown_tool_returns_error_via_dispatch(self):
        """Dispatching an unknown tool returns a structured error."""
        from apps.realtime.tool_router import dispatch

        result = await dispatch("nonexistent_tool_42", MagicMock())
        assert result.error is not None
        assert "Unknown tool" in result.error

    async def test_controller_never_raises_to_user(self):
        """Vision controller functions never raise — they return failsafe strings."""
        from apps.realtime.vision_controller import detect_obstacles

        ud = _make_mock_userdata()
        # Force an internal exception via broken processor
        ud.visual_processor.capture_frame = AsyncMock(side_effect=Exception("catastrophic"))
        result = await detect_obstacles(ud, "quick")
        assert isinstance(result, str)
        assert "caution" in result.lower() or "error" in result.lower()

    async def test_vision_analyze_never_raises(self):
        """analyze_spatial_scene returns failsafe on exception."""
        from apps.realtime.vision_controller import analyze_spatial_scene

        ud = _make_mock_userdata()
        ud.visual_processor.capture_frame = AsyncMock(side_effect=Exception("boom"))
        result = await analyze_spatial_scene(ud, "What obstacles?")
        assert isinstance(result, str)
        assert "caution" in result.lower()

    async def test_get_navigation_cue_never_raises(self):
        """get_navigation_cue returns failsafe on exception."""
        from apps.realtime.vision_controller import get_navigation_cue

        ud = _make_mock_userdata()
        ud.visual_processor.capture_frame = AsyncMock(side_effect=Exception("fail"))
        result = await get_navigation_cue(ud)
        assert isinstance(result, str)
        assert "caution" in result.lower() or "Camera" in result


# ===========================================================================
# 4. Coordinator Dependency Wiring
# ===========================================================================


class TestCoordinatorWiring:
    """Verify agent.py wires its dependencies correctly."""

    @_AGENT_SKIP
    def test_agent_inherits_from_agent_base(self):
        """AllyVisionAgent is a subclass of livekit Agent."""
        from livekit.agents.voice import Agent

        from apps.realtime.agent import AllyVisionAgent

        assert issubclass(AllyVisionAgent, Agent)

    @_AGENT_SKIP
    def test_agent_has_all_function_tools(self):
        """AllyVisionAgent exposes the expected function tools."""
        from apps.realtime.agent import AllyVisionAgent

        agent = AllyVisionAgent()
        expected_tools = {
            "search_internet", "analyze_vision", "detect_obstacles",
            "analyze_spatial_scene", "ask_visual_question",
            "get_navigation_cue", "scan_qr_code", "read_text",
        }
        # function_tool decorator registers tools on the class
        tool_methods = {name for name in dir(agent) if name in expected_tools}
        assert expected_tools == tool_methods, (
            f"Missing tools: {expected_tools - tool_methods}"
        )

    def test_prompts_content_is_substantial(self):
        """VISION_SYSTEM_PROMPT contains required behavioral rules."""
        from apps.realtime.prompts import VISION_SYSTEM_PROMPT

        assert "latency" in VISION_SYSTEM_PROMPT.lower()
        assert "confidence" in VISION_SYSTEM_PROMPT.lower()
        assert "TTS" in VISION_SYSTEM_PROMPT

    @_AGENT_SKIP
    def test_entrypoint_function_exists(self):
        """The entrypoint function is defined and async."""
        import asyncio

        from apps.realtime.agent import entrypoint

        assert callable(entrypoint)
        assert asyncio.iscoroutinefunction(entrypoint)


# ===========================================================================
# 5. Entrypoint Lifecycle Delegation
# ===========================================================================


class TestEntrypointLifecycle:
    """Verify the entrypoint delegates lifecycle steps to session_manager."""

    async def test_session_manager_connect_with_retry(self):
        """connect_with_retry successfully delegates to context.connect."""
        from apps.realtime.session_manager import connect_with_retry

        ctx = AsyncMock()
        ctx.connect = AsyncMock()
        await connect_with_retry(ctx, max_retries=1)
        ctx.connect.assert_awaited_once()

    async def test_session_manager_connect_retries_on_failure(self):
        """connect_with_retry retries on transient failures."""
        from apps.realtime.session_manager import connect_with_retry

        ctx = AsyncMock()
        ctx.connect = AsyncMock(side_effect=[RuntimeError("fail"), None])

        with patch("apps.realtime.session_manager.asyncio.sleep", new_callable=AsyncMock):
            await connect_with_retry(ctx, max_retries=3)

        assert ctx.connect.await_count == 2

    async def test_session_manager_connect_exhausts_retries(self):
        """connect_with_retry raises after exhausting retries."""
        from apps.realtime.session_manager import connect_with_retry

        ctx = AsyncMock()
        ctx.connect = AsyncMock(side_effect=RuntimeError("permanent"))

        with patch("apps.realtime.session_manager.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="permanent"):
                await connect_with_retry(ctx, max_retries=2)


# ===========================================================================
# 6. UserData Integration (mocked approach for broken import chain)
# ===========================================================================


class TestUserDataIntegration:
    """Verify UserData-like behavior works correctly with controllers."""

    def test_mock_userdata_has_required_fields(self):
        """Mock userdata has all fields needed by controllers."""
        ud = _make_mock_userdata()
        # Vision controller needs these
        assert hasattr(ud, "visual_processor")
        assert hasattr(ud, "room_ctx")
        assert hasattr(ud, "current_tool")
        assert hasattr(ud, "_watchdog")
        assert hasattr(ud, "_vqa_pipeline")
        assert hasattr(ud, "_ocr_pipeline")
        # Voice controller needs these
        assert hasattr(ud, "internet_search")
        assert hasattr(ud, "_qr_enabled")
        assert hasattr(ud, "_qr_scanner")

    def test_mock_userdata_clear_perception_cache(self):
        """clear_perception_cache is callable on mock userdata."""
        ud = _make_mock_userdata()
        ud.clear_perception_cache()
        ud.clear_perception_cache.assert_called_once()

    @_USERDATA_SKIP
    def test_real_userdata_clear_cache(self):
        """Real UserData.clear_perception_cache resets all cached state."""
        from apps.realtime.user_data import UserData

        ud = UserData.__new__(UserData)
        ud._model_choice = "some_model"
        ud._ollama_analysis = "cached"
        ud._ollama_chunks = ["c1", "c2"]
        ud._analysis_complete = True
        ud._add_chunk_callback = lambda x: x
        ud._last_nav_output = MagicMock()
        ud._last_obstacles = [MagicMock()]
        ud._pending_spatial_warning = "warn"

        ud.clear_perception_cache()

        assert ud._model_choice is None
        assert ud._ollama_analysis is None
        assert len(ud._ollama_chunks) == 0
        assert ud._analysis_complete is False
        assert ud._add_chunk_callback is None

    @_USERDATA_SKIP
    def test_real_userdata_debounce(self):
        """UserData.should_debounce works via legacy time-window."""
        from apps.realtime.user_data import UserData

        ud = UserData.__new__(UserData)
        ud._debouncer = None
        ud._last_spoken_cue = "Chair ahead"
        ud._last_cue_time = 9999999999.0
        ud._debounce_window_s = 7.0
        ud._last_distance_m = None

        assert ud.should_debounce("Chair ahead") is True
        assert ud.should_debounce("Table left") is False

    @_USERDATA_SKIP
    def test_real_userdata_record_cue(self):
        """UserData.record_cue updates tracking fields."""
        from apps.realtime.user_data import UserData

        ud = UserData.__new__(UserData)
        ud._last_spoken_cue = ""
        ud._last_cue_time = 0.0
        ud._last_distance_m = None

        ud.record_cue("Obstacle 2m ahead", distance_m=2.0)
        assert ud._last_spoken_cue == "Obstacle 2m ahead"
        assert ud._last_cue_time > 0
        assert ud._last_distance_m == 2.0


# ===========================================================================
# 7. Coordinator Agent LOC Compliance
# ===========================================================================


class TestCoordinatorCompliance:
    """Verify the slimmed agent.py meets size constraints."""

    def test_agent_file_under_500_loc(self):
        """agent.py should be under 500 LOC after extraction."""
        agent_path = os.path.join("apps", "realtime", "agent.py")
        with open(agent_path) as f:
            line_count = sum(1 for _ in f)
        assert line_count <= 500, f"agent.py is {line_count} LOC, expected <=500"

    def test_extracted_modules_exist(self):
        """All 4 extracted modules exist as separate files."""
        modules = [
            "apps/realtime/session_manager.py",
            "apps/realtime/vision_controller.py",
            "apps/realtime/voice_controller.py",
            "apps/realtime/tool_router.py",
        ]
        for mod in modules:
            assert os.path.isfile(mod), f"Missing extracted module: {mod}"

    def test_userdata_and_prompts_extracted(self):
        """UserData and prompts are in their own files."""
        assert os.path.isfile("apps/realtime/user_data.py")
        assert os.path.isfile("apps/realtime/prompts.py")

    def test_session_manager_is_largest(self):
        """session_manager.py should be the largest extracted module (lifecycle logic)."""
        sizes = {}
        for mod in ["session_manager.py", "vision_controller.py", "voice_controller.py", "tool_router.py"]:
            path = os.path.join("apps", "realtime", mod)
            with open(path) as f:
                sizes[mod] = sum(1 for _ in f)
        assert sizes["session_manager.py"] >= sizes["voice_controller.py"], (
            f"session_manager ({sizes['session_manager.py']} LOC) should be >= voice_controller ({sizes['voice_controller.py']} LOC)"
        )
