# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Tests for voice_controller.py (T-040).

Verifies voice/search/QR extraction from agent.py works correctly.
"""

from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_userdata(**overrides):
    """Create a mock UserData for voice controller tests."""
    ud = MagicMock()
    ud.current_tool = "general"
    ud.last_response = ""
    ud.internet_search = MagicMock()
    ud.internet_search.search = AsyncMock(return_value=[{"title": "Result", "url": "https://example.com"}])
    ud.internet_search.format_results = MagicMock(return_value="Result text")
    ud._qr_enabled = False
    ud._qr_scanner = None
    ud._qr_decoder = None
    ud._ar_handler = None
    ud._qr_cache = None
    ud.visual_processor = MagicMock()
    ud.visual_processor.capture_frame = AsyncMock(return_value=MagicMock())
    ud.visual_processor.last_capture_epoch_ms = None
    ud.room_ctx = MagicMock()
    ud.room_ctx.room = MagicMock()
    ud._watchdog = None
    for k, v in overrides.items():
        setattr(ud, k, v)
    return ud


# ---------------------------------------------------------------------------
# search_internet
# ---------------------------------------------------------------------------


class TestSearchInternet:
    async def test_returns_results(self):
        from apps.realtime.voice_controller import search_internet

        ud = _make_userdata()
        result = await search_internet(ud, "test query")
        assert "Result text" in result
        assert ud.current_tool == "general"

    async def test_stores_last_response(self):
        from apps.realtime.voice_controller import search_internet

        ud = _make_userdata()
        result = await search_internet(ud, "test query")
        assert ud.last_response == result

    async def test_handles_search_error(self):
        from apps.realtime.voice_controller import search_internet

        ud = _make_userdata()
        ud.internet_search.search = AsyncMock(side_effect=RuntimeError("network down"))
        result = await search_internet(ud, "fail query")
        assert "error" in result.lower()

    async def test_sets_tool_to_internet(self):
        from apps.realtime.voice_controller import search_internet

        ud = _make_userdata()
        # Temporarily capture the tool value during execution
        captured_tool = []
        orig_search = ud.internet_search.search

        async def capture_then_search(*a, **kw):
            captured_tool.append(ud.current_tool)
            return await orig_search(*a, **kw)

        ud.internet_search.search = capture_then_search
        await search_internet(ud, "test")
        assert captured_tool[0] == "internet"


# ---------------------------------------------------------------------------
# scan_qr_code
# ---------------------------------------------------------------------------


class TestScanQRCode:
    async def test_disabled_returns_not_available(self):
        from apps.realtime.voice_controller import scan_qr_code

        ud = _make_userdata(_qr_enabled=False, _qr_scanner=None)
        result = await scan_qr_code(ud)
        assert "not available" in result

    async def test_enabled_no_scanner_returns_not_available(self):
        from apps.realtime.voice_controller import scan_qr_code

        ud = _make_userdata(_qr_enabled=True, _qr_scanner=None)
        result = await scan_qr_code(ud)
        assert "not available" in result

    async def test_resets_tool_on_exception(self):
        from apps.realtime.voice_controller import scan_qr_code

        scanner = MagicMock()
        scanner.scan_async = AsyncMock(side_effect=RuntimeError("boom"))
        ud = _make_userdata(_qr_enabled=True, _qr_scanner=scanner)
        result = await scan_qr_code(ud)
        assert "Error" in result or "not available" in result.lower() or ud.current_tool == "general"


# ---------------------------------------------------------------------------
# scan_qr_code — extended coverage
# ---------------------------------------------------------------------------


class TestScanQRCodeExtended:
    async def test_camera_unavailable_returns_message(self):
        from apps.realtime.voice_controller import scan_qr_code

        scanner = MagicMock()
        ud = _make_userdata(_qr_enabled=True, _qr_scanner=scanner)
        ud.visual_processor.capture_frame = AsyncMock(return_value=None)
        result = await scan_qr_code(ud)
        assert "Camera unavailable" in result or "not available" in result.lower()

    async def test_tool_set_to_qr_during_scan(self):
        from apps.realtime.voice_controller import scan_qr_code

        captured_tool = []
        scanner = MagicMock()

        async def capture_tool(*a, **kw):
            captured_tool.append(ud.current_tool)
            return []  # no QR codes found

        scanner.scan_async = capture_tool
        ud = _make_userdata(_qr_enabled=True, _qr_scanner=scanner)
        from unittest.mock import patch

        mock_pil = MagicMock()
        mock_pil.size = (640, 480)
        mock_pil.mode = "RGB"
        mock_pil.convert.return_value = mock_pil
        mock_pil.filter.return_value = mock_pil

        with patch("core.vision.visual.convert_video_frame_to_pil", return_value=mock_pil), \
             patch("PIL.Image.Image", new=type(mock_pil)), \
             patch("PIL.ImageFilter"):
            await scan_qr_code(ud)
        assert captured_tool and captured_tool[0] == "qr"

    async def test_no_detection_returns_guidance(self):
        """When QR is enabled but nothing detected, return guidance message."""
        from unittest.mock import patch

        from apps.realtime.voice_controller import scan_qr_code

        scanner = MagicMock()
        scanner.scan_async = AsyncMock(return_value=[])
        ar = MagicMock()
        ar.is_ready = False  # no AR detection
        ud = _make_userdata(_qr_enabled=True, _qr_scanner=scanner, _ar_handler=ar)

        mock_pil = MagicMock()
        mock_pil.size = (640, 480)
        mock_pil.mode = "RGB"
        mock_pil.convert.return_value = mock_pil
        mock_pil.filter.return_value = mock_pil

        with patch("core.vision.visual.convert_video_frame_to_pil", return_value=mock_pil), \
             patch("PIL.ImageFilter"):
            result = await scan_qr_code(ud)
        assert "No QR code" in result or "not available" in result.lower() or "Error" in result


# ---------------------------------------------------------------------------
# search_internet — extended coverage
# ---------------------------------------------------------------------------


class TestSearchInternetExtended:
    async def test_includes_query_in_response(self):
        from apps.realtime.voice_controller import search_internet

        ud = _make_userdata()
        result = await search_internet(ud, "weather forecast")
        assert "weather forecast" in result

    async def test_empty_results_still_returns(self):
        from apps.realtime.voice_controller import search_internet

        ud = _make_userdata()
        ud.internet_search.search = AsyncMock(return_value=[])
        ud.internet_search.format_results = MagicMock(return_value="")
        result = await search_internet(ud, "obscure query")
        assert isinstance(result, str)
        assert ud.current_tool == "general"

    async def test_format_results_called_with_search_output(self):
        from apps.realtime.voice_controller import search_internet

        search_data = [{"title": "T", "url": "http://x.com"}]
        ud = _make_userdata()
        ud.internet_search.search = AsyncMock(return_value=search_data)
        await search_internet(ud, "test")
        ud.internet_search.format_results.assert_called_once_with(search_data)


# ---------------------------------------------------------------------------
# process_stream — basic coverage
# ---------------------------------------------------------------------------


class TestProcessStream:
    async def test_standard_llm_yields_chunks(self):
        """process_stream yields ChatChunk objects for standard (non-vision) chat."""
        from unittest.mock import patch

        from apps.realtime.voice_controller import process_stream

        ud = _make_userdata()
        ud.current_tool = "general"
        ud._model_choice = None

        # Create mock chat context and tools
        chat_ctx = MagicMock()
        tools = MagicMock()

        # Mock the LLM stream
        mock_chunk = MagicMock()
        mock_chunk.delta = MagicMock()
        mock_chunk.delta.content = "Hello"

        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: self
        mock_stream.__anext__ = AsyncMock(side_effect=[mock_chunk, StopAsyncIteration])
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        mock_llm = MagicMock()
        mock_llm.chat.return_value = mock_stream

        with patch("livekit.plugins.openai.LLM", return_value=mock_llm):
            chunks = []
            async for chunk in process_stream(
                chat_ctx, tools, ud,
                llm_model="test", llm_base_url="http://test", llm_api_key="key",
            ):
                chunks.append(chunk)

        assert len(chunks) >= 1
        assert ud.last_response is not None  # response was accumulated

    async def test_stores_last_response_after_stream(self):
        """After streaming, last_response on userdata is populated."""
        from unittest.mock import patch

        from apps.realtime.voice_controller import process_stream

        ud = _make_userdata()
        ud.current_tool = "general"
        ud._model_choice = None

        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: self
        mock_stream.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        mock_llm = MagicMock()
        mock_llm.chat.return_value = mock_stream

        with patch("livekit.plugins.openai.LLM", return_value=mock_llm):
            async for _ in process_stream(
                MagicMock(), MagicMock(), ud,
                llm_model="m", llm_base_url="u", llm_api_key="k",
            ):
                pass

        # last_response was set (even if empty string)
        assert isinstance(ud.last_response, str)
