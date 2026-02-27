"""P4: Load Test Infrastructure Tests (T-075).

Tests for the Locust load testing infrastructure to ensure it works
correctly before running actual load tests.
"""

from __future__ import annotations

import os
import sys
import time
from typing import List

import pytest

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------

class TestLoadTestImports:
    """Test that load test modules import correctly."""
    
    def test_locustfile_import(self):
        """locustfile.py should import without errors."""
        from tests.load.locustfile import (
            TestDataGenerator,
            LatencyTracker,
            VoiceUser,
            VisionUser,
            MixedUser,
            LOCUST_AVAILABLE,
        )
        
        assert TestDataGenerator is not None
        assert LatencyTracker is not None
        assert VoiceUser is not None
        assert VisionUser is not None
        assert MixedUser is not None
    
    def test_conftest_import(self):
        """conftest.py fixtures should be importable."""
        # This is implicitly tested by pytest fixture usage
        pass


# ---------------------------------------------------------------------------
# Test Data Generator Tests
# ---------------------------------------------------------------------------

class TestTestDataGenerator:
    """Test the TestDataGenerator class."""
    
    def test_random_voice_query(self, data_generator):
        """Should return a valid voice query."""
        query = data_generator.random_voice_query()
        
        assert isinstance(query, str)
        assert len(query) > 0
        assert query in data_generator.VOICE_QUERIES
    
    def test_random_vision_prompt(self, data_generator):
        """Should return a valid vision prompt."""
        prompt = data_generator.random_vision_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert prompt in data_generator.VISION_PROMPTS
    
    def test_mock_audio_bytes(self, data_generator):
        """Should generate correct-sized audio data."""
        # 1000ms = 16000 samples * 2 bytes = 32000 bytes
        audio = data_generator.mock_audio_bytes(1000)
        
        assert isinstance(audio, bytes)
        assert len(audio) == 32000
    
    def test_mock_audio_bytes_variable_duration(self, data_generator):
        """Should scale audio data with duration."""
        audio_500 = data_generator.mock_audio_bytes(500)
        audio_2000 = data_generator.mock_audio_bytes(2000)
        
        assert len(audio_500) == 16000  # 500ms
        assert len(audio_2000) == 64000  # 2000ms
    
    def test_mock_image_base64(self, data_generator):
        """Should generate valid base64 image data."""
        image_b64 = data_generator.mock_image_base64()
        
        assert isinstance(image_b64, str)
        assert len(image_b64) > 0
        
        # Should be valid base64
        import base64
        try:
            decoded = base64.b64decode(image_b64)
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Invalid base64: {e}")


# ---------------------------------------------------------------------------
# Latency Tracker Tests
# ---------------------------------------------------------------------------

class TestLatencyTracker:
    """Test the LatencyTracker class."""
    
    def test_record_single_request(self, latency_tracker):
        """Should record a single request correctly."""
        latency_tracker.record(
            total_ms=400.0,
            stt_ms=80.0,
            llm_ms=200.0,
            tts_ms=80.0
        )
        
        assert latency_tracker.total_requests == 1
        assert len(latency_tracker.total_latencies) == 1
        assert len(latency_tracker.stt_latencies) == 1
        assert len(latency_tracker.llm_latencies) == 1
        assert len(latency_tracker.tts_latencies) == 1
    
    def test_record_sla_violation(self, latency_tracker):
        """Should track SLA violations (>500ms)."""
        latency_tracker.record(total_ms=450.0)  # Pass
        latency_tracker.record(total_ms=550.0)  # Fail
        latency_tracker.record(total_ms=600.0)  # Fail
        
        assert latency_tracker.total_requests == 3
        assert latency_tracker.sla_violations == 2
    
    def test_get_stats_empty(self, latency_tracker):
        """Should handle empty tracker gracefully."""
        stats = latency_tracker.get_stats()
        
        assert stats["total_requests"] == 0
        assert stats["sla_violation_rate"] == 0
        assert stats["total"]["avg"] == 0
    
    def test_get_stats_with_data(self, latency_tracker):
        """Should calculate statistics correctly."""
        # Add 10 requests with known latencies
        for i in range(10):
            latency_tracker.record(
                total_ms=350.0 + i * 20,  # 350, 370, ..., 530
                stt_ms=80.0,
                llm_ms=200.0 + i * 10,
                tts_ms=80.0
            )
        
        stats = latency_tracker.get_stats()
        
        assert stats["total_requests"] == 10
        # Avg should be around 440ms
        assert 430 < stats["total"]["avg"] < 450
        # P50 should be around 430-450ms
        assert 400 < stats["total"]["p50"] < 480
        # Some should violate SLA (>500ms)
        assert stats["sla_violation_rate"] > 0
    
    def test_partial_latency_recording(self, latency_tracker):
        """Should handle partial latency recording (e.g., only total)."""
        latency_tracker.record(total_ms=400.0)  # No component breakdown
        latency_tracker.record(total_ms=450.0, llm_ms=200.0)  # Only LLM
        
        assert latency_tracker.total_requests == 2
        assert len(latency_tracker.total_latencies) == 2
        assert len(latency_tracker.stt_latencies) == 0
        assert len(latency_tracker.llm_latencies) == 1


# ---------------------------------------------------------------------------
# Mock User Tests
# ---------------------------------------------------------------------------

class TestMockUsers:
    """Test mock user behavior classes."""
    
    def test_voice_user_instantiation(self):
        """VoiceUser should be instantiable."""
        from tests.load.locustfile import VoiceUser
        
        # Note: Without Locust, this is a mock class
        user = VoiceUser()
        assert user is not None
    
    def test_vision_user_instantiation(self):
        """VisionUser should be instantiable."""
        from tests.load.locustfile import VisionUser
        
        user = VisionUser()
        assert user is not None
    
    def test_mixed_user_instantiation(self):
        """MixedUser should be instantiable."""
        from tests.load.locustfile import MixedUser
        
        user = MixedUser()
        assert user is not None


# ---------------------------------------------------------------------------
# Mock Test Runner Tests
# ---------------------------------------------------------------------------

class TestMockTestRunner:
    """Test the mock test runner (runs without Locust)."""
    
    def test_run_mock_test(self):
        """Mock test should run and return valid stats."""
        from tests.load.locustfile import run_mock_test
        
        # Reset the global tracker first
        from tests.load import locustfile
        locustfile._latency_tracker = locustfile.LatencyTracker()
        
        stats = run_mock_test(num_iterations=5)
        
        assert stats["total_requests"] == 5
        assert stats["total"]["avg"] > 0
        assert stats["total"]["p95"] > 0


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestLoadTestIntegration:
    """Integration tests for load test infrastructure."""
    
    def test_full_workflow(self, data_generator, latency_tracker):
        """Test the full workflow without Locust."""
        # Generate test data
        query = data_generator.random_voice_query()
        audio = data_generator.mock_audio_bytes(1000)
        image = data_generator.mock_image_base64()
        
        assert query is not None
        assert len(audio) > 0
        assert len(image) > 0
        
        # Simulate a request
        import random
        total_ms = random.uniform(300, 500)
        latency_tracker.record(total_ms=total_ms)
        
        # Verify tracking
        stats = latency_tracker.get_stats()
        assert stats["total_requests"] == 1
        assert 300 <= stats["total"]["avg"] <= 500
    
    def test_latency_tracker_independence(self):
        """Each test should get a fresh tracker."""
        from tests.load.locustfile import LatencyTracker
        
        tracker1 = LatencyTracker()
        tracker1.record(total_ms=100.0)
        
        tracker2 = LatencyTracker()
        tracker2.record(total_ms=200.0)
        
        # They should be independent
        assert tracker1.total_latencies[0] == 100.0
        assert tracker2.total_latencies[0] == 200.0
        assert len(tracker1.total_latencies) == 1
        assert len(tracker2.total_latencies) == 1
