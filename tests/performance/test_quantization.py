"""P4: INT8 Quantization Tests (T-078).

Tests for INT8 quantization support in vision models.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

# Project imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Import Tests
# ---------------------------------------------------------------------------

class TestQuantizationImports:
    """Test quantization module imports."""

    def test_model_loader_import(self):
        """model_loader module should import correctly."""
        from core.vision.model_loader import (
            ModelConfig,
            ModelLoader,
            QuantizationMode,
        )

        assert ModelLoader is not None
        assert ModelConfig is not None
        assert QuantizationMode is not None


# ---------------------------------------------------------------------------
# QuantizationMode Tests
# ---------------------------------------------------------------------------

class TestQuantizationMode:
    """Test QuantizationMode enum."""

    def test_mode_values(self):
        """Should have expected mode values."""
        from core.vision.model_loader import QuantizationMode

        assert QuantizationMode.NONE.value == "none"
        assert QuantizationMode.INT8.value == "int8"
        assert QuantizationMode.FP16.value == "fp16"
        assert QuantizationMode.DYNAMIC.value == "dynamic"

    def test_mode_from_string(self):
        """Should create mode from string."""
        from core.vision.model_loader import QuantizationMode

        assert QuantizationMode("int8") == QuantizationMode.INT8
        assert QuantizationMode("fp16") == QuantizationMode.FP16


# ---------------------------------------------------------------------------
# ModelConfig Tests
# ---------------------------------------------------------------------------

class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_config_creation(self):
        """Should create config with defaults."""
        from core.vision.model_loader import ModelConfig, QuantizationMode

        config = ModelConfig(
            name="test_model",
            original_path="models/test.onnx",
        )

        assert config.name == "test_model"
        assert config.quantization_mode == QuantizationMode.NONE
        assert config.accuracy_threshold == 0.95

    def test_use_quantized_without_path(self):
        """Should not use quantized without path."""
        from core.vision.model_loader import ModelConfig, QuantizationMode

        config = ModelConfig(
            name="test",
            original_path="models/test.onnx",
            quantization_mode=QuantizationMode.INT8,
            quantized_path=None,
        )

        assert config.use_quantized is False

    def test_active_path_original(self):
        """Should return original path when not quantized."""
        from core.vision.model_loader import ModelConfig

        config = ModelConfig(
            name="test",
            original_path="models/original.onnx",
        )

        assert config.active_path == "models/original.onnx"


# ---------------------------------------------------------------------------
# Model Registry Tests
# ---------------------------------------------------------------------------

class TestModelRegistry:
    """Test model registry functions."""

    def test_register_model(self):
        """Should register model configuration."""
        from core.vision.model_loader import (
            ModelConfig,
            get_model_config,
            register_model,
        )

        config = ModelConfig(
            name="test_registry",
            original_path="models/test.onnx",
        )
        register_model(config)

        retrieved = get_model_config("test_registry")
        assert retrieved is not None
        assert retrieved.name == "test_registry"

    def test_list_models(self):
        """Should list all registered models."""
        from core.vision.model_loader import list_models

        models = list_models()

        assert isinstance(models, list)
        assert "yolo" in models  # Default model
        assert "midas" in models  # Default model

    def test_get_nonexistent_model(self):
        """Should return None for unknown model."""
        from core.vision.model_loader import get_model_config

        config = get_model_config("nonexistent_model_xyz")
        assert config is None


# ---------------------------------------------------------------------------
# Quantization Settings Tests
# ---------------------------------------------------------------------------

class TestQuantizationSettings:
    """Test quantization settings functions."""

    def test_is_quantization_enabled_default(self):
        """Should be disabled by default."""
        from core.vision.model_loader import is_quantization_enabled

        # Clear env var
        with patch.dict(os.environ, {}, clear=True):
            result = is_quantization_enabled()
            assert result is False

    def test_is_quantization_enabled_true(self):
        """Should be enabled when env var is true."""
        from core.vision.model_loader import is_quantization_enabled

        with patch.dict(os.environ, {"ENABLE_QUANTIZATION": "true"}):
            result = is_quantization_enabled()
            assert result is True

    def test_get_quantization_mode_default(self):
        """Should return INT8 by default."""
        from core.vision.model_loader import QuantizationMode, get_quantization_mode

        with patch.dict(os.environ, {}, clear=True):
            mode = get_quantization_mode()
            assert mode == QuantizationMode.INT8

    def test_get_quantization_mode_custom(self):
        """Should return configured mode."""
        from core.vision.model_loader import QuantizationMode, get_quantization_mode

        with patch.dict(os.environ, {"QUANTIZATION_MODE": "fp16"}):
            mode = get_quantization_mode()
            assert mode == QuantizationMode.FP16


# ---------------------------------------------------------------------------
# ModelLoader Tests
# ---------------------------------------------------------------------------

class TestModelLoader:
    """Test ModelLoader class."""

    def test_loader_creation(self):
        """Should create loader instance."""
        from core.vision.model_loader import ModelLoader

        loader = ModelLoader(enable_quantization=False)
        assert loader is not None
        assert loader.enable_quantization is False

    def test_loader_load_stats(self):
        """Should track loading stats."""
        from core.vision.model_loader import ModelLoader

        loader = ModelLoader(enable_quantization=False)

        # Try to load (will fail without model file, but tracks stats)
        session, stats = loader.load_onnx_model("yolo")

        assert stats is not None
        assert "name" in stats
        assert stats["name"] == "yolo"

    def test_loader_is_loaded(self):
        """Should track loaded models."""
        from core.vision.model_loader import ModelLoader

        loader = ModelLoader()

        assert loader.is_loaded("nonexistent") is False

    def test_global_loader(self):
        """Should provide global loader instance."""
        from core.vision.model_loader import get_model_loader

        loader1 = get_model_loader()
        loader2 = get_model_loader()

        assert loader1 is loader2


# ---------------------------------------------------------------------------
# QuantizationResult Tests
# ---------------------------------------------------------------------------

class TestQuantizationResult:
    """Test QuantizationResult dataclass."""

    def test_result_creation(self):
        """Should create result with all fields."""
        from core.vision.model_loader import QuantizationResult

        result = QuantizationResult(
            original_path="models/model.onnx",
            quantized_path="models/model_int8.onnx",
            original_size_mb=100.0,
            quantized_size_mb=25.0,
            compression_ratio=4.0,
            success=True,
        )

        assert result.success is True
        assert result.compression_ratio == 4.0

    def test_result_with_error(self):
        """Should handle error case."""
        from core.vision.model_loader import QuantizationResult

        result = QuantizationResult(
            original_path="models/model.onnx",
            quantized_path="models/model_int8.onnx",
            original_size_mb=0,
            quantized_size_mb=0,
            compression_ratio=1.0,
            success=False,
            error="File not found",
        )

        assert result.success is False
        assert result.error == "File not found"


# ---------------------------------------------------------------------------
# BenchmarkResult Tests
# ---------------------------------------------------------------------------

class TestBenchmarkResult:
    """Test BenchmarkResult dataclass."""

    def test_benchmark_result_creation(self):
        """Should create benchmark result."""
        from core.vision.model_loader import BenchmarkResult

        result = BenchmarkResult(
            model_name="yolo",
            original_latency_ms=50.0,
            quantized_latency_ms=30.0,
            speedup=1.67,
            accuracy_retained=0.97,
            vram_original_mb=500.0,
            vram_quantized_mb=200.0,
            vram_reduction_pct=60.0,
            within_budget=True,
        )

        assert result.speedup == 1.67
        assert result.accuracy_retained == 0.97

    def test_benchmark_to_dict(self):
        """Should serialize to dict."""
        from core.vision.model_loader import BenchmarkResult

        result = BenchmarkResult(
            model_name="test",
            original_latency_ms=50.0,
            quantized_latency_ms=30.0,
            speedup=1.67,
            accuracy_retained=0.97,
            vram_original_mb=500.0,
            vram_quantized_mb=200.0,
            vram_reduction_pct=60.0,
            within_budget=True,
        )

        d = result.to_dict()

        assert d["model_name"] == "test"
        assert d["speedup"] == 1.67
        assert d["within_budget"] is True


# ---------------------------------------------------------------------------
# Quantize Function Tests
# ---------------------------------------------------------------------------

class TestQuantizeFunction:
    """Test quantize_onnx_model function."""

    def test_quantize_missing_input(self):
        """Should handle missing input file."""
        from core.vision.model_loader import QuantizationMode, quantize_onnx_model

        result = quantize_onnx_model(
            input_path="nonexistent/model.onnx",
            output_path="output/model_int8.onnx",
            mode=QuantizationMode.INT8,
        )

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_quantize_unsupported_mode(self):
        """Should handle unsupported quantization mode."""
        import os
        import tempfile

        from core.vision.model_loader import QuantizationMode, quantize_onnx_model

        # Create a temp file to test with
        with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as f:
            f.write(b"dummy data")
            temp_path = f.name

        try:
            result = quantize_onnx_model(
                input_path=temp_path,
                output_path="output/model.onnx",
                mode=QuantizationMode.NONE,
            )

            assert result.success is False
        finally:
            os.unlink(temp_path)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestQuantizationIntegration:
    """Integration tests for quantization workflow."""

    def test_full_config_workflow(self):
        """Test complete configuration workflow."""
        from core.vision.model_loader import (
            ModelConfig,
            ModelLoader,
            QuantizationMode,
        )

        # Create config
        config = ModelConfig(
            name="integration_test",
            original_path="models/test.onnx",
            quantized_path="models/test_int8.onnx",
            quantization_mode=QuantizationMode.INT8,
            accuracy_threshold=0.95,
            latency_budget_ms=100.0,
        )

        # Verify config properties
        assert config.accuracy_threshold == 0.95
        assert config.latency_budget_ms == 100.0

        # Create loader
        loader = ModelLoader(enable_quantization=True)
        assert loader.enable_quantization is True

    def test_default_models_registered(self):
        """Default models should be pre-registered."""
        from core.vision.model_loader import get_model_config

        yolo_config = get_model_config("yolo")
        midas_config = get_model_config("midas")

        assert yolo_config is not None
        assert midas_config is not None

        assert yolo_config.latency_budget_ms == 100.0
        assert midas_config.latency_budget_ms == 150.0
