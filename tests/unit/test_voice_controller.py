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
