"""Tests for core.action.action_context — Action Context Integration (T-118)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from core.action.action_context import (
    ActionContextConfig,
    ActionContextIntegrator,
    ActionContextResult,
    SceneContext,
    create_action_context_integrator,
)
from core.action.clip_recognizer import (
    ALERT_ACTIONS,
    CLIPActionRecognizer,
    CLIPActionResult,
    CLIPConfig,
    IndoorAction,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def default_config():
    return ActionContextConfig()


@pytest.fixture
def scene_indoor():
    return SceneContext(
        detected_objects=["chair", "table", "computer"],
        scene_type="indoor",
        lighting="bright",
        crowd_level="empty",
        timestamp_ms=1000.0,
    )


@pytest.fixture
def scene_crosswalk():
    return SceneContext(
        detected_objects=["car", "traffic_light"],
        scene_type="crosswalk",
        lighting="bright",
        crowd_level="sparse",
        timestamp_ms=1000.0,
    )


@pytest.fixture
def scene_dark_stairs():
    return SceneContext(
        detected_objects=["railing"],
        scene_type="stairs",
        lighting="dim",
        crowd_level="empty",
        timestamp_ms=1000.0,
    )


@pytest.fixture
def mock_clip_recognizer():
    recognizer = MagicMock(spec=CLIPActionRecognizer)
    recognizer.health.return_value = {"initialized": False, "model_name": "mock"}

    async def mock_classify(clip, timestamp_ms=None):
        return CLIPActionResult(
            action=IndoorAction.WALKING,
            confidence=0.7,
            timestamp_ms=timestamp_ms or time.time() * 1000,
            all_scores={"walking": 0.7, "standing": 0.2},
            frames_analyzed=len(clip),
            latency_ms=5.0,
        )

    recognizer.classify = AsyncMock(side_effect=mock_classify)
    return recognizer


@pytest.fixture
def sample_clip():
    """4-frame video clip."""
    return [np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8) for _ in range(4)]


@pytest.fixture
def integrator(mock_clip_recognizer):
    return ActionContextIntegrator(clip_recognizer=mock_clip_recognizer)


# =============================================================================
# ActionContextConfig Tests
# =============================================================================


class TestActionContextConfig:
    """Tests for ActionContextConfig dataclass."""

    def test_default_values(self):
        config = ActionContextConfig()
        assert config.scene_weight == 0.4
        assert config.action_weight == 0.6
        assert config.min_combined_confidence == 0.25
        assert config.max_context_age_ms == 5000
        assert config.enable_temporal_smoothing is True

    def test_custom_values(self):
        config = ActionContextConfig(
            scene_weight=0.5,
            action_weight=0.5,
            min_combined_confidence=0.3,
            max_context_age_ms=3000,
            enable_temporal_smoothing=False,
        )
        assert config.scene_weight == 0.5
        assert config.action_weight == 0.5
        assert config.min_combined_confidence == 0.3
        assert config.max_context_age_ms == 3000
        assert config.enable_temporal_smoothing is False

    def test_weights_sum_to_one(self):
        config = ActionContextConfig()
        assert abs(config.scene_weight + config.action_weight - 1.0) < 1e-6


# =============================================================================
# SceneContext Tests
# =============================================================================


class TestSceneContext:
    """Tests for SceneContext dataclass."""

    def test_default_scene_context(self):
        ctx = SceneContext()
        assert ctx.detected_objects == []
        assert ctx.scene_type == "unknown"
        assert ctx.lighting == "normal"
        assert ctx.crowd_level == "empty"
        assert ctx.timestamp_ms == 0.0

    def test_custom_scene_context(self, scene_indoor):
        assert scene_indoor.scene_type == "indoor"
        assert "chair" in scene_indoor.detected_objects
        assert scene_indoor.lighting == "bright"
        assert scene_indoor.crowd_level == "empty"

    def test_scene_context_crosswalk(self, scene_crosswalk):
        assert scene_crosswalk.scene_type == "crosswalk"
        assert "car" in scene_crosswalk.detected_objects


# =============================================================================
# ActionContextResult Tests
# =============================================================================


class TestActionContextResult:
    """Tests for ActionContextResult serialization and properties."""

    def test_to_dict(self, scene_indoor):
        result = ActionContextResult(
            action=IndoorAction.WALKING,
            confidence=0.75,
            scene_context=scene_indoor,
            contextual_description="Someone is walking in indoor area",
            is_alert=False,
            risk_level="safe",
            timestamp_ms=1000.0,
        )
        d = result.to_dict()
        assert d["action"] == "walking"
        assert d["confidence"] == 0.75
        assert d["scene_type"] == "indoor"
        assert d["risk_level"] == "safe"
        assert d["is_alert"] is False
        assert "detected_objects" in d
        assert d["timestamp_ms"] == 1000.0

    def test_to_dict_keys(self, scene_indoor):
        result = ActionContextResult(
            action=IndoorAction.STANDING,
            confidence=0.5,
            scene_context=scene_indoor,
            contextual_description="test",
            is_alert=False,
            risk_level="safe",
            timestamp_ms=0.0,
        )
        expected_keys = {
            "action", "confidence", "scene_type", "detected_objects",
            "lighting", "crowd_level", "contextual_description",
            "is_alert", "risk_level", "timestamp_ms",
        }
        assert set(result.to_dict().keys()) == expected_keys

    def test_user_cue_alert(self, scene_indoor):
        result = ActionContextResult(
            action=IndoorAction.FALLING,
            confidence=0.9,
            scene_context=scene_indoor,
            contextual_description="Someone is falling down",
            is_alert=True,
            risk_level="danger",
            timestamp_ms=0.0,
        )
        assert result.user_cue.startswith("Alert:")

    def test_user_cue_danger(self, scene_indoor):
        result = ActionContextResult(
            action=IndoorAction.RUNNING,
            confidence=0.8,
            scene_context=scene_indoor,
            contextual_description="Someone is running",
            is_alert=False,
            risk_level="danger",
            timestamp_ms=0.0,
        )
        assert result.user_cue.startswith("Warning:")

    def test_user_cue_caution(self, scene_indoor):
        result = ActionContextResult(
            action=IndoorAction.WALKING,
            confidence=0.6,
            scene_context=scene_indoor,
            contextual_description="Someone is walking",
            is_alert=False,
            risk_level="caution",
            timestamp_ms=0.0,
        )
        assert result.user_cue.startswith("Caution:")

    def test_user_cue_safe(self, scene_indoor):
        result = ActionContextResult(
            action=IndoorAction.STANDING,
            confidence=0.6,
            scene_context=scene_indoor,
            contextual_description="Someone is standing still",
            is_alert=False,
            risk_level="safe",
            timestamp_ms=0.0,
        )
        assert not result.user_cue.startswith("Alert:")
        assert not result.user_cue.startswith("Warning:")
        assert not result.user_cue.startswith("Caution:")
        assert result.user_cue == "Someone is standing still"

    def test_confidence_rounding(self, scene_indoor):
        result = ActionContextResult(
            action=IndoorAction.WALKING,
            confidence=0.33333,
            scene_context=scene_indoor,
            contextual_description="test",
            is_alert=False,
            risk_level="safe",
            timestamp_ms=0.0,
        )
        assert result.to_dict()["confidence"] == 0.333


# =============================================================================
# Risk Level Computation Tests
# =============================================================================


class TestRiskLevel:
    """Tests for risk level computation."""

    def test_falling_always_danger(self, integrator, scene_indoor):
        risk = integrator._compute_risk_level(IndoorAction.FALLING, scene_indoor, 0.9)
        assert risk == "danger"

    def test_stumbling_always_danger(self, integrator, scene_indoor):
        risk = integrator._compute_risk_level(IndoorAction.STUMBLING, scene_indoor, 0.5)
        assert risk == "danger"

    def test_running_on_crosswalk_danger(self, integrator, scene_crosswalk):
        risk = integrator._compute_risk_level(IndoorAction.RUNNING, scene_crosswalk, 0.8)
        assert risk == "danger"

    def test_walking_on_road_danger(self, integrator):
        scene = SceneContext(scene_type="road", timestamp_ms=0)
        risk = integrator._compute_risk_level(IndoorAction.WALKING, scene, 0.8)
        assert risk == "danger"

    def test_walking_on_road_low_conf_caution(self, integrator):
        scene = SceneContext(scene_type="road", timestamp_ms=0)
        risk = integrator._compute_risk_level(IndoorAction.WALKING, scene, 0.3)
        assert risk == "caution"

    def test_high_risk_scene_alert_action(self, integrator):
        scene = SceneContext(scene_type="intersection", timestamp_ms=0)
        risk = integrator._compute_risk_level(IndoorAction.APPROACHING, scene, 0.6)
        assert risk == "danger"

    def test_high_risk_scene_normal_action(self, integrator):
        scene = SceneContext(scene_type="parking", timestamp_ms=0)
        risk = integrator._compute_risk_level(IndoorAction.STANDING, scene, 0.5)
        assert risk == "caution"

    def test_stairs_running_danger(self, integrator, scene_dark_stairs):
        risk = integrator._compute_risk_level(IndoorAction.RUNNING, scene_dark_stairs, 0.8)
        assert risk == "danger"

    def test_dim_lighting_walking_caution(self, integrator):
        scene = SceneContext(scene_type="hallway", lighting="dim", timestamp_ms=0)
        risk = integrator._compute_risk_level(IndoorAction.WALKING, scene, 0.6)
        assert risk == "caution"

    def test_safe_indoor_standing(self, integrator, scene_indoor):
        risk = integrator._compute_risk_level(IndoorAction.STANDING, scene_indoor, 0.7)
        assert risk == "safe"

    def test_safe_indoor_sitting(self, integrator, scene_indoor):
        risk = integrator._compute_risk_level(IndoorAction.SITTING, scene_indoor, 0.8)
        assert risk == "safe"


# =============================================================================
# Contextual Description Tests
# =============================================================================


class TestContextualDescription:
    """Tests for contextual description generation."""

    def test_basic_description(self, integrator, scene_indoor):
        desc = integrator._generate_contextual_description(IndoorAction.WALKING, scene_indoor)
        assert "walking" in desc.lower()

    def test_scene_type_in_description(self, integrator, scene_indoor):
        desc = integrator._generate_contextual_description(IndoorAction.WALKING, scene_indoor)
        assert "indoor" in desc.lower()

    def test_objects_in_description(self, integrator, scene_indoor):
        desc = integrator._generate_contextual_description(IndoorAction.SITTING, scene_indoor)
        assert "chair" in desc.lower() or "table" in desc.lower() or "computer" in desc.lower()

    def test_dim_lighting_in_description(self, integrator, scene_dark_stairs):
        desc = integrator._generate_contextual_description(IndoorAction.WALKING, scene_dark_stairs)
        assert "low light" in desc.lower()

    def test_crowded_in_description(self, integrator):
        scene = SceneContext(
            scene_type="outdoor",
            crowd_level="crowded",
            timestamp_ms=0,
        )
        desc = integrator._generate_contextual_description(IndoorAction.WALKING, scene)
        assert "crowded" in desc.lower()

    def test_sparse_crowd_in_description(self, integrator):
        scene = SceneContext(
            scene_type="outdoor",
            crowd_level="sparse",
            timestamp_ms=0,
        )
        desc = integrator._generate_contextual_description(IndoorAction.WALKING, scene)
        assert "few people" in desc.lower()

    def test_unknown_action_fallback(self, integrator, scene_indoor):
        desc = integrator._generate_contextual_description(IndoorAction.UNKNOWN, scene_indoor)
        assert "indoor" in desc.lower()


# =============================================================================
# Full Integration Tests
# =============================================================================


class TestActionContextIntegrator:
    """Tests for the full ActionContextIntegrator analysis pipeline."""

    async def test_analyze_returns_result(self, integrator, sample_clip, scene_indoor):
        result = await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=1000.0)
        assert isinstance(result, ActionContextResult)
        assert result.action == IndoorAction.WALKING
        assert result.confidence > 0

    async def test_analyze_with_crosswalk(self, mock_clip_recognizer, sample_clip, scene_crosswalk):
        integrator = ActionContextIntegrator(clip_recognizer=mock_clip_recognizer)
        result = await integrator.analyze(sample_clip, scene_crosswalk, timestamp_ms=1000.0)
        assert isinstance(result, ActionContextResult)
        assert result.risk_level in ("safe", "caution", "danger")

    async def test_analyze_sets_alert_for_alert_actions(self, sample_clip, scene_indoor):
        recognizer = MagicMock(spec=CLIPActionRecognizer)
        recognizer.health.return_value = {}

        async def classify(clip, timestamp_ms=None):
            return CLIPActionResult(
                action=IndoorAction.FALLING,
                confidence=0.9,
                timestamp_ms=timestamp_ms or 0,
                frames_analyzed=len(clip),
            )

        recognizer.classify = AsyncMock(side_effect=classify)
        integrator = ActionContextIntegrator(clip_recognizer=recognizer)
        result = await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=1000.0)
        assert result.is_alert is True
        assert result.risk_level == "danger"

    async def test_analyze_low_confidence_becomes_unknown(self, sample_clip, scene_indoor):
        recognizer = MagicMock(spec=CLIPActionRecognizer)
        recognizer.health.return_value = {}

        async def classify(clip, timestamp_ms=None):
            return CLIPActionResult(
                action=IndoorAction.COOKING,
                confidence=0.05,
                timestamp_ms=timestamp_ms or 0,
                frames_analyzed=len(clip),
            )

        recognizer.classify = AsyncMock(side_effect=classify)
        config = ActionContextConfig(min_combined_confidence=0.5)
        integrator = ActionContextIntegrator(config=config, clip_recognizer=recognizer)
        result = await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=1000.0)
        assert result.action == IndoorAction.UNKNOWN
        assert result.confidence == 0.0

    async def test_analyze_exception_returns_safe_default(self, sample_clip, scene_indoor):
        recognizer = MagicMock(spec=CLIPActionRecognizer)
        recognizer.health.return_value = {}
        recognizer.classify = AsyncMock(side_effect=RuntimeError("boom"))
        integrator = ActionContextIntegrator(clip_recognizer=recognizer)
        result = await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=1000.0)
        assert result.action == IndoorAction.UNKNOWN
        assert result.risk_level == "safe"

    async def test_analyze_updates_history(self, integrator, sample_clip, scene_indoor):
        assert len(integrator._history) == 0
        await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=1000.0)
        assert len(integrator._history) == 1

    async def test_health(self, integrator, sample_clip, scene_indoor):
        await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=1000.0)
        h = integrator.health()
        assert h["total_analyses"] == 1
        assert h["history_size"] == 1
        assert h["temporal_smoothing"] is True
        assert "clip_recognizer_health" in h


# =============================================================================
# Temporal Smoothing Tests
# =============================================================================


class TestTemporalSmoothing:
    """Tests for temporal smoothing behavior."""

    async def test_smoothing_stabilizes_flickering(self, sample_clip, scene_indoor):
        """When history consistently shows WALKING, a one-off low-conf STANDING is smoothed."""
        call_count = 0

        async def classify(clip, timestamp_ms=None):
            nonlocal call_count
            call_count += 1
            # First 3 calls: WALKING, 4th call: STANDING with low confidence
            if call_count <= 3:
                return CLIPActionResult(
                    action=IndoorAction.WALKING,
                    confidence=0.7,
                    timestamp_ms=timestamp_ms or 0,
                    frames_analyzed=len(clip),
                )
            return CLIPActionResult(
                action=IndoorAction.STANDING,
                confidence=0.35,
                timestamp_ms=timestamp_ms or 0,
                frames_analyzed=len(clip),
            )

        recognizer = MagicMock(spec=CLIPActionRecognizer)
        recognizer.health.return_value = {}
        recognizer.classify = AsyncMock(side_effect=classify)
        integrator = ActionContextIntegrator(clip_recognizer=recognizer)

        ts = 1000.0
        for i in range(3):
            await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=ts + i * 100)

        # 4th call should be smoothed to WALKING
        result = await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=ts + 300)
        assert result.action == IndoorAction.WALKING

    async def test_smoothing_disabled(self, sample_clip, scene_indoor):
        """When temporal smoothing is off, no override happens."""
        call_count = 0

        async def classify(clip, timestamp_ms=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return CLIPActionResult(
                    action=IndoorAction.WALKING,
                    confidence=0.7,
                    timestamp_ms=timestamp_ms or 0,
                    frames_analyzed=len(clip),
                )
            return CLIPActionResult(
                action=IndoorAction.STANDING,
                confidence=0.5,
                timestamp_ms=timestamp_ms or 0,
                frames_analyzed=len(clip),
            )

        recognizer = MagicMock(spec=CLIPActionRecognizer)
        recognizer.health.return_value = {}
        recognizer.classify = AsyncMock(side_effect=classify)
        config = ActionContextConfig(enable_temporal_smoothing=False)
        integrator = ActionContextIntegrator(config=config, clip_recognizer=recognizer)

        ts = 1000.0
        for i in range(3):
            await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=ts + i * 100)

        result = await integrator.analyze(sample_clip, scene_indoor, timestamp_ms=ts + 300)
        assert result.action == IndoorAction.STANDING


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactory:
    """Tests for the factory function."""

    def test_create_default(self):
        integrator = create_action_context_integrator()
        assert isinstance(integrator, ActionContextIntegrator)

    def test_create_with_config(self):
        config = ActionContextConfig(scene_weight=0.3, action_weight=0.7)
        integrator = create_action_context_integrator(config=config)
        assert integrator.config.scene_weight == 0.3

    def test_create_with_recognizer(self, mock_clip_recognizer):
        integrator = create_action_context_integrator(clip_recognizer=mock_clip_recognizer)
        assert integrator._clip_recognizer is mock_clip_recognizer
