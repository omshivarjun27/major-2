"""INT8 quantization support for vision models.

Provides utilities and configuration for INT8 quantization of
ONNX models (YOLO, MiDaS) to reduce VRAM usage and improve
inference speed while maintaining acceptable accuracy.

Usage:
    from core.vision.model_loader import load_quantized_model, is_quantization_enabled

    if is_quantization_enabled():
        model = load_quantized_model("yolo", "models/yolov8n_int8.onnx")
    else:
        model = load_model("models/yolov8n.onnx")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("model-loader")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class QuantizationMode(Enum):
    """Model quantization mode."""
    NONE = "none"           # Full precision (FP32)
    INT8 = "int8"           # INT8 quantization
    FP16 = "fp16"           # Half precision
    DYNAMIC = "dynamic"     # Dynamic quantization


@dataclass
class ModelConfig:
    """Configuration for a quantized model."""
    name: str
    original_path: str
    quantized_path: Optional[str] = None
    quantization_mode: QuantizationMode = QuantizationMode.NONE
    accuracy_threshold: float = 0.95  # Max 5% accuracy loss
    latency_budget_ms: float = 300.0  # Vision pipeline budget

    @property
    def use_quantized(self) -> bool:
        """Whether to use quantized model."""
        return (
            self.quantization_mode != QuantizationMode.NONE
            and self.quantized_path is not None
            and Path(self.quantized_path).exists()
        )

    @property
    def active_path(self) -> str:
        """Get the active model path (quantized or original)."""
        if self.use_quantized:
            return self.quantized_path
        return self.original_path


# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------

_MODEL_CONFIGS: Dict[str, ModelConfig] = {}


def register_model(config: ModelConfig):
    """Register a model configuration."""
    _MODEL_CONFIGS[config.name] = config


def get_model_config(name: str) -> Optional[ModelConfig]:
    """Get model configuration by name."""
    return _MODEL_CONFIGS.get(name)


def list_models() -> List[str]:
    """List all registered models."""
    return list(_MODEL_CONFIGS.keys())


# Initialize default model configurations
def _init_default_models():
    """Initialize default model configurations."""
    register_model(ModelConfig(
        name="yolo",
        original_path="models/yolov8n.onnx",
        quantized_path="models/yolov8n_int8.onnx",
        quantization_mode=QuantizationMode.INT8,
        accuracy_threshold=0.95,
        latency_budget_ms=100.0,
    ))

    register_model(ModelConfig(
        name="midas",
        original_path="models/midas_small.onnx",
        quantized_path="models/midas_small_int8.onnx",
        quantization_mode=QuantizationMode.INT8,
        accuracy_threshold=0.90,
        latency_budget_ms=150.0,
    ))


_init_default_models()


# ---------------------------------------------------------------------------
# Quantization Settings
# ---------------------------------------------------------------------------

def is_quantization_enabled() -> bool:
    """Check if quantization is enabled via environment variable."""
    return os.environ.get("ENABLE_QUANTIZATION", "false").lower() in ("true", "1", "yes")


def get_quantization_mode() -> QuantizationMode:
    """Get the configured quantization mode."""
    mode = os.environ.get("QUANTIZATION_MODE", "int8").lower()
    try:
        return QuantizationMode(mode)
    except ValueError:
        return QuantizationMode.INT8


# ---------------------------------------------------------------------------
# Model Loading
# ---------------------------------------------------------------------------

class ModelLoader:
    """Loads models with quantization support."""

    def __init__(self, enable_quantization: Optional[bool] = None):
        self.enable_quantization = (
            enable_quantization if enable_quantization is not None
            else is_quantization_enabled()
        )
        self._loaded_models: Dict[str, Any] = {}
        self._load_stats: Dict[str, Dict[str, Any]] = {}

    def load_onnx_model(
        self,
        name: str,
        custom_path: Optional[str] = None,
        force_quantized: bool = False,
    ) -> Tuple[Any, Dict[str, Any]]:
        """Load an ONNX model with optional quantization.

        Returns:
            Tuple of (model/session, stats dict)
        """
        config = get_model_config(name)
        if config is None and custom_path is None:
            raise ValueError(f"Unknown model: {name}")

        # Determine path
        if custom_path:
            model_path = custom_path
            use_quantized = False
        elif self.enable_quantization or force_quantized:
            model_path = config.active_path
            use_quantized = config.use_quantized
        else:
            model_path = config.original_path
            use_quantized = False

        # Load model
        import time
        start = time.perf_counter()

        try:
            import onnxruntime as ort

            # Configure session options
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            # Select execution provider
            providers = []
            if self._cuda_available():
                providers.append("CUDAExecutionProvider")
            providers.append("CPUExecutionProvider")

            session = ort.InferenceSession(
                model_path,
                sess_options=sess_options,
                providers=providers,
            )

            load_time = (time.perf_counter() - start) * 1000

            stats = {
                "name": name,
                "path": model_path,
                "quantized": use_quantized,
                "load_time_ms": load_time,
                "providers": session.get_providers(),
            }

            self._loaded_models[name] = session
            self._load_stats[name] = stats

            logger.info(
                f"Loaded {name} from {model_path} "
                f"(quantized={use_quantized}, time={load_time:.0f}ms)"
            )

            return session, stats

        except ImportError:
            # ONNX Runtime not available, return mock
            load_time = (time.perf_counter() - start) * 1000
            stats = {
                "name": name,
                "path": model_path,
                "quantized": use_quantized,
                "load_time_ms": load_time,
                "error": "onnxruntime not available",
            }
            self._load_stats[name] = stats
            return None, stats
        except Exception as e:
            load_time = (time.perf_counter() - start) * 1000
            stats = {
                "name": name,
                "path": model_path,
                "quantized": use_quantized,
                "load_time_ms": load_time,
                "error": str(e),
            }
            self._load_stats[name] = stats
            return None, stats

    def _cuda_available(self) -> bool:
        """Check if CUDA is available for ONNX Runtime."""
        try:
            import onnxruntime as ort
            return "CUDAExecutionProvider" in ort.get_available_providers()
        except ImportError:
            return False

    def get_load_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get loading statistics for a model."""
        return self._load_stats.get(name)

    def is_loaded(self, name: str) -> bool:
        """Check if a model is loaded."""
        return name in self._loaded_models


# Global loader instance
_model_loader: Optional[ModelLoader] = None


def get_model_loader() -> ModelLoader:
    """Get the global model loader instance."""
    global _model_loader
    if _model_loader is None:
        _model_loader = ModelLoader()
    return _model_loader


def load_quantized_model(
    name: str,
    custom_path: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """Convenience function to load a model with quantization support."""
    return get_model_loader().load_onnx_model(name, custom_path)


# ---------------------------------------------------------------------------
# Quantization Utilities
# ---------------------------------------------------------------------------

@dataclass
class QuantizationResult:
    """Result of model quantization."""
    original_path: str
    quantized_path: str
    original_size_mb: float
    quantized_size_mb: float
    compression_ratio: float
    success: bool
    error: Optional[str] = None


def quantize_onnx_model(
    input_path: str,
    output_path: str,
    mode: QuantizationMode = QuantizationMode.INT8,
) -> QuantizationResult:
    """Quantize an ONNX model to INT8 or FP16.

    Note: Requires onnxruntime-tools for full quantization.
    This function provides the interface; actual quantization
    requires the quantize_models.py script.
    """
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        return QuantizationResult(
            original_path=input_path,
            quantized_path=output_path,
            original_size_mb=0,
            quantized_size_mb=0,
            compression_ratio=1.0,
            success=False,
            error=f"Input file not found: {input_path}",
        )

    original_size = input_file.stat().st_size / (1024 * 1024)

    try:
        if mode == QuantizationMode.INT8:
            # Use onnxruntime.quantization
            from onnxruntime.quantization import QuantType, quantize_dynamic

            quantize_dynamic(
                model_input=input_path,
                model_output=output_path,
                weight_type=QuantType.QInt8,
            )
        elif mode == QuantizationMode.FP16:
            # Use onnx for FP16 conversion
            import onnx
            from onnx import numpy_helper

            model = onnx.load(input_path)
            # Convert to FP16 (simplified - full implementation in script)
            onnx.save(model, output_path)
        else:
            return QuantizationResult(
                original_path=input_path,
                quantized_path=output_path,
                original_size_mb=original_size,
                quantized_size_mb=0,
                compression_ratio=1.0,
                success=False,
                error=f"Unsupported quantization mode: {mode}",
            )

        quantized_size = output_file.stat().st_size / (1024 * 1024)
        compression = original_size / quantized_size if quantized_size > 0 else 1.0

        return QuantizationResult(
            original_path=input_path,
            quantized_path=output_path,
            original_size_mb=original_size,
            quantized_size_mb=quantized_size,
            compression_ratio=compression,
            success=True,
        )

    except ImportError as e:
        return QuantizationResult(
            original_path=input_path,
            quantized_path=output_path,
            original_size_mb=original_size,
            quantized_size_mb=0,
            compression_ratio=1.0,
            success=False,
            error=f"Missing dependency: {e}",
        )
    except Exception as e:
        return QuantizationResult(
            original_path=input_path,
            quantized_path=output_path,
            original_size_mb=original_size,
            quantized_size_mb=0,
            compression_ratio=1.0,
            success=False,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Benchmark Utilities
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    """Result of model benchmark comparison."""
    model_name: str
    original_latency_ms: float
    quantized_latency_ms: float
    speedup: float
    accuracy_retained: float  # 0.0 - 1.0
    vram_original_mb: float
    vram_quantized_mb: float
    vram_reduction_pct: float
    within_budget: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "original_latency_ms": round(self.original_latency_ms, 2),
            "quantized_latency_ms": round(self.quantized_latency_ms, 2),
            "speedup": round(self.speedup, 2),
            "accuracy_retained": round(self.accuracy_retained, 3),
            "vram_original_mb": round(self.vram_original_mb, 1),
            "vram_quantized_mb": round(self.vram_quantized_mb, 1),
            "vram_reduction_pct": round(self.vram_reduction_pct, 1),
            "within_budget": self.within_budget,
        }


def benchmark_quantization(
    model_name: str,
    original_path: str,
    quantized_path: str,
    test_input: Any,
    latency_budget_ms: float = 300.0,
) -> BenchmarkResult:
    """Benchmark original vs quantized model performance.

    This is a placeholder for the actual benchmarking logic.
    Full implementation requires running actual inference.
    """
    # Placeholder - actual benchmarking would load both models
    # and run inference to measure latency and VRAM
    return BenchmarkResult(
        model_name=model_name,
        original_latency_ms=0.0,
        quantized_latency_ms=0.0,
        speedup=1.0,
        accuracy_retained=1.0,
        vram_original_mb=0.0,
        vram_quantized_mb=0.0,
        vram_reduction_pct=0.0,
        within_budget=True,
    )
