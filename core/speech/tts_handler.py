"""
TTS Handler Module
==================

Handles Text-to-Speech conversion for VQA responses.
"""

import base64
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("tts-handler")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class TTSConfig:
    """Configuration for TTS processing."""

    # TTS settings
    tts_model: str = "eleven_turbo_v2_5"
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    # Audio settings
    output_format: str = "mp3_44100_128"
    sample_rate: int = 44100

    # Processing settings
    max_text_length: int = 500
    chunk_size: int = 150  # Characters per chunk

    # Latency targets
    target_tts_latency_ms: float = 100.0

    # Voice settings
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


# ============================================================================
# TTS Handler
# ============================================================================

class TTSHandler:
    """
    Handles text-to-speech conversion for VQA responses.

    Integrates with ElevenLabs TTS or other TTS providers.
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self._tts_client = None
        self._is_initialized = False

        # Metrics
        self._total_generations = 0
        self._avg_latency_ms = 0.0
        self._total_chars = 0

    async def initialize(self, tts_client=None):
        """
        Initialize TTS handler with optional client.

        Args:
            tts_client: Existing TTS client (e.g., ElevenLabs)
        """
        self._tts_client = tts_client
        self._is_initialized = True
        logger.info("TTS handler initialized")

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> Tuple[bytes, float]:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID override

        Returns:
            Tuple of (audio_bytes, latency_ms)
        """
        start_time = time.time()

        if not self._is_initialized:
            await self.initialize()

        try:
            # Preprocess text for TTS
            processed_text = self._preprocess_text(text)

            # Truncate if needed
            if len(processed_text) > self.config.max_text_length:
                processed_text = processed_text[:self.config.max_text_length] + "..."

            # Use voice ID or default
            voice = voice_id or self.config.voice_id

            # If we have an ElevenLabs client, use it
            if self._tts_client and hasattr(self._tts_client, 'generate'):
                audio_data = await self._synthesize_with_client(processed_text, voice)
            else:
                # Fallback to REST API
                audio_data = await self._synthesize_rest_api(processed_text, voice)

            latency_ms = (time.time() - start_time) * 1000

            # Update metrics
            self._total_generations += 1
            self._total_chars += len(processed_text)
            self._avg_latency_ms = (self._avg_latency_ms * 0.9) + (latency_ms * 0.1)

            logger.debug(f"TTS completed in {latency_ms:.1f}ms for {len(processed_text)} chars")

            return audio_data, latency_ms

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"TTS synthesis failed: {e}")
            return b"", latency_ms

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for better TTS output."""
        # Remove markdown
        import re
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)       # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)         # Code
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links

        # Replace technical notation
        text = text.replace(">=", "greater than or equal to")
        text = text.replace("<=", "less than or equal to")
        text = text.replace("->", "leading to")
        text = text.replace("=>", "implies")

        # Handle numbers with units
        text = re.sub(r'(\d+)m\b', r'\1 meters', text)
        text = re.sub(r'(\d+)cm\b', r'\1 centimeters', text)
        text = re.sub(r'(\d+)ft\b', r'\1 feet', text)
        text = re.sub(r'(\d+)%', r'\1 percent', text)

        # Clean up
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    async def _synthesize_with_client(
        self,
        text: str,
        voice_id: str,
    ) -> bytes:
        """Synthesize using existing TTS client."""
        try:
            # This assumes an ElevenLabs-like API
            audio = await self._tts_client.generate(
                text=text,
                voice=voice_id,
                model=self.config.tts_model,
            )

            # If it's a generator, collect chunks
            if hasattr(audio, '__aiter__'):
                chunks = []
                async for chunk in audio:
                    chunks.append(chunk)
                return b"".join(chunks)

            return audio

        except Exception as e:
            logger.warning(f"Client TTS failed, falling back to REST: {e}")
            return await self._synthesize_rest_api(text, voice_id)

    async def _synthesize_rest_api(
        self,
        text: str,
        voice_id: str,
    ) -> bytes:
        """Synthesize using ElevenLabs REST API."""
        try:
            import os

            import httpx

            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                logger.error("ELEVENLABS_API_KEY not set")
                return b""

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }

            payload = {
                "text": text,
                "model_id": self.config.tts_model,
                "voice_settings": {
                    "stability": self.config.stability,
                    "similarity_boost": self.config.similarity_boost,
                    "style": self.config.style,
                    "use_speaker_boost": self.config.use_speaker_boost,
                }
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                return response.content

        except Exception as e:
            logger.error(f"REST API TTS failed: {e}")
            return b""

    async def synthesize_to_base64(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Synthesize and return base64-encoded audio.

        Args:
            text: Text to convert
            voice_id: Optional voice ID

        Returns:
            Tuple of (base64_audio, latency_ms)
        """
        audio_data, latency_ms = await self.synthesize(text, voice_id)

        if audio_data:
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            return f"data:audio/mpeg;base64,{audio_base64}", latency_ms

        return "", latency_ms

    async def synthesize_streaming(
        self,
        text: str,
        voice_id: Optional[str] = None,
        chunk_callback: Optional[Callable[[bytes], None]] = None,
    ):
        """
        Stream TTS audio in chunks.

        Args:
            text: Text to convert
            voice_id: Optional voice ID
            chunk_callback: Optional callback for each audio chunk

        Yields:
            Audio chunks as bytes
        """
        try:
            import os

            import httpx

            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                logger.error("ELEVENLABS_API_KEY not set")
                return

            voice = voice_id or self.config.voice_id
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/stream"

            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json",
            }

            payload = {
                "text": self._preprocess_text(text),
                "model_id": self.config.tts_model,
                "voice_settings": {
                    "stability": self.config.stability,
                    "similarity_boost": self.config.similarity_boost,
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for chunk in response.aiter_bytes(1024):
                        if chunk_callback:
                            chunk_callback(chunk)
                        yield chunk

        except Exception as e:
            logger.error(f"Streaming TTS failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics."""
        return {
            "total_generations": self._total_generations,
            "total_chars": self._total_chars,
            "avg_latency_ms": round(self._avg_latency_ms, 1),
            "is_initialized": self._is_initialized,
            "has_client": self._tts_client is not None,
        }


# ============================================================================
# Response Formatter
# ============================================================================

class ResponseFormatter:
    """Formats VQA responses for optimal TTS output."""

    @staticmethod
    def format_hazard_response(hazards: List[Dict]) -> str:
        """Format hazard list for TTS."""
        if not hazards:
            return "Path appears clear. No immediate hazards detected."

        parts = []
        for i, hazard in enumerate(hazards[:3], 1):
            name = hazard.get("name", "obstacle")
            direction = hazard.get("direction", "ahead")
            distance = hazard.get("distance_m", 0)

            parts.append(f"{name} {direction}, {distance:.1f} meters away")

        if len(hazards) == 1:
            return f"Warning: {parts[0]}."
        else:
            return "Hazards detected: " + "; ".join(parts) + "."

    @staticmethod
    def format_scene_description(scene: Dict) -> str:
        """Format scene description for TTS."""
        objects = scene.get("objects", [])

        if not objects:
            return "I don't detect any significant objects in view."

        # Group by type
        people = [o for o in objects if o.get("class") == "person"]
        obstacles = [o for o in objects if o.get("is_obstacle")]
        others = [o for o in objects if not o.get("is_obstacle") and o.get("class") != "person"]

        parts = []

        if people:
            if len(people) == 1:
                parts.append("One person")
            else:
                parts.append(f"{len(people)} people")

        if obstacles:
            if len(obstacles) == 1:
                parts.append("one obstacle ahead")
            else:
                parts.append(f"{len(obstacles)} obstacles in the area")

        if others:
            names = list(set(o.get("class", "object") for o in others[:3]))
            parts.append(", ".join(names))

        return "I see: " + ", ".join(parts) + "."

    @staticmethod
    def format_navigation_instruction(instruction: str) -> str:
        """Format navigation instruction for clear TTS."""
        # Replace abbreviations
        instruction = instruction.replace("approx.", "approximately")
        instruction = instruction.replace("~", "about ")

        # Ensure proper sentence structure
        if not instruction.endswith(('.', '!', '?')):
            instruction += "."

        return instruction
