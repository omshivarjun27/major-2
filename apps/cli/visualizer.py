"""
Debug Visualizer Module
=======================

Provides debug visualization tools for perception outputs:
- Bounding boxes with class labels
- Depth value overlays
- Segmentation masks
- Hazard annotations

Output: Annotated image for /perception/debug endpoint
"""

import base64
import io
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("debug-visualizer")

# Try to import image processing libraries
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False
    logger.warning("PIL/numpy not available, debug visualizer disabled")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class VisualizerConfig:
    """Configuration for debug visualizer."""

    # Drawing settings
    bbox_thickness: int = 2
    font_size: int = 14
    label_padding: int = 4

    # Colors (RGB)
    default_color: Tuple[int, int, int] = (0, 255, 0)  # Green
    hazard_color: Tuple[int, int, int] = (255, 0, 0)    # Red
    warning_color: Tuple[int, int, int] = (255, 165, 0) # Orange
    info_color: Tuple[int, int, int] = (0, 191, 255)    # Deep sky blue

    # Segmentation settings
    segmentation_alpha: float = 0.4

    # Depth visualization
    depth_colormap: str = "viridis"
    depth_alpha: float = 0.5
    show_depth_values: bool = True

    # Output settings
    output_format: str = "PNG"
    output_quality: int = 85


# Color palette for different classes
CLASS_COLORS = {
    "person": (255, 0, 255),      # Magenta
    "car": (255, 0, 0),           # Red
    "truck": (200, 0, 0),         # Dark red
    "bus": (180, 0, 0),           # Darker red
    "bicycle": (255, 128, 0),     # Orange
    "motorcycle": (255, 100, 0),  # Orange-red
    "dog": (0, 255, 255),         # Cyan
    "cat": (0, 200, 200),         # Dark cyan
    "chair": (128, 128, 0),       # Olive
    "table": (100, 100, 0),       # Dark olive
    "door": (0, 128, 255),        # Light blue
    "stairs": (255, 255, 0),      # Yellow
    "curb": (200, 200, 0),        # Dark yellow
    "pole": (128, 0, 128),        # Purple
    "default": (0, 255, 0),       # Green
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AnnotationLayer:
    """A layer of annotations to render."""

    name: str
    visible: bool = True
    opacity: float = 1.0
    annotations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DebugVisualizerResult:
    """Result of debug visualization."""

    image_bytes: bytes
    image_format: str
    image_base64: str

    # Metadata
    width: int
    height: int
    num_annotations: int
    layers_rendered: List[str]
    processing_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "image_base64": self.image_base64,
            "image_format": self.image_format,
            "dimensions": {"width": self.width, "height": self.height},
            "num_annotations": self.num_annotations,
            "layers": self.layers_rendered,
            "processing_time_ms": round(self.processing_time_ms, 1),
        }


# ============================================================================
# Debug Visualizer
# ============================================================================

class DebugVisualizer:
    """
    Creates annotated debug images from perception outputs.

    Features:
    - Bounding boxes with class labels
    - Depth value overlays
    - Segmentation mask overlays
    - Hazard highlighting
    """

    def __init__(self, config: Optional[VisualizerConfig] = None):
        self.config = config or VisualizerConfig()
        self._font = None

        if IMAGING_AVAILABLE:
            self._load_font()

    def _load_font(self):
        """Load font for text rendering."""
        try:
            self._font = ImageFont.truetype("arial.ttf", self.config.font_size)
        except Exception:
            try:
                self._font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                                 self.config.font_size)
            except Exception:
                self._font = ImageFont.load_default()

    def render(
        self,
        image: Union[bytes, np.ndarray, Image.Image],
        detections: Optional[List[Dict]] = None,
        depth_map: Optional[np.ndarray] = None,
        segmentation_mask: Optional[np.ndarray] = None,
        hazards: Optional[List[Dict]] = None,
        layers: Optional[List[str]] = None,
    ) -> DebugVisualizerResult:
        """
        Render annotated debug image.

        Args:
            image: Input image (bytes, numpy array, or PIL Image)
            detections: List of detection dicts
            depth_map: Depth map array
            segmentation_mask: Segmentation mask array
            hazards: List of hazard dicts with priority info
            layers: Which layers to render (default: all)

        Returns:
            DebugVisualizerResult with annotated image
        """
        start_time = time.time()

        if not IMAGING_AVAILABLE:
            return self._fallback_result()

        # Convert input to PIL Image
        pil_image = self._to_pil_image(image)
        if pil_image is None:
            return self._fallback_result()

        width, height = pil_image.size

        # Create working copy
        annotated = pil_image.copy().convert("RGBA")

        # Determine which layers to render
        render_layers = layers or ["depth", "segmentation", "detections", "hazards"]
        rendered_layers = []
        num_annotations = 0

        # Render each layer
        if "depth" in render_layers and depth_map is not None:
            annotated = self._render_depth_layer(annotated, depth_map)
            rendered_layers.append("depth")

        if "segmentation" in render_layers and segmentation_mask is not None:
            annotated = self._render_segmentation_layer(annotated, segmentation_mask)
            rendered_layers.append("segmentation")

        if "detections" in render_layers and detections:
            annotated, count = self._render_detections(annotated, detections)
            rendered_layers.append("detections")
            num_annotations += count

        if "hazards" in render_layers and hazards:
            annotated, count = self._render_hazards(annotated, hazards)
            rendered_layers.append("hazards")
            num_annotations += count

        # Convert to RGB for output
        annotated = annotated.convert("RGB")

        # Encode output
        output_buffer = io.BytesIO()
        annotated.save(output_buffer, format=self.config.output_format,
                       quality=self.config.output_quality)
        image_bytes = output_buffer.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        processing_time = (time.time() - start_time) * 1000

        return DebugVisualizerResult(
            image_bytes=image_bytes,
            image_format=self.config.output_format.lower(),
            image_base64=f"data:image/{self.config.output_format.lower()};base64,{image_base64}",
            width=width,
            height=height,
            num_annotations=num_annotations,
            layers_rendered=rendered_layers,
            processing_time_ms=processing_time,
        )

    def _to_pil_image(self, image: Union[bytes, np.ndarray, Image.Image]) -> Optional[Image.Image]:
        """Convert various image formats to PIL Image."""
        try:
            if isinstance(image, Image.Image):
                return image
            elif isinstance(image, bytes):
                return Image.open(io.BytesIO(image))
            elif isinstance(image, np.ndarray):
                if len(image.shape) == 2:
                    return Image.fromarray(image, mode='L')
                elif image.shape[2] == 3:
                    return Image.fromarray(image, mode='RGB')
                elif image.shape[2] == 4:
                    return Image.fromarray(image, mode='RGBA')
                else:
                    return Image.fromarray(image[:, :, :3], mode='RGB')
            else:
                logger.error(f"Unsupported image type: {type(image)}")
                return None
        except Exception as e:
            logger.error(f"Failed to convert image: {e}")
            return None

    def _render_depth_layer(
        self,
        image: Image.Image,
        depth_map: np.ndarray,
    ) -> Image.Image:
        """Render depth map overlay."""
        try:
            # Normalize depth map
            depth_normalized = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-6)
            depth_normalized = (depth_normalized * 255).astype(np.uint8)

            # Apply colormap
            depth_colored = self._apply_colormap(depth_normalized)

            # Resize to match image
            depth_pil = Image.fromarray(depth_colored).resize(image.size, Image.BILINEAR)
            depth_pil = depth_pil.convert("RGBA")

            # Set alpha
            alpha = int(self.config.depth_alpha * 255)
            depth_pil.putalpha(alpha)

            # Composite
            return Image.alpha_composite(image, depth_pil)

        except Exception as e:
            logger.warning(f"Failed to render depth layer: {e}")
            return image

    def _apply_colormap(self, array: np.ndarray) -> np.ndarray:
        """Apply viridis-like colormap to array."""
        # Simple viridis approximation
        result = np.zeros((*array.shape, 3), dtype=np.uint8)
        normalized = array / 255.0

        # Viridis-like colors
        result[:, :, 0] = (68 + 180 * normalized).astype(np.uint8)   # R
        result[:, :, 1] = (1 + 220 * normalized).astype(np.uint8)    # G
        result[:, :, 2] = (84 + 90 * (1 - normalized)).astype(np.uint8)  # B

        return result

    def _render_segmentation_layer(
        self,
        image: Image.Image,
        segmentation_mask: np.ndarray,
    ) -> Image.Image:
        """Render segmentation mask overlay."""
        try:
            # Create colored segmentation
            height, width = segmentation_mask.shape[:2]
            seg_colored = np.zeros((height, width, 4), dtype=np.uint8)

            # Get unique classes
            unique_classes = np.unique(segmentation_mask)

            # Generate colors for each class
            np.random.seed(42)  # Consistent colors
            for class_id in unique_classes:
                if class_id == 0:  # Background
                    continue

                mask = segmentation_mask == class_id
                color = np.random.randint(50, 255, 3)
                seg_colored[mask, 0] = color[0]
                seg_colored[mask, 1] = color[1]
                seg_colored[mask, 2] = color[2]
                seg_colored[mask, 3] = int(self.config.segmentation_alpha * 255)

            # Resize and composite
            seg_pil = Image.fromarray(seg_colored, mode='RGBA')
            seg_pil = seg_pil.resize(image.size, Image.NEAREST)

            return Image.alpha_composite(image, seg_pil)

        except Exception as e:
            logger.warning(f"Failed to render segmentation layer: {e}")
            return image

    def _render_detections(
        self,
        image: Image.Image,
        detections: List[Dict],
    ) -> Tuple[Image.Image, int]:
        """Render detection bounding boxes and labels."""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        count = 0

        for det in detections:
            try:
                bbox = det.get("bbox", det.get("box", []))
                if len(bbox) < 4:
                    continue

                class_name = det.get("class", det.get("label", "object"))
                confidence = det.get("confidence", det.get("score", 0.5))
                depth = det.get("depth")

                # Convert normalized to pixel coords
                x1 = int(bbox[0] * width) if bbox[0] <= 1 else int(bbox[0])
                y1 = int(bbox[1] * height) if bbox[1] <= 1 else int(bbox[1])
                x2 = int(bbox[2] * width) if bbox[2] <= 1 else int(bbox[2])
                y2 = int(bbox[3] * height) if bbox[3] <= 1 else int(bbox[3])

                # Get color
                color = CLASS_COLORS.get(class_name.lower(), CLASS_COLORS["default"])

                # Draw bounding box
                draw.rectangle(
                    [x1, y1, x2, y2],
                    outline=color,
                    width=self.config.bbox_thickness,
                )

                # Build label
                label = f"{class_name} {confidence:.2f}"
                if depth and self.config.show_depth_values:
                    label += f" {depth:.1f}m"

                # Draw label background
                text_bbox = draw.textbbox((x1, y1), label, font=self._font)
                label_bg = [
                    text_bbox[0] - self.config.label_padding,
                    text_bbox[1] - self.config.label_padding,
                    text_bbox[2] + self.config.label_padding,
                    text_bbox[3] + self.config.label_padding,
                ]
                draw.rectangle(label_bg, fill=color)

                # Draw label text
                text_color = (0, 0, 0) if sum(color) > 400 else (255, 255, 255)
                draw.text((x1, y1 - self.config.label_padding), label,
                         fill=text_color, font=self._font)

                count += 1

            except Exception as e:
                logger.debug(f"Failed to render detection: {e}")

        return image, count

    def _render_hazards(
        self,
        image: Image.Image,
        hazards: List[Dict],
    ) -> Tuple[Image.Image, int]:
        """Render hazard annotations with priority indicators."""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        count = 0

        for i, hazard in enumerate(hazards):
            try:
                bbox = hazard.get("bbox", [])
                if len(bbox) < 4:
                    continue

                # Convert coords
                x1 = int(bbox[0] * width) if bbox[0] <= 1 else int(bbox[0])
                y1 = int(bbox[1] * height) if bbox[1] <= 1 else int(bbox[1])
                x2 = int(bbox[2] * width) if bbox[2] <= 1 else int(bbox[2])
                y2 = int(bbox[3] * height) if bbox[3] <= 1 else int(bbox[3])

                # Color based on severity
                severity = hazard.get("severity", "medium")
                if severity == "critical":
                    color = (255, 0, 0)  # Red
                elif severity == "high":
                    color = (255, 100, 0)  # Orange-red
                elif severity == "medium":
                    color = (255, 165, 0)  # Orange
                else:
                    color = (255, 255, 0)  # Yellow

                # Draw thick hazard box
                for offset in range(3):
                    draw.rectangle(
                        [x1 - offset, y1 - offset, x2 + offset, y2 + offset],
                        outline=color,
                        width=2,
                    )

                # Draw priority indicator
                priority_label = f"#{i+1}"
                circle_x = x1 + 15
                circle_y = y1 + 15
                draw.ellipse(
                    [circle_x - 12, circle_y - 12, circle_x + 12, circle_y + 12],
                    fill=color,
                    outline=(255, 255, 255),
                    width=2,
                )
                draw.text((circle_x - 6, circle_y - 8), priority_label,
                         fill=(255, 255, 255), font=self._font)

                # Draw hazard info
                name = hazard.get("name", hazard.get("class_name", "hazard"))
                distance = hazard.get("distance_m", 0)
                direction = hazard.get("direction", "ahead")
                risk = hazard.get("risk_score", 0)

                info_label = f"{name} | {distance:.1f}m {direction} | risk:{risk:.2f}"

                # Draw info background
                text_bbox = draw.textbbox((x1, y2 + 5), info_label, font=self._font)
                draw.rectangle(
                    [text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 2, text_bbox[3] + 2],
                    fill=(0, 0, 0, 180),
                )
                draw.text((x1, y2 + 5), info_label, fill=(255, 255, 255), font=self._font)

                count += 1

            except Exception as e:
                logger.debug(f"Failed to render hazard: {e}")

        return image, count

    def _fallback_result(self) -> DebugVisualizerResult:
        """Return fallback result when imaging is unavailable."""
        return DebugVisualizerResult(
            image_bytes=b"",
            image_format="png",
            image_base64="",
            width=0,
            height=0,
            num_annotations=0,
            layers_rendered=[],
            processing_time_ms=0,
        )


# ============================================================================
# Convenience Functions
# ============================================================================

def render_debug_image(
    image: Union[bytes, np.ndarray],
    detections: Optional[List[Dict]] = None,
    depth_map: Optional[np.ndarray] = None,
    segmentation_mask: Optional[np.ndarray] = None,
    hazards: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Quick debug image rendering.

    Args:
        image: Input image
        detections: Detection list
        depth_map: Depth map
        segmentation_mask: Segmentation mask
        hazards: Hazard list

    Returns:
        Result dictionary with base64 image
    """
    visualizer = DebugVisualizer()
    result = visualizer.render(
        image, detections, depth_map, segmentation_mask, hazards
    )
    return result.to_dict()


def annotate_image(
    image_bytes: bytes,
    annotations: Dict[str, Any],
) -> bytes:
    """
    Annotate image with various overlays.

    Args:
        image_bytes: Input image bytes
        annotations: Dict with optional keys:
            - detections: List of detection dicts
            - depth_map: Depth array
            - segmentation: Segmentation array
            - hazards: Hazard list

    Returns:
        Annotated image bytes
    """
    visualizer = DebugVisualizer()
    result = visualizer.render(
        image_bytes,
        detections=annotations.get("detections"),
        depth_map=annotations.get("depth_map"),
        segmentation_mask=annotations.get("segmentation"),
        hazards=annotations.get("hazards"),
    )
    return result.image_bytes
