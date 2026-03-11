"""
VQA Engine - Perception Module
==============================

Object detection, edge-aware segmentation, and depth estimation.
Supports both lightweight mock implementations and real ML models.

Performance targets:
- Detection: ≤100ms
- Segmentation: ≤100ms
- Depth: ≤100ms
- Total pipeline: ≤300ms

All core data types are imported from ``shared`` — do NOT redefine them here.
"""

import asyncio
import logging
import os
import time
from typing import Any, List, Optional

import numpy as np

# ── Canonical types from shared module ────────────────────────────────────
from shared.schemas import (  # noqa: F401  – re-exported for backward compat
    BoundingBox,
    DepthEstimator,
    DepthMap,
    Detection,
    ObjectDetector,
    PerceptionResult,
    SegmentationMask,
    Segmenter,
)

try:
    from shared.logging.logging_config import log_event as _log_event
except ImportError:
    def _log_event(*a, **kw): pass

logger = logging.getLogger("vqa-perception")


def _to_numpy(image: Any) -> np.ndarray:
    """Convert any supported image type to a numpy array.

    Handles:
    - numpy arrays (returned as-is)
    - PIL Images (via np.array)
    - LiveKit VideoFrame objects (converted via RGBA buffer)
    """
    if isinstance(image, np.ndarray):
        return image
    if hasattr(image, 'size') and hasattr(image, 'mode'):  # PIL Image
        return np.array(image)
    # LiveKit VideoFrame — has .convert() but no .size / .shape
    if hasattr(image, 'convert') and not hasattr(image, 'shape'):
        try:
            import livekit.rtc as _rtc
            rgba = image.convert(_rtc.VideoBufferType.RGBA)
            arr = np.frombuffer(bytes(rgba.data), dtype=np.uint8).reshape(
                (rgba.height, rgba.width, 4)
            )[:, :, :3]  # drop alpha
            return arr.copy()  # own memory
        except Exception:
            pass
    # Fallback: try np.array
    try:
        return np.array(image)
    except Exception:
        return np.zeros((480, 640, 3), dtype=np.uint8)

# ============================================================================
# Configuration
# ============================================================================

USE_QUANTIZED = os.environ.get("USE_QUANTIZED", "true").lower() == "true"
MAX_DETECTIONS = int(os.environ.get("VQA_MAX_DETECTIONS", "5"))
DETECTION_CONFIDENCE_THRESHOLD = float(os.environ.get("VQA_DETECTION_CONF", "0.5"))

# Try importing optional dependencies
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PILImage = None

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    ort = None


# ============================================================================
# Mock Implementations (Fast, for development/testing)
# ============================================================================

class MockObjectDetector(ObjectDetector):
    """
    Fast mock detector for development and testing.
    Returns deterministic detections based on image size.
    Target latency: <10ms

    NOTE: No dimension-based cache — every call produces fresh detections
    so the system never answers from a stale frame.
    """

    CLASSES = ("person", "chair", "table", "door", "wall", "car", "bicycle", "dog")

    def __init__(self):
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    async def detect(self, image: Any, max_detections: int = MAX_DETECTIONS) -> List[Detection]:
        """Ultra-fast mock detection — no caching, always fresh."""
        # Get image dimensions
        if hasattr(image, 'shape'):
            height, width = image.shape[:2]
        elif hasattr(image, 'size'):
            width, height = image.size
        else:
            width, height = 640, 480

        # Generate deterministic mock detections (no cache)
        detections = []

        # Center object
        cx, cy = width // 2, height // 2
        detections.append(Detection(
            id="obj_1",
            class_name="chair",
            confidence=0.87,
            bbox=BoundingBox(cx - 60, cy - 40, cx + 60, cy + 80)
        ))

        # Left object
        if width > 400:
            detections.append(Detection(
                id="obj_2",
                class_name="table",
                confidence=0.75,
                bbox=BoundingBox(50, cy, 180, cy + 100)
            ))

        # Right object (sometimes)
        if width > 500:
            detections.append(Detection(
                id="obj_3",
                class_name="person",
                confidence=0.82,
                bbox=BoundingBox(width - 150, cy - 80, width - 30, cy + 100)
            ))

        return detections[:max_detections]


class YOLODetector(ObjectDetector):
    """
    YOLO-based object detector using ONNX Runtime or PyTorch.
    Supports YOLOv8 nano/small for fast inference.
    """

    COCO_CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
        "toothbrush"
    ]

    def __init__(self, model_path: Optional[str] = None, use_onnx: bool = True):
        self._model_path = model_path or os.environ.get("DETECTION_MODEL_PATH")
        self._use_onnx = use_onnx
        self._model = None
        self._session = None
        self._ready = False
        self._conf_threshold = DETECTION_CONFIDENCE_THRESHOLD

        if self._model_path:
            self._load_model()

    def _load_model(self):
        """Load YOLO model."""
        try:
            if self._use_onnx and ONNX_AVAILABLE and self._model_path.endswith('.onnx'):
                sess_options = ort.SessionOptions()
                sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self._session = ort.InferenceSession(self._model_path, sess_options)
                self._ready = True
                logger.info(f"Loaded ONNX YOLO model: {self._model_path}")
            elif TORCH_AVAILABLE:
                try:
                    from ultralytics import YOLO
                    self._model = YOLO(self._model_path or "yolov8n.pt")
                    self._ready = True
                    logger.info("Loaded YOLO model with ultralytics")
                except ImportError:
                    logger.warning("ultralytics not available")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self._ready = False

    def is_ready(self) -> bool:
        return self._ready

    async def detect(self, image: Any) -> List[Detection]:
        """Run YOLO detection."""
        if not self._ready:
            return []

        try:
            # Convert to numpy if needed
            if hasattr(image, 'size'):  # PIL Image
                img_np = np.array(image)
            else:
                img_np = image

            # Ensure RGB
            if len(img_np.shape) == 2:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB) if CV2_AVAILABLE else np.stack([img_np]*3, axis=-1)
            elif img_np.shape[2] == 4:
                img_np = img_np[:, :, :3]

            detections = []

            if self._model and hasattr(self._model, 'predict'):
                # Ultralytics YOLO
                results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.predict(img_np, conf=self._conf_threshold, verbose=False)
                )

                for r in results:
                    for i, box in enumerate(r.boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        cls_name = self.COCO_CLASSES[cls_id] if cls_id < len(self.COCO_CLASSES) else "object"

                        detections.append(Detection(
                            id=f"obj_{i+1}",
                            class_name=cls_name,
                            confidence=conf,
                            bbox=BoundingBox(x1, y1, x2, y2)
                        ))

            return detections[:MAX_DETECTIONS]

        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            return []


# ============================================================================
# Segmentation Implementations
# ============================================================================

class EdgeAwareSegmenter(Segmenter):
    """
    Lightweight edge-aware segmentation.
    Uses Canny edges or variance-based confidence estimation.
    Target latency: <50ms
    """

    MAX_SIZE = (160, 120)  # Process at reduced resolution

    def __init__(self, use_canny: bool = False):
        self._use_canny = use_canny and CV2_AVAILABLE
        self._ready = True

    async def segment(self, image: Any, detections: List[Detection]) -> List[SegmentationMask]:
        """Generate edge-aware masks for detections."""
        if not detections:
            return []

        try:
            # Convert and resize for efficiency
            if hasattr(image, 'size'):
                img = image.resize(self.MAX_SIZE, PILImage.Resampling.NEAREST) if PIL_AVAILABLE else image
                img_np = np.array(img, dtype=np.uint8)
                orig_w, orig_h = image.size
            else:
                img_np = image
                orig_h, orig_w = image.shape[:2]

            # Convert to grayscale
            if len(img_np.shape) == 3:
                gray = np.mean(img_np, axis=2).astype(np.uint8)
            else:
                gray = img_np

            # Scale factors
            scale_x = self.MAX_SIZE[0] / orig_w
            scale_y = self.MAX_SIZE[1] / orig_h

            masks = []
            for det in detections[:MAX_DETECTIONS]:
                # Scale bbox to processing resolution
                x1 = int(det.bbox.x1 * scale_x)
                y1 = int(det.bbox.y1 * scale_y)
                x2 = int(det.bbox.x2 * scale_x)
                y2 = int(det.bbox.y2 * scale_y)

                # Clamp
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(self.MAX_SIZE[0], x2), min(self.MAX_SIZE[1], y2)

                if x2 <= x1 or y2 <= y1:
                    boundary_conf = 0.5
                else:
                    roi = gray[y1:y2, x1:x2]

                    if self._use_canny and CV2_AVAILABLE:
                        edges = cv2.Canny(roi, 50, 150)
                        edge_strength = np.mean(edges) / 255.0
                        boundary_conf = min(0.5 + edge_strength * 0.5, 0.95)
                    else:
                        # Variance-based confidence
                        variance = np.var(roi) if roi.size > 0 else 0
                        boundary_conf = min(0.5 + variance / 5000.0, 0.95)

                # Create simple binary mask for bounding box
                mask_array = np.zeros((orig_h, orig_w), dtype=np.uint8)
                mask_array[det.bbox.y1:det.bbox.y2, det.bbox.x1:det.bbox.x2] = 255

                masks.append(SegmentationMask(
                    detection_id=det.id,
                    mask=mask_array,
                    boundary_confidence=boundary_conf
                ))

            return masks

        except Exception as e:
            logger.error(f"Segmentation error: {e}")
            return []


# ============================================================================
# Depth Estimation Implementations
# ============================================================================

class SimpleDepthEstimator(DepthEstimator):
    """
    Fast heuristic-based depth estimation.
    Uses y-position as proxy for distance (closer objects at bottom).
    Target latency: <20ms
    """

    DOWNSCALE = 4

    def __init__(self, min_depth: float = 0.5, max_depth: float = 10.0):
        self._min_depth = min_depth
        self._max_depth = max_depth
        # NOTE: No dimension-based cache — every call produces a fresh depth map.

    async def estimate(self, image: Any) -> DepthMap:
        """Estimate depth using position heuristics — no caching, always fresh."""
        try:
            # Convert VideoFrame / PIL → numpy early
            img_np = _to_numpy(image)
            orig_h, orig_w = img_np.shape[:2]

            # Reduced resolution
            h = orig_h // self.DOWNSCALE
            w = orig_w // self.DOWNSCALE

            # Generate depth map (linear gradient: top=far, bottom=near)
            row_depths = np.linspace(self._max_depth, self._min_depth, h, dtype=np.float32)
            depth = np.tile(row_depths[:, np.newaxis], (1, w))

            return DepthMap(
                depth_array=depth,
                min_depth=self._min_depth,
                max_depth=self._max_depth,
                is_metric=False
            )

        except Exception as e:
            logger.error(f"Depth estimation error: {e}")
            return DepthMap(
                depth_array=np.full((60, 80), 5.0, dtype=np.float32),
                min_depth=5.0,
                max_depth=5.0,
                is_metric=False
            )


class MiDaSDepthEstimator(DepthEstimator):
    """
    MiDaS-based monocular depth estimation.
    Provides more accurate relative depth.
    """

    def __init__(self, model_path: Optional[str] = None, model_type: str = "MiDaS_small"):
        self._model_path = model_path or os.environ.get("DEPTH_MODEL_PATH")
        self._model_type = model_type
        self._model = None
        self._transform = None
        self._ready = False

        if TORCH_AVAILABLE:
            self._load_model()

    def _load_model(self):
        """Load MiDaS model."""
        try:
            if self._model_path and ONNX_AVAILABLE:
                # ONNX path
                self._session = ort.InferenceSession(self._model_path)
                self._ready = True
            elif TORCH_AVAILABLE:
                # PyTorch hub
                self._model = torch.hub.load("intel-isl/MiDaS", self._model_type)
                self._model.eval()
                midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
                self._transform = midas_transforms.small_transform
                self._ready = True
                logger.info(f"Loaded MiDaS model: {self._model_type}")
        except Exception as e:
            logger.warning(f"Failed to load MiDaS: {e}")
            self._ready = False

    async def estimate(self, image: Any) -> DepthMap:
        """Estimate depth using MiDaS."""
        if not self._ready:
            # Fallback to simple estimator
            fallback = SimpleDepthEstimator()
            return await fallback.estimate(image)

        try:
            img_np = _to_numpy(image)

            if self._transform and self._model:
                input_batch = self._transform(img_np)

                with torch.no_grad():
                    prediction = self._model(input_batch)
                    prediction = torch.nn.functional.interpolate(
                        prediction.unsqueeze(1),
                        size=img_np.shape[:2],
                        mode="bicubic",
                        align_corners=False,
                    ).squeeze()

                depth = prediction.cpu().numpy()

                # Normalize to metric-like range (0.5m - 10m)
                d_min, d_max = np.min(depth), np.max(depth)
                depth_normalized = (depth - d_min) / (d_max - d_min + 1e-6)
                depth_metric = 0.5 + depth_normalized * 9.5

                return DepthMap(
                    depth_array=depth_metric.astype(np.float32),
                    min_depth=float(np.min(depth_metric)),
                    max_depth=float(np.max(depth_metric)),
                    is_metric=False
                )

        except Exception as e:
            logger.error(f"MiDaS estimation error: {e}")

        # Fallback
        fallback = SimpleDepthEstimator()
        return await fallback.estimate(image)


# ============================================================================
# Unified Perception Pipeline
# ============================================================================

class PerceptionPipeline:
    """
    Unified perception pipeline running detection, segmentation, and depth
    in parallel for maximum throughput.

    Target total latency: <300ms
    """

    def __init__(
        self,
        detector: Optional[ObjectDetector] = None,
        segmenter: Optional[Segmenter] = None,
        depth_estimator: Optional[DepthEstimator] = None,
        enable_segmentation: bool = True,
        enable_depth: bool = True,
    ):
        self._detector = detector or MockObjectDetector()
        self._segmenter = segmenter or EdgeAwareSegmenter() if enable_segmentation else None
        self._depth_estimator = depth_estimator or SimpleDepthEstimator() if enable_depth else None

        self._enable_segmentation = enable_segmentation
        self._enable_depth = enable_depth

        logger.info(f"PerceptionPipeline initialized: detector={self._detector.name}, "
                   f"seg={enable_segmentation}, depth={enable_depth}")

    # ── Public accessors (used by frame_orchestrator via main.py) ────
    @property
    def detector(self) -> ObjectDetector:
        """Public accessor for the underlying detector."""
        return self._detector

    @property
    def depth_estimator(self) -> Optional[DepthEstimator]:
        """Public accessor for the underlying depth estimator."""
        return self._depth_estimator

    @property
    def segmenter(self) -> Optional[Segmenter]:
        """Public accessor for the underlying segmenter."""
        return self._segmenter

    @property
    def is_ready(self) -> bool:
        return self._detector.is_ready()

    async def detect(self, image: Any) -> list:
        """Delegate detection to the underlying detector (public API)."""
        image = _to_numpy(image)
        return await self._detector.detect(image)

    async def estimate_depth(self, image: Any):
        """Delegate depth estimation to the underlying estimator (public API)."""
        if self._depth_estimator:
            image = _to_numpy(image)
            return await self._depth_estimator.estimate(image)
        return None

    async def process(self, image: Any) -> PerceptionResult:
        """
        Run full perception pipeline.
        Returns detections, masks, depth map, and timing info.

        Accepts PIL Image, numpy array, or LiveKit VideoFrame (auto-converted).
        """
        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        # ── Auto-convert LiveKit VideoFrame → PIL Image ──────────────
        # VideoFrame objects lack .shape and .size; convert them early so
        # every downstream stage receives a format it can work with.
        if not hasattr(image, 'size') and not hasattr(image, 'shape'):
            if hasattr(image, 'convert') and PIL_AVAILABLE:
                try:
                    import livekit.rtc as _rtc
                    rgba = image.convert(_rtc.VideoBufferType.RGBA)
                    image = PILImage.frombytes(
                        'RGBA', (rgba.width, rgba.height), bytes(rgba.data)
                    ).convert('RGB')
                    del rgba
                except Exception as conv_err:
                    logger.warning(f"VideoFrame auto-convert failed: {conv_err}")
                    # Fall through with original image; downstream will handle gracefully

        # Get image size
        if hasattr(image, 'size'):
            img_size = image.size
        elif hasattr(image, 'shape'):
            img_size = (image.shape[1], image.shape[0])
        else:
            img_size = (640, 480)

        # Step 1: Detection
        detections = await self._detector.detect(image)

        if not detections:
            # Fast path for empty scene
            return PerceptionResult(
                detections=[],
                masks=[],
                depth_map=DepthMap(
                    depth_array=np.full((img_size[1] // 4, img_size[0] // 4), 5.0, dtype=np.float32),
                    min_depth=5.0,
                    max_depth=5.0,
                    is_metric=False
                ),
                image_size=img_size,
                latency_ms=(time.time() - start_time) * 1000,
                timestamp=timestamp
            )

        # Steps 2 & 3: Run segmentation and depth in parallel
        masks = []
        depth_map = None

        async def run_segmentation():
            nonlocal masks
            if self._segmenter and self._enable_segmentation:
                masks = await self._segmenter.segment(image, detections)

        async def run_depth():
            nonlocal depth_map
            if self._depth_estimator and self._enable_depth:
                depth_map = await self._depth_estimator.estimate(image)

        await asyncio.gather(run_segmentation(), run_depth())

        # Default depth map if not computed
        if depth_map is None:
            depth_map = DepthMap(
                depth_array=np.full((img_size[1] // 4, img_size[0] // 4), 3.0, dtype=np.float32),
                min_depth=3.0,
                max_depth=3.0,
                is_metric=False
            )

        latency_ms = (time.time() - start_time) * 1000

        # ── Structured event log ─────────────────────────────────────
        _log_event(
            "vqa-perception", "perception_complete",
            component="perception_pipeline",
            latency_ms=latency_ms,
            detections_count=len(detections),
        )

        return PerceptionResult(
            detections=detections,
            masks=masks,
            depth_map=depth_map,
            image_size=img_size,
            latency_ms=latency_ms,
            timestamp=timestamp
        )


# ============================================================================
# Factory Functions
# ============================================================================

def create_detector(use_yolo: bool = False, model_path: Optional[str] = None) -> ObjectDetector:
    """Create an object detector based on configuration."""
    if use_yolo:
        detector = YOLODetector(model_path=model_path)
        if detector.is_ready():
            return detector
        logger.warning("YOLO not ready, falling back to mock")
    return MockObjectDetector()


def create_depth_estimator(use_midas: bool = False, model_path: Optional[str] = None) -> DepthEstimator:
    """Create a depth estimator based on configuration."""
    if use_midas:
        estimator = MiDaSDepthEstimator(model_path=model_path)
        if estimator._ready:
            return estimator
        logger.warning("MiDaS not ready, falling back to simple")
    return SimpleDepthEstimator()


def create_pipeline(
    use_yolo: bool = False,
    use_midas: bool = False,
    enable_segmentation: bool = True,
    enable_depth: bool = True,
    use_mock: bool = False,
) -> PerceptionPipeline:
    """Create a perception pipeline with configured components.

    When *use_yolo*/*use_midas* are False **and** *use_mock* is also False,
    the factory auto-detects model files on disk (via env vars or default
    paths) and enables real inference when models are present.
    """
    if use_mock:
        use_yolo = False
        use_midas = False
    else:
        # ── Auto-enable YOLO when model file exists ──────────────
        if not use_yolo:
            yolo_path = os.environ.get("YOLO_MODEL_PATH", "models/yolov8n.onnx")
            if os.path.isfile(yolo_path):
                use_yolo = True
                logger.info("Auto-enabled YOLO — found model at %s", yolo_path)
        # ── Auto-enable MiDaS when model file exists ─────────────
        if not use_midas:
            midas_path = os.environ.get("MIDAS_MODEL_PATH", "models/midas_v21_small_256.onnx")
            if os.path.isfile(midas_path):
                use_midas = True
                logger.info("Auto-enabled MiDaS — found model at %s", midas_path)

    detector = create_detector(use_yolo=use_yolo)
    segmenter = EdgeAwareSegmenter() if enable_segmentation else None
    depth_estimator = create_depth_estimator(use_midas=use_midas) if enable_depth else None

    return PerceptionPipeline(
        detector=detector,
        segmenter=segmenter,
        depth_estimator=depth_estimator,
        enable_segmentation=enable_segmentation,
        enable_depth=enable_depth,
    )
