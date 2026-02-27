"""Load test fixtures and configuration.

Provides shared fixtures for load testing the Voice-Vision Assistant.
"""

from __future__ import annotations

import base64
import io
import os
import sys
from typing import Generator

import pytest

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Mock Data Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_audio_1s() -> bytes:
    """1 second of mock audio data (16kHz, 16-bit mono silence)."""
    return b"\x00\x00" * 16000


@pytest.fixture
def mock_audio_3s() -> bytes:
    """3 seconds of mock audio data."""
    return b"\x00\x00" * 48000


@pytest.fixture
def mock_image_640x480() -> bytes:
    """640x480 mock JPEG image."""
    try:
        from PIL import Image
        img = Image.new("RGB", (640, 480), color=(128, 128, 128))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        return buffer.getvalue()
    except ImportError:
        pytest.skip("PIL not available")


@pytest.fixture
def mock_image_base64(mock_image_640x480: bytes) -> str:
    """Base64 encoded mock image."""
    return base64.b64encode(mock_image_640x480).decode("utf-8")


@pytest.fixture
def sample_voice_queries() -> list[str]:
    """Sample voice queries for testing."""
    return [
        "What do you see in front of me?",
        "Is there anyone nearby?",
        "Describe the scene around me",
        "Are there any obstacles ahead?",
        "What color is the object to my left?",
    ]


@pytest.fixture
def sample_vision_prompts() -> list[str]:
    """Sample vision prompts for testing."""
    return [
        "Describe everything you see",
        "Are there any people in this image?",
        "What objects are in the foreground?",
        "Is this area safe to walk?",
        "What's the dominant color?",
    ]


# ---------------------------------------------------------------------------
# Latency Tracker Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def latency_tracker():
    """Fresh latency tracker for each test."""
    from tests.load.locustfile import LatencyTracker
    return LatencyTracker()


# ---------------------------------------------------------------------------
# Test Data Generator Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def data_generator():
    """Test data generator instance."""
    from tests.load.locustfile import TestDataGenerator
    return TestDataGenerator()
