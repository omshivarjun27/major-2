# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Tests for vision_controller.py (T-039).

Verifies vision processing extraction from agent.py works correctly
with mocked UserData and visual processor dependencies.
"""

from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_userdata(**overrides):
    """Create a mock UserData with sensible defaults."""
    ud = MagicMock()
    ud.visual_processor = MagicMock()
    ud.visual_processor.capture_frame = AsyncMock(return_value=MagicMock())
    ud.visual_processor.last_capture_epoch_ms = None
    ud.visual_processor.spatial_enabled = True
    ud.visual_processor.process_spatial = AsyncMock(return_value=None)
    ud.visual_processor.get_quick_warning = AsyncMock(return_value="Path clear.")
    ud.visual_processor.last_obstacles = []
    ud.room_ctx = MagicMock()
    ud.room_ctx.room = MagicMock()
    ud.current_tool = "general"
    ud._watchdog = None
    ud._model_choice = None
    ud._ollama_chunks = []
    ud._add_chunk_callback = None
    ud._analysis_complete = False
    ud._last_nav_output = None
    ud._last_obstacles = []
    ud._pending_spatial_warning = None
    ud._vqa_pipeline = None
    ud._vqa_fuser = None
    ud._vqa_reasoner = None
    ud._vqa_memory = None
    ud._vqa_session_id = None
    ud._ocr_pipeline = None
    ud.ollama_handler = None
    ud.should_debounce = MagicMock(return_value=False)
    ud.record_cue = MagicMock()
    for k, v in overrides.items():
        setattr(ud, k, v)
    return ud


# ---------------------------------------------------------------------------
# capture_fresh_frame
# ---------------------------------------------------------------------------


class TestCaptureFrame:
    async def test_returns_image(self):
        from apps.realtime.vision_controller import capture_fresh_frame

        ud = _make_userdata()
        result = await capture_fresh_frame(ud)
        assert result is not None

    async def test_returns_none_when_no_processor(self):
        from apps.realtime.vision_controller import capture_fresh_frame

        ud = _make_userdata(visual_processor=None)
        result = await capture_fresh_frame(ud)
        assert result is None

    async def test_returns_none_when_no_room(self):
        from apps.realtime.vision_controller import capture_fresh_frame

        ud = _make_userdata(room_ctx=None)
        result = await capture_fresh_frame(ud)
        assert result is None


# ---------------------------------------------------------------------------
# detect_obstacles
# ---------------------------------------------------------------------------


class TestDetectObstacles:
    async def test_quick_mode_returns_warning(self):
        from apps.realtime.vision_controller import detect_obstacles

        ud = _make_userdata()
        ud.visual_processor.get_quick_warning = AsyncMock(return_value="Chair 1.5m ahead.")
        result = await detect_obstacles(ud, "quick")
        assert "Chair" in result

    async def test_returns_failsafe_on_no_camera(self):
        from apps.realtime.vision_controller import detect_obstacles

        ud = _make_userdata()
        ud.visual_processor.capture_frame = AsyncMock(return_value=None)
        result = await detect_obstacles(ud)
        assert "Camera unavailable" in result

    async def test_returns_failsafe_when_spatial_disabled(self):
        from apps.realtime.vision_controller import detect_obstacles

        ud = _make_userdata()
        ud.visual_processor.spatial_enabled = False
        result = await detect_obstacles(ud)
        assert "Sensing unavailable" in result

    async def test_detailed_mode_path_clear(self):
        from apps.realtime.vision_controller import detect_obstacles

        ud = _make_userdata()
        ud.visual_processor.process_spatial = AsyncMock(return_value=None)
        result = await detect_obstacles(ud, "detailed")
        assert "Path clear" in result

    async def test_detailed_mode_with_nav_output(self):
        from apps.realtime.vision_controller import detect_obstacles

        nav = MagicMock()
        nav.short_cue = "Caution, table 2m left."
        nav.has_critical = False
        ud = _make_userdata()
        ud.visual_processor.process_spatial = AsyncMock(return_value=nav)
        result = await detect_obstacles(ud, "detailed")
        assert "table" in result

    async def test_debounce_suppresses(self):
        from apps.realtime.vision_controller import detect_obstacles

        ud = _make_userdata()
        ud.visual_processor.get_quick_warning = AsyncMock(return_value="Same cue.")
        ud.should_debounce = MagicMock(return_value=True)
        result = await detect_obstacles(ud, "quick")
        assert result == "Same cue."
        ud.record_cue.assert_not_called()


# ---------------------------------------------------------------------------
# get_navigation_cue
# ---------------------------------------------------------------------------


class TestGetNavigationCue:
    async def test_returns_warning(self):
        from apps.realtime.vision_controller import get_navigation_cue

        ud = _make_userdata()
        ud.visual_processor.get_quick_warning = AsyncMock(return_value="Path clear.")
        result = await get_navigation_cue(ud)
        assert result == "Path clear."

    async def test_returns_failsafe_on_no_image(self):
        from apps.realtime.vision_controller import get_navigation_cue

        ud = _make_userdata()
        ud.visual_processor.capture_frame = AsyncMock(return_value=None)
        result = await get_navigation_cue(ud)
        assert "Camera unavailable" in result


# ---------------------------------------------------------------------------
# analyze_with_ollama
# ---------------------------------------------------------------------------


class TestAnalyzeWithOllama:
    async def test_returns_response(self):
        from apps.realtime.vision_controller import analyze_with_ollama

        handler = AsyncMock()
        handler.model_choice_with_analysis = AsyncMock(return_value=("model", "A chair is visible.", None))
        ud = _make_userdata(ollama_handler=handler)
        result = await analyze_with_ollama(ud, MagicMock(), "What do you see?")
        assert "chair" in result

    async def test_returns_fallback_when_no_handler(self):
        from apps.realtime.vision_controller import analyze_with_ollama

        ud = _make_userdata(ollama_handler=None)
        result = await analyze_with_ollama(ud, MagicMock(), "What?")
        assert result == "Unable to analyze."


# ---------------------------------------------------------------------------
# read_text
# ---------------------------------------------------------------------------


class TestReadText:
    async def test_no_ocr_available(self):
        from apps.realtime.vision_controller import read_text

        ud = _make_userdata(_ocr_pipeline=None)
        result = await read_text(ud)
        assert "not available" in result
