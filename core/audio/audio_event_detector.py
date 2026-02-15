"""
Audio Event Detector — Sound classification for safety-critical events.

Classifies ambient sounds (car horn, footsteps, voice, alarms, dog bark, etc.)
using a lightweight CNN classifier with graceful fallback to energy/spectral heuristics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("audio-event-detector")

_LIBROSA_AVAILABLE = False
try:
    import librosa
    _LIBROSA_AVAILABLE = True
except ImportError:
    pass


class AudioEventType(str, Enum):
    CAR_HORN = "car_horn"
    SIREN = "siren"
    ALARM = "alarm"
    VOICE = "voice"
    FOOTSTEPS = "footsteps"
    DOG_BARK = "dog_bark"
    DOOR = "door"
    TRAFFIC = "traffic"
    SILENCE = "silence"
    UNKNOWN = "unknown"


# Safety-critical events that should trigger immediate alerts
CRITICAL_EVENTS = {AudioEventType.CAR_HORN, AudioEventType.SIREN, AudioEventType.ALARM}


@dataclass
class AudioEventConfig:
    """Configuration for audio event detection."""
    sample_rate: int = 16000
    frame_length_ms: float = 1000.0
    hop_length_ms: float = 500.0
    min_confidence: float = 0.3
    n_mfcc: int = 13
    n_mel: int = 40
    model_path: Optional[str] = None  # path to trained classifier


@dataclass
class AudioEvent:
    """A detected audio event."""
    event_type: AudioEventType
    confidence: float
    energy_db: float
    timestamp_ms: float
    duration_ms: float = 0.0
    is_critical: bool = False
    all_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "confidence": round(self.confidence, 3),
            "energy_db": round(self.energy_db, 1),
            "is_critical": self.is_critical,
            "timestamp_ms": self.timestamp_ms,
            "duration_ms": round(self.duration_ms, 1),
        }

    @property
    def user_cue(self) -> str:
        cues = {
            AudioEventType.CAR_HORN: "Car horn detected nearby — exercise caution",
            AudioEventType.SIREN: "Emergency siren detected — stay alert",
            AudioEventType.ALARM: "Alarm sounding nearby",
            AudioEventType.VOICE: "Someone speaking nearby",
            AudioEventType.FOOTSTEPS: "Footsteps detected",
            AudioEventType.DOG_BARK: "Dog barking nearby",
            AudioEventType.DOOR: "Door opening or closing",
            AudioEventType.TRAFFIC: "Traffic sounds detected",
        }
        return cues.get(self.event_type, "")


class AudioEventDetector:
    """Lightweight audio event classifier.

    Uses spectral features (MFCC, spectral centroid, zero-crossing rate)
    with a rule-based classifier. Can be upgraded to a trained CNN model.

    Usage::

        detector = AudioEventDetector()
        events = detector.detect(audio_chunk)
    """

    def __init__(self, config: Optional[AudioEventConfig] = None):
        self.config = config or AudioEventConfig()
        self._model = None
        self._init_model()

    def _init_model(self) -> None:
        if self.config.model_path:
            try:
                import torch
                self._model = torch.jit.load(self.config.model_path)
                self._model.eval()
                logger.info("Audio event model loaded from %s", self.config.model_path)
                return
            except Exception as exc:
                logger.warning("Failed to load audio model: %s", exc)
        logger.info("Audio event detector: using spectral heuristic classifier")

    def detect(self, audio: np.ndarray, timestamp_ms: float = 0.0) -> List[AudioEvent]:
        """Detect events in an audio chunk.

        Args:
            audio: 1D array of audio samples (mono, float32 or int16)
            timestamp_ms: timestamp of the audio chunk start

        Returns:
            List of detected AudioEvents.
        """
        if timestamp_ms == 0:
            timestamp_ms = time.time() * 1000

        # Normalize to float32
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        audio = audio.flatten()

        if len(audio) < 100:
            return []

        energy_db = self._energy_db(audio)
        if energy_db < -50:
            return [AudioEvent(
                event_type=AudioEventType.SILENCE,
                confidence=0.9,
                energy_db=energy_db,
                timestamp_ms=timestamp_ms,
                duration_ms=len(audio) / self.config.sample_rate * 1000,
            )]

        if self._model is not None:
            return self._classify_with_model(audio, energy_db, timestamp_ms)

        return self._classify_heuristic(audio, energy_db, timestamp_ms)

    def _classify_heuristic(self, audio: np.ndarray, energy_db: float, ts: float) -> List[AudioEvent]:
        """Rule-based classification using spectral features."""
        features = self._extract_features(audio)
        duration_ms = len(audio) / self.config.sample_rate * 1000

        scores: Dict[str, float] = {}

        zcr = features.get("zcr_mean", 0)
        centroid = features.get("spectral_centroid", 0)
        rolloff = features.get("spectral_rolloff", 0)
        bandwidth = features.get("spectral_bandwidth", 0)

        # High-energy + high-frequency = horn/siren/alarm
        if energy_db > -15 and centroid > 2000:
            if bandwidth > 2000:
                scores["siren"] = 0.6
                scores["alarm"] = 0.4
            else:
                scores["car_horn"] = 0.6
                scores["alarm"] = 0.3

        # Voice: moderate ZCR, centroid 300-3000 Hz
        if 0.02 < zcr < 0.15 and 300 < centroid < 3500:
            scores["voice"] = 0.5

        # Footsteps: low frequency, periodic transients
        if centroid < 1000 and energy_db > -30:
            scores["footsteps"] = 0.3

        # Dog bark: high energy, high ZCR, 200-2000 Hz centroid
        if zcr > 0.1 and 200 < centroid < 2500 and energy_db > -20:
            scores["dog_bark"] = 0.35

        # Traffic: broadband noise
        if bandwidth > 3000 and energy_db > -25:
            scores["traffic"] = 0.4

        if not scores:
            scores["unknown"] = 0.3

        events = []
        for event_name, conf in scores.items():
            if conf < self.config.min_confidence:
                continue
            try:
                evt = AudioEventType(event_name)
            except ValueError:
                evt = AudioEventType.UNKNOWN
            events.append(AudioEvent(
                event_type=evt,
                confidence=conf,
                energy_db=energy_db,
                timestamp_ms=ts,
                duration_ms=duration_ms,
                is_critical=evt in CRITICAL_EVENTS,
                all_scores=scores,
            ))

        return sorted(events, key=lambda e: e.confidence, reverse=True)

    def _classify_with_model(self, audio: np.ndarray, energy_db: float, ts: float) -> List[AudioEvent]:
        """Neural model classification (stub — uses heuristic if model fails)."""
        try:
            import torch
            features = self._extract_mel_spectrogram(audio)
            tensor = torch.FloatTensor(features).unsqueeze(0).unsqueeze(0)
            with torch.no_grad():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=-1).squeeze().numpy()

            event_types = list(AudioEventType)
            events = []
            for i, prob in enumerate(probs):
                if prob < self.config.min_confidence or i >= len(event_types):
                    continue
                et = event_types[i]
                events.append(AudioEvent(
                    event_type=et,
                    confidence=float(prob),
                    energy_db=energy_db,
                    timestamp_ms=ts,
                    is_critical=et in CRITICAL_EVENTS,
                ))
            return sorted(events, key=lambda e: e.confidence, reverse=True)
        except Exception as exc:
            logger.debug("Model inference failed, falling back: %s", exc)
            return self._classify_heuristic(audio, energy_db, ts)

    def _extract_features(self, audio: np.ndarray) -> Dict[str, float]:
        """Extract spectral features."""
        features: Dict[str, float] = {}

        if _LIBROSA_AVAILABLE:
            try:
                sr = self.config.sample_rate
                zcr = librosa.feature.zero_crossing_rate(audio)[0]
                features["zcr_mean"] = float(np.mean(zcr))

                centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
                features["spectral_centroid"] = float(np.mean(centroid))

                rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
                features["spectral_rolloff"] = float(np.mean(rolloff))

                bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]
                features["spectral_bandwidth"] = float(np.mean(bandwidth))

                mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=self.config.n_mfcc)
                for i in range(min(self.config.n_mfcc, mfcc.shape[0])):
                    features[f"mfcc_{i}"] = float(np.mean(mfcc[i]))

                return features
            except Exception as exc:
                logger.debug("librosa feature extraction failed: %s", exc)

        # Numpy-only fallback
        features["zcr_mean"] = float(np.mean(np.abs(np.diff(np.sign(audio)))) / 2)
        fft = np.abs(np.fft.rfft(audio))
        freqs = np.fft.rfftfreq(len(audio), 1.0 / self.config.sample_rate)
        if fft.sum() > 0:
            features["spectral_centroid"] = float(np.sum(freqs * fft) / np.sum(fft))
            cumsum = np.cumsum(fft)
            rolloff_idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
            features["spectral_rolloff"] = float(freqs[min(rolloff_idx, len(freqs) - 1)])
            mean_freq = np.sum(freqs * fft) / np.sum(fft)
            features["spectral_bandwidth"] = float(np.sqrt(np.sum(((freqs - mean_freq) ** 2) * fft) / np.sum(fft)))
        else:
            features["spectral_centroid"] = 0.0
            features["spectral_rolloff"] = 0.0
            features["spectral_bandwidth"] = 0.0

        return features

    def _extract_mel_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        if _LIBROSA_AVAILABLE:
            mel = librosa.feature.melspectrogram(y=audio, sr=self.config.sample_rate, n_mels=self.config.n_mel)
            return librosa.power_to_db(mel, ref=np.max)
        # Fallback: raw spectrogram
        return np.abs(np.fft.rfft(audio)).reshape(1, -1)[:, :self.config.n_mel]

    @staticmethod
    def _energy_db(audio: np.ndarray) -> float:
        rms = np.sqrt(np.mean(audio.astype(np.float64) ** 2))
        if rms < 1e-10:
            return -80.0
        return float(20 * np.log10(rms))

    def health(self) -> dict:
        return {
            "model_loaded": self._model is not None,
            "librosa_available": _LIBROSA_AVAILABLE,
            "config": {
                "sample_rate": self.config.sample_rate,
                "min_confidence": self.config.min_confidence,
            },
        }
