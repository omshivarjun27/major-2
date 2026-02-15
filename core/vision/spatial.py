"""
Spatial Perception Module for Voice & Vision Assistant
=======================================================

This module provides object detection, edge-aware segmentation, depth estimation,
and spatial fusion capabilities for real-time micro-navigation assistance.

Pipeline: FRAME → DETECT → SEGMENT → DEPTH → FUSE → NAVIGATION

All core data types are imported from ``shared`` — do NOT redefine them here.
"""

import asyncio
import gc
import logging
import math
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any, Union, TYPE_CHECKING
import numpy as np

# ── Canonical types from shared module ────────────────────────────────────
from shared.schemas import (
    BoundingBox,
    Detection,
    SegmentationMask,
    DepthMap,
    PerceptionResult,
    ObstacleRecord,
    NavigationOutput,
    Priority,
    Direction,
    SizeCategory,
)

# Memory optimization constants - ULTRA-LOW-LATENCY
MAX_DETECTIONS = 2  # Strict limit for speed
MAX_MASK_SIZE = (160, 120)  # Aggressive downscale for segmentation
DEPTH_DOWNSCALE = 4  # Aggressive downscale for depth
SKIP_SEGMENTATION_BELOW_MS = 50  # Skip segmentation if detection is fast
USE_NUMPY_MEMMAP = False  # Disable memmapped arrays
GC_AFTER_FRAME = True  # Force GC after each frame

# Type checking imports
if TYPE_CHECKING:
    from PIL import Image as PILImageType
else:
    PILImageType = Any

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

# Optional imports for ML models
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

logger = logging.getLogger("spatial-perception")

try:
    from shared.logging.logging_config import log_event as _log_event
except ImportError:
    def _log_event(*a, **kw): pass


# =============================================================================
# ABSTRACT BASE CLASSES (spatial-specific names wrapping shared ABCs)
# =============================================================================

class BaseDetector(ABC):
    """Abstract base class for object detectors."""

    @abstractmethod
    async def detect(self, image: Any) -> List[Detection]:
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass


class BaseSegmenter(ABC):
    """Abstract base class for segmentation."""

    @abstractmethod
    async def segment(self, image: Any, detections: List[Detection]) -> List[SegmentationMask]:
        pass


class BaseDepthEstimator(ABC):
    """Abstract base class for depth estimation."""

    @abstractmethod
    async def estimate_depth(self, image: Any) -> DepthMap:
        pass


# =============================================================================
# OBJECT DETECTOR IMPLEMENTATIONS
# =============================================================================

class MockObjectDetector(BaseDetector):
    """
    Fast mock object detector for testing and fallback.
    ULTRA-OPTIMIZED: Zero-copy, pre-allocated, minimal latency.
    """
    
    __slots__ = ('_ready', '_classes')
    
    def __init__(self):
        self._ready = True
        self._classes = ("person", "chair", "table", "door", "wall")  # Tuple for speed
    
    def is_ready(self) -> bool:
        return self._ready
    
    async def detect(self, image: Any) -> List[Detection]:
        """ULTRA-FAST mock detection — always fresh, never cached."""
        width, height = image.size
        
        # Pre-calculate positions (deterministic for consistency)
        hw, hh = width // 2, height // 2
        detections = [
            Detection(
                id="obj_1",
                class_name=self._classes[0],
                confidence=0.85,
                bbox=BoundingBox(hw - 50, hh - 50, hw + 50, hh + 50)
            )
        ]
        
        return detections


class YOLODetector(BaseDetector):
    """
    YOLO-based object detector using ONNX Runtime or PyTorch.
    Supports YOLOv8, YOLOv7-tiny for optimized inference.
    """
    
    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = 0.5):
        self._model_path = model_path
        self._conf_threshold = conf_threshold
        self._model = None
        self._ready = False
        self._class_names = self._get_coco_classes()
        
        if model_path:
            self._load_model()
    
    def _get_coco_classes(self) -> List[str]:
        """COCO class names"""
        return [
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
    
    def _load_model(self):
        """Load YOLO model"""
        try:
            if ONNX_AVAILABLE and self._model_path and self._model_path.endswith('.onnx'):
                self._model = ort.InferenceSession(self._model_path)
                self._ready = True
                logger.info(f"Loaded ONNX YOLO model: {self._model_path}")
            elif TORCH_AVAILABLE:
                # Try loading with ultralytics
                try:
                    from ultralytics import YOLO
                    self._model = YOLO(self._model_path or "yolov8n.pt")
                    self._ready = True
                    logger.info("Loaded YOLO model with ultralytics")
                except ImportError:
                    logger.warning("ultralytics not available, using mock detector")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self._ready = False
    
    def is_ready(self) -> bool:
        return self._ready
    
    async def detect(self, image: Any) -> List[Detection]:
        """Run YOLO detection (ONNX or ultralytics)."""
        if not self._ready:
            return []
        
        try:
            # Convert to numpy
            img_np = np.array(image)
            if len(img_np.shape) == 2:
                if CV2_AVAILABLE:
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
                else:
                    img_np = np.stack([img_np]*3, axis=-1)
            elif img_np.shape[2] == 4:
                img_np = img_np[:, :, :3]
            
            detections = []
            
            if ONNX_AVAILABLE and isinstance(self._model, ort.InferenceSession):
                # ── ONNX YOLOv8 inference ──────────────────────────────
                detections = await asyncio.get_event_loop().run_in_executor(
                    None, self._onnx_detect, img_np
                )
            elif hasattr(self._model, 'predict'):
                # Ultralytics YOLO
                results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.predict(img_np, conf=self._conf_threshold, verbose=False)
                )
                
                for r in results:
                    boxes = r.boxes
                    for i, box in enumerate(boxes):
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        cls_name = self._class_names[cls_id] if cls_id < len(self._class_names) else "object"
                        
                        detections.append(Detection(
                            id=f"obj_{i+1}",
                            class_name=cls_name,
                            confidence=conf,
                            bbox=BoundingBox(x1, y1, x2, y2)
                        ))
            
            return detections[:MAX_DETECTIONS * 5]  # generous but bounded
            
        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            return []

    # ── ONNX YOLOv8 pre/post processing ──────────────────────────────────

    def _onnx_detect(self, img_np: np.ndarray) -> List[Detection]:
        """Synchronous ONNX YOLOv8 inference with NMS.

        YOLOv8 ONNX output shape: (1, 84, 8400) where 84 = 4 bbox + 80 classes.
        """
        h0, w0 = img_np.shape[:2]
        input_size = 640

        # Letterbox resize
        scale = min(input_size / w0, input_size / h0)
        nw, nh = int(w0 * scale), int(h0 * scale)
        pad_w, pad_h = (input_size - nw) // 2, (input_size - nh) // 2

        if CV2_AVAILABLE:
            resized = cv2.resize(img_np, (nw, nh), interpolation=cv2.INTER_LINEAR)
        else:
            from PIL import Image as _PIL
            resized = np.array(_PIL.fromarray(img_np).resize((nw, nh)))

        padded = np.full((input_size, input_size, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h+nh, pad_w:pad_w+nw] = resized

        # HWC→NCHW, normalize 0-1, float32
        blob = padded.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]

        # Infer
        input_name = self._model.get_inputs()[0].name
        raw = self._model.run(None, {input_name: blob})[0]  # (1, 84, 8400)

        # Transpose → (8400, 84)
        preds = raw[0].T  # (8400, 84)

        # Parse: first 4 cols = cx, cy, w, h; remaining 80 = class scores
        cx   = preds[:, 0]
        cy   = preds[:, 1]
        pw   = preds[:, 2]
        ph   = preds[:, 3]
        scores = preds[:, 4:]

        class_ids = np.argmax(scores, axis=1)
        confidences = scores[np.arange(len(scores)), class_ids]

        # Confidence filter
        mask = confidences >= self._conf_threshold
        if not mask.any():
            return []

        cx, cy, pw, ph = cx[mask], cy[mask], pw[mask], ph[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        # Convert cx,cy,w,h → x1,y1,x2,y2 in input_size coordinates
        x1 = cx - pw / 2
        y1 = cy - ph / 2
        x2 = cx + pw / 2
        y2 = cy + ph / 2

        # Simple NMS (greedy, IoU > 0.45)
        order = np.argsort(-confidences)
        keep = []
        suppressed = set()
        for idx in order:
            if idx in suppressed:
                continue
            keep.append(idx)
            for jdx in order:
                if jdx in suppressed or jdx == idx:
                    continue
                iou = self._iou(x1[idx], y1[idx], x2[idx], y2[idx],
                                x1[jdx], y1[jdx], x2[jdx], y2[jdx])
                if iou > 0.45:
                    suppressed.add(jdx)
            if len(keep) >= 25:
                break

        # Re-scale to original image
        detections = []
        for i, k in enumerate(keep):
            bx1 = int((x1[k] - pad_w) / scale)
            by1 = int((y1[k] - pad_h) / scale)
            bx2 = int((x2[k] - pad_w) / scale)
            by2 = int((y2[k] - pad_h) / scale)
            bx1, by1 = max(0, bx1), max(0, by1)
            bx2, by2 = min(w0, bx2), min(h0, by2)
            cid = int(class_ids[k])
            cls_name = self._class_names[cid] if cid < len(self._class_names) else "object"
            detections.append(Detection(
                id=f"obj_{i+1}",
                class_name=cls_name,
                confidence=float(confidences[k]),
                bbox=BoundingBox(bx1, by1, bx2, by2),
            ))
        return detections

    @staticmethod
    def _iou(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2) -> float:
        ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        return inter / (area_a + area_b - inter + 1e-6)


# =============================================================================
# EDGE-AWARE SEGMENTATION
# =============================================================================

class EdgeAwareSegmenter(BaseSegmenter):
    """
    ULTRA-FAST edge-aware segmentation.
    Skip heavy processing, use confidence estimation only.
    """
    
    __slots__ = ('_ready', '_cached_masks', '_gray_buffer')
    
    def __init__(self):
        self._ready = cv2 is not None
        self._cached_masks: List[SegmentationMask] = []
        self._gray_buffer: Optional[np.ndarray] = None
    
    async def segment(self, image: Any, detections: List[Detection]) -> List[SegmentationMask]:
        """ULTRA-FAST segmentation - minimal processing."""
        if not self._ready or not detections:
            return []
        
        try:
            # FAST PATH: Return cached if available
            if len(detections) <= len(self._cached_masks):
                for i, det in enumerate(detections[:MAX_DETECTIONS]):
                    self._cached_masks[i] = SegmentationMask(
                        detection_id=det.id,
                        mask=None,
                        boundary_confidence=0.75,  # Default confidence
                        edge_pixels=None
                    )
                return self._cached_masks[:len(detections)]
            
            # Aggressive downscale - use PIL resize (faster than cv2 for small sizes)
            small_img = image.resize(MAX_MASK_SIZE, PILImage.Resampling.NEAREST)
            img_np = np.asarray(small_img, dtype=np.uint8)
            
            if len(img_np.shape) == 3:
                # Fast grayscale conversion
                gray = np.mean(img_np, axis=2, dtype=np.uint8)
            else:
                gray = img_np
            
            scale_x = MAX_MASK_SIZE[0] / image.size[0]
            scale_y = MAX_MASK_SIZE[1] / image.size[1]
            
            masks = []
            for det in detections[:MAX_DETECTIONS]:
                bbox = det.bbox
                x1, y1 = int(bbox.x1 * scale_x), int(bbox.y1 * scale_y)
                x2, y2 = int(bbox.x2 * scale_x), int(bbox.y2 * scale_y)
                
                # Bounds check
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(MAX_MASK_SIZE[0], x2), min(MAX_MASK_SIZE[1], y2)
                
                if x2 <= x1 or y2 <= y1:
                    boundary_conf = 0.5
                else:
                    # Simple variance-based confidence (faster than Canny)
                    roi = gray[y1:y2, x1:x2]
                    variance = np.var(roi) if roi.size > 0 else 0
                    boundary_conf = min(0.5 + variance / 5000.0, 0.95)
                
                masks.append(SegmentationMask(
                    detection_id=det.id,
                    mask=None,
                    boundary_confidence=boundary_conf,
                    edge_pixels=None
                ))
            
            self._cached_masks = masks
            return masks
            
        except Exception as e:
            logger.error(f"Segmentation error: {e}")
            return []


# =============================================================================
# DEPTH ESTIMATION
# =============================================================================

class SimpleDepthEstimator(BaseDepthEstimator):
    """
    ULTRA-FAST depth estimation using pre-allocated arrays.
    Zero-copy where possible.
    """
    
    __slots__ = ('_ready', '_min_depth', '_max_depth', '_cached_depth', '_cached_dims')
    
    def __init__(self, default_depth_range: Tuple[float, float] = (0.5, 10.0)):
        self._ready = True
        self._min_depth = default_depth_range[0]
        self._max_depth = default_depth_range[1]
        self._cached_depth: Optional[np.ndarray] = None
        self._cached_dims: Tuple[int, int] = (0, 0)
    
    async def estimate_depth(self, image: Any) -> DepthMap:
        """ULTRA-FAST depth estimation with caching."""
        try:
            orig_width, orig_height = image.size
            height = orig_height // DEPTH_DOWNSCALE
            width = orig_width // DEPTH_DOWNSCALE
            
            # Reuse cached depth array if dimensions match
            if (height, width) == self._cached_dims and self._cached_depth is not None:
                return DepthMap(
                    depth_array=self._cached_depth,
                    min_depth=self._min_depth,
                    max_depth=self._max_depth,
                    is_metric=False
                )
            
            # Pre-allocate and fill in-place
            depth = np.empty((height, width), dtype=np.float32)
            depth_range = self._max_depth - self._min_depth
            
            # Vectorized fill - single operation
            row_depths = np.linspace(self._max_depth, self._min_depth, height, dtype=np.float32)
            depth[:] = row_depths[:, np.newaxis]
            
            self._cached_depth = depth
            self._cached_dims = (height, width)
            
            return DepthMap(
                depth_array=depth,
                min_depth=self._min_depth,
                max_depth=self._max_depth,
                is_metric=False
            )
            
        except Exception as e:
            logger.error(f"Depth estimation error: {e}")
            return DepthMap(
                depth_array=np.full((30, 40), 5.0, dtype=np.float32),
                min_depth=5.0,
                max_depth=5.0,
                is_metric=False
            )


class MiDaSDepthEstimator(BaseDepthEstimator):
    """
    MiDaS-based depth estimation using ONNX or PyTorch.
    Provides more accurate monocular depth estimation.
    """
    
    def __init__(self, model_path: Optional[str] = None, model_type: str = "MiDaS_small"):
        self._model_path = model_path
        self._model_type = model_type
        self._model = None
        self._transform = None
        self._ready = False
        
        if TORCH_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load MiDaS model (ONNX preferred for speed, PyTorch fallback)."""
        try:
            if self._model_path and ONNX_AVAILABLE and self._model_path.endswith('.onnx'):
                import os as _os
                if _os.path.isfile(self._model_path):
                    self._model = ort.InferenceSession(self._model_path)
                    self._ready = True
                    logger.info("Loaded ONNX MiDaS model: %s", self._model_path)
                else:
                    logger.warning("MiDaS model file not found: %s", self._model_path)
            elif TORCH_AVAILABLE:
                # Try loading from torch hub
                try:
                    self._model = torch.hub.load("intel-isl/MiDaS", self._model_type)
                    self._model.eval()
                    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
                    self._transform = midas_transforms.small_transform
                    self._ready = True
                    logger.info(f"Loaded MiDaS model: {self._model_type}")
                except Exception as e:
                    logger.warning(f"Could not load MiDaS from hub: {e}")
        except Exception as e:
            logger.error(f"Failed to load MiDaS model: {e}")
    
    async def estimate_depth(self, image: Any) -> DepthMap:
        """Estimate depth using MiDaS (ONNX or PyTorch)."""
        if not self._ready:
            # Fallback to simple estimator
            simple = SimpleDepthEstimator()
            return await simple.estimate_depth(image)
        
        try:
            img_np = np.array(image)

            if ONNX_AVAILABLE and isinstance(self._model, ort.InferenceSession):
                # ── ONNX MiDaS inference ──────────────────────────────
                depth = await asyncio.get_event_loop().run_in_executor(
                    None, self._onnx_depth, img_np
                )
            elif self._transform:
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
            else:
                depth = np.zeros(img_np.shape[:2], dtype=np.float32)
            
            # Normalize to metric range (approximate)
            depth_min = np.min(depth)
            depth_max = np.max(depth)
            depth_normalized = (depth - depth_min) / (depth_max - depth_min + 1e-6)
            depth_metric = 0.5 + depth_normalized * 9.5  # 0.5m to 10m range
            
            return DepthMap(
                depth_array=depth_metric.astype(np.float32),
                min_depth=float(np.min(depth_metric)),
                max_depth=float(np.max(depth_metric)),
                is_metric=False  # Approximate, not calibrated
            )
            
        except Exception as e:
            logger.error(f"MiDaS depth estimation error: {e}")
            simple = SimpleDepthEstimator()
            return await simple.estimate_depth(image)

    def _onnx_depth(self, img_np: np.ndarray) -> np.ndarray:
        """Synchronous ONNX MiDaS inference.

        MiDaS small expects (1, 3, 256, 256) float32 normalised input.
        Output: (1, 256, 256) inverse-depth map.
        """
        h0, w0 = img_np.shape[:2]
        input_size = 256

        # Resize
        if CV2_AVAILABLE:
            resized = cv2.resize(img_np, (input_size, input_size), interpolation=cv2.INTER_CUBIC)
        else:
            from PIL import Image as _PIL
            resized = np.array(_PIL.fromarray(img_np).resize((input_size, input_size)))

        # Normalize (ImageNet stats)
        blob = resized.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        blob = (blob - mean) / std
        blob = blob.transpose(2, 0, 1)[np.newaxis, ...]  # NCHW

        # Infer
        input_name = self._model.get_inputs()[0].name
        raw = self._model.run(None, {input_name: blob})[0]  # (1, 256, 256)
        depth_small = raw.squeeze()

        # Resize back to original dimensions
        if CV2_AVAILABLE:
            depth = cv2.resize(depth_small, (w0, h0), interpolation=cv2.INTER_LINEAR)
        else:
            from PIL import Image as _PIL
            depth = np.array(_PIL.fromarray(depth_small).resize((w0, h0)))

        return depth


# =============================================================================
# SPATIAL FUSION
# =============================================================================

class SpatialFuser:
    """
    Fuses detection, segmentation, and depth data into unified obstacle records.
    Computes distance, direction, size, and priority for each obstacle.
    """
    
    # Priority thresholds in meters
    CRITICAL_THRESHOLD = 1.0
    NEAR_THRESHOLD = 2.0
    FAR_THRESHOLD = 5.0
    
    # FOV assumption for direction calculation (degrees)
    HORIZONTAL_FOV = 70.0
    
    def __init__(self, image_width: int = 640, image_height: int = 480):
        self._img_width = image_width
        self._img_height = image_height
    
    def _calculate_direction(self, center_x: int) -> Tuple[Direction, float]:
        """Calculate direction and angle from image center"""
        # Normalize x position to -1 to 1
        normalized_x = (center_x - self._img_width / 2) / (self._img_width / 2)
        
        # Calculate angle in degrees
        angle = normalized_x * (self.HORIZONTAL_FOV / 2)
        
        # Determine direction category
        if angle < -25:
            direction = Direction.FAR_LEFT
        elif angle < -15:
            direction = Direction.LEFT
        elif angle < -5:
            direction = Direction.SLIGHTLY_LEFT
        elif angle < 5:
            direction = Direction.CENTER
        elif angle < 15:
            direction = Direction.SLIGHTLY_RIGHT
        elif angle < 25:
            direction = Direction.RIGHT
        else:
            direction = Direction.FAR_RIGHT
        
        return direction, angle
    
    def _calculate_priority(self, distance: float) -> Priority:
        """Determine priority based on distance"""
        if distance < self.CRITICAL_THRESHOLD:
            return Priority.CRITICAL
        elif distance < self.NEAR_THRESHOLD:
            return Priority.NEAR_HAZARD
        elif distance < self.FAR_THRESHOLD:
            return Priority.FAR_HAZARD
        else:
            return Priority.SAFE
    
    def _calculate_size_category(self, bbox: BoundingBox) -> str:
        """Categorize object size"""
        area_ratio = bbox.area / (self._img_width * self._img_height)
        if area_ratio > 0.25:
            return "large"
        elif area_ratio > 0.05:
            return "medium"
        else:
            return "small"
    
    def _generate_action(self, direction: Direction, distance: float, priority: Priority) -> str:
        """Generate recommended action"""
        if priority == Priority.SAFE:
            return "clear path"
        
        if priority == Priority.CRITICAL:
            prefix = "stop immediately, "
        elif priority == Priority.NEAR_HAZARD:
            prefix = ""
        else:
            prefix = "be aware, "
        
        if direction in [Direction.FAR_LEFT, Direction.LEFT, Direction.SLIGHTLY_LEFT]:
            action = f"{prefix}step right"
        elif direction in [Direction.FAR_RIGHT, Direction.RIGHT, Direction.SLIGHTLY_RIGHT]:
            action = f"{prefix}step left"
        else:
            if priority == Priority.CRITICAL:
                action = "stop and reassess"
            else:
                action = "proceed with caution"
        
        return action
    
    def fuse(
        self,
        detections: List[Detection],
        masks: List[SegmentationMask],
        depth_map: DepthMap
    ) -> List[ObstacleRecord]:
        """Fuse all spatial data into obstacle records"""
        
        # Create mask lookup
        mask_lookup = {m.detection_id: m for m in masks}
        
        obstacles = []
        
        for det in detections:
            bbox = det.bbox
            center_x, center_y = bbox.center
            
            # Get depth for this detection
            _, _, mean_depth = depth_map.get_region_depth(bbox)
            
            # If depth seems invalid, estimate from position
            # Note: get_region_depth returns (min, median, max) — we use max as proxy
            if mean_depth == float('inf') or mean_depth > 100:
                # Fallback: estimate from y-position
                mean_depth = 0.5 + (1 - center_y / self._img_height) * 9.5
            
            # Get mask confidence
            mask = mask_lookup.get(det.id)
            mask_conf = mask.boundary_confidence if mask else 0.5
            
            # Calculate direction
            direction, angle = self._calculate_direction(center_x)
            
            # Calculate priority
            priority = self._calculate_priority(mean_depth)
            
            # Calculate size
            size_cat = self._calculate_size_category(bbox)
            
            # Generate action
            action = self._generate_action(direction, mean_depth, priority)
            
            obstacles.append(ObstacleRecord(
                id=det.id,
                class_name=det.class_name,
                bbox=bbox,
                centroid_px=(center_x, center_y),
                distance_m=mean_depth,
                direction=direction,
                direction_deg=angle,
                mask_confidence=mask_conf,
                detection_confidence=det.confidence,
                priority=priority,
                size_category=size_cat,
                action_recommendation=action
            ))
        
        # Sort by priority (critical first) then by distance
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.NEAR_HAZARD: 1,
            Priority.FAR_HAZARD: 2,
            Priority.SAFE: 3
        }
        obstacles.sort(key=lambda o: (priority_order[o.priority], o.distance_m))
        
        return obstacles


# =============================================================================
# MICRO-NAVIGATION FORMATTER
# =============================================================================

class MicroNavFormatter:
    """
    Formats spatial obstacle data into navigation cues for TTS output.
    Generates short, medium, and verbose descriptions.
    """
    
    # LLM System Prompt for micro-navigation (can be used with Ollama)
    MICRO_NAV_SYSTEM_PROMPT = """You are a micro-navigation assistant for blind users.
Given spatial obstacle data, generate VERY concise spoken warnings.

FORMAT RULES:
- Maximum 10 words for critical/near obstacles
- Use meters for distance (round to 0.5m)
- Direction: "ahead", "left", "right", "slightly left", "slightly right"
- Priority words: "Stop!" for <1m, "Caution" for 1-2m, "Ahead" for 2-5m

EXAMPLES:
- "Stop! Chair half meter left."
- "Caution, table 1.5 meters right."
- "Person 3 meters ahead."

OUTPUT: Single spoken sentence only. No punctuation except period."""
    
    def format_short_cue(self, obstacles: List[ObstacleRecord]) -> str:
        """Generate short TTS-ready cue (max 15 words)"""
        if not obstacles:
            return "Path clear."
        
        # Focus on highest priority obstacle
        top = obstacles[0]
        
        # Distance formatting
        dist_rounded = round(top.distance_m * 2) / 2  # Round to 0.5
        if dist_rounded < 1:
            dist_str = f"half meter" if dist_rounded == 0.5 else f"{dist_rounded:.1f} meters"
        else:
            dist_str = f"{dist_rounded:.1g} meters" if dist_rounded != int(dist_rounded) else f"{int(dist_rounded)} meter{'s' if dist_rounded != 1 else ''}"
        
        # Priority prefix
        if top.priority == Priority.CRITICAL:
            prefix = "Stop!"
        elif top.priority == Priority.NEAR_HAZARD:
            prefix = "Caution,"
        else:
            prefix = ""
        
        # Direction formatting
        if top.direction == Direction.CENTER:
            dir_str = "ahead"
        else:
            dir_str = top.direction.value
        
        # Build cue
        cue = f"{prefix} {top.class_name.title()} {dist_str} {dir_str}"
        
        # Add action for critical
        if top.priority in [Priority.CRITICAL, Priority.NEAR_HAZARD]:
            cue += f" – {top.action_recommendation}"
        
        return cue.strip().replace("  ", " ")
    
    def format_verbose(self, obstacles: List[ObstacleRecord]) -> str:
        """Generate detailed verbal description"""
        if not obstacles:
            return "The path ahead appears clear with no obstacles detected."
        
        descriptions = []
        
        for obs in obstacles[:3]:  # Limit to top 3
            dist_str = f"{obs.distance_m:.1f} meters"
            
            desc = (
                f"A {obs.class_name} is detected {dist_str} {obs.direction.value} of center, "
                f"at approximately {abs(obs.direction_deg):.0f} degrees. "
            )
            
            if obs.priority == Priority.CRITICAL:
                desc += f"This is a critical hazard requiring immediate attention. "
            elif obs.priority == Priority.NEAR_HAZARD:
                desc += f"This is a near hazard. "
            
            desc += f"Recommended action: {obs.action_recommendation}."
            descriptions.append(desc)
        
        if len(obstacles) > 3:
            descriptions.append(f"Additionally, {len(obstacles) - 3} more objects detected further away.")
        
        return " ".join(descriptions)
    
    def format_telemetry(self, obstacles: List[ObstacleRecord]) -> List[Dict]:
        """Generate JSON telemetry for downstream processing"""
        return [obs.to_dict() for obs in obstacles]
    
    def format_all(self, obstacles: List[ObstacleRecord]) -> NavigationOutput:
        """Generate all output formats"""
        has_critical = any(o.priority == Priority.CRITICAL for o in obstacles)
        
        return NavigationOutput(
            short_cue=self.format_short_cue(obstacles),
            verbose_description=self.format_verbose(obstacles),
            telemetry=self.format_telemetry(obstacles),
            has_critical=has_critical
        )


# =============================================================================
# SPATIAL PROCESSOR (Main Pipeline)
# =============================================================================

class SpatialProcessor:
    """
    Main spatial perception processor that orchestrates the full pipeline:
    FRAME → DETECT → SEGMENT → DEPTH → FUSE → NAVIGATION
    """
    
    def __init__(
        self,
        detector: Optional[BaseDetector] = None,
        segmenter: Optional[BaseSegmenter] = None,
        depth_estimator: Optional[BaseDepthEstimator] = None,
        enable_segmentation: bool = True,
        enable_depth: bool = True
    ):
        # Initialize components
        self._detector = detector or MockObjectDetector()
        self._segmenter = segmenter or EdgeAwareSegmenter() if enable_segmentation else None
        self._depth_estimator = depth_estimator or SimpleDepthEstimator() if enable_depth else None
        self._fuser = SpatialFuser()
        self._formatter = MicroNavFormatter()
        
        # Configuration
        self._enable_segmentation = enable_segmentation
        self._enable_depth = enable_depth
        
        # State
        self._last_obstacles: List[ObstacleRecord] = []
        self._last_nav_output: Optional[NavigationOutput] = None
        self._processing = False
        
        logger.info("SpatialProcessor initialized")
    
    @property
    def is_ready(self) -> bool:
        """Check if processor is ready"""
        return self._detector.is_ready()
    
    @property
    def last_obstacles(self) -> List[ObstacleRecord]:
        """Get last processed obstacles"""
        return self._last_obstacles
    
    @property
    def last_navigation(self) -> Optional[NavigationOutput]:
        """Get last navigation output"""
        return self._last_nav_output
    
    async def process_frame(self, image: Any) -> NavigationOutput:
        """
        ULTRA-FAST spatial perception pipeline.
        Parallel execution, aggressive caching, minimal allocations.
        Target: <100ms total.
        """
        if self._processing:
            return self._last_nav_output or NavigationOutput(
                short_cue="Processing...",
                verbose_description="Still processing.",
                telemetry=[],
                has_critical=False
            )
        
        self._processing = True
        start_time = time.time()
        
        try:
            width, height = image.size
            
            # Reuse fuser if dimensions match
            if not hasattr(self, '_fuser_dims') or self._fuser_dims != (width, height):
                self._fuser = SpatialFuser(width, height)
                self._fuser_dims = (width, height)
            
            # Step 1: Object Detection (FAST)
            detections = await self._detector.detect(image)
            
            if not detections:
                self._last_obstacles = []
                self._last_nav_output = NavigationOutput(
                    short_cue="Path clear.",
                    verbose_description="No obstacles detected.",
                    telemetry=[],
                    has_critical=False
                )
                return self._last_nav_output
            
            # Steps 2-3: Run segmentation and depth in PARALLEL
            masks = []
            depth_map = None
            
            async def run_segmentation():
                nonlocal masks
                if self._segmenter and self._enable_segmentation:
                    masks = await self._segmenter.segment(image, detections)
            
            async def run_depth():
                nonlocal depth_map
                if self._depth_estimator and self._enable_depth:
                    depth_map = await self._depth_estimator.estimate_depth(image)
            
            # Execute in parallel
            await asyncio.gather(run_segmentation(), run_depth())
            
            # Fallback depth map
            if depth_map is None:
                depth_map = DepthMap(
                    depth_array=np.full((height // DEPTH_DOWNSCALE, width // DEPTH_DOWNSCALE), 3.0, dtype=np.float32),
                    min_depth=3.0,
                    max_depth=3.0,
                    is_metric=False
                )
            
            # Step 4: Fast Fusion
            obstacles = self._fuser.fuse(detections, masks, depth_map)
            
            # Step 5: Format Output
            nav_output = self._formatter.format_all(obstacles)
            
            # Store state
            self._last_obstacles = obstacles[:MAX_DETECTIONS]
            self._last_nav_output = nav_output
            
            total_time = (time.time() - start_time) * 1000

            _log_event(
                "spatial-perception", "spatial_frame_processed",
                component="spatial_processor",
                latency_ms=total_time,
                detections_count=len(detections),
                obstacles=len(obstacles),
                has_critical=nav_output.has_critical,
            )

            if total_time > 150:
                logger.warning(f"Spatial pipeline slow: {total_time:.0f}ms")
            
            return nav_output
            
        except Exception as e:
            logger.error(f"Spatial processing error: {e}")
            return NavigationOutput(
                short_cue="Processing error.",
                verbose_description=f"Error: {str(e)}",
                telemetry=[],
                has_critical=False
            )
        finally:
            self._processing = False
            if GC_AFTER_FRAME:
                gc.collect()
    
    async def get_quick_warning(self, image: Any) -> str:
        """
        Fast path for immediate hazard detection.
        Returns short TTS cue only, skipping verbose processing.
        """
        try:
            # Quick detection only
            detections = await self._detector.detect(image)
            
            if not detections:
                return "Path clear."
            
            # Quick depth estimate for closest object
            width, height = image.size
            
            # Find detection closest to bottom of frame (likely closest)
            closest = max(detections, key=lambda d: d.bbox.y2)
            
            # Estimate distance from y-position
            est_distance = 0.5 + (1 - closest.bbox.y2 / height) * 5.0
            
            # Quick direction
            center_x = closest.bbox.center[0]
            if center_x < width * 0.4:
                direction = "left"
            elif center_x > width * 0.6:
                direction = "right"
            else:
                direction = "ahead"
            
            # Format quick warning
            if est_distance < 1.0:
                return f"Stop! {closest.class_name.title()} very close {direction}."
            elif est_distance < 2.0:
                return f"Caution, {closest.class_name} {est_distance:.1f}m {direction}."
            else:
                return f"{closest.class_name.title()} {est_distance:.0f}m {direction}."
            
        except Exception as e:
            logger.error(f"Quick warning error: {e}")
            return "Unable to assess obstacles."


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_spatial_processor(
    use_yolo: bool = False,
    yolo_model_path: Optional[str] = None,
    use_midas: bool = False,
    midas_model_path: Optional[str] = None,
    enable_segmentation: bool = True,
    enable_depth: bool = True
) -> SpatialProcessor:
    """
    Factory function to create a configured SpatialProcessor.
    
    Args:
        use_yolo: Use YOLO detector instead of mock
        yolo_model_path: Path to YOLO ONNX model
        use_midas: Use MiDaS depth instead of simple heuristics
        midas_model_path: Path to MiDaS ONNX model
        enable_segmentation: Enable edge-aware segmentation
        enable_depth: Enable depth estimation
    
    Returns:
        Configured SpatialProcessor instance
    """
    # Select detector
    if use_yolo:
        detector = YOLODetector(model_path=yolo_model_path)
        if not detector.is_ready():
            logger.warning("YOLO not ready, falling back to mock detector")
            detector = MockObjectDetector()
    else:
        detector = MockObjectDetector()
    
    # Select depth estimator
    if use_midas:
        depth_estimator = MiDaSDepthEstimator(model_path=midas_model_path)
    else:
        depth_estimator = SimpleDepthEstimator()
    
    # Segmenter
    segmenter = EdgeAwareSegmenter() if enable_segmentation else None
    
    return SpatialProcessor(
        detector=detector,
        segmenter=segmenter,
        depth_estimator=depth_estimator,
        enable_segmentation=enable_segmentation,
        enable_depth=enable_depth
    )
