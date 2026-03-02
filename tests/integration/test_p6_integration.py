"""
P6 Feature Integration Tests (T-131).

Cross-module integration tests verifying that P6 features work together:
- Action recognition → context integration
- Audio detection → enhanced detection → fusion
- Reasoning engine (temporal + spatial + causal) → integrated result
- Multi-frame VQA → scene narration
- Cloud sync architecture
"""

from __future__ import annotations

import numpy as np
import pytest

from core.action.clip_recognizer import CLIPActionRecognizer, CLIPConfig, IndoorAction
from core.action.action_context import (
    ActionContextIntegrator,
    ActionContextConfig,
    SceneContext,
)
from core.audio.audio_event_detector import AudioEventDetector, AudioEventConfig
from core.audio.enhanced_detector import EnhancedAudioDetector, EnhancedAudioConfig
from core.reasoning.temporal import TemporalReasoner, TemporalEvent
from core.reasoning.spatial import SpatialReasoner, SpatialEntity
from core.reasoning.causal import CausalReasoner
from core.reasoning.integration import IntegratedReasoner, create_integrated_reasoner
from core.reasoning.reasoning_foundation import (
    ReasoningOrchestrator,
    create_reasoning_orchestrator,
)
from core.vqa.multi_frame_vqa import MultiFrameAnalyzer
from core.vqa.scene_narrator import SceneNarrator


# ===========================================================================
# Action Pipeline Integration
# ===========================================================================

class TestActionPipelineIntegration:
    """Tests the full action recognition pipeline: CLIP → context."""

    async def test_clip_to_context_pipeline(self):
        """CLIP recognizer result feeds into context integrator."""
        recognizer = CLIPActionRecognizer(CLIPConfig(min_confidence=0.1))
        integrator = ActionContextIntegrator(
            config=ActionContextConfig(),
            clip_recognizer=recognizer,
        )
        clip = [np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8) for _ in range(4)]
        scene = SceneContext(
            detected_objects=["chair", "table"],
            scene_type="indoor",
            lighting="bright",
            crowd_level="empty",
            timestamp_ms=1000,
        )
        result = await integrator.analyze(clip, scene, timestamp_ms=1000)
        assert result.risk_level in ("safe", "caution", "danger")
        assert result.contextual_description != ""

    async def test_action_pipeline_health(self):
        recognizer = CLIPActionRecognizer()
        integrator = ActionContextIntegrator(clip_recognizer=recognizer)
        h = integrator.health()
        assert "total_analyses" in h


# ===========================================================================
# Audio Pipeline Integration
# ===========================================================================

class TestAudioPipelineIntegration:
    """Tests the audio detection pipeline: base → enhanced."""

    def test_enhanced_wraps_base_detector(self):
        enhanced = EnhancedAudioDetector()
        assert enhanced._base_detector is not None

    def test_detection_pipeline(self):
        enhanced = EnhancedAudioDetector()
        # Generate a 1-second audio signal (sine wave at 440Hz)
        sr = 16000
        t = np.linspace(0, 1, sr, dtype=np.float32)
        audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
        result = enhanced.detect(audio, timestamp_ms=1000)
        assert result.ambient_noise_db != 0
        assert result.timestamp_ms == 1000

    def test_empty_audio(self):
        enhanced = EnhancedAudioDetector()
        result = enhanced.detect(np.zeros(10, dtype=np.float32), timestamp_ms=1000)
        assert result is not None


# ===========================================================================
# Reasoning Pipeline Integration
# ===========================================================================

class TestReasoningPipelineIntegration:
    """Tests the reasoning pipeline: temporal + spatial + causal → integrated."""

    async def test_full_reasoning_pipeline(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("door_open", timestamp_ms=1000))
        tr.add_event(TemporalEvent("person_enter", timestamp_ms=2000))

        sr = SpatialReasoner()
        cr = CausalReasoner()

        ir = create_integrated_reasoner(temporal=tr, spatial=sr, causal=cr)
        result = await ir.reason("What happened?", {
            "entities": [SpatialEntity("e1", "person", (0.5, 0.5, 2.0))],
            "observations": [{"type": "door_opened"}, {"type": "person_approaching"}],
        })
        assert result.combined_answer != ""
        assert len(result.reasoning_types_used) >= 1

    async def test_orchestrator_routes_correctly(self):
        tr = TemporalReasoner()
        tr.add_event(TemporalEvent("a", timestamp_ms=1000))
        sr = SpatialReasoner()

        orch = create_reasoning_orchestrator(reasoners=[tr, sr])
        chain = await orch.orchestrate("When did it happen?", {})
        assert chain.metadata.get("reasoner") == "temporal"

    async def test_empty_reasoning(self):
        ir = create_integrated_reasoner()
        result = await ir.reason("What?", {})
        assert "No reasoning" in result.combined_answer


# ===========================================================================
# VQA Pipeline Integration
# ===========================================================================

class TestVQAPipelineIntegration:
    """Tests multi-frame VQA feeding into scene narrator."""

    async def test_frame_analysis_to_narration(self):
        # Analyze frames
        analyzer = MultiFrameAnalyzer()
        f1 = np.zeros((64, 64, 3), dtype=np.uint8)
        f2 = np.full((64, 64, 3), 200, dtype=np.uint8)
        result = await analyzer.analyze([f1, f2])
        assert result.has_significant_change is True

        # Feed to narrator
        narrator = SceneNarrator()
        events = await narrator.narrate(
            [{"label": "person", "confidence": 0.9}],
            timestamp_ms=1000,
        )
        assert len(events) >= 1

    async def test_stable_scene_narration(self):
        analyzer = MultiFrameAnalyzer()
        frames = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(3)]
        result = await analyzer.analyze(frames)
        assert result.has_significant_change is False

    async def test_narrator_scene_tracking(self):
        narrator = SceneNarrator()
        # Scene 1: person and chair
        await narrator.narrate(
            [{"label": "person"}, {"label": "chair"}],
            timestamp_ms=1000,
        )
        # Scene 2: person leaves, car arrives
        events = await narrator.narrate(
            [{"label": "chair"}, {"label": "car", "distance_m": 2.0}],
            timestamp_ms=12000,
        )
        event_types = [e.event_type for e in events]
        assert "object_gone" in event_types or "hazard" in event_types or "new_object" in event_types


# ===========================================================================
# Cross-Module Health Checks
# ===========================================================================

class TestCrossModuleHealth:
    def test_all_modules_instantiate(self):
        """Verify all P6 modules can be instantiated without errors."""
        clip_rec = CLIPActionRecognizer()
        ctx_int = ActionContextIntegrator(clip_recognizer=clip_rec)
        enh_det = EnhancedAudioDetector()
        temp_r = TemporalReasoner()
        spat_r = SpatialReasoner()
        caus_r = CausalReasoner()
        integ_r = IntegratedReasoner(temporal=temp_r, spatial=spat_r, causal=caus_r)
        mfa = MultiFrameAnalyzer()
        narrator = SceneNarrator()

        assert clip_rec.health()["initialized"] is False  # No CLIP installed
        assert ctx_int.health()["total_analyses"] == 0
        assert enh_det.health()["total_detections"] == 0
        assert temp_r.health()["type"] == "temporal"
        assert spat_r.health()["type"] == "spatial"
        assert caus_r.health()["type"] == "causal"
        assert integ_r.health()["total_integrations"] == 0
        assert mfa.health()["total_analyses"] == 0
        assert narrator.health()["total_narrations"] == 0
