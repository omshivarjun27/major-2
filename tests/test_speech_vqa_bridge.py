"""
Tests for Speech-VQA Bridge Module
==================================

Tests for STT ↔ VQA ↔ TTS integration.
"""

import asyncio
import base64
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# Test Voice Router
# ============================================================================

class TestVoiceRouter:
    """Tests for intent detection and routing."""
    
    def test_import(self):
        """Test module imports successfully."""
        from core.speech import VoiceRouter, IntentType, RouteResult
        assert VoiceRouter is not None
    
    def test_visual_intent_detection(self):
        """Test detection of visual/VQA intents."""
        from core.speech import VoiceRouter, IntentType
        
        router = VoiceRouter()
        
        # Test visual queries
        visual_queries = [
            "What do you see in front of me?",
            "Describe what you see",
            "What is this object?",
            "Can you read this sign?",
            "What color is this?",
        ]
        
        for query in visual_queries:
            result = router.route(query)
            assert result.handler in ["vqa", "spatial"], f"Failed for: {query}"
    
    def test_spatial_intent_detection(self):
        """Test detection of spatial/navigation intents."""
        from core.speech import VoiceRouter, IntentType
        
        router = VoiceRouter()
        
        spatial_queries = [
            "Any obstacles ahead?",
            "Is the path clear?",
            "How far is the door?",
            "Which way should I go?",
            "Are there any hazards?",
        ]
        
        for query in spatial_queries:
            result = router.route(query)
            assert result.handler in ["spatial", "vqa"], f"Failed for: {query}"
    
    def test_priority_intent_detection(self):
        """Test detection of priority/urgent intents."""
        from core.speech import VoiceRouter, IntentType
        
        router = VoiceRouter()
        
        priority_queries = [
            "Quick scan",
            "Priority hazards",
            "Emergency check",
            "What are the main hazards?",
        ]
        
        for query in priority_queries:
            result = router.route(query)
            assert result.handler == "priority" or result.intent == IntentType.PRIORITY_SCAN, \
                f"Failed for: {query}"

    def test_qr_intent_detection(self):
        """Test detection of explicit QR/AR scan intents."""
        from core.speech import VoiceRouter, IntentType

        router = VoiceRouter()

        qr_queries = [
            "Scan this QR code",
            "Read the QR",
            "What does this code say?",
            "Scan the tag",
        ]

        for query in qr_queries:
            result = router.route(query)
            assert result.intent == IntentType.QR_SCAN, \
                f"Expected QR_SCAN for: '{query}', got {result.intent.name}"
            assert result.handler == "qr", \
                f"Expected handler 'qr' for: '{query}', got {result.handler}"

    def test_qr_not_triggered_by_surroundings(self):
        """Surroundings / spatial queries must NOT trigger QR scan."""
        from core.speech import VoiceRouter, IntentType

        router = VoiceRouter()

        non_qr_queries = [
            "What is around me?",
            "Describe my surroundings",
            "Any obstacles ahead?",
            "What do you see?",
        ]

        for query in non_qr_queries:
            result = router.route(query)
            assert result.intent != IntentType.QR_SCAN, \
                f"QR_SCAN incorrectly triggered for: '{query}'"

    def test_navigation_route_intent(self):
        """Test detection of guided navigation intents."""
        from core.speech import VoiceRouter, IntentType

        router = VoiceRouter()

        nav_queries = [
            "Take me to the exit",
            "Guide me to the door",
            "Help me get out",
            "Help me exit",
        ]

        for query in nav_queries:
            result = router.route(query)
            assert result.intent == IntentType.NAVIGATION_ROUTE, \
                f"Expected NAVIGATION_ROUTE for: '{query}', got {result.intent.name}"
            assert result.handler == "spatial", \
                f"Expected handler 'spatial' for nav route: '{query}', got {result.handler}"

    def test_toggle_mode_intent(self):
        """Test detection of mode toggle intents."""
        from core.speech import VoiceRouter, IntentType

        router = VoiceRouter()

        toggle_queries = [
            "Enable always-on",
            "Disable proactive",
            "Turn on proactive mode",
            "Turn off continuous mode",
        ]

        for query in toggle_queries:
            result = router.route(query)
            assert result.intent == IntentType.TOGGLE_MODE, \
                f"Expected TOGGLE_MODE for: '{query}', got {result.intent.name}"
            assert result.handler == "command", \
                f"Expected handler 'command' for toggle: '{query}', got {result.handler}"
    
    def test_general_intent_fallback(self):
        """Test fallback to general LLM for non-visual queries."""
        from core.speech import VoiceRouter, IntentType
        
        router = VoiceRouter()
        
        general_queries = [
            "Tell me a joke",
            "What time is it?",
            "How are you?",
        ]
        
        for query in general_queries:
            result = router.route(query)
            assert result.handler == "llm", f"Failed for: {query}"
    
    def test_route_result_structure(self):
        """Test RouteResult contains all required fields."""
        from core.speech import VoiceRouter
        
        router = VoiceRouter()
        result = router.route("What do you see?")
        
        assert hasattr(result, 'intent')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'handler')
        assert hasattr(result, 'query')
        assert hasattr(result, 'processed_query')
        assert hasattr(result, 'mode')
        assert hasattr(result, 'metadata')
        
        assert 0 <= result.confidence <= 1
    
    def test_is_visual_intent(self):
        """Test helper method for visual intent check."""
        from core.speech import VoiceRouter, IntentType
        
        router = VoiceRouter()
        
        assert router.is_visual_intent(IntentType.VISUAL_DESCRIBE)
        assert router.is_visual_intent(IntentType.SPATIAL_OBSTACLE)
        assert router.is_visual_intent(IntentType.QR_SCAN)
        assert router.is_visual_intent(IntentType.NAVIGATION_ROUTE)
        assert not router.is_visual_intent(IntentType.GENERAL_CHAT)
        assert not router.is_visual_intent(IntentType.TOGGLE_MODE)

    def test_is_qr_intent(self):
        """Test QR intent helper."""
        from core.speech import VoiceRouter, IntentType

        router = VoiceRouter()
        assert router.is_qr_intent(IntentType.QR_SCAN)
        assert not router.is_qr_intent(IntentType.VISUAL_DESCRIBE)
        assert not router.is_qr_intent(IntentType.SPATIAL_OBSTACLE)

    def test_is_toggle_intent(self):
        """Test toggle intent helper."""
        from core.speech import VoiceRouter, IntentType

        router = VoiceRouter()
        assert router.is_toggle_intent(IntentType.TOGGLE_MODE)
        assert not router.is_toggle_intent(IntentType.GENERAL_COMMAND)


# ============================================================================
# Test Speech Handler
# ============================================================================

class TestSpeechHandler:
    """Tests for STT processing."""
    
    def test_import(self):
        """Test module imports successfully."""
        from core.speech import SpeechHandler, SpeechConfig
        assert SpeechHandler is not None
    
    def test_config_defaults(self):
        """Test default configuration values."""
        from core.speech import SpeechConfig
        
        config = SpeechConfig()
        
        assert config.stt_model == "nova-3"
        assert config.sample_rate == 16000
        assert config.target_stt_latency_ms == 100.0
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initializes correctly."""
        from core.speech import SpeechHandler
        
        handler = SpeechHandler()
        await handler.initialize()
        
        assert handler._is_initialized
    
    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self):
        """Test handling of empty audio."""
        from core.speech import SpeechHandler
        
        handler = SpeechHandler()
        await handler.initialize()
        
        text, latency = await handler.transcribe_audio(b"")
        
        assert text == "" or text is None or isinstance(text, str)
        assert isinstance(latency, float)
    
    def test_stats_tracking(self):
        """Test statistics tracking."""
        from core.speech import SpeechHandler
        
        handler = SpeechHandler()
        stats = handler.get_stats()
        
        assert "total_transcriptions" in stats
        assert "avg_latency_ms" in stats
        assert "is_initialized" in stats


# ============================================================================
# Test TTS Handler
# ============================================================================

class TestTTSHandler:
    """Tests for TTS processing."""
    
    def test_import(self):
        """Test module imports successfully."""
        from core.speech import TTSHandler, TTSConfig
        assert TTSHandler is not None
    
    def test_config_defaults(self):
        """Test default configuration values."""
        from core.speech import TTSConfig
        
        config = TTSConfig()
        
        assert config.tts_model == "eleven_turbo_v2_5"
        assert config.target_tts_latency_ms == 100.0
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initializes correctly."""
        from core.speech import TTSHandler
        
        handler = TTSHandler()
        await handler.initialize()
        
        assert handler._is_initialized
    
    def test_text_preprocessing(self):
        """Test text preprocessing for TTS."""
        from core.speech import TTSHandler
        
        handler = TTSHandler()
        
        # Test markdown removal
        processed = handler._preprocess_text("**Bold** and *italic*")
        assert "**" not in processed
        assert "*" not in processed or "*" == processed  # Single asterisk edge case
        
        # Test unit conversion
        processed = handler._preprocess_text("5m away")
        assert "meters" in processed
    
    def test_stats_tracking(self):
        """Test statistics tracking."""
        from core.speech import TTSHandler
        
        handler = TTSHandler()
        stats = handler.get_stats()
        
        assert "total_generations" in stats
        assert "avg_latency_ms" in stats


# ============================================================================
# Test Response Formatter
# ============================================================================

class TestResponseFormatter:
    """Tests for TTS response formatting."""
    
    def test_import(self):
        """Test module imports successfully."""
        from core.speech import ResponseFormatter
        assert ResponseFormatter is not None
    
    def test_hazard_response_empty(self):
        """Test formatting with no hazards."""
        from core.speech import ResponseFormatter
        
        result = ResponseFormatter.format_hazard_response([])
        assert "clear" in result.lower()
    
    def test_hazard_response_single(self):
        """Test formatting with single hazard."""
        from core.speech import ResponseFormatter
        
        hazards = [{
            "name": "chair",
            "direction": "ahead",
            "distance_m": 2.5,
        }]
        
        result = ResponseFormatter.format_hazard_response(hazards)
        assert "chair" in result
        assert "ahead" in result
        assert "2.5" in result
    
    def test_hazard_response_multiple(self):
        """Test formatting with multiple hazards."""
        from core.speech import ResponseFormatter
        
        hazards = [
            {"name": "person", "direction": "left", "distance_m": 1.5},
            {"name": "table", "direction": "ahead", "distance_m": 3.0},
            {"name": "door", "direction": "right", "distance_m": 4.0},
        ]
        
        result = ResponseFormatter.format_hazard_response(hazards)
        assert "person" in result
        assert "table" in result
        assert "door" in result


# ============================================================================
# Test Voice Ask Pipeline
# ============================================================================

class TestVoiceAskPipeline:
    """Tests for end-to-end voice pipeline."""
    
    def test_import(self):
        """Test module imports successfully."""
        from core.speech import VoiceAskPipeline, VoiceAskConfig
        assert VoiceAskPipeline is not None
    
    def test_config_defaults(self):
        """Test default configuration values."""
        from core.speech import VoiceAskConfig
        
        config = VoiceAskConfig()
        
        assert config.target_total_latency == 500.0
        assert config.target_stt_latency == 100.0
        assert config.target_vqa_latency == 300.0
        assert config.target_tts_latency == 100.0
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """Test pipeline initializes correctly."""
        from core.speech import VoiceAskPipeline
        
        pipeline = VoiceAskPipeline()
        await pipeline.initialize()
        
        assert pipeline._is_initialized
    
    def test_stats_tracking(self):
        """Test statistics tracking."""
        from core.speech import VoiceAskPipeline
        
        pipeline = VoiceAskPipeline()
        stats = pipeline.get_stats()
        
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "success_rate" in stats
        assert "avg_latency_ms" in stats


# ============================================================================
# Test Telemetry
# ============================================================================

class TestVoiceAskTelemetry:
    """Tests for telemetry data."""
    
    def test_import(self):
        """Test module imports successfully."""
        from core.speech import VoiceAskTelemetry
        assert VoiceAskTelemetry is not None
    
    def test_telemetry_to_dict(self):
        """Test telemetry serialization."""
        from core.speech import VoiceAskTelemetry
        
        telemetry = VoiceAskTelemetry(
            request_id="test-001",
            timestamp=time.time(),
            stt_latency_ms=50.0,
            vqa_latency_ms=200.0,
            tts_latency_ms=80.0,
            total_latency_ms=330.0,
            success=True,
        )
        
        data = telemetry.to_dict()
        
        assert "request_id" in data
        assert "latencies" in data
        assert "targets_met" in data
        assert "success" in data


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
