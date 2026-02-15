"""
Sound Source Localization (SSL) — GCC-PHAT pipeline with optional neural fallback.

Estimates azimuth/elevation and rough distance from microphone array data.
Gracefully degrades to single-mic mode (no spatial info, classification only).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("audio-ssl")

try:
    from scipy.signal import fftconvolve
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


@dataclass
class SSLConfig:
    """Configuration for sound source localization."""
    sample_rate: int = 16000
    mic_spacing_m: float = 0.1      # distance between mics for stereo/array
    speed_of_sound: float = 343.0    # m/s
    frame_length_ms: float = 50.0    # analysis window
    max_sources: int = 3
    min_energy_db: float = -40.0     # ignore below this threshold
    single_mic_mode: bool = False    # auto-detected if only 1 channel


@dataclass
class SSLResult:
    """Localization result for a sound source."""
    source_id: str
    azimuth_deg: float           # horizontal angle (0 = front, positive = right)
    elevation_deg: float = 0.0   # vertical angle
    distance_estimate: str = "unknown"  # "near", "mid", "far", "unknown"
    energy_db: float = 0.0
    confidence: float = 0.0
    timestamp_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "azimuth_deg": round(self.azimuth_deg, 1),
            "elevation_deg": round(self.elevation_deg, 1),
            "distance_estimate": self.distance_estimate,
            "energy_db": round(self.energy_db, 1),
            "confidence": round(self.confidence, 3),
            "timestamp_ms": self.timestamp_ms,
        }

    @property
    def direction_label(self) -> str:
        az = self.azimuth_deg
        if abs(az) < 15:
            return "ahead"
        elif az >= 15 and az < 75:
            return "right-front"
        elif az >= 75 and az < 105:
            return "right"
        elif az >= 105:
            return "right-behind"
        elif az <= -15 and az > -75:
            return "left-front"
        elif az <= -75 and az > -105:
            return "left"
        else:
            return "left-behind"


class SoundSourceLocalizer:
    """GCC-PHAT-based sound source localization.

    Supports multi-channel (2+ mics) for directional estimation.
    Falls back to energy-only analysis for single-mic input.

    Usage::

        ssl = SoundSourceLocalizer()
        results = ssl.localize(audio_data)  # (channels, samples)
    """

    def __init__(self, config: Optional[SSLConfig] = None):
        self.config = config or SSLConfig()
        self._frame_samples = int(self.config.sample_rate * self.config.frame_length_ms / 1000)

    def localize(self, audio: np.ndarray, timestamp_ms: float = 0.0) -> List[SSLResult]:
        """Localize sound sources from audio data.

        Args:
            audio: shape (channels, samples) or (samples,) for single mic
            timestamp_ms: frame timestamp

        Returns:
            List of SSLResult, sorted by confidence.
        """
        if timestamp_ms == 0:
            timestamp_ms = time.time() * 1000

        # Handle single-channel
        if audio.ndim == 1:
            audio = audio.reshape(1, -1)

        n_channels = audio.shape[0]

        if n_channels < 2 or self.config.single_mic_mode:
            return self._single_mic_analysis(audio[0], timestamp_ms)

        return self._gcc_phat_localize(audio, timestamp_ms)

    def _gcc_phat_localize(self, audio: np.ndarray, ts: float) -> List[SSLResult]:
        """Multi-channel GCC-PHAT localization."""
        n_channels = audio.shape[0]
        results = []

        # Compute GCC-PHAT for each mic pair with reference mic 0
        for ch in range(1, min(n_channels, 4)):  # limit to first 4 channels
            tdoa = self._gcc_phat(audio[0], audio[ch])
            if tdoa is None:
                continue

            # Convert TDOA to angle
            max_delay = self.config.mic_spacing_m / self.config.speed_of_sound
            if max_delay == 0:
                continue

            sin_theta = tdoa / max_delay
            sin_theta = np.clip(sin_theta, -1.0, 1.0)
            azimuth = math.degrees(math.asin(sin_theta))

            # Energy estimation
            energy = self._compute_energy_db(audio[0])

            if energy < self.config.min_energy_db:
                continue

            # Distance heuristic from energy
            if energy > -10:
                dist = "near"
            elif energy > -25:
                dist = "mid"
            else:
                dist = "far"

            confidence = min(1.0, max(0.0, (energy - self.config.min_energy_db) / 40))

            results.append(SSLResult(
                source_id=f"src_{ch}",
                azimuth_deg=azimuth,
                distance_estimate=dist,
                energy_db=energy,
                confidence=confidence,
                timestamp_ms=ts,
            ))

        return sorted(results, key=lambda r: r.confidence, reverse=True)[:self.config.max_sources]

    def _gcc_phat(self, sig1: np.ndarray, sig2: np.ndarray) -> Optional[float]:
        """Compute GCC-PHAT time delay of arrival."""
        if not _SCIPY_AVAILABLE:
            return self._simple_xcorr_tdoa(sig1, sig2)

        n = len(sig1) + len(sig2) - 1
        n_fft = 2 ** int(np.ceil(np.log2(n)))

        S1 = np.fft.rfft(sig1, n=n_fft)
        S2 = np.fft.rfft(sig2, n=n_fft)
        R = S1 * np.conj(S2)
        mag = np.abs(R)
        mag[mag < 1e-10] = 1e-10
        R_phat = R / mag
        gcc = np.fft.irfft(R_phat, n=n_fft)

        max_delay_samples = int(self.config.mic_spacing_m / self.config.speed_of_sound * self.config.sample_rate) + 1
        center = 0
        # Search in valid range
        indices = np.concatenate([
            np.arange(0, min(max_delay_samples + 1, len(gcc))),
            np.arange(max(0, len(gcc) - max_delay_samples), len(gcc)),
        ])
        if len(indices) == 0:
            return None

        best_idx = indices[np.argmax(gcc[indices])]
        if best_idx > len(gcc) // 2:
            best_idx -= len(gcc)

        return best_idx / self.config.sample_rate

    def _simple_xcorr_tdoa(self, sig1: np.ndarray, sig2: np.ndarray) -> Optional[float]:
        """Simple cross-correlation fallback when scipy is unavailable."""
        max_lag = int(self.config.mic_spacing_m / self.config.speed_of_sound * self.config.sample_rate) + 1
        min_len = min(len(sig1), len(sig2))
        if min_len < 2 * max_lag:
            return None
        best_lag = 0
        best_val = -1
        for lag in range(-max_lag, max_lag + 1):
            if lag >= 0:
                corr = np.dot(sig1[lag:min_len], sig2[:min_len - lag])
            else:
                corr = np.dot(sig1[:min_len + lag], sig2[-lag:min_len])
            if corr > best_val:
                best_val = corr
                best_lag = lag
        return best_lag / self.config.sample_rate

    def _single_mic_analysis(self, audio: np.ndarray, ts: float) -> List[SSLResult]:
        """Single-mic mode: energy detection only (no direction)."""
        energy = self._compute_energy_db(audio)
        if energy < self.config.min_energy_db:
            return []

        if energy > -10:
            dist = "near"
        elif energy > -25:
            dist = "mid"
        else:
            dist = "far"

        return [SSLResult(
            source_id="src_mono",
            azimuth_deg=0.0,  # unknown direction
            distance_estimate=dist,
            energy_db=energy,
            confidence=0.5,  # lower confidence for single-mic
            timestamp_ms=ts,
        )]

    @staticmethod
    def _compute_energy_db(audio: np.ndarray) -> float:
        rms = np.sqrt(np.mean(audio.astype(np.float64) ** 2))
        if rms < 1e-10:
            return -80.0
        return float(20 * np.log10(rms))

    def health(self) -> dict:
        return {
            "scipy_available": _SCIPY_AVAILABLE,
            "sample_rate": self.config.sample_rate,
            "single_mic_mode": self.config.single_mic_mode,
        }
