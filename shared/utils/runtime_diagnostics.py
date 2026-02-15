"""
Runtime Diagnostics Module
===========================

Provides preflight checks, structured status reporting, and runtime
monitoring for TTS and VQA components.

Emits machine-readable JSON diagnostics + human-readable summaries
on every startup and error event.

Usage::

    from shared.utils.runtime_diagnostics import RuntimeDiagnostics
    diag = RuntimeDiagnostics()
    status = await diag.run_all_preflight()
    print(status.to_json())
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import struct
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("runtime-diagnostics")


# ============================================================================
# Enums & Constants
# ============================================================================

class SystemHealth(str, Enum):
    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"


class VQASkipCode(str, Enum):
    SKIP_NO_FRAME = "SKIP_NO_FRAME"
    SKIP_MODEL_LOAD = "SKIP_MODEL_LOAD"
    SKIP_SHAPE_MISMATCH = "SKIP_SHAPE_MISMATCH"
    SKIP_TIMEOUT = "SKIP_TIMEOUT"
    SKIP_RESOURCE = "SKIP_RESOURCE"
    SKIP_DEP_MISSING = "SKIP_DEP_MISSING"


SKIP_REMEDIATION = {
    VQASkipCode.SKIP_NO_FRAME: "Camera returned empty frames; check camera permissions/hardware. "
                                "Try: python -c \"import cv2; c=cv2.VideoCapture(0); print(c.read())\"",
    VQASkipCode.SKIP_MODEL_LOAD: "Model failed to load or checksum mismatch; check weights path and memory. "
                                  "Try: python -c \"from core.vqa import create_perception_pipeline; "
                                  "p=create_perception_pipeline(use_mock=True); print(p)\"",
    VQASkipCode.SKIP_SHAPE_MISMATCH: "Unexpected input shape/dtype; add resize/convert in pipeline. "
                                      "Verify frame dtype (uint8) and shape (H,W,3).",
    VQASkipCode.SKIP_TIMEOUT: "Warmup inference timed out; increase timeout or reduce model size. "
                               "Try: WARMUP_TIMEOUT_S=30 python app.py dev",
    VQASkipCode.SKIP_RESOURCE: "Insufficient GPU/CPU/memory for model load. "
                                "Try reducing batch size or using a lighter model variant.",
    VQASkipCode.SKIP_DEP_MISSING: "Required dependency not present or version mismatch. "
                                   "Run: pip install -r requirements.txt",
}

# Valid TTS sample rates
VALID_SAMPLE_RATES = {8000, 16000, 22050, 24000, 44100, 48000}

# TTS chunk size targets (ms)
TTS_CHUNK_TARGET_MS = 40
TTS_LATENCY_TARGET_MS = 250
TTS_STREAM_CHUNK_TARGET_MS = 100
TTS_JITTER_MAX_MS = 50


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TTSPreflightResult:
    """TTS preflight check results."""
    ready: bool = False
    sample_rate: int = 0
    expected_sample_rate: int = 44100
    sample_rate_match: bool = False
    codec: str = "unknown"
    codec_compatible: bool = False
    chunk_ms: float = 0.0
    chunk_strategy: str = "fixed"
    jitter_buffer_ms: int = 200
    provider: str = "unknown"
    model: str = "unknown"
    voice_id: str = ""
    latency_target_ms: float = TTS_LATENCY_TARGET_MS
    stream_chunk_target_ms: float = TTS_STREAM_CHUNK_TARGET_MS
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": "tts",
            "ready": self.ready,
            "sample_rate": self.sample_rate,
            "expected_sample_rate": self.expected_sample_rate,
            "sample_rate_match": self.sample_rate_match,
            "codec": self.codec,
            "codec_compatible": self.codec_compatible,
            "chunk_ms": self.chunk_ms,
            "chunk_strategy": self.chunk_strategy,
            "jitter_buffer_ms": self.jitter_buffer_ms,
            "provider": self.provider,
            "model": self.model,
            "voice_id": self.voice_id,
            "latency_target_ms": self.latency_target_ms,
            "stream_chunk_target_ms": self.stream_chunk_target_ms,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class TTSEventLog:
    """Structured TTS event for debug logging."""
    event: str = "unknown"
    timestamp: float = 0.0
    sample_rate: int = 0
    codec: str = "unknown"
    chunk_ms: float = 0.0
    chunks_sent: int = 0
    chunks_played: int = 0
    jitter_ms: float = 0.0
    packet_loss: float = 0.0
    last_error_code: Optional[str] = None
    waveform_rms: float = 0.0
    waveform_peak: float = 0.0
    waveform_clipping_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": "tts",
            "event": self.event,
            "timestamp": self.timestamp,
            "sample_rate": self.sample_rate,
            "codec": self.codec,
            "chunk_ms": self.chunk_ms,
            "chunks_sent": self.chunks_sent,
            "chunks_played": self.chunks_played,
            "jitter_ms": round(self.jitter_ms, 2),
            "packet_loss": round(self.packet_loss, 4),
            "last_error": self.last_error_code,
            "waveform_stats": {
                "rms": round(self.waveform_rms, 4),
                "peak": round(self.waveform_peak, 4),
                "clipping_pct": round(self.waveform_clipping_pct, 4),
            },
        }


@dataclass
class VQAPreflightResult:
    """VQA preflight check results."""
    status: str = "skipped"  # "ready" | "skipped"
    skip_code: Optional[str] = None
    message: str = ""
    frame_ok: bool = False
    model_loaded: bool = False
    warmup_ms: float = 0.0
    input_shape: Optional[str] = None
    input_dtype: Optional[str] = None
    detectors_loaded: List[str] = field(default_factory=list)
    detectors_missing: List[str] = field(default_factory=list)
    remediation: str = ""
    reproduce_command: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": "vqa",
            "status": self.status,
            "skip_code": self.skip_code,
            "message": self.message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "metrics": {
                "frame_ok": self.frame_ok,
                "model_loaded": self.model_loaded,
                "warmup_ms": round(self.warmup_ms, 2),
                "input_shape": self.input_shape,
                "input_dtype": self.input_dtype,
                "detectors_loaded": self.detectors_loaded,
                "detectors_missing": self.detectors_missing,
            },
            "remediation": self.remediation,
            "reproduce_command": self.reproduce_command,
            "errors": self.errors,
        }


@dataclass
class SystemStatus:
    """Consolidated system startup status."""
    system_status: str = "OK"
    tts: Optional[TTSPreflightResult] = None
    vqa: Optional[VQAPreflightResult] = None
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    startup_time_ms: float = 0.0
    human_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_status": self.system_status,
            "startup_time_ms": round(self.startup_time_ms, 2),
            "components": {
                "tts": self.tts.to_dict() if self.tts else {},
                "vqa": self.vqa.to_dict() if self.vqa else {},
                **self.components,
            },
            "human_summary": self.human_summary,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ============================================================================
# Audio Analysis Utilities
# ============================================================================

def analyze_audio_chunk(audio_bytes: bytes, sample_rate: int = 16000,
                        sample_width: int = 2) -> Dict[str, float]:
    """Analyze audio chunk for waveform statistics.

    Returns dict with rms, peak, and clipping_pct.
    """
    if not audio_bytes or len(audio_bytes) < sample_width:
        return {"rms": 0.0, "peak": 0.0, "clipping_pct": 0.0}

    num_samples = len(audio_bytes) // sample_width
    if num_samples == 0:
        return {"rms": 0.0, "peak": 0.0, "clipping_pct": 0.0}

    # Parse PCM16 samples
    try:
        fmt = f"<{num_samples}h"
        samples = struct.unpack(fmt, audio_bytes[:num_samples * sample_width])
    except struct.error:
        return {"rms": 0.0, "peak": 0.0, "clipping_pct": 0.0}

    max_val = 32767.0
    abs_samples = [abs(s) for s in samples]
    peak = max(abs_samples) / max_val
    rms = math.sqrt(sum(s * s for s in samples) / num_samples) / max_val

    # Clipping detection: samples at or near max amplitude
    clip_threshold = 0.99 * max_val
    clipped = sum(1 for s in abs_samples if s >= clip_threshold)
    clipping_pct = clipped / num_samples

    return {
        "rms": rms,
        "peak": peak,
        "clipping_pct": clipping_pct,
    }


def apply_soft_fade(audio_bytes: bytes, fade_ms: float = 4.0,
                     sample_rate: int = 16000, sample_width: int = 2,
                     fade_in: bool = True, fade_out: bool = True) -> bytes:
    """Apply soft fade-in/out on chunk boundaries to prevent clicks.

    Args:
        audio_bytes: Raw PCM16 audio
        fade_ms: Fade duration in milliseconds (2-8ms recommended)
        sample_rate: Audio sample rate
        sample_width: Bytes per sample (2 for PCM16)
        fade_in: Apply fade-in at start
        fade_out: Apply fade-out at end

    Returns:
        Modified PCM16 audio bytes
    """
    if not audio_bytes or len(audio_bytes) < sample_width * 4:
        return audio_bytes

    num_samples = len(audio_bytes) // sample_width
    fade_samples = max(1, int(sample_rate * fade_ms / 1000))
    fade_samples = min(fade_samples, num_samples // 4)

    try:
        fmt = f"<{num_samples}h"
        samples = list(struct.unpack(fmt, audio_bytes[:num_samples * sample_width]))
    except struct.error:
        return audio_bytes

    if fade_in:
        for i in range(fade_samples):
            gain = i / fade_samples
            samples[i] = int(samples[i] * gain)

    if fade_out:
        for i in range(fade_samples):
            gain = i / fade_samples
            samples[num_samples - 1 - i] = int(samples[num_samples - 1 - i] * gain)

    return struct.pack(f"<{num_samples}h", *samples)


def normalize_audio(audio_bytes: bytes, target_rms: float = 0.15,
                    max_gain_db: float = 20.0,
                    sample_width: int = 2) -> bytes:
    """Normalize audio amplitude, detect and reduce clipping.

    Args:
        audio_bytes: Raw PCM16 audio
        target_rms: Target RMS level (0.0-1.0)
        max_gain_db: Maximum gain to apply in dB
        sample_width: Bytes per sample

    Returns:
        Normalized PCM16 audio bytes
    """
    if not audio_bytes or len(audio_bytes) < sample_width:
        return audio_bytes

    num_samples = len(audio_bytes) // sample_width
    try:
        fmt = f"<{num_samples}h"
        samples = list(struct.unpack(fmt, audio_bytes[:num_samples * sample_width]))
    except struct.error:
        return audio_bytes

    max_val = 32767.0
    rms = math.sqrt(sum(s * s for s in samples) / max(num_samples, 1)) / max_val

    if rms < 0.001:
        return audio_bytes  # Silence — don't amplify noise

    gain = target_rms / rms
    max_gain = 10 ** (max_gain_db / 20)
    gain = min(gain, max_gain)

    # Apply gain with clipping prevention
    result = []
    for s in samples:
        v = int(s * gain)
        v = max(-32768, min(32767, v))
        result.append(v)

    return struct.pack(f"<{num_samples}h", *result)


# ============================================================================
# TTS Diagnostics
# ============================================================================

class TTSDiagnostics:
    """TTS preflight and runtime diagnostics.

    Performs sample-rate verification, codec compatibility checks,
    chunk consistency validation, and anti-artifact monitoring.
    """

    def __init__(self):
        self._event_log: deque = deque(maxlen=100)
        self._chunk_times: List[float] = []
        self._chunks_sent = 0
        self._chunks_played = 0
        self._last_chunk_time = 0.0
        self._retry_count = 0
        self._max_retries = 3

    def preflight(
        self,
        tts_config: Optional[Any] = None,
        provider: str = "elevenlabs",
        model: str = "eleven_turbo_v2_5",
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        sample_rate: int = 44100,
        codec: str = "mp3",
    ) -> TTSPreflightResult:
        """Run TTS preflight checks.

        Validates sample rate, codec, and chunk configuration.
        """
        result = TTSPreflightResult(
            provider=provider,
            model=model,
            voice_id=voice_id,
            sample_rate=sample_rate,
            codec=codec,
        )

        # 1. Sample rate validation
        if sample_rate in VALID_SAMPLE_RATES:
            result.sample_rate_match = True
            result.expected_sample_rate = sample_rate
        else:
            result.errors.append(
                f"Sample rate {sample_rate} not in valid set {sorted(VALID_SAMPLE_RATES)}"
            )

        # 2. Codec compatibility
        short_codecs = {"pcm16", "pcm", "mp3", "opus", "ulaw"}
        composite_codecs = {"pcm_16000", "pcm_22050", "pcm_44100",
                            "mp3_44100_128", "mp3_22050_32",
                            "ulaw_8000"}
        if codec in short_codecs or codec in composite_codecs:
            result.codec_compatible = True
        else:
            result.warnings.append(f"Codec '{codec}' may not be compatible")
            result.codec_compatible = True  # permissive

        # 3. Chunk configuration
        result.chunk_ms = TTS_CHUNK_TARGET_MS
        result.chunk_strategy = "fixed_40ms"
        result.jitter_buffer_ms = 200  # Recommended jitter buffer

        # 4. Determine readiness
        result.ready = result.sample_rate_match and len(result.errors) == 0

        if result.ready:
            logger.info("TTS preflight PASSED: %s/%s @ %dHz %s",
                        provider, model, sample_rate, codec)
        else:
            logger.warning("TTS preflight FAILED: %s", result.errors)

        # Emit structured event
        self._emit_event("preflight_complete", sample_rate=sample_rate,
                         codec=codec)

        return result

    def on_stream_start(self, sample_rate: int = 0, codec: str = "") -> TTSEventLog:
        """Record stream start event."""
        self._chunks_sent = 0
        self._chunks_played = 0
        self._chunk_times.clear()
        self._last_chunk_time = time.monotonic()
        return self._emit_event("stream_start", sample_rate=sample_rate, codec=codec)

    def on_chunk_sent(self, chunk_bytes: Optional[bytes] = None,
                      sample_rate: int = 16000) -> TTSEventLog:
        """Record chunk sent and compute jitter."""
        now = time.monotonic()
        self._chunks_sent += 1

        # Compute jitter from inter-chunk timing
        if self._last_chunk_time > 0:
            delta_ms = (now - self._last_chunk_time) * 1000
            self._chunk_times.append(delta_ms)
        self._last_chunk_time = now

        jitter = self._compute_jitter()

        # Waveform analysis
        stats = {"rms": 0.0, "peak": 0.0, "clipping_pct": 0.0}
        if chunk_bytes:
            stats = analyze_audio_chunk(chunk_bytes, sample_rate)

        evt = self._emit_event(
            "chunk_sent",
            sample_rate=sample_rate,
            chunks_sent=self._chunks_sent,
            jitter_ms=jitter,
        )
        evt.waveform_rms = stats["rms"]
        evt.waveform_peak = stats["peak"]
        evt.waveform_clipping_pct = stats["clipping_pct"]

        # Auto-detect issues
        if stats["clipping_pct"] > 0.01:
            logger.warning("TTS clipping detected: %.1f%% of samples", stats["clipping_pct"] * 100)
        if jitter > TTS_JITTER_MAX_MS:
            logger.warning("TTS jitter %.1fms exceeds target %dms", jitter, TTS_JITTER_MAX_MS)

        return evt

    def on_chunk_played(self) -> None:
        """Record that a chunk was played."""
        self._chunks_played += 1

    def on_stream_end(self) -> TTSEventLog:
        """Record stream end with summary stats."""
        loss = 0.0
        if self._chunks_sent > 0:
            loss = max(0, self._chunks_sent - self._chunks_played) / self._chunks_sent
        return self._emit_event(
            "stream_end",
            chunks_sent=self._chunks_sent,
            chunks_played=self._chunks_played,
            packet_loss=loss,
            jitter_ms=self._compute_jitter(),
        )

    def on_error(self, error_code: str, error_msg: str = "") -> TTSEventLog:
        """Record TTS error event."""
        self._retry_count += 1
        evt = self._emit_event("error", last_error_code=error_code)
        logger.error("TTS error [%s]: %s (retry %d/%d)",
                     error_code, error_msg, self._retry_count, self._max_retries)
        return evt

    def should_retry(self) -> bool:
        """Check if retry is allowed."""
        return self._retry_count < self._max_retries

    def get_debug_summary(self) -> Dict[str, Any]:
        """Get TTS debug summary for user-facing diagnostics."""
        jitter = self._compute_jitter()
        return {
            "component": "tts",
            "chunks_sent": self._chunks_sent,
            "chunks_played": self._chunks_played,
            "jitter_ms": round(jitter, 2),
            "packet_loss_pct": round(
                max(0, self._chunks_sent - self._chunks_played) / max(1, self._chunks_sent) * 100, 2
            ),
            "retry_count": self._retry_count,
            "recent_events": [e.to_dict() for e in list(self._event_log)[-5:]],
        }

    def _compute_jitter(self) -> float:
        """Compute jitter from inter-chunk timing."""
        if len(self._chunk_times) < 2:
            return 0.0
        mean = sum(self._chunk_times) / len(self._chunk_times)
        variance = sum((t - mean) ** 2 for t in self._chunk_times) / len(self._chunk_times)
        return math.sqrt(variance)

    def _emit_event(self, event: str, **kwargs) -> TTSEventLog:
        """Create and log a TTS event."""
        evt = TTSEventLog(
            event=event,
            timestamp=time.time(),
            sample_rate=kwargs.get("sample_rate", 0),
            codec=kwargs.get("codec", ""),
            chunk_ms=kwargs.get("chunk_ms", TTS_CHUNK_TARGET_MS),
            chunks_sent=kwargs.get("chunks_sent", self._chunks_sent),
            chunks_played=kwargs.get("chunks_played", self._chunks_played),
            jitter_ms=kwargs.get("jitter_ms", 0.0),
            packet_loss=kwargs.get("packet_loss", 0.0),
            last_error_code=kwargs.get("last_error_code", None),
        )
        self._event_log.append(evt)
        logger.debug("TTS_EVENT: %s", json.dumps(evt.to_dict()))
        return evt


# ============================================================================
# VQA Diagnostics
# ============================================================================

class VQADiagnostics:
    """VQA preflight checks with structured skip codes.

    Validates camera, model, input shape, warmup, and dependencies
    before marking VQA as ready.
    """

    def __init__(self):
        self._diagnostic_frames: List[Any] = []

    async def preflight(
        self,
        vqa_pipeline: Optional[Any] = None,
        capture_frame_fn: Optional[Any] = None,
        warmup_timeout_s: float = 15.0,
    ) -> VQAPreflightResult:
        """Run the full VQA preflight check sequence.

        1. Camera access check
        2. Model load verification
        3. Input shape/dtype validation
        4. Warmup inference
        5. Dependency checks
        """
        result = VQAPreflightResult()

        # ── 1. Camera access ──
        if capture_frame_fn is not None:
            try:
                frame = await asyncio.wait_for(
                    capture_frame_fn(), timeout=5.0
                )
                if frame is not None:
                    result.frame_ok = True
                    # Check shape
                    if hasattr(frame, "shape"):
                        result.input_shape = str(frame.shape)
                        result.input_dtype = str(frame.dtype) if hasattr(frame, "dtype") else "unknown"
                    elif hasattr(frame, "size"):
                        w, h = frame.size
                        result.input_shape = f"({h}, {w}, 3)"
                        result.input_dtype = "uint8"
                    else:
                        result.input_shape = "unknown"
                else:
                    result.skip_code = VQASkipCode.SKIP_NO_FRAME.value
                    result.message = "Camera returned empty frame"
                    result.remediation = SKIP_REMEDIATION[VQASkipCode.SKIP_NO_FRAME]
                    result.reproduce_command = 'python -c "import cv2; c=cv2.VideoCapture(0); ok,f=c.read(); print(ok,f.shape if ok else None)"'
            except asyncio.TimeoutError:
                result.skip_code = VQASkipCode.SKIP_TIMEOUT.value
                result.message = "Camera capture timed out"
                result.remediation = "Check camera connection and permissions"
                result.reproduce_command = 'python -c "import cv2; c=cv2.VideoCapture(0); print(c.isOpened())"'
            except Exception as e:
                result.skip_code = VQASkipCode.SKIP_NO_FRAME.value
                result.message = f"Camera error: {e}"
                result.errors.append(str(e))
        else:
            # No capture function - use synthetic frame
            result.frame_ok = True
            result.input_shape = "(480, 640, 3)"
            result.input_dtype = "uint8"
            logger.info("VQA preflight: no capture function, using synthetic frame")

        # ── 2. Model load verification ──
        if vqa_pipeline is not None:
            result.model_loaded = True
            # Check available detectors
            for detector_name in ["yolo", "midas", "face", "ocr"]:
                attr = f"_{detector_name}" if hasattr(vqa_pipeline, f"_{detector_name}") else None
                has_it = hasattr(vqa_pipeline, detector_name) or attr
                if has_it:
                    result.detectors_loaded.append(detector_name)
                else:
                    result.detectors_missing.append(detector_name)
        else:
            if result.skip_code is None:
                result.skip_code = VQASkipCode.SKIP_MODEL_LOAD.value
                result.message = "VQA pipeline not initialized"
                result.remediation = SKIP_REMEDIATION[VQASkipCode.SKIP_MODEL_LOAD]
                result.reproduce_command = ("python -c \"from core.vqa import "
                                            "create_perception_pipeline; "
                                            "p=create_perception_pipeline(use_mock=True); print(p)\"")

        # ── 3. Input shape/dtype validation ──
        if result.frame_ok and result.input_dtype not in (None, "unknown"):
            if result.input_dtype not in ("uint8", "float32"):
                if result.skip_code is None:
                    result.skip_code = VQASkipCode.SKIP_SHAPE_MISMATCH.value
                    result.message = f"Unexpected dtype: {result.input_dtype}"
                    result.remediation = SKIP_REMEDIATION[VQASkipCode.SKIP_SHAPE_MISMATCH]

        # ── 4. Warmup inference ──
        if vqa_pipeline is not None and result.skip_code is None:
            try:
                from PIL import Image as PILImage
                warmup_img = PILImage.new("RGB", (640, 480), color=(128, 128, 128))
                warmup_start = time.monotonic()
                await asyncio.wait_for(
                    vqa_pipeline.process(warmup_img),
                    timeout=warmup_timeout_s,
                )
                result.warmup_ms = (time.monotonic() - warmup_start) * 1000
                logger.info("VQA warmup completed in %.1fms", result.warmup_ms)
            except asyncio.TimeoutError:
                result.skip_code = VQASkipCode.SKIP_TIMEOUT.value
                result.message = f"Warmup timed out after {warmup_timeout_s}s"
                result.warmup_ms = warmup_timeout_s * 1000
                result.remediation = SKIP_REMEDIATION[VQASkipCode.SKIP_TIMEOUT]
            except MemoryError:
                result.skip_code = VQASkipCode.SKIP_RESOURCE.value
                result.message = "Out of memory during warmup"
                result.remediation = SKIP_REMEDIATION[VQASkipCode.SKIP_RESOURCE]
            except ImportError as ie:
                result.skip_code = VQASkipCode.SKIP_DEP_MISSING.value
                result.message = f"Missing dependency: {ie}"
                result.remediation = SKIP_REMEDIATION[VQASkipCode.SKIP_DEP_MISSING]
            except Exception as e:
                result.skip_code = VQASkipCode.SKIP_MODEL_LOAD.value
                result.message = f"Warmup failed: {e}"
                result.errors.append(str(e))

        # ── 5. Dependency checks ──
        dep_checks = {
            "opencv": "cv2",
            "pillow": "PIL",
            "numpy": "numpy",
        }
        for name, module in dep_checks.items():
            try:
                __import__(module)
                if name not in result.detectors_loaded:
                    result.detectors_loaded.append(name)
            except ImportError:
                result.detectors_missing.append(name)
                if result.skip_code is None:
                    result.skip_code = VQASkipCode.SKIP_DEP_MISSING.value
                    result.message = f"Missing dependency: {name}"
                    result.remediation = SKIP_REMEDIATION[VQASkipCode.SKIP_DEP_MISSING]

        # ── Final status ──
        if result.skip_code is None:
            result.status = "ready"
            result.message = "VQA pipeline ready"
        else:
            result.status = "skipped"

        logger.info("VQA preflight %s: %s (skip_code=%s)",
                    result.status.upper(), result.message, result.skip_code)

        return result


# ============================================================================
# Runtime Diagnostics (Orchestrator)
# ============================================================================

class RuntimeDiagnostics:
    """Top-level runtime diagnostics orchestrator.

    Runs TTS and VQA preflight checks, emits consolidated
    SYSTEM_STATUS, and provides ongoing runtime monitoring.
    """

    def __init__(self):
        self.tts_diag = TTSDiagnostics()
        self.vqa_diag = VQADiagnostics()
        self._system_status: Optional[SystemStatus] = None

    async def run_all_preflight(
        self,
        tts_config: Optional[Dict[str, Any]] = None,
        vqa_pipeline: Optional[Any] = None,
        capture_frame_fn: Optional[Any] = None,
        tts_provider: str = "elevenlabs",
        tts_model: str = "eleven_turbo_v2_5",
        tts_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        tts_sample_rate: int = 44100,
        tts_codec: str = "mp3",
        warmup_timeout_s: float = 15.0,
    ) -> SystemStatus:
        """Run all preflight checks and emit consolidated status."""
        start = time.perf_counter()

        # Run TTS and VQA preflight concurrently
        tts_result = self.tts_diag.preflight(
            provider=tts_provider,
            model=tts_model,
            voice_id=tts_voice_id,
            sample_rate=tts_sample_rate,
            codec=tts_codec,
        )

        vqa_result = await self.vqa_diag.preflight(
            vqa_pipeline=vqa_pipeline,
            capture_frame_fn=capture_frame_fn,
            warmup_timeout_s=warmup_timeout_s,
        )

        # Determine overall health
        if not tts_result.ready and vqa_result.status == "skipped":
            health = SystemHealth.ERROR
        elif not tts_result.ready or vqa_result.status == "skipped":
            health = SystemHealth.WARN
        else:
            health = SystemHealth.OK

        # Build human summary
        tts_summary = "TTS ready" if tts_result.ready else f"TTS issues: {'; '.join(tts_result.errors or tts_result.warnings)}"
        vqa_summary = "VQA ready" if vqa_result.status == "ready" else f"VQA {vqa_result.status}: {vqa_result.message}"
        human = f"{vqa_summary}. {tts_summary}."

        elapsed = max((time.perf_counter() - start) * 1000, 0.001)

        status = SystemStatus(
            system_status=health.value,
            tts=tts_result,
            vqa=vqa_result,
            startup_time_ms=elapsed,
            human_summary=human,
        )

        self._system_status = status

        # Emit to logs
        logger.info("SYSTEM_STATUS: %s", status.to_json())
        logger.info("Startup summary: %s", human)

        return status

    def get_status(self) -> Optional[SystemStatus]:
        """Get the last computed system status."""
        return self._system_status

    def handle_tts_breaking(self) -> Dict[str, Any]:
        """Generate diagnostic response when user reports TTS issues.

        Returns dict with debug JSON, human explanation, and action list.
        """
        debug = self.tts_diag.get_debug_summary()
        tts_status = self._system_status.tts if self._system_status else None

        human_lines = [
            f"TTS jitter: {debug['jitter_ms']}ms (target <{TTS_JITTER_MAX_MS}ms)",
            f"Chunks sent: {debug['chunks_sent']}, played: {debug['chunks_played']}",
            f"Packet loss: {debug['packet_loss_pct']}%",
        ]

        actions = [
            "1. Check sample_rate matches TTS model (expected 44100 for ElevenLabs)",
            "2. Apply jitter buffer (200ms) + soft fades (4ms) on chunk boundaries",
            "3. Enable fallback TTS model or switch to edge-based piper-tts",
        ]

        return {
            "debug_json": debug,
            "human_explanation": "\n".join(human_lines),
            "action_list": actions,
            "tts_preflight": tts_status.to_dict() if tts_status else {},
        }


# ── Singleton accessor ──

_diagnostics: Optional[RuntimeDiagnostics] = None


def get_diagnostics() -> RuntimeDiagnostics:
    """Return the process-wide RuntimeDiagnostics singleton."""
    global _diagnostics
    if _diagnostics is None:
        _diagnostics = RuntimeDiagnostics()
    return _diagnostics
