"""Tests for apps.realtime.tool_router — T-041.

Covers:
- QueryType enum values
- classify_query() mapping for all query types
- ToolRegistry registration, retrieval, and listing
- dispatch() success and error paths
- validate_detail_level() normalisation
- validate_query() sanitisation
- auto_dispatch() classification + dispatch combo
- SPATIAL_TRIGGER_PHRASES coverage
"""

from unittest.mock import AsyncMock

from apps.realtime.tool_router import (
    OCR_TRIGGER_PHRASES,
    QR_TRIGGER_PHRASES,
    SEARCH_TRIGGER_PHRASES,
    SPATIAL_TRIGGER_PHRASES,
    QueryType,
    ToolRegistry,
    _failsafe_for_type,
    classify_query,
    dispatch,
    get_registry,
    validate_detail_level,
    validate_query,
)

# ---------------------------------------------------------------------------
# QueryType enum
# ---------------------------------------------------------------------------

class TestQueryType:
    def test_all_values_exist(self):
        expected = {"visual", "spatial", "search", "qr_ar", "ocr", "vqa", "navigation", "general"}
        actual = {qt.value for qt in QueryType}
        assert actual == expected

    def test_enum_members(self):
        assert QueryType.VISUAL.value == "visual"
        assert QueryType.GENERAL.value == "general"
        assert QueryType.QR_AR.value == "qr_ar"


# ---------------------------------------------------------------------------
# classify_query
# ---------------------------------------------------------------------------

class TestClassifyQuery:
    def test_empty_query(self):
        assert classify_query("") == QueryType.GENERAL

    def test_whitespace_query(self):
        assert classify_query("   ") == QueryType.GENERAL

    def test_qr_trigger(self):
        assert classify_query("scan qr code") == QueryType.QR_AR

    def test_qr_trigger_case_insensitive(self):
        assert classify_query("SCAN QR CODE") == QueryType.QR_AR

    def test_ocr_trigger(self):
        assert classify_query("read text from this sign") == QueryType.OCR

    def test_search_trigger(self):
        assert classify_query("search for weather today") == QueryType.SEARCH

    def test_spatial_trigger_obstacles(self):
        assert classify_query("any obstacles nearby?") == QueryType.SPATIAL

    def test_spatial_trigger_navigation(self):
        assert classify_query("help me navigate to the door") == QueryType.SPATIAL

    def test_spatial_trigger_distance(self):
        assert classify_query("how far is the wall?") == QueryType.SPATIAL

    def test_vision_trigger_describe(self):
        assert classify_query("describe what you see") == QueryType.VISUAL

    def test_general_fallback(self):
        assert classify_query("hello world") == QueryType.GENERAL

    def test_priority_qr_over_spatial(self):
        """QR should win when both QR and spatial phrases match."""
        assert classify_query("scan qr nearby obstacles") == QueryType.QR_AR

    def test_priority_ocr_over_vision(self):
        """OCR should win over vision for read-text queries."""
        assert classify_query("read this text") == QueryType.OCR


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        handler = AsyncMock(return_value="ok")
        reg.register("test_tool", QueryType.VISUAL, handler, description="test", sla_ms=100)
        entry = reg.get("test_tool")
        assert entry is not None
        assert entry.name == "test_tool"
        assert entry.query_type == QueryType.VISUAL
        assert entry.sla_ms == 100

    def test_get_missing(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_get_for_type(self):
        reg = ToolRegistry()
        h1 = AsyncMock(return_value="a")
        h2 = AsyncMock(return_value="b")
        reg.register("t1", QueryType.SPATIAL, h1)
        reg.register("t2", QueryType.SPATIAL, h2)
        entries = reg.get_for_type(QueryType.SPATIAL)
        assert len(entries) == 2

    def test_tool_names(self):
        reg = ToolRegistry()
        reg.register("alpha", QueryType.GENERAL, AsyncMock())
        reg.register("beta", QueryType.SEARCH, AsyncMock())
        assert set(reg.tool_names) == {"alpha", "beta"}

    def test_len(self):
        reg = ToolRegistry()
        assert len(reg) == 0
        reg.register("x", QueryType.OCR, AsyncMock())
        assert len(reg) == 1


# ---------------------------------------------------------------------------
# Global registry — default tools
# ---------------------------------------------------------------------------

class TestDefaultRegistry:
    def test_default_tools_registered(self):
        reg = get_registry()
        assert len(reg) >= 8  # 8 standard tools
        expected_names = {
            "analyze_vision", "detect_obstacles", "analyze_spatial_scene",
            "ask_visual_question", "get_navigation_cue", "read_text",
            "search_internet", "scan_qr_code",
        }
        assert expected_names.issubset(set(reg.tool_names))

    def test_registry_entries_have_handlers(self):
        reg = get_registry()
        for name in reg.tool_names:
            entry = reg.get(name)
            assert entry is not None
            assert callable(entry.handler)


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

class TestDispatch:
    async def test_dispatch_success(self):
        """Dispatch to a known tool returns handler result."""
        result = await dispatch("search_internet", type("UD", (), {
            "current_tool": "general",
            "internet_search": type("IS", (), {
                "search": AsyncMock(return_value=[]),
                "format_results": lambda self, r: "no results",
            })(),
            "last_response": "",
        })(), query="test query")
        assert result.error is None
        assert "test query" in result.response or result.response  # handler ran

    async def test_dispatch_unknown_tool(self):
        result = await dispatch("nonexistent_tool_xyz", object())
        assert result.error is not None
        assert "Unknown tool" in result.error

    async def test_dispatch_handler_exception(self):
        """If handler raises, dispatch returns a failsafe."""
        from apps.realtime.tool_router import _registry
        # Temporarily register a failing handler
        failing = AsyncMock(side_effect=RuntimeError("boom"))
        _registry.register("_test_fail", QueryType.GENERAL, failing)
        try:
            result = await dispatch("_test_fail", object())
            assert result.error is not None
            assert "boom" in result.error
        finally:
            # Cleanup
            _registry._tools.pop("_test_fail", None)


# ---------------------------------------------------------------------------
# validate_detail_level
# ---------------------------------------------------------------------------

class TestValidateDetailLevel:
    def test_quick(self):
        assert validate_detail_level("quick") == "quick"

    def test_detailed(self):
        assert validate_detail_level("detailed") == "detailed"

    def test_case_insensitive(self):
        assert validate_detail_level("QUICK") == "quick"
        assert validate_detail_level("Detailed") == "detailed"

    def test_whitespace(self):
        assert validate_detail_level("  quick  ") == "quick"

    def test_invalid_defaults_to_quick(self):
        assert validate_detail_level("fast") == "quick"
        assert validate_detail_level("") == "quick"


# ---------------------------------------------------------------------------
# validate_query
# ---------------------------------------------------------------------------

class TestValidateQuery:
    def test_normal(self):
        assert validate_query("what is this?") == "what is this?"

    def test_strips_whitespace(self):
        assert validate_query("  hello  ") == "hello"

    def test_empty_returns_default(self):
        assert validate_query("") == "general query"
        assert validate_query("   ") == "general query"

    def test_truncates_long_query(self):
        long = "x" * 3000
        result = validate_query(long, max_length=100)
        assert len(result) == 100

    def test_custom_max_length(self):
        result = validate_query("hello world", max_length=5)
        assert result == "hello"


# ---------------------------------------------------------------------------
# _failsafe_for_type
# ---------------------------------------------------------------------------

class TestFailsafe:
    def test_vision_failsafe(self):
        msg = _failsafe_for_type(QueryType.VISUAL)
        assert "caution" in msg.lower()

    def test_qr_failsafe(self):
        msg = _failsafe_for_type(QueryType.QR_AR)
        assert "QR" in msg or "scanning" in msg.lower()

    def test_search_failsafe(self):
        msg = _failsafe_for_type(QueryType.SEARCH)
        assert "searching" in msg.lower()

    def test_general_failsafe(self):
        msg = _failsafe_for_type(QueryType.GENERAL)
        assert msg  # non-empty


# ---------------------------------------------------------------------------
# Trigger phrases coverage
# ---------------------------------------------------------------------------

class TestTriggerPhrases:
    def test_spatial_phrases_nonempty(self):
        assert len(SPATIAL_TRIGGER_PHRASES) > 10

    def test_qr_phrases_nonempty(self):
        assert len(QR_TRIGGER_PHRASES) > 5

    def test_ocr_phrases_nonempty(self):
        assert len(OCR_TRIGGER_PHRASES) > 5

    def test_search_phrases_nonempty(self):
        assert len(SEARCH_TRIGGER_PHRASES) > 3

    def test_spatial_phrases_are_lowercase(self):
        """Trigger phrases should be lowercase for consistent matching."""
        for phrase in SPATIAL_TRIGGER_PHRASES:
            assert phrase == phrase.lower(), f"Phrase not lowercase: {phrase}"
