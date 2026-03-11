"""
Voice Ask Pipeline
==================

End-to-end voice query processing: STT → VQA → TTS
with latency optimization for real-time responses.
"""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .speech_handler import SpeechConfig, SpeechHandler
from .tts_handler import ResponseFormatter, TTSConfig, TTSHandler
from .voice_router import IntentType, RouteResult, VoiceRouter

logger = logging.getLogger("voice-ask")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class VoiceAskConfig:
    """Configuration for voice ask pipeline."""

    # Component configs
    speech_config: SpeechConfig = field(default_factory=SpeechConfig)
    tts_config: TTSConfig = field(default_factory=TTSConfig)

    # Pipeline settings
    enable_intent_routing: bool = True
    enable_response_formatting: bool = True

    # Latency targets (ms)
    target_stt_latency: float = 100.0
    target_vqa_latency: float = 300.0
    target_tts_latency: float = 100.0
    target_total_latency: float = 500.0

    # Timeout settings
    stt_timeout: float = 5.0
    vqa_timeout: float = 10.0
    tts_timeout: float = 5.0


# ============================================================================
# Telemetry
# ============================================================================

@dataclass
class VoiceAskTelemetry:
    """Telemetry data for voice ask request."""

    request_id: str
    timestamp: float

    # Latencies (ms)
    stt_latency_ms: float = 0.0
    routing_latency_ms: float = 0.0
    vqa_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    # Results
    transcribed_text: str = ""
    intent: str = ""
    intent_confidence: float = 0.0
    handler: str = ""
    response_text: str = ""

    # Status
    success: bool = False
    error: Optional[str] = None

    # Targets met
    stt_target_met: bool = False
    vqa_target_met: bool = False
    tts_target_met: bool = False
    total_target_met: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "latencies": {
                "stt_ms": round(self.stt_latency_ms, 1),
                "routing_ms": round(self.routing_latency_ms, 1),
                "vqa_ms": round(self.vqa_latency_ms, 1),
                "tts_ms": round(self.tts_latency_ms, 1),
                "total_ms": round(self.total_latency_ms, 1),
            },
            "targets_met": {
                "stt": self.stt_target_met,
                "vqa": self.vqa_target_met,
                "tts": self.tts_target_met,
                "total": self.total_target_met,
            },
            "intent": {
                "type": self.intent,
                "confidence": round(self.intent_confidence, 2),
                "handler": self.handler,
            },
            "transcription": self.transcribed_text,
            "response": self.response_text[:100] + "..." if len(self.response_text) > 100 else self.response_text,
            "success": self.success,
            "error": self.error,
        }


# ============================================================================
# Voice Ask Pipeline
# ============================================================================

class VoiceAskPipeline:
    """
    End-to-end voice query pipeline.

    Flow: Audio Input → STT → Intent Routing → VQA/LLM → TTS → Audio Output

    Target latency: 500ms total
    """

    def __init__(
        self,
        config: Optional[VoiceAskConfig] = None,
        vqa_handler=None,
        spatial_handler=None,
        priority_handler=None,
        llm_handler=None,
    ):
        self.config = config or VoiceAskConfig()

        # Initialize components
        self.speech_handler = SpeechHandler(self.config.speech_config)
        self.voice_router = VoiceRouter()
        self.tts_handler = TTSHandler(self.config.tts_config)
        self.formatter = ResponseFormatter()

        # External handlers
        self._vqa_handler = vqa_handler
        self._spatial_handler = spatial_handler
        self._priority_handler = priority_handler
        self._llm_handler = llm_handler

        # State
        self._is_initialized = False
        self._request_counter = 0

        # Metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._latency_history: List[float] = []
        self._LATENCY_HISTORY_MAX = 200  # bounded to last 200 entries

    async def initialize(
        self,
        stt_client=None,
        tts_client=None,
        vqa_handler=None,
        spatial_handler=None,
        priority_handler=None,
        llm_handler=None,
    ):
        """
        Initialize all pipeline components.

        Args:
            stt_client: STT client (e.g., Deepgram)
            tts_client: TTS client (e.g., ElevenLabs)
            vqa_handler: VQA processing handler
            spatial_handler: Spatial analysis handler
            priority_handler: Priority scene handler
            llm_handler: General LLM handler
        """
        await self.speech_handler.initialize(stt_client)
        await self.tts_handler.initialize(tts_client)

        if vqa_handler:
            self._vqa_handler = vqa_handler
        if spatial_handler:
            self._spatial_handler = spatial_handler
        if priority_handler:
            self._priority_handler = priority_handler
        if llm_handler:
            self._llm_handler = llm_handler

        self._is_initialized = True
        logger.info("Voice ask pipeline initialized")

    async def process_audio(
        self,
        audio_bytes: bytes,
        image_bytes: Optional[bytes] = None,
        sample_rate: int = 16000,
        return_audio: bool = True,
    ) -> Tuple[str, Optional[bytes], VoiceAskTelemetry]:
        """
        Process audio query end-to-end.

        Args:
            audio_bytes: Raw audio input
            image_bytes: Optional image for VQA
            sample_rate: Audio sample rate
            return_audio: Whether to return TTS audio

        Returns:
            Tuple of (response_text, audio_bytes, telemetry)
        """
        start_time = time.time()
        self._request_counter += 1
        self._total_requests += 1

        telemetry = VoiceAskTelemetry(
            request_id=f"va-{self._request_counter:06d}",
            timestamp=start_time,
        )

        try:
            # Step 1: STT
            time.time()
            text, stt_latency = await asyncio.wait_for(
                self.speech_handler.transcribe_audio(audio_bytes, sample_rate),
                timeout=self.config.stt_timeout,
            )
            telemetry.stt_latency_ms = stt_latency
            telemetry.transcribed_text = text
            telemetry.stt_target_met = stt_latency <= self.config.target_stt_latency

            if not text:
                telemetry.error = "STT returned empty result"
                return "", None, telemetry

            # Step 2: Intent Routing
            route_start = time.time()
            route_result = self.voice_router.route(text)
            telemetry.routing_latency_ms = (time.time() - route_start) * 1000
            telemetry.intent = route_result.intent.name
            telemetry.intent_confidence = route_result.confidence
            telemetry.handler = route_result.handler

            # Step 3: Process with appropriate handler
            vqa_start = time.time()
            response_text = await self._dispatch_to_handler(
                route_result,
                image_bytes,
            )
            telemetry.vqa_latency_ms = (time.time() - vqa_start) * 1000
            telemetry.vqa_target_met = telemetry.vqa_latency_ms <= self.config.target_vqa_latency
            telemetry.response_text = response_text

            # Step 4: TTS
            audio_output = None
            if return_audio and response_text:
                time.time()
                audio_output, tts_latency = await asyncio.wait_for(
                    self.tts_handler.synthesize(response_text),
                    timeout=self.config.tts_timeout,
                )
                telemetry.tts_latency_ms = tts_latency
                telemetry.tts_target_met = tts_latency <= self.config.target_tts_latency

            # Calculate totals
            telemetry.total_latency_ms = (time.time() - start_time) * 1000
            telemetry.total_target_met = telemetry.total_latency_ms <= self.config.target_total_latency
            telemetry.success = True

            self._successful_requests += 1
            self._latency_history.append(telemetry.total_latency_ms)
            # Trim to bounded size
            if len(self._latency_history) > self._LATENCY_HISTORY_MAX:
                self._latency_history = self._latency_history[-self._LATENCY_HISTORY_MAX:]

            logger.info(
                f"Voice ask completed in {telemetry.total_latency_ms:.0f}ms "
                f"(STT:{telemetry.stt_latency_ms:.0f}, VQA:{telemetry.vqa_latency_ms:.0f}, "
                f"TTS:{telemetry.tts_latency_ms:.0f})"
            )

            return response_text, audio_output, telemetry

        except asyncio.TimeoutError:
            telemetry.total_latency_ms = (time.time() - start_time) * 1000
            telemetry.error = "Request timed out"
            logger.error("Voice ask request timed out")
            return "", None, telemetry

        except Exception as e:
            telemetry.total_latency_ms = (time.time() - start_time) * 1000
            telemetry.error = str(e)
            logger.error(f"Voice ask failed: {e}")
            return "", None, telemetry

    async def _dispatch_to_handler(
        self,
        route_result: RouteResult,
        image_bytes: Optional[bytes],
    ) -> str:
        """Dispatch query to appropriate handler."""
        handler = route_result.handler
        query = route_result.processed_query
        mode = route_result.mode

        try:
            if handler == "priority" and self._priority_handler:
                result = await self._priority_handler(image_bytes, query)
                return self.formatter.format_hazard_response(result.get("hazards", []))

            elif handler == "spatial" and self._spatial_handler:
                result = await self._spatial_handler(image_bytes, query, mode)
                if mode == "hazards":
                    return self.formatter.format_hazard_response(result.get("hazards", []))
                return result.get("description", "Unable to analyze spatial information.")

            elif handler == "vqa" and self._vqa_handler:
                result = await self._vqa_handler(image_bytes, query, mode)
                return result.get("answer", "Unable to process visual query.")

            elif handler == "llm" and self._llm_handler:
                result = await self._llm_handler(query)
                return result.get("response", "I'm sorry, I couldn't process that request.")

            else:
                # Fallback response
                return self._generate_fallback_response(route_result)

        except Exception as e:
            logger.error(f"Handler {handler} failed: {e}")
            return "I'm having trouble processing that request. Please try again."

    def _generate_fallback_response(self, route_result: RouteResult) -> str:
        """Generate fallback response when handlers unavailable."""
        intent = route_result.intent

        if self.voice_router.is_visual_intent(intent):
            return "Visual processing is currently unavailable. Please try again."
        elif intent == IntentType.GENERAL_HELP:
            return "I can help you with visual descriptions, obstacle detection, and navigation assistance."
        else:
            return "I'm sorry, I couldn't process that request."

    async def process_base64_audio(
        self,
        audio_base64: str,
        image_base64: Optional[str] = None,
        sample_rate: int = 16000,
    ) -> Dict[str, Any]:
        """
        Process base64-encoded audio.

        Args:
            audio_base64: Base64-encoded audio
            image_base64: Optional base64-encoded image
            sample_rate: Audio sample rate

        Returns:
            Response dict with audio and telemetry
        """
        # Decode audio
        if "," in audio_base64:
            audio_base64 = audio_base64.split(",", 1)[1]
        audio_bytes = base64.b64decode(audio_base64)

        # Decode image if provided
        image_bytes = None
        if image_base64:
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            image_bytes = base64.b64decode(image_base64)

        # Process
        response_text, audio_output, telemetry = await self.process_audio(
            audio_bytes,
            image_bytes,
            sample_rate,
        )

        # Encode output
        response_audio_base64 = ""
        if audio_output:
            response_audio_base64 = base64.b64encode(audio_output).decode('utf-8')

        return {
            "spoken_response": response_text,
            "audio_base64": response_audio_base64,
            "telemetry": telemetry.to_dict(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        avg_latency = 0.0
        if self._latency_history:
            avg_latency = sum(self._latency_history[-100:]) / len(self._latency_history[-100:])

        return {
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "success_rate": self._successful_requests / max(1, self._total_requests),
            "avg_latency_ms": round(avg_latency, 1),
            "speech_handler": self.speech_handler.get_stats(),
            "tts_handler": self.tts_handler.get_stats(),
            "router": self.voice_router.get_stats(),
        }
