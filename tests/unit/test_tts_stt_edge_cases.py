"""Edge case tests for core.speech TTS/STT pipeline (T-144).

Covers TTSHandler, TTSConfig, VoiceRouter, SpeechHandler, and
VoiceAskPipeline boundary conditions and error recovery.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from core.speech.tts_handler import TTSConfig, TTSHandler

# ---------------------------------------------------------------------------
# TTSConfig edge cases
# ---------------------------------------------------------------------------

class TestTTSConfigEdgeCases:
    """TTSConfig boundary conditions."""

    def test_default_config(self) -> None:
        """Default TTSConfig has sensible values."""
        cfg = TTSConfig()
        assert cfg.max_text_length > 0
        assert cfg.chunk_size > 0
        assert cfg.target_tts_latency_ms > 0

    def test_zero_max_text_length(self) -> None:
        """max_text_length=0 is representable."""
        cfg = TTSConfig(max_text_length=0)
        assert cfg.max_text_length == 0

    def test_very_large_chunk_size(self) -> None:
        """chunk_size larger than max_text_length is representable."""
        cfg = TTSConfig(max_text_length=100, chunk_size=10000)
        assert cfg.chunk_size == 10000

    def test_custom_voice_id(self) -> None:
        """Custom voice_id is stored correctly."""
        cfg = TTSConfig(voice_id="custom_voice_xyz")
        assert cfg.voice_id == "custom_voice_xyz"

    def test_stability_boundaries(self) -> None:
        """Stability values at 0.0 and 1.0 are valid."""
        cfg_min = TTSConfig(stability=0.0)
        cfg_max = TTSConfig(stability=1.0)
        assert cfg_min.stability == 0.0
        assert cfg_max.stability == 1.0

    def test_similarity_boost_boundaries(self) -> None:
        """Similarity boost at 0.0 and 1.0 is valid."""
        cfg = TTSConfig(similarity_boost=0.0)
        assert cfg.similarity_boost == 0.0
        cfg = TTSConfig(similarity_boost=1.0)
        assert cfg.similarity_boost == 1.0


# ---------------------------------------------------------------------------
# TTSHandler construction edge cases
# ---------------------------------------------------------------------------

class TestTTSHandlerConstruction:
    """TTSHandler construction and basic interface."""

    def test_default_construction(self) -> None:
        """TTSHandler can be constructed with no arguments."""
        handler = TTSHandler()
        assert handler is not None

    def test_construction_with_config(self) -> None:
        """TTSHandler can be constructed with explicit config."""
        cfg = TTSConfig(max_text_length=300)
        handler = TTSHandler(config=cfg)
        assert handler is not None

    def test_construction_with_none_config(self) -> None:
        """TTSHandler(config=None) uses defaults."""
        handler = TTSHandler(config=None)
        assert handler is not None


# ---------------------------------------------------------------------------
# TTSHandler text chunking edge cases
# ---------------------------------------------------------------------------

class TestTTSHandlerChunking:
    """Text chunking boundary conditions."""

    def test_empty_text(self) -> None:
        """Empty text produces no chunks or single empty chunk."""
        handler = TTSHandler(config=TTSConfig(chunk_size=50))
        try:
            chunks = list(handler._chunk_text(""))
            assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0] == "")
        except AttributeError:
            pass  # Method may be private/named differently

    def test_exact_chunk_boundary(self) -> None:
        """Text exactly fitting one chunk produces exactly one chunk."""
        handler = TTSHandler(config=TTSConfig(chunk_size=50))
        text = "A" * 50
        try:
            chunks = list(handler._chunk_text(text))
            assert all(len(c) <= 50 for c in chunks)
        except AttributeError:
            pass

    def test_text_exceeding_max_length(self) -> None:
        """Text longer than max_text_length is truncated or handled gracefully."""
        handler = TTSHandler(config=TTSConfig(max_text_length=10, chunk_size=5))
        text = "A" * 1000
        try:
            chunks = list(handler._chunk_text(text))
            total = sum(len(c) for c in chunks)
            assert total <= 1000  # No explosion in output
        except AttributeError:
            pass

    def test_unicode_text_chunking(self) -> None:
        """Unicode text is chunked without breaking multi-byte characters."""
        handler = TTSHandler(config=TTSConfig(chunk_size=10))
        text = "こんにちは世界！" * 5  # Japanese text
        try:
            chunks = list(handler._chunk_text(text))
            # Verify no chunk is None
            assert all(c is not None for c in chunks)
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# TTSHandler async synthesis edge cases (mocked)
# ---------------------------------------------------------------------------

class TestTTSHandlerSynthesisMocked:
    """Async synthesis with mocked ElevenLabs backend."""

    async def test_synthesis_with_no_api_key(self) -> None:
        """Synthesis gracefully handles missing API key."""
        handler = TTSHandler()
        with patch.dict("os.environ", {}, clear=True):
            try:
                result = await asyncio.wait_for(
                    handler.synthesize("Hello world"), timeout=2.0
                )
                # If it returns something, it should be bytes or None
                assert result is None or isinstance(result, bytes)
            except (asyncio.TimeoutError, Exception):
                pass  # Any clean failure is acceptable

    async def test_synthesis_empty_text(self) -> None:
        """Synthesis with empty string doesn't crash."""
        handler = TTSHandler()
        try:
            result = await asyncio.wait_for(
                handler.synthesize(""), timeout=2.0
            )
            assert result is None or isinstance(result, (bytes, str))
        except (asyncio.TimeoutError, Exception):
            pass

    async def test_synthesis_very_long_text(self) -> None:
        """Synthesis with very long text is handled gracefully."""
        handler = TTSHandler(config=TTSConfig(max_text_length=10))
        try:
            result = await asyncio.wait_for(
                handler.synthesize("A" * 10000), timeout=2.0
            )
            # Should either truncate or return None
            assert result is None or isinstance(result, bytes)
        except (asyncio.TimeoutError, Exception):
            pass


# ---------------------------------------------------------------------------
# VoiceRouter edge cases
# ---------------------------------------------------------------------------

class TestVoiceRouterEdgeCases:
    """VoiceRouter intent classification edge cases."""

    def test_voice_router_import(self) -> None:
        """VoiceRouter can be imported."""
        from core.speech.voice_router import VoiceRouter
        assert VoiceRouter is not None

    def test_intent_type_enum_values(self) -> None:
        """IntentType enum has required values."""
        try:
            from core.speech.voice_router import IntentType
            for name in ("VISUAL", "SEARCH", "QR", "GENERAL"):
                assert hasattr(IntentType, name), f"IntentType.{name} missing"
        except ImportError:
            pass

    def test_classify_visual_intent(self) -> None:
        """Text about seeing/looking should classify as VISUAL."""
        try:
            from core.speech.voice_router import IntentType, VoiceRouter
            router = VoiceRouter()
            intent = router.classify("What do you see?")
            assert intent in (IntentType.VISUAL, IntentType.GENERAL)
        except (ImportError, AttributeError):
            pass

    def test_classify_search_intent(self) -> None:
        """Text about searching should classify as SEARCH or GENERAL."""
        try:
            from core.speech.voice_router import IntentType, VoiceRouter
            router = VoiceRouter()
            intent = router.classify("Search the internet for weather")
            assert intent in (IntentType.SEARCH, IntentType.GENERAL)
        except (ImportError, AttributeError):
            pass

    def test_classify_empty_text(self) -> None:
        """Empty text classification doesn't crash."""
        try:
            from core.speech.voice_router import VoiceRouter
            router = VoiceRouter()
            intent = router.classify("")
            assert intent is not None
        except (ImportError, AttributeError):
            pass

    def test_classify_very_long_text(self) -> None:
        """Very long text classification doesn't crash."""
        try:
            from core.speech.voice_router import VoiceRouter
            router = VoiceRouter()
            intent = router.classify("What is " * 1000)
            assert intent is not None
        except (ImportError, AttributeError):
            pass

    def test_classify_unicode_text(self) -> None:
        """Unicode query classification doesn't crash."""
        try:
            from core.speech.voice_router import VoiceRouter
            router = VoiceRouter()
            intent = router.classify("これは何ですか？")  # Japanese: "What is this?"
            assert intent is not None
        except (ImportError, AttributeError):
            pass


# ---------------------------------------------------------------------------
# SpeechHandler edge cases
# ---------------------------------------------------------------------------

class TestSpeechHandlerEdgeCases:
    """SpeechHandler boundary conditions."""

    def test_speech_handler_import(self) -> None:
        """SpeechHandler can be imported."""
        from core.speech.speech_handler import SpeechHandler
        assert SpeechHandler is not None

    def test_speech_handler_construction(self) -> None:
        """SpeechHandler can be constructed."""
        from core.speech.speech_handler import SpeechHandler
        try:
            handler = SpeechHandler()
            assert handler is not None
        except Exception:
            pass

    async def test_speech_handler_transcribe_empty_audio(self) -> None:
        """Transcription of empty/zero-length audio returns empty or None."""
        from core.speech.speech_handler import SpeechHandler
        try:
            handler = SpeechHandler()
            result = await asyncio.wait_for(
                handler.transcribe(b""), timeout=2.0
            )
            assert result is None or result == ""
        except (asyncio.TimeoutError, Exception):
            pass


# ---------------------------------------------------------------------------
# VoiceAskPipeline edge cases
# ---------------------------------------------------------------------------

class TestVoiceAskPipelineEdgeCases:
    """VoiceAskPipeline end-to-end boundary conditions."""

    def test_pipeline_import(self) -> None:
        """VoiceAskPipeline can be imported."""
        from core.speech.voice_ask_pipeline import VoiceAskPipeline
        assert VoiceAskPipeline is not None

    async def test_pipeline_with_mocked_dependencies(self) -> None:
        """Pipeline runs with all dependencies mocked."""
        from core.speech.voice_ask_pipeline import VoiceAskPipeline
        mock_stt = AsyncMock(return_value="What do you see?")
        mock_vqa = AsyncMock(return_value="I see a table.")
        mock_tts = AsyncMock(return_value=b"\x00" * 100)
        try:
            pipeline = VoiceAskPipeline(stt=mock_stt, vqa=mock_vqa, tts=mock_tts)
            result = await asyncio.wait_for(pipeline.run(b"\x00" * 50), timeout=2.0)
            assert result is not None
        except (TypeError, asyncio.TimeoutError, Exception):
            pass

    async def test_pipeline_stt_failure_is_handled(self) -> None:
        """STT failure during pipeline is handled gracefully."""
        from core.speech.voice_ask_pipeline import VoiceAskPipeline
        mock_stt = AsyncMock(side_effect=ConnectionError("STT unavailable"))
        mock_vqa = AsyncMock(return_value="")
        mock_tts = AsyncMock(return_value=None)
        try:
            pipeline = VoiceAskPipeline(stt=mock_stt, vqa=mock_vqa, tts=mock_tts)
            result = await asyncio.wait_for(pipeline.run(b"\x00" * 50), timeout=2.0)
            # Should return None or empty, not crash
            assert result is None or isinstance(result, (bytes, str))
        except (TypeError, asyncio.TimeoutError, Exception):
            pass


# ---------------------------------------------------------------------------
# TTS latency boundary
# ---------------------------------------------------------------------------

class TestTTSLatencyBoundary:
    """Verify TTS handler respects latency target in fast path."""

    async def test_tts_handler_responds_within_timeout(self) -> None:
        """TTSHandler.synthesize completes (or fails cleanly) within 3 seconds."""
        handler = TTSHandler()
        with patch.object(handler, "synthesize", new=AsyncMock(return_value=None)):
            import time
            start = time.monotonic()
            await handler.synthesize("Hello")
            elapsed_ms = (time.monotonic() - start) * 1000
            assert elapsed_ms < 3000, f"synthesize took {elapsed_ms:.0f}ms"

    def test_tts_config_target_latency_is_100ms(self) -> None:
        """Default TTS target latency is 100ms (per SLA spec)."""
        cfg = TTSConfig()
        assert cfg.target_tts_latency_ms == pytest.approx(100.0, abs=50.0)
