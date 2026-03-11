"""Unit tests for metrics instrumentation module.

Tests T-095: Custom Metrics Instrumentation
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry


class TestPipelineStageMetrics:
    """Tests for PipelineStageMetrics dataclass."""

    def test_metrics_initialization(self):
        """Test metrics object initialization."""
        from infrastructure.monitoring.instrumentation import PipelineStageMetrics

        metrics = PipelineStageMetrics(stage="test_stage", pipeline="test_pipeline")

        assert metrics.stage == "test_stage"
        assert metrics.pipeline == "test_pipeline"
        assert metrics.success is True
        assert metrics.error_type is None
        assert metrics.end_time is None

    def test_duration_before_complete(self):
        """Test duration calculation before completion."""
        from infrastructure.monitoring.instrumentation import PipelineStageMetrics

        metrics = PipelineStageMetrics(stage="test", pipeline="test")
        time.sleep(0.01)

        duration = metrics.duration_seconds
        assert duration >= 0.01

    def test_duration_after_complete(self):
        """Test duration calculation after completion."""
        from infrastructure.monitoring.instrumentation import PipelineStageMetrics

        metrics = PipelineStageMetrics(stage="test", pipeline="test")
        time.sleep(0.01)
        metrics.complete(success=True)

        duration1 = metrics.duration_seconds
        time.sleep(0.01)
        duration2 = metrics.duration_seconds

        # Duration should be fixed after completion
        assert duration1 == duration2

    def test_complete_with_error(self):
        """Test marking stage as failed."""
        from infrastructure.monitoring.instrumentation import PipelineStageMetrics

        metrics = PipelineStageMetrics(stage="test", pipeline="test")
        metrics.complete(success=False, error_type="ValueError")

        assert metrics.success is False
        assert metrics.error_type == "ValueError"
        assert metrics.end_time is not None


class TestTimedStageContextManager:
    """Tests for timed_stage context manager."""

    def test_successful_stage(self):
        """Test timed_stage with successful execution."""
        from infrastructure.monitoring.instrumentation import timed_stage

        # Use isolated registry to avoid conflicts
        CollectorRegistry()

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            with timed_stage("vision", "detection") as metrics:
                time.sleep(0.01)

            assert metrics.success is True
            mock_metrics.record_inference.assert_called_once()
            call_args = mock_metrics.record_inference.call_args
            assert call_args[0][0] == "vision_detection"
            assert call_args[0][1] >= 0.01

    def test_failed_stage(self):
        """Test timed_stage with exception."""
        from infrastructure.monitoring.instrumentation import timed_stage

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            with pytest.raises(ValueError):
                with timed_stage("vision", "detection") as metrics:
                    raise ValueError("test error")

            assert metrics.success is False
            assert metrics.error_type == "ValueError"
            mock_metrics.record_error.assert_called_once_with("vision_detection", "ValueError")

    async def test_async_timed_stage(self):
        """Test async_timed_stage context manager."""
        from infrastructure.monitoring.instrumentation import async_timed_stage

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            async with async_timed_stage("rag", "embedding") as metrics:
                await asyncio.sleep(0.01)

            assert metrics.success is True
            mock_metrics.record_inference.assert_called_once()


class TestInstrumentStageDecorator:
    """Tests for instrument_stage decorator."""

    def test_sync_function_instrumentation(self):
        """Test decorator with sync function."""
        from infrastructure.monitoring.instrumentation import instrument_stage

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            @instrument_stage("vision", "detection")
            def detect(frame):
                time.sleep(0.01)
                return "detected"

            result = detect("frame_data")

            assert result == "detected"
            mock_metrics.record_inference.assert_called_once()

    async def test_async_function_instrumentation(self):
        """Test decorator with async function."""
        from infrastructure.monitoring.instrumentation import instrument_stage

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            @instrument_stage("rag", "search")
            async def search(query):
                await asyncio.sleep(0.01)
                return ["result1", "result2"]

            result = await search("test query")

            assert result == ["result1", "result2"]
            mock_metrics.record_inference.assert_called_once()


class TestPipelineSpecificDecorators:
    """Tests for pipeline-specific decorators."""

    def test_instrument_vision(self):
        """Test instrument_vision decorator."""
        from infrastructure.monitoring.instrumentation import VisionStage, instrument_vision

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            @instrument_vision(VisionStage.OBJECT_DETECTION)
            def detect(frame):
                return []

            detect("frame")

            call_args = mock_metrics.record_inference.call_args
            assert "vision_object_detection" in call_args[0][0]

    def test_instrument_rag(self):
        """Test instrument_rag decorator."""
        from infrastructure.monitoring.instrumentation import RAGStage, instrument_rag

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            @instrument_rag(RAGStage.EMBEDDING)
            def embed(text):
                return [0.1, 0.2, 0.3]

            embed("test text")

            call_args = mock_metrics.record_inference.call_args
            assert "rag_embedding" in call_args[0][0]

    def test_instrument_speech(self):
        """Test instrument_speech decorator."""
        from infrastructure.monitoring.instrumentation import SpeechStage, instrument_speech

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            @instrument_speech(SpeechStage.STT)
            def transcribe(audio):
                return "transcribed text"

            transcribe(b"audio_data")

            call_args = mock_metrics.record_inference.call_args
            assert "speech_stt" in call_args[0][0]


class TestFAISSMetricsTracker:
    """Tests for FAISSMetricsTracker."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        from infrastructure.monitoring.instrumentation import FAISSMetricsTracker

        tracker = FAISSMetricsTracker(index_name="test_index")

        assert tracker._index_name == "test_index"
        assert tracker._query_count == 0
        assert tracker._vector_count == 0

    def test_record_query(self):
        """Test recording a query."""
        from infrastructure.monitoring.instrumentation import FAISSMetricsTracker

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            tracker = FAISSMetricsTracker()
            tracker.record_query(0.05, result_count=10)

            assert tracker._query_count == 1
            mock_metrics.record_faiss_query.assert_called_once_with(0.05)

    def test_set_vector_count(self):
        """Test setting vector count."""
        from infrastructure.monitoring.instrumentation import FAISSMetricsTracker

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            tracker = FAISSMetricsTracker(index_name="main")
            tracker.set_vector_count(1000)

            assert tracker._vector_count == 1000
            mock_metrics.set_queue_size.assert_called_once_with("faiss_main_vectors", 1000)

    def test_timed_query_context(self):
        """Test timed_query context manager."""
        from infrastructure.monitoring.instrumentation import FAISSMetricsTracker

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            tracker = FAISSMetricsTracker()

            with tracker.timed_query() as query:
                time.sleep(0.01)
                query["result_count"] = 5

            assert tracker._query_count == 1
            mock_metrics.record_faiss_query.assert_called_once()


class TestCircuitBreakerMetricsTracker:
    """Tests for CircuitBreakerMetricsTracker."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        from infrastructure.monitoring.instrumentation import CircuitBreakerMetricsTracker
        from infrastructure.monitoring.prometheus_metrics import CircuitBreakerState

        tracker = CircuitBreakerMetricsTracker("deepgram")

        assert tracker._service_name == "deepgram"
        assert tracker._current_state == CircuitBreakerState.CLOSED
        assert tracker._trip_count == 0

    def test_state_transitions(self):
        """Test state transitions."""
        from infrastructure.monitoring.instrumentation import CircuitBreakerMetricsTracker
        from infrastructure.monitoring.prometheus_metrics import CircuitBreakerState

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            tracker = CircuitBreakerMetricsTracker("elevenlabs")

            # Open the circuit
            tracker.open()
            assert tracker.state == CircuitBreakerState.OPEN
            assert tracker.trip_count == 1
            mock_metrics.record_circuit_breaker_trip.assert_called_once_with("elevenlabs")

            # Half-open
            tracker.half_open()
            assert tracker.state == CircuitBreakerState.HALF_OPEN

            # Close
            tracker.close()
            assert tracker.state == CircuitBreakerState.CLOSED

    def test_open_increments_trip_count(self):
        """Test that opening circuit increments trip count."""
        from infrastructure.monitoring.instrumentation import CircuitBreakerMetricsTracker

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            tracker = CircuitBreakerMetricsTracker("test")

            tracker.open()
            tracker.close()
            tracker.open()

            assert tracker.trip_count == 2


class TestWebRTCMetricsTracker:
    """Tests for WebRTCMetricsTracker."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        from infrastructure.monitoring.instrumentation import WebRTCMetricsTracker

        tracker = WebRTCMetricsTracker()

        assert tracker.active_sessions == 0
        assert tracker.total_sessions == 0
        assert tracker.reconnection_count == 0

    def test_session_lifecycle(self):
        """Test session start and end."""
        from infrastructure.monitoring.instrumentation import WebRTCMetricsTracker

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            tracker = WebRTCMetricsTracker()

            # Start sessions
            tracker.session_started("session1")
            tracker.session_started("session2")
            assert tracker.active_sessions == 2
            assert tracker.total_sessions == 2

            # End one session
            tracker.session_ended("session1")
            assert tracker.active_sessions == 1
            assert tracker.total_sessions == 2

            # Verify metrics calls
            assert mock_metrics.inc_connections.call_count == 2
            assert mock_metrics.dec_connections.call_count == 1

    def test_reconnection_tracking(self):
        """Test reconnection event tracking."""
        from infrastructure.monitoring.instrumentation import WebRTCMetricsTracker

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            tracker = WebRTCMetricsTracker()

            tracker.record_reconnection("session1")
            tracker.record_reconnection("session1")

            assert tracker.reconnection_count == 2
            assert mock_metrics.record_error.call_count == 2


class TestSpeechMetricsFunctions:
    """Tests for speech metrics helper functions."""

    def test_record_stt_latency(self):
        """Test recording STT latency."""
        from infrastructure.monitoring.instrumentation import record_stt_latency

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            record_stt_latency(0.15)

            mock_metrics.record_stt_latency.assert_called_once_with(0.15)

    def test_record_tts_latency(self):
        """Test recording TTS latency."""
        from infrastructure.monitoring.instrumentation import record_tts_latency

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            record_tts_latency(0.08)

            mock_metrics.record_tts_latency.assert_called_once_with(0.08)

    def test_record_llm_latency(self):
        """Test recording LLM latency."""
        from infrastructure.monitoring.instrumentation import record_llm_latency

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_metrics = MagicMock()
            mock_get.return_value = mock_metrics

            record_llm_latency(0.35)

            mock_metrics.record_llm_latency.assert_called_once_with(0.35)

    def test_timed_stt_context(self):
        """Test timed_stt context manager."""
        from infrastructure.monitoring.instrumentation import timed_stt

        with patch("infrastructure.monitoring.instrumentation.record_stt_latency") as mock_record:
            with timed_stt():
                time.sleep(0.01)

            mock_record.assert_called_once()
            latency = mock_record.call_args[0][0]
            assert latency >= 0.01

    def test_timed_tts_context(self):
        """Test timed_tts context manager."""
        from infrastructure.monitoring.instrumentation import timed_tts

        with patch("infrastructure.monitoring.instrumentation.record_tts_latency") as mock_record:
            with timed_tts():
                time.sleep(0.01)

            mock_record.assert_called_once()

    def test_timed_llm_context(self):
        """Test timed_llm context manager."""
        from infrastructure.monitoring.instrumentation import timed_llm

        with patch("infrastructure.monitoring.instrumentation.record_llm_latency") as mock_record:
            with timed_llm():
                time.sleep(0.01)

            mock_record.assert_called_once()


class TestAsyncSpeechContextManagers:
    """Tests for async speech context managers."""

    async def test_async_timed_stt(self):
        """Test async_timed_stt context manager."""
        from infrastructure.monitoring.instrumentation import async_timed_stt

        with patch("infrastructure.monitoring.instrumentation.record_stt_latency") as mock_record:
            async with async_timed_stt():
                await asyncio.sleep(0.01)

            mock_record.assert_called_once()

    async def test_async_timed_tts(self):
        """Test async_timed_tts context manager."""
        from infrastructure.monitoring.instrumentation import async_timed_tts

        with patch("infrastructure.monitoring.instrumentation.record_tts_latency") as mock_record:
            async with async_timed_tts():
                await asyncio.sleep(0.01)

            mock_record.assert_called_once()

    async def test_async_timed_llm(self):
        """Test async_timed_llm context manager."""
        from infrastructure.monitoring.instrumentation import async_timed_llm

        with patch("infrastructure.monitoring.instrumentation.record_llm_latency") as mock_record:
            async with async_timed_llm():
                await asyncio.sleep(0.01)

            mock_record.assert_called_once()


class TestGlobalTrackers:
    """Tests for global tracker singleton functions."""

    def test_get_webrtc_tracker_singleton(self):
        """Test WebRTC tracker singleton."""
        from infrastructure.monitoring.instrumentation import (
            get_webrtc_tracker,
            reset_trackers,
        )

        reset_trackers()

        tracker1 = get_webrtc_tracker()
        tracker2 = get_webrtc_tracker()

        assert tracker1 is tracker2

        reset_trackers()

    def test_get_faiss_tracker_per_index(self):
        """Test FAISS tracker per index."""
        from infrastructure.monitoring.instrumentation import (
            get_faiss_tracker,
            reset_trackers,
        )

        reset_trackers()

        tracker_default = get_faiss_tracker()
        tracker_memory = get_faiss_tracker("memory")
        tracker_default2 = get_faiss_tracker("default")

        assert tracker_default is tracker_default2
        assert tracker_default is not tracker_memory

        reset_trackers()

    def test_get_circuit_breaker_tracker_per_service(self):
        """Test circuit breaker tracker per service."""
        from infrastructure.monitoring.instrumentation import (
            get_circuit_breaker_tracker,
            reset_trackers,
        )

        reset_trackers()

        tracker_dg = get_circuit_breaker_tracker("deepgram")
        tracker_el = get_circuit_breaker_tracker("elevenlabs")
        tracker_dg2 = get_circuit_breaker_tracker("deepgram")

        assert tracker_dg is tracker_dg2
        assert tracker_dg is not tracker_el

        reset_trackers()

    def test_reset_trackers(self):
        """Test reset_trackers clears all."""
        from infrastructure.monitoring.instrumentation import (
            get_circuit_breaker_tracker,
            get_faiss_tracker,
            get_webrtc_tracker,
            reset_trackers,
        )

        # Create trackers
        tracker1 = get_webrtc_tracker()
        tracker2 = get_faiss_tracker()
        tracker3 = get_circuit_breaker_tracker("test")

        # Reset
        reset_trackers()

        # New trackers should be different instances
        new_tracker1 = get_webrtc_tracker()
        new_tracker2 = get_faiss_tracker()
        new_tracker3 = get_circuit_breaker_tracker("test")

        assert tracker1 is not new_tracker1
        assert tracker2 is not new_tracker2
        assert tracker3 is not new_tracker3

        reset_trackers()


class TestStageEnums:
    """Tests for stage enum definitions."""

    def test_vision_stage_values(self):
        """Test VisionStage enum values."""
        from infrastructure.monitoring.instrumentation import VisionStage

        assert VisionStage.OBJECT_DETECTION.value == "object_detection"
        assert VisionStage.SEGMENTATION.value == "segmentation"
        assert VisionStage.DEPTH_ESTIMATION.value == "depth_estimation"
        assert VisionStage.SPATIAL_FUSION.value == "spatial_fusion"

    def test_rag_stage_values(self):
        """Test RAGStage enum values."""
        from infrastructure.monitoring.instrumentation import RAGStage

        assert RAGStage.EMBEDDING.value == "embedding"
        assert RAGStage.SEARCH.value == "search"
        assert RAGStage.RETRIEVAL.value == "retrieval"
        assert RAGStage.REASONING.value == "reasoning"

    def test_speech_stage_values(self):
        """Test SpeechStage enum values."""
        from infrastructure.monitoring.instrumentation import SpeechStage

        assert SpeechStage.STT.value == "stt"
        assert SpeechStage.TTS.value == "tts"
        assert SpeechStage.VOICE_ACTIVITY.value == "voice_activity"


class TestMetricsFailureSafety:
    """Tests for graceful failure handling in metrics."""

    def test_timed_stage_survives_metrics_failure(self):
        """Test that timed_stage doesn't crash on metrics failure."""
        from infrastructure.monitoring.instrumentation import timed_stage

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_get.side_effect = RuntimeError("Metrics unavailable")

            # Should not raise
            with timed_stage("vision", "detection") as metrics:
                pass

            assert metrics.success is True

    def test_record_stt_survives_failure(self):
        """Test that record_stt_latency doesn't crash on failure."""
        from infrastructure.monitoring.instrumentation import record_stt_latency

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_get.side_effect = RuntimeError("Metrics unavailable")

            # Should not raise
            record_stt_latency(0.1)

    def test_tracker_survives_metrics_failure(self):
        """Test that trackers don't crash on metrics failure."""
        from infrastructure.monitoring.instrumentation import FAISSMetricsTracker

        with patch("infrastructure.monitoring.instrumentation.get_metrics") as mock_get:
            mock_get.side_effect = RuntimeError("Metrics unavailable")

            tracker = FAISSMetricsTracker()

            # Should not raise
            tracker.record_query(0.05)
            tracker.set_vector_count(100)
