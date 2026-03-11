"""
Tests for Debug Visualizer Module
==================================

Tests for perception output visualization.
"""

import io

import pytest

# Check if imaging libraries available
try:
    import numpy as np
    from PIL import Image
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False


# ============================================================================
# Test Debug Visualizer
# ============================================================================

@pytest.mark.skipif(not IMAGING_AVAILABLE, reason="PIL/numpy not available")
class TestDebugVisualizer:
    """Tests for debug visualization."""

    def test_import(self):
        """Test module imports successfully."""
        from apps.cli import DebugVisualizer
        assert DebugVisualizer is not None

    def test_visualizer_creation(self):
        """Test visualizer instantiation."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        assert visualizer is not None

    def test_config_defaults(self):
        """Test default configuration values."""
        from apps.cli import VisualizerConfig

        config = VisualizerConfig()

        assert config.bbox_thickness == 2
        assert config.font_size == 14
        assert config.output_format == "PNG"

    def _create_test_image(self, width=640, height=480) -> np.ndarray:
        """Create a test image array."""
        return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

    def test_render_empty_annotations(self):
        """Test rendering with no annotations."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()

        result = visualizer.render(image)

        assert result.width == 640
        assert result.height == 480
        assert result.image_bytes
        assert result.image_base64

    def test_render_detections(self):
        """Test rendering with detection annotations."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()

        detections = [
            {"class": "person", "confidence": 0.95, "bbox": [0.1, 0.2, 0.3, 0.8], "depth": 2.5},
            {"class": "chair", "confidence": 0.88, "bbox": [0.5, 0.4, 0.7, 0.9], "depth": 3.0},
        ]

        result = visualizer.render(image, detections=detections)

        assert result.num_annotations == 2
        assert "detections" in result.layers_rendered

    def test_render_hazards(self):
        """Test rendering with hazard annotations."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()

        hazards = [
            {
                "name": "person",
                "bbox": [0.2, 0.3, 0.4, 0.8],
                "severity": "critical",
                "distance_m": 1.5,
                "direction": "ahead",
                "risk_score": 0.9,
            },
        ]

        result = visualizer.render(image, hazards=hazards)

        assert result.num_annotations >= 1
        assert "hazards" in result.layers_rendered

    def test_render_depth_map(self):
        """Test rendering with depth map overlay."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()
        depth_map = np.random.random((480, 640)).astype(np.float32) * 10  # 0-10m

        result = visualizer.render(image, depth_map=depth_map)

        assert "depth" in result.layers_rendered

    def test_render_segmentation(self):
        """Test rendering with segmentation mask."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()
        segmentation = np.random.randint(0, 10, (480, 640), dtype=np.uint8)

        result = visualizer.render(image, segmentation_mask=segmentation)

        assert "segmentation" in result.layers_rendered

    def test_render_all_layers(self):
        """Test rendering with all annotation types."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()

        detections = [
            {"class": "person", "confidence": 0.95, "bbox": [0.1, 0.2, 0.3, 0.8]},
        ]
        depth_map = np.random.random((480, 640)).astype(np.float32) * 10
        segmentation = np.random.randint(0, 10, (480, 640), dtype=np.uint8)
        hazards = [
            {"name": "person", "bbox": [0.1, 0.2, 0.3, 0.8], "severity": "high",
             "distance_m": 2.0, "direction": "ahead", "risk_score": 0.7},
        ]

        result = visualizer.render(
            image,
            detections=detections,
            depth_map=depth_map,
            segmentation_mask=segmentation,
            hazards=hazards,
        )

        assert len(result.layers_rendered) >= 3

    def test_render_pil_image_input(self):
        """Test rendering with PIL Image input."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        pil_image = Image.new('RGB', (640, 480), color='blue')

        result = visualizer.render(pil_image)

        assert result.width == 640
        assert result.height == 480

    def test_render_bytes_input(self):
        """Test rendering with bytes input."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()

        # Create a test image and convert to bytes
        pil_image = Image.new('RGB', (640, 480), color='green')
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        result = visualizer.render(image_bytes)

        assert result.width == 640
        assert result.height == 480

    def test_layer_selection(self):
        """Test selective layer rendering."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()

        detections = [
            {"class": "person", "confidence": 0.95, "bbox": [0.1, 0.2, 0.3, 0.8]},
        ]
        depth_map = np.random.random((480, 640)).astype(np.float32) * 10

        # Only render detections
        result = visualizer.render(
            image,
            detections=detections,
            depth_map=depth_map,
            layers=["detections"],  # Explicitly only detections
        )

        assert "detections" in result.layers_rendered
        # Depth should not be rendered even though provided

    def test_result_to_dict(self):
        """Test result serialization."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()

        detections = [
            {"class": "test", "confidence": 0.9, "bbox": [0.2, 0.3, 0.4, 0.6]},
        ]

        result = visualizer.render(image, detections=detections)
        result_dict = result.to_dict()

        assert "image_base64" in result_dict
        assert "image_format" in result_dict
        assert "dimensions" in result_dict
        assert "num_annotations" in result_dict
        assert "layers" in result_dict
        assert "processing_time_ms" in result_dict

    def test_output_is_valid_image(self):
        """Test that output can be decoded back to valid image."""
        from apps.cli import DebugVisualizer

        visualizer = DebugVisualizer()
        image = self._create_test_image()

        result = visualizer.render(image)

        # Decode and verify
        output_image = Image.open(io.BytesIO(result.image_bytes))
        assert output_image.size == (640, 480)


# ============================================================================
# Test Convenience Functions
# ============================================================================

@pytest.mark.skipif(not IMAGING_AVAILABLE, reason="PIL/numpy not available")
class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def _create_test_image(self) -> np.ndarray:
        """Create a test image array."""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    def test_render_debug_image(self):
        """Test render_debug_image function."""
        from apps.cli import render_debug_image

        image = self._create_test_image()
        detections = [
            {"class": "obj", "confidence": 0.9, "bbox": [0.2, 0.3, 0.5, 0.7]},
        ]

        result = render_debug_image(image, detections=detections)

        assert isinstance(result, dict)
        assert "image_base64" in result

    def test_annotate_image(self):
        """Test annotate_image function."""
        from apps.cli import annotate_image

        # Create test image bytes
        pil_image = Image.new('RGB', (320, 240), color='red')
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        annotations = {
            "detections": [
                {"class": "test", "confidence": 0.95, "bbox": [0.1, 0.2, 0.4, 0.6]},
            ],
        }

        result_bytes = annotate_image(image_bytes, annotations)

        assert isinstance(result_bytes, bytes)
        assert len(result_bytes) > 0


# ============================================================================
# Test Without Imaging Libraries
# ============================================================================

class TestFallbackBehavior:
    """Tests for behavior when imaging libraries unavailable."""

    def test_fallback_result(self):
        """Test that fallback result is returned when imaging unavailable."""
        from apps.cli import DebugVisualizerResult

        # Create a minimal fallback result
        result = DebugVisualizerResult(
            image_bytes=b"",
            image_format="png",
            image_base64="",
            width=0,
            height=0,
            num_annotations=0,
            layers_rendered=[],
            processing_time_ms=0,
        )

        assert result.width == 0
        assert result.height == 0
        assert result.image_bytes == b""


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
