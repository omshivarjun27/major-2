"""Unit tests for Whisper local STT fallback adapter.

Tests cover:
- WhisperSTT initialization and configuration
- Lazy model loading behavior
- Transcription with mocked model
- Error handling when faster-whisper is not installed
- TranscriptionResult dataclass
- Health and availability checks
"""

import asyncio
from unittest.mock import MagicMock, patch


class TestWhisperConfig:
    """Tests for WhisperConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        from infrastructure.speech.local.whisper_stt import WhisperConfig

        config = WhisperConfig()
        assert config.model_size == "base"
        assert config.device == "auto"
        assert config.compute_type == "auto"
        assert config.language == "en"
        assert config.beam_size == 5
        assert config.vad_filter is True

    def test_custom_config(self):
        """Test custom configuration values."""
        from infrastructure.speech.local.whisper_stt import WhisperConfig

        config = WhisperConfig(
            model_size="tiny",
            device="cpu",
            compute_type="int8",
            language="es",
            beam_size=3,
            vad_filter=False,
        )
        assert config.model_size == "tiny"
        assert config.device == "cpu"
        assert config.compute_type == "int8"
        assert config.language == "es"
        assert config.beam_size == 3
        assert config.vad_filter is False

    def test_from_env_default(self):
        """Test from_env with default environment."""
        from infrastructure.speech.local.whisper_stt import WhisperConfig

        with patch.dict("os.environ", {}, clear=True):
            config = WhisperConfig.from_env()
            assert config.model_size == "base"
            assert config.device == "auto"

    def test_from_env_custom(self):
        """Test from_env with custom environment variables."""
        from infrastructure.speech.local.whisper_stt import WhisperConfig

        env_vars = {
            "WHISPER_MODEL_SIZE": "small",
            "WHISPER_DEVICE": "cuda",
            "WHISPER_COMPUTE_TYPE": "float16",
            "WHISPER_LANGUAGE": "fr",
            "WHISPER_BEAM_SIZE": "10",
            "WHISPER_VAD_FILTER": "false",
        }
        with patch.dict("os.environ", env_vars, clear=True):
            config = WhisperConfig.from_env()
            assert config.model_size == "small"
            assert config.device == "cuda"
            assert config.compute_type == "float16"
            assert config.language == "fr"
            assert config.beam_size == 10
            assert config.vad_filter is False


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_successful_result(self):
        """Test a successful transcription result."""
        from infrastructure.speech.local.whisper_stt import TranscriptionResult

        result = TranscriptionResult(
            text="Hello, world!",
            language="en",
            latency_ms=150.5,
            confidence=0.92,
            model_size="base",
            segments=2,
        )
        assert result.text == "Hello, world!"
        assert result.language == "en"
        assert result.latency_ms == 150.5
        assert result.confidence == 0.92
        assert result.model_size == "base"
        assert result.segments == 2
        assert result.error is None
        assert result.success is True

    def test_failed_result(self):
        """Test a failed transcription result."""
        from infrastructure.speech.local.whisper_stt import TranscriptionResult

        result = TranscriptionResult(
            text="",
            language="en",
            latency_ms=50.0,
            confidence=0.0,
            model_size="base",
            segments=0,
            error="Model failed to load",
        )
        assert result.text == ""
        assert result.error == "Model failed to load"
        assert result.success is False

    def test_empty_text_is_failure(self):
        """Test that empty text counts as failure."""
        from infrastructure.speech.local.whisper_stt import TranscriptionResult

        result = TranscriptionResult(
            text="",
            language="en",
            latency_ms=100.0,
            confidence=0.0,
            model_size="base",
            segments=0,
        )
        assert result.success is False


class TestWhisperSTTInitialization:
    """Tests for WhisperSTT initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        from infrastructure.speech.local.whisper_stt import WhisperSTT

        stt = WhisperSTT()
        assert stt.config.model_size == "base"
        assert stt._model is None
        assert stt._model_loaded is False

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        from infrastructure.speech.local.whisper_stt import WhisperConfig, WhisperSTT

        config = WhisperConfig(model_size="tiny", device="cpu")
        stt = WhisperSTT(config=config)
        assert stt.config.model_size == "tiny"
        assert stt.config.device == "cpu"

    def test_init_with_invalid_model_size_falls_back_to_base(self):
        """Test that invalid model size defaults to 'base'."""
        from infrastructure.speech.local.whisper_stt import WhisperConfig, WhisperSTT

        config = WhisperConfig(model_size="invalid_size")
        stt = WhisperSTT(config=config)
        assert stt.config.model_size == "base"


class TestWhisperSTTAvailability:
    """Tests for Whisper availability checks."""

    def test_is_available_when_installed(self):
        """Test is_available returns True when faster-whisper is installed."""
        from infrastructure.speech.local import whisper_stt

        # Save original value
        original = whisper_stt.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt = whisper_stt.WhisperSTT()
            assert stt.is_available() is True
        finally:
            # Restore original value
            whisper_stt.WHISPER_AVAILABLE = original

    def test_is_available_when_not_installed(self):
        """Test is_available returns False when faster-whisper is not installed."""
        from infrastructure.speech.local import whisper_stt

        original = whisper_stt.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = False
            stt = whisper_stt.WhisperSTT()
            assert stt.is_available() is False
        finally:
            whisper_stt.WHISPER_AVAILABLE = original

    def test_is_loaded_initially_false(self):
        """Test is_loaded returns False before model is loaded."""
        from infrastructure.speech.local.whisper_stt import WhisperSTT

        stt = WhisperSTT()
        assert stt.is_loaded() is False


class TestWhisperSTTLazyLoading:
    """Tests for lazy model loading behavior."""

    async def test_model_not_loaded_on_init(self):
        """Test that model is not loaded during initialization."""
        from infrastructure.speech.local.whisper_stt import WhisperSTT

        stt = WhisperSTT()
        assert stt._model is None
        assert stt._model_loaded is False

    async def test_ensure_model_loaded_returns_false_when_not_available(self):
        """Test _ensure_model_loaded returns False when whisper unavailable."""
        from infrastructure.speech.local import whisper_stt

        original = whisper_stt.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = False
            stt = whisper_stt.WhisperSTT()
            result = await stt._ensure_model_loaded()
            assert result is False
            assert stt._model_loaded is False
        finally:
            whisper_stt.WHISPER_AVAILABLE = original

    async def test_ensure_model_loaded_success_with_mock(self):
        """Test successful model loading with mocked faster-whisper."""
        from infrastructure.speech.local import whisper_stt

        original_available = whisper_stt.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True

            # Mock faster_whisper module
            mock_model = MagicMock()
            mock_fw = MagicMock()
            mock_fw.WhisperModel.return_value = mock_model
            whisper_stt._faster_whisper = mock_fw

            stt = whisper_stt.WhisperSTT()
            result = await stt._ensure_model_loaded()

            assert result is True
            assert stt._model_loaded is True
            assert stt._model is mock_model
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            whisper_stt._faster_whisper = original_fw

    async def test_ensure_model_loaded_only_once(self):
        """Test that model is only loaded once even with concurrent calls."""
        from infrastructure.speech.local import whisper_stt

        original_available = whisper_stt.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True

            load_count = 0
            mock_model = MagicMock()

            def mock_load(*args, **kwargs):
                nonlocal load_count
                load_count += 1
                return mock_model

            mock_fw = MagicMock()
            mock_fw.WhisperModel.side_effect = mock_load
            whisper_stt._faster_whisper = mock_fw

            stt = whisper_stt.WhisperSTT()

            # Call concurrently
            results = await asyncio.gather(
                stt._ensure_model_loaded(),
                stt._ensure_model_loaded(),
                stt._ensure_model_loaded(),
            )

            assert all(results)
            assert load_count == 1  # Only loaded once
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            whisper_stt._faster_whisper = original_fw


class TestWhisperSTTTranscription:
    """Tests for transcription functionality."""

    async def test_transcribe_returns_error_when_not_available(self):
        """Test transcribe returns error result when whisper is not available."""
        from infrastructure.speech.local import whisper_stt

        original = whisper_stt.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = False
            stt = whisper_stt.WhisperSTT()
            result = await stt.transcribe(b"audio data")

            assert result.success is False
            assert result.error is not None and "faster-whisper not installed" in result.error
            assert result.text == ""
        finally:
            whisper_stt.WHISPER_AVAILABLE = original

    async def test_transcribe_returns_error_when_model_fails_to_load(self):
        """Test transcribe returns error when model fails to load."""
        from infrastructure.speech.local import whisper_stt

        original_available = whisper_stt.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True

            mock_fw = MagicMock()
            mock_fw.WhisperModel.side_effect = RuntimeError("GPU memory error")
            whisper_stt._faster_whisper = mock_fw

            stt = whisper_stt.WhisperSTT()
            result = await stt.transcribe(b"audio data")

            assert result.success is False
            assert result.text == ""
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            whisper_stt._faster_whisper = original_fw

    async def test_transcribe_success_with_mock(self):
        """Test successful transcription with mocked model."""
        from infrastructure.speech.local import whisper_stt

        original_available = whisper_stt.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True

            # Create mock segment
            mock_segment = MagicMock()
            mock_segment.text = "Hello, world!"
            mock_segment.avg_logprob = -0.5  # ~0.6 confidence

            # Create mock info
            mock_info = MagicMock()
            mock_info.language = "en"

            # Create mock model
            mock_model = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)

            mock_fw = MagicMock()
            mock_fw.WhisperModel.return_value = mock_model
            whisper_stt._faster_whisper = mock_fw

            stt = whisper_stt.WhisperSTT()
            result = await stt.transcribe(b"audio data")

            assert result.success is True
            assert result.text == "Hello, world!"
            assert result.language == "en"
            assert result.segments == 1
            assert result.latency_ms >= 0  # May be 0 with mocked fast transcription
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            whisper_stt._faster_whisper = original_fw

    async def test_transcribe_with_language_override(self):
        """Test transcription with language override."""
        from infrastructure.speech.local import whisper_stt

        original_available = whisper_stt.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True

            mock_segment = MagicMock()
            mock_segment.text = "Bonjour"
            mock_segment.avg_logprob = -0.3

            mock_info = MagicMock()
            mock_info.language = "fr"

            mock_model = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)

            mock_fw = MagicMock()
            mock_fw.WhisperModel.return_value = mock_model
            whisper_stt._faster_whisper = mock_fw

            stt = whisper_stt.WhisperSTT()
            result = await stt.transcribe(b"audio data", language="fr")

            assert result.success is True
            assert result.language == "fr"

            # Verify transcribe was called with language parameter
            mock_model.transcribe.assert_called_once()
            call_kwargs = mock_model.transcribe.call_args[1]
            assert call_kwargs["language"] == "fr"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            whisper_stt._faster_whisper = original_fw

    async def test_transcribe_handles_exception(self):
        """Test transcription handles exceptions gracefully."""
        from infrastructure.speech.local import whisper_stt

        original_available = whisper_stt.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True

            mock_model = MagicMock()
            mock_model.transcribe.side_effect = RuntimeError("Transcription failed")

            mock_fw = MagicMock()
            mock_fw.WhisperModel.return_value = mock_model
            whisper_stt._faster_whisper = mock_fw

            stt = whisper_stt.WhisperSTT()
            # First ensure model is loaded
            await stt._ensure_model_loaded()

            result = await stt.transcribe(b"audio data")

            assert result.success is False
            assert result.error is not None and "Transcription failed" in result.error
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            whisper_stt._faster_whisper = original_fw


class TestWhisperSTTUnload:
    """Tests for model unloading."""

    async def test_unload_when_loaded(self):
        """Test unloading a loaded model."""
        from infrastructure.speech.local import whisper_stt

        original_available = whisper_stt.WHISPER_AVAILABLE
        original_fw = whisper_stt._faster_whisper

        try:
            whisper_stt.WHISPER_AVAILABLE = True

            mock_model = MagicMock()
            mock_fw = MagicMock()
            mock_fw.WhisperModel.return_value = mock_model
            whisper_stt._faster_whisper = mock_fw

            stt = whisper_stt.WhisperSTT()
            await stt._ensure_model_loaded()
            assert stt.is_loaded() is True

            await stt.unload()
            assert stt.is_loaded() is False
            assert stt._model is None
        finally:
            whisper_stt.WHISPER_AVAILABLE = original_available
            whisper_stt._faster_whisper = original_fw

    async def test_unload_when_not_loaded(self):
        """Test unloading when model is not loaded (no-op)."""
        from infrastructure.speech.local.whisper_stt import WhisperSTT

        stt = WhisperSTT()
        assert stt.is_loaded() is False

        await stt.unload()
        assert stt.is_loaded() is False


class TestWhisperSTTHealth:
    """Tests for health check functionality."""

    def test_health_when_not_available(self):
        """Test health snapshot when whisper is not available."""
        from infrastructure.speech.local import whisper_stt

        original = whisper_stt.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = False
            stt = whisper_stt.WhisperSTT()
            health = stt.health()

            assert health["available"] is False
            assert health["loaded"] is False
            assert health["model_size"] == "base"
        finally:
            whisper_stt.WHISPER_AVAILABLE = original

    def test_health_when_available_not_loaded(self):
        """Test health snapshot when available but not loaded."""
        from infrastructure.speech.local import whisper_stt

        original = whisper_stt.WHISPER_AVAILABLE

        try:
            whisper_stt.WHISPER_AVAILABLE = True
            stt = whisper_stt.WhisperSTT()
            health = stt.health()

            assert health["available"] is True
            assert health["loaded"] is False
            assert health["model_size"] == "base"
            assert health["estimated_vram_mb"] == 200  # base model
        finally:
            whisper_stt.WHISPER_AVAILABLE = original

    def test_health_with_different_model_sizes(self):
        """Test health reports correct VRAM for different model sizes."""
        from infrastructure.speech.local.whisper_stt import WhisperConfig, WhisperSTT

        test_cases = [
            ("tiny", 100),
            ("base", 200),
            ("small", 500),
            ("medium", 1500),
            ("large", 3000),
        ]

        for model_size, expected_vram in test_cases:
            config = WhisperConfig(model_size=model_size)
            stt = WhisperSTT(config=config)
            health = stt.health()
            assert health["estimated_vram_mb"] == expected_vram, f"Failed for {model_size}"


class TestModelInfo:
    """Tests for MODEL_INFO dictionary."""

    def test_model_info_contains_all_sizes(self):
        """Test MODEL_INFO contains all expected model sizes."""
        from infrastructure.speech.local.whisper_stt import MODEL_INFO

        expected_sizes = ["tiny", "base", "small", "medium", "large"]
        for size in expected_sizes:
            assert size in MODEL_INFO

    def test_model_info_has_required_keys(self):
        """Test each MODEL_INFO entry has required keys."""
        from infrastructure.speech.local.whisper_stt import MODEL_INFO

        required_keys = ["vram_mb", "latency_ms", "quality"]
        for size, info in MODEL_INFO.items():
            for key in required_keys:
                assert key in info, f"Missing {key} for {size}"


class TestWhisperModuleExports:
    """Tests for module exports."""

    def test_exports_from_init(self):
        """Test all expected symbols are exported from __init__."""
        from infrastructure.speech.local import (
            WHISPER_AVAILABLE,
            TranscriptionResult,
            WhisperConfig,
            WhisperSTT,
        )

        assert WhisperSTT is not None
        assert WhisperConfig is not None
        assert TranscriptionResult is not None
        assert isinstance(WHISPER_AVAILABLE, bool)


class TestConfigIntegration:
    """Tests for integration with shared config."""

    def test_get_whisper_config(self):
        """Test get_whisper_config returns expected structure."""
        from shared.config.settings import get_whisper_config

        config = get_whisper_config()
        assert "model_size" in config
        assert "device" in config
        assert "compute_type" in config
        assert "language" in config
        assert "vad_filter" in config

    def test_whisper_stt_enabled(self):
        """Test whisper_stt_enabled returns True for valid model sizes."""
        from shared.config.settings import whisper_stt_enabled

        # Default model size is 'base' which is valid
        assert whisper_stt_enabled() is True
