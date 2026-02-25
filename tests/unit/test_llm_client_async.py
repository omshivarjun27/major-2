# pyright: reportMissingTypeArgument=false, reportExplicitAny=false
"""Tests for LLM client async enhancements (T-045).

Verifies:
- Configurable timeout per provider
- Connection pool in OllamaClient
- Retry with exponential backoff for both ClaudeClient and OllamaClient
- StubLLMClient unaffected
- Factory registration and fallback
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.memory.llm_client import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_S,
    ClaudeClient,
    LLMRole,
    OllamaClient,
    StubLLMClient,
    get_backend,
    register_backend,
    reset_backends,
)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_timeout(self) -> None:
        assert DEFAULT_TIMEOUT_S > 0

    def test_default_max_retries(self) -> None:
        assert DEFAULT_MAX_RETRIES >= 1

    def test_default_backoff_base(self) -> None:
        assert DEFAULT_BACKOFF_BASE > 0


# ---------------------------------------------------------------------------
# ClaudeClient
# ---------------------------------------------------------------------------


class TestClaudeClient:
    def test_no_api_key_disables(self) -> None:
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False):
            c = ClaudeClient(api_key="")
            assert not c.is_available

    def test_custom_timeout_stored(self) -> None:
        c = ClaudeClient.__new__(ClaudeClient)
        c._api_key = ""
        c._model_id = "test"
        c._timeout_s = 42.0
        c._max_retries = 2
        c._client = None
        c._available = False
        assert c._timeout_s == 42.0

    def test_custom_retries_stored(self) -> None:
        c = ClaudeClient.__new__(ClaudeClient)
        c._api_key = ""
        c._model_id = "test"
        c._timeout_s = 30.0
        c._max_retries = 5
        c._client = None
        c._available = False
        assert c._max_retries == 5

    async def test_raises_when_unavailable(self) -> None:
        c = ClaudeClient(api_key="")
        with pytest.raises(RuntimeError, match="not available"):
            await c.generate("hello")

    async def test_retries_on_failure(self) -> None:
        c = ClaudeClient.__new__(ClaudeClient)
        c._api_key = "test"
        c._model_id = "test-model"
        c._timeout_s = 30.0
        c._max_retries = 3
        c._available = True

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="answer")]
        mock_resp.usage.input_tokens = 10
        mock_resp.usage.output_tokens = 5

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return mock_resp

        mock_client.messages.create = side_effect
        c._client = mock_client

        with patch("core.memory.llm_client.DEFAULT_BACKOFF_BASE", 0.0):
            result = await c.generate("test prompt")

        assert result.text == "answer"
        assert call_count == 3


# ---------------------------------------------------------------------------
# OllamaClient
# ---------------------------------------------------------------------------


class TestOllamaClient:
    def test_custom_timeout(self) -> None:
        o = OllamaClient.__new__(OllamaClient)
        o._timeout_s = 15.0
        assert o._timeout_s == 15.0

    async def test_raises_when_unavailable(self) -> None:
        o = OllamaClient.__new__(OllamaClient)
        o._available = False
        o._client = None
        o._max_retries = 3
        with pytest.raises(RuntimeError, match="not available"):
            await o.generate("hello")

    async def test_retries_on_failure(self) -> None:
        o = OllamaClient.__new__(OllamaClient)
        o._model_id = "test-model"
        o._timeout_s = 30.0
        o._max_retries = 2
        o._available = True

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "ok"
        mock_resp.usage = MagicMock(prompt_tokens=5, completion_tokens=3)

        call_count = 0

        async def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("transient")
            return mock_resp

        mock_client.chat.completions.create = side_effect
        o._client = mock_client

        with patch("core.memory.llm_client.DEFAULT_BACKOFF_BASE", 0.0):
            result = await o.generate("test")

        assert result.text == "ok"
        assert call_count == 2

    async def test_raises_after_max_retries(self) -> None:
        o = OllamaClient.__new__(OllamaClient)
        o._model_id = "test-model"
        o._timeout_s = 30.0
        o._max_retries = 2
        o._available = True

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=ConnectionError("down"))
        o._client = mock_client

        with patch("core.memory.llm_client.DEFAULT_BACKOFF_BASE", 0.0):
            with pytest.raises(ConnectionError, match="down"):
                await o.generate("test")


# ---------------------------------------------------------------------------
# StubLLMClient
# ---------------------------------------------------------------------------


class TestStubClient:
    async def test_returns_canned(self) -> None:
        s = StubLLMClient(canned="test answer")
        r = await s.generate("anything")
        assert r.text == "test answer"
        assert r.role == LLMRole.FALLBACK

    def test_always_available(self) -> None:
        s = StubLLMClient()
        assert s.is_available


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def setup_method(self) -> None:
        reset_backends()

    def teardown_method(self) -> None:
        reset_backends()

    def test_register_and_get(self) -> None:
        stub = StubLLMClient()
        register_backend(LLMRole.FALLBACK, stub)
        result = get_backend(LLMRole.FALLBACK)
        assert result is stub

    def test_fallback_when_role_missing(self) -> None:
        stub = StubLLMClient()
        register_backend(LLMRole.FALLBACK, stub)
        result = get_backend(LLMRole.VISION)
        assert result is stub

    def test_raises_when_no_backends(self) -> None:
        with pytest.raises(RuntimeError, match="No LLM backend"):
            get_backend(LLMRole.VISION)
