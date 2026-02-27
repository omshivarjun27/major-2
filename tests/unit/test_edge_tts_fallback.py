"""Unit tests for Edge TTS local fallback adapter.

Tests cover:
- LocalTTSConfig initialization and configuration
- LocalTTSFallback backend selection
- Sync and async synthesis methods
- Error handling when backends are unavailable
- SynthesisResult dataclass
- Health and availability checks
- create_local_tts_fn helper
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestLocalTTSConfig:
    """Tests for LocalTTSConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSConfig

        config = LocalTTSConfig()
        assert config.voice == "en-US-AriaNeural"
        assert config.rate == "+0%"
        assert config.volume == "+0%"
        assert config.pyttsx3_rate == 150
        assert config.pyttsx3_volume == 1.0
        assert config.prefer_edge_tts is True

    def test_custom_config(self):
        """Test custom configuration values."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSConfig

        config = LocalTTSConfig(
            voice="en-GB-SoniaNeural",
            rate="+10%",
            volume="-5%",
            pyttsx3_rate=200,
            pyttsx3_volume=0.8,
            prefer_edge_tts=False,
        )
        assert config.voice == "en-GB-SoniaNeural"
        assert config.rate == "+10%"
        assert config.volume == "-5%"
        assert config.pyttsx3_rate == 200
        assert config.pyttsx3_volume == 0.8
        assert config.prefer_edge_tts is False

    def test_from_env_default(self):
        """Test from_env with default environment."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSConfig

        with patch.dict("os.environ", {}, clear=True):
            config = LocalTTSConfig.from_env()
            assert config.voice == "en-US-AriaNeural"
            assert config.rate == "+0%"
            assert config.prefer_edge_tts is True

    def test_from_env_custom(self):
        """Test from_env with custom environment variables."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSConfig

        env_vars = {
            "LOCAL_TTS_VOICE": "es-ES-ElviraNeural",
            "LOCAL_TTS_RATE": "-10%",
            "LOCAL_TTS_VOLUME": "+5%",
            "LOCAL_TTS_PYTTSX3_RATE": "180",
            "LOCAL_TTS_PYTTSX3_VOLUME": "0.9",
            "LOCAL_TTS_PREFER_EDGE": "false",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            config = LocalTTSConfig.from_env()
            assert config.voice == "es-ES-ElviraNeural"
            assert config.rate == "-10%"
            assert config.volume == "+5%"
            assert config.pyttsx3_rate == 180
            assert config.pyttsx3_volume == 0.9
            assert config.prefer_edge_tts is False


class TestSynthesisResult:
    """Tests for SynthesisResult dataclass."""

    def test_successful_result(self):
        """Test a successful synthesis result."""
        from infrastructure.speech.local.edge_tts_fallback import SynthesisResult

        result = SynthesisResult(
            audio_bytes=b"\x00\x01\x02",
            backend="edge-tts",
            latency_ms=150.5,
            voice="en-US-AriaNeural",
        )
        assert len(result.audio_bytes) == 3
        assert result.backend == "edge-tts"
        assert result.latency_ms == 150.5
        assert result.voice == "en-US-AriaNeural"
        assert result.error is None
        assert result.success is True

    def test_failed_result(self):
        """Test a failed synthesis result."""
        from infrastructure.speech.local.edge_tts_fallback import SynthesisResult

        result = SynthesisResult(
            audio_bytes=b"",
            backend="edge-tts",
            latency_ms=50.0,
            voice="en-US-AriaNeural",
            error="Network error",
        )
        assert result.audio_bytes == b""
        assert result.error == "Network error"
        assert result.success is False

    def test_empty_audio_is_failure(self):
        """Test that empty audio bytes counts as failure."""
        from infrastructure.speech.local.edge_tts_fallback import SynthesisResult

        result = SynthesisResult(
            audio_bytes=b"",
            backend="edge-tts",
            latency_ms=100.0,
            voice="en-US-AriaNeural",
        )
        assert result.success is False


class TestLocalTTSFallbackInitialization:
    """Tests for LocalTTSFallback initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSFallback

        tts = LocalTTSFallback()
        assert tts.config.voice == "en-US-AriaNeural"

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        from infrastructure.speech.local.edge_tts_fallback import (
            LocalTTSFallback,
            LocalTTSConfig,
        )

        config = LocalTTSConfig(voice="en-GB-SoniaNeural", prefer_edge_tts=False)
        tts = LocalTTSFallback(config=config)
        assert tts.config.voice == "en-GB-SoniaNeural"
        assert tts.config.prefer_edge_tts is False


class TestLocalTTSFallbackBackendSelection:
    """Tests for backend selection logic."""

    def test_selects_edge_tts_when_available_and_preferred(self):
        """Test that edge-tts is selected when available and preferred."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            edge_tts_fallback.PYTTSX3_AVAILABLE = True

            tts = edge_tts_fallback.LocalTTSFallback()
            assert tts.get_backend() == "edge-tts"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_selects_pyttsx3_when_edge_not_preferred(self):
        """Test that pyttsx3 is selected when edge-tts not preferred."""
        from infrastructure.speech.local import edge_tts_fallback
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSConfig

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            edge_tts_fallback.PYTTSX3_AVAILABLE = True

            config = LocalTTSConfig(prefer_edge_tts=False)
            tts = edge_tts_fallback.LocalTTSFallback(config=config)
            assert tts.get_backend() == "pyttsx3"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_selects_pyttsx3_when_edge_unavailable(self):
        """Test that pyttsx3 is selected when edge-tts is unavailable."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = True

            tts = edge_tts_fallback.LocalTTSFallback()
            assert tts.get_backend() == "pyttsx3"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_selects_none_when_no_backend_available(self):
        """Test that 'none' is selected when no backend is available."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            assert tts.get_backend() == "none"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3


class TestLocalTTSFallbackAvailability:
    """Tests for availability checks."""

    def test_is_available_when_edge_installed(self):
        """Test is_available returns True when edge-tts is installed."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            assert tts.is_available() is True
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_is_available_when_pyttsx3_installed(self):
        """Test is_available returns True when pyttsx3 is installed."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = True

            tts = edge_tts_fallback.LocalTTSFallback()
            assert tts.is_available() is True
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_is_not_available_when_nothing_installed(self):
        """Test is_available returns False when nothing is installed."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            assert tts.is_available() is False
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3


class TestLocalTTSFallbackSynthesisSync:
    """Tests for synchronous synthesis."""

    def test_synthesize_returns_error_when_no_backend(self):
        """Test synthesize returns empty bytes when no backend available."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            result = tts.synthesize("Hello, world!")

            assert result == b""
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_synthesize_with_result_returns_error_details(self):
        """Test synthesize_with_result returns detailed error."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            result = tts.synthesize_with_result("Hello, world!")

            assert result.success is False
            assert result.error is not None
            assert "No TTS backend available" in result.error
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_synthesize_empty_text_returns_error(self):
        """Test that empty text returns error result."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSFallback

        tts = LocalTTSFallback()
        result = tts.synthesize_with_result("")

        assert result.success is False
        assert result.error == "Empty text provided"

    def test_synthesize_whitespace_text_returns_error(self):
        """Test that whitespace-only text returns error result."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSFallback

        tts = LocalTTSFallback()
        result = tts.synthesize_with_result("   ")

        assert result.success is False
        assert result.error == "Empty text provided"


class TestLocalTTSFallbackSynthesisAsync:
    """Tests for asynchronous synthesis."""

    async def test_async_synthesize_returns_error_when_no_backend(self):
        """Test async_synthesize returns empty bytes when no backend."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            result = await tts.async_synthesize("Hello, world!")

            assert result == b""
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    async def test_async_synthesize_with_result_returns_error_details(self):
        """Test async_synthesize_with_result returns detailed error."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            result = await tts.async_synthesize_with_result("Hello, world!")

            assert result.success is False
            assert result.error is not None
            assert "No TTS backend available" in result.error
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    async def test_async_synthesize_empty_text_returns_error(self):
        """Test that async with empty text returns error result."""
        from infrastructure.speech.local.edge_tts_fallback import LocalTTSFallback

        tts = LocalTTSFallback()
        result = await tts.async_synthesize_with_result("")

        assert result.success is False
        assert result.error == "Empty text provided"


class TestLocalTTSFallbackHealth:
    """Tests for health check functionality."""

    def test_health_when_edge_available(self):
        """Test health snapshot when edge-tts is available."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            health = tts.health()

            assert health["available"] is True
            assert health["backend"] == "edge-tts"
            assert health["edge_tts_available"] is True
            assert health["pyttsx3_available"] is False
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_health_when_both_available(self):
        """Test health snapshot when both backends are available."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = True
            edge_tts_fallback.PYTTSX3_AVAILABLE = True

            tts = edge_tts_fallback.LocalTTSFallback()
            health = tts.health()

            assert health["available"] is True
            assert health["edge_tts_available"] is True
            assert health["pyttsx3_available"] is True
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3

    def test_health_when_nothing_available(self):
        """Test health snapshot when nothing is available."""
        from infrastructure.speech.local import edge_tts_fallback

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            tts = edge_tts_fallback.LocalTTSFallback()
            health = tts.health()

            assert health["available"] is False
            assert health["backend"] == "none"
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3


class TestCreateLocalTTSFn:
    """Tests for create_local_tts_fn helper."""

    def test_create_returns_callable(self):
        """Test that create_local_tts_fn returns a callable."""
        from infrastructure.speech.local.edge_tts_fallback import create_local_tts_fn

        fn = create_local_tts_fn()
        assert callable(fn)

    def test_create_with_custom_config(self):
        """Test create_local_tts_fn with custom config."""
        from infrastructure.speech.local.edge_tts_fallback import (
            create_local_tts_fn,
            LocalTTSConfig,
        )

        config = LocalTTSConfig(voice="en-GB-SoniaNeural")
        fn = create_local_tts_fn(config=config)
        assert callable(fn)

    def test_created_fn_returns_bytes(self):
        """Test that created function returns bytes."""
        from infrastructure.speech.local import edge_tts_fallback
        from infrastructure.speech.local.edge_tts_fallback import create_local_tts_fn

        original_edge = edge_tts_fallback.EDGE_TTS_AVAILABLE
        original_pyttsx3 = edge_tts_fallback.PYTTSX3_AVAILABLE

        try:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = False
            edge_tts_fallback.PYTTSX3_AVAILABLE = False

            fn = create_local_tts_fn()
            result = fn("Hello")
            assert isinstance(result, bytes)
        finally:
            edge_tts_fallback.EDGE_TTS_AVAILABLE = original_edge
            edge_tts_fallback.PYTTSX3_AVAILABLE = original_pyttsx3


class TestModuleExports:
    """Tests for module exports."""

    def test_exports_from_init(self):
        """Test all expected symbols are exported from __init__."""
        from infrastructure.speech.local import (
            LocalTTSFallback,
            LocalTTSConfig,
            SynthesisResult,
            EDGE_TTS_AVAILABLE,
            PYTTSX3_AVAILABLE,
            create_local_tts_fn,
        )

        assert LocalTTSFallback is not None
        assert LocalTTSConfig is not None
        assert SynthesisResult is not None
        assert isinstance(EDGE_TTS_AVAILABLE, bool)
        assert isinstance(PYTTSX3_AVAILABLE, bool)
        assert callable(create_local_tts_fn)


class TestEdgeTTSVoices:
    """Tests for edge-tts voice configuration."""

    def test_edge_tts_voices_dict_exists(self):
        """Test that EDGE_TTS_VOICES dictionary exists."""
        from infrastructure.speech.local.edge_tts_fallback import EDGE_TTS_VOICES

        assert isinstance(EDGE_TTS_VOICES, dict)
        assert "en" in EDGE_TTS_VOICES
        assert "en-US" in EDGE_TTS_VOICES
        assert "en-GB" in EDGE_TTS_VOICES

    def test_edge_tts_voices_format(self):
        """Test that voice IDs have expected format."""
        from infrastructure.speech.local.edge_tts_fallback import EDGE_TTS_VOICES

        for lang, voice_id in EDGE_TTS_VOICES.items():
            # Voice IDs should end with "Neural"
            assert voice_id.endswith("Neural"), f"Voice {voice_id} for {lang} doesn't end with Neural"


class TestConfigIntegration:
    """Tests for integration with shared config."""

    def test_get_local_tts_config(self):
        """Test get_local_tts_config returns expected structure."""
        from shared.config.settings import get_local_tts_config

        config = get_local_tts_config()
        assert "voice" in config
        assert "rate" in config
        assert "volume" in config
        assert "pyttsx3_rate" in config
        assert "pyttsx3_volume" in config
        assert "prefer_edge_tts" in config

    def test_local_tts_enabled(self):
        """Test local_tts_enabled returns True when voice is configured."""
        from shared.config.settings import local_tts_enabled

        # Default voice is set, so it should be enabled
        assert local_tts_enabled() is True
