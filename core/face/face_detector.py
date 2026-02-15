"""
Face Detector — Lightweight on-device face detection.

Supports MTCNN (default) and RetinaFace backends with graceful fallback
to OpenCV Haar cascades when deep-learning backends are unavailable.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("face-detector")

# ── Backend availability probes ────────────────────────────────────────

_MTCNN_AVAILABLE = False
_RETINA_AVAILABLE = False
_CV2_AVAILABLE = False

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    pass

try:
    from facenet_pytorch import MTCNN as _MTCNN  # type: ignore
    _MTCNN_AVAILABLE = True
except ImportError:
    pass

try:
    from retinaface import RetinaFace as _RetinaFace  # type: ignore
    _RETINA_AVAILABLE = True
except ImportError:
    pass


# ── Data Structures ────────────────────────────────────────────────────

@dataclass
class FaceDetectorConfig:
    """Configuration for face detection."""
    backend: str = "auto"  # "mtcnn", "retinaface", "haar", "auto"
    min_confidence: float = 0.7
    min_face_size: int = 40  # px
    max_faces: int = 10
    device: str = "cpu"  # "cpu" or "cuda"


@dataclass
class FaceDetection:
    """A single detected face."""
    face_id: str
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    landmarks: Optional[Dict[str, Tuple[float, float]]] = None
    embedding: Optional[np.ndarray] = None
    timestamp_ms: float = 0.0
    frame_id: str = ""

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2)

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict:
        return {
            "face_id": self.face_id,
            "bbox": list(self.bbox),
            "confidence": round(self.confidence, 3),
            "width": self.width,
            "height": self.height,
            "center": [round(c, 1) for c in self.center],
            "has_landmarks": self.landmarks is not None,
            "has_embedding": self.embedding is not None,
            "timestamp_ms": self.timestamp_ms,
            "frame_id": self.frame_id,
        }


# ── Face Detector ──────────────────────────────────────────────────────

class FaceDetector:
    """Lightweight on-device face detection with multiple backends.

    Usage::

        detector = FaceDetector()
        faces = detector.detect(image)
    """

    def __init__(self, config: Optional[FaceDetectorConfig] = None):
        self.config = config or FaceDetectorConfig()
        self._backend_name = "none"
        self._mtcnn = None
        self._haar_cascade = None
        self._init_backend()

    def _init_backend(self) -> None:
        backend = self.config.backend

        if backend in ("auto", "mtcnn") and _MTCNN_AVAILABLE:
            try:
                self._mtcnn = _MTCNN(
                    keep_all=True,
                    min_face_size=self.config.min_face_size,
                    device=self.config.device,
                )
                self._backend_name = "mtcnn"
                logger.info("Face detector: MTCNN backend initialized")
                return
            except Exception as exc:
                logger.warning("MTCNN init failed: %s", exc)

        if backend in ("auto", "retinaface") and _RETINA_AVAILABLE:
            self._backend_name = "retinaface"
            logger.info("Face detector: RetinaFace backend ready")
            return

        if _CV2_AVAILABLE:
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self._haar_cascade = cv2.CascadeClassifier(cascade_path)
                self._backend_name = "haar"
                logger.info("Face detector: OpenCV Haar cascade fallback")
                return
            except Exception as exc:
                logger.warning("Haar cascade init failed: %s", exc)

        # Mock backend for testing
        self._backend_name = "mock"
        logger.warning("Face detector: no backend available, using mock")

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def detect(self, image: Any, frame_id: str = "", timestamp_ms: float = 0.0) -> List[FaceDetection]:
        """Detect faces in an image (PIL Image or numpy array).

        Returns list of FaceDetection sorted by area (largest first).
        """
        if timestamp_ms == 0.0:
            timestamp_ms = time.time() * 1000

        try:
            if self._backend_name == "mtcnn":
                return self._detect_mtcnn(image, frame_id, timestamp_ms)
            elif self._backend_name == "retinaface":
                return self._detect_retinaface(image, frame_id, timestamp_ms)
            elif self._backend_name == "haar":
                return self._detect_haar(image, frame_id, timestamp_ms)
            else:
                return self._detect_mock(image, frame_id, timestamp_ms)
        except Exception as exc:
            logger.error("Face detection error (%s): %s", self._backend_name, exc)
            return []

    def _detect_mtcnn(self, image: Any, frame_id: str, ts: float) -> List[FaceDetection]:
        import torch
        boxes, probs, landmarks = self._mtcnn.detect(image, landmarks=True)
        if boxes is None:
            return []
        faces = []
        for i, (box, prob) in enumerate(zip(boxes, probs)):
            if prob < self.config.min_confidence:
                continue
            x1, y1, x2, y2 = [int(v) for v in box]
            lm = None
            if landmarks is not None and len(landmarks) > i:
                pts = landmarks[i]
                lm = {
                    "left_eye": (float(pts[0][0]), float(pts[0][1])),
                    "right_eye": (float(pts[1][0]), float(pts[1][1])),
                    "nose": (float(pts[2][0]), float(pts[2][1])),
                    "mouth_left": (float(pts[3][0]), float(pts[3][1])),
                    "mouth_right": (float(pts[4][0]), float(pts[4][1])),
                }
            faces.append(FaceDetection(
                face_id=f"face_{uuid.uuid4().hex[:8]}",
                bbox=(x1, y1, x2, y2),
                confidence=float(prob),
                landmarks=lm,
                timestamp_ms=ts,
                frame_id=frame_id,
            ))
        return sorted(faces, key=lambda f: f.area, reverse=True)[:self.config.max_faces]

    def _detect_retinaface(self, image: Any, frame_id: str, ts: float) -> List[FaceDetection]:
        if isinstance(image, np.ndarray):
            img_arr = image
        else:
            img_arr = np.array(image)
        resp = _RetinaFace.detect_faces(img_arr)
        if not isinstance(resp, dict):
            return []
        faces = []
        for key, val in resp.items():
            conf = val.get("score", 0.0)
            if conf < self.config.min_confidence:
                continue
            fa = val.get("facial_area", [0, 0, 0, 0])
            lm = {}
            for lm_name in ("left_eye", "right_eye", "nose", "mouth_left", "mouth_right"):
                pt = val.get("landmarks", {}).get(lm_name)
                if pt:
                    lm[lm_name] = (float(pt[0]), float(pt[1]))
            faces.append(FaceDetection(
                face_id=f"face_{uuid.uuid4().hex[:8]}",
                bbox=(int(fa[0]), int(fa[1]), int(fa[2]), int(fa[3])),
                confidence=float(conf),
                landmarks=lm if lm else None,
                timestamp_ms=ts,
                frame_id=frame_id,
            ))
        return sorted(faces, key=lambda f: f.area, reverse=True)[:self.config.max_faces]

    def _detect_haar(self, image: Any, frame_id: str, ts: float) -> List[FaceDetection]:
        if isinstance(image, np.ndarray):
            img = image
        else:
            img = np.array(image)
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        else:
            gray = img
        rects = self._haar_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(self.config.min_face_size, self.config.min_face_size),
        )
        faces = []
        for (x, y, w, h) in rects:
            faces.append(FaceDetection(
                face_id=f"face_{uuid.uuid4().hex[:8]}",
                bbox=(x, y, x + w, y + h),
                confidence=0.8,  # Haar doesn't provide confidence
                timestamp_ms=ts,
                frame_id=frame_id,
            ))
        return sorted(faces, key=lambda f: f.area, reverse=True)[:self.config.max_faces]

    def _detect_mock(self, image: Any, frame_id: str, ts: float) -> List[FaceDetection]:
        """Mock detector for testing — returns a synthetic face if image is large enough."""
        if isinstance(image, np.ndarray):
            h, w = image.shape[:2]
        elif hasattr(image, "size"):
            w, h = image.size
        else:
            return []
        if w < 100 or h < 100:
            return []
        cx, cy = w // 2, h // 3
        sz = min(w, h) // 4
        return [FaceDetection(
            face_id=f"face_{uuid.uuid4().hex[:8]}",
            bbox=(cx - sz, cy - sz, cx + sz, cy + sz),
            confidence=0.85,
            landmarks={
                "left_eye": (float(cx - sz // 3), float(cy - sz // 6)),
                "right_eye": (float(cx + sz // 3), float(cy - sz // 6)),
                "nose": (float(cx), float(cy + sz // 6)),
                "mouth_left": (float(cx - sz // 4), float(cy + sz // 3)),
                "mouth_right": (float(cx + sz // 4), float(cy + sz // 3)),
            },
            timestamp_ms=ts,
            frame_id=frame_id,
        )]

    def health(self) -> dict:
        return {
            "backend": self._backend_name,
            "available_backends": {
                "mtcnn": _MTCNN_AVAILABLE,
                "retinaface": _RETINA_AVAILABLE,
                "haar": _CV2_AVAILABLE,
            },
            "config": {
                "min_confidence": self.config.min_confidence,
                "max_faces": self.config.max_faces,
            },
        }
