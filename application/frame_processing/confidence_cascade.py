"""
Confidence Cascade & Robustness Heuristics
============================================

Implements:
  1. Three-tier confidence filtering  (≥0.60 / 0.30–0.59 / <0.30)
  2. Secondary verifier for known confusion pairs
  3. Edge-density, aspect-ratio, small-crop, depth-range robustness heuristics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("confidence-cascade")

# ---------------------------------------------------------------------------
# Configuration (populated from config.yaml at runtime)
# ---------------------------------------------------------------------------

@dataclass
class CascadeConfig:
    detected_threshold: float = 0.60
    low_confidence_threshold: float = 0.30
    confusion_pair_penalty: float = 0.20
    small_crop_min_area: int = 1024
    small_crop_penalty: float = 0.15
    edge_density_min: float = 0.05
    edge_density_penalty: float = 0.10


def config_from_yaml(cfg: Dict[str, Any]) -> CascadeConfig:
    """Build CascadeConfig from parsed config.yaml dict."""
    conf = cfg.get("confidence", {})
    rob = cfg.get("robustness", {})
    return CascadeConfig(
        detected_threshold=conf.get("detected_threshold", 0.60),
        low_confidence_threshold=conf.get("low_confidence_threshold", 0.30),
        confusion_pair_penalty=conf.get("confusion_pair_penalty", 0.20),
        small_crop_min_area=rob.get("small_crop_min_area", 1024),
        small_crop_penalty=rob.get("small_crop_penalty", 0.15),
        edge_density_min=rob.get("edge_density_min", 0.05),
        edge_density_penalty=rob.get("edge_density_penalty", 0.10),
    )


# ---------------------------------------------------------------------------
# Known confusion pairs
# ---------------------------------------------------------------------------

CONFUSION_PAIRS: Dict[str, str] = {}

_RAW_PAIRS = [
    ("bottle", "smartphone"),
    ("cup", "bowl"),
    ("remote", "phone"),
    ("mouse", "remote"),
]
for a, b in _RAW_PAIRS:
    CONFUSION_PAIRS[a] = b
    CONFUSION_PAIRS[b] = a


def load_confusion_pairs_from_config(cfg: Dict[str, Any]) -> None:
    """Optionally extend confusion pairs from config.yaml."""
    pairs = cfg.get("confusion_pairs", [])
    for pair in pairs:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            CONFUSION_PAIRS[pair[0]] = pair[1]
            CONFUSION_PAIRS[pair[1]] = pair[0]


# ---------------------------------------------------------------------------
# Tier filtering
# ---------------------------------------------------------------------------

def filter_by_confidence(
    detections: List[Dict[str, Any]],
    config: Optional[CascadeConfig] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split detections into (reported, log_only) by confidence tier.

    - >= detected_threshold   → label as "detected"
    - low_confidence_threshold – detected  → "possible — low confidence"
    - < low_confidence_threshold → log only, never reported
    """
    if config is None:
        config = CascadeConfig()

    reported: List[Dict[str, Any]] = []
    log_only: List[Dict[str, Any]] = []

    for det in detections:
        conf = det.get("conf", det.get("confidence", 0.0))
        if conf >= config.detected_threshold:
            det["status"] = "detected"
            reported.append(det)
        elif conf >= config.low_confidence_threshold:
            det["status"] = "possible — low confidence"
            reported.append(det)
        else:
            det["status"] = "below_threshold"
            log_only.append(det)

    return reported, log_only


# ---------------------------------------------------------------------------
# Edge density computation
# ---------------------------------------------------------------------------

def compute_edge_density(crop: np.ndarray) -> float:
    """Compute Sobel edge density (fraction of strong-edge pixels)."""
    try:
        import cv2
    except ImportError:
        return 0.5  # neutral default

    if crop is None or crop.size == 0:
        return 0.0

    if len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop

    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)

    # Threshold at mean + 1 std
    threshold = magnitude.mean() + magnitude.std()
    edge_pixels = np.sum(magnitude > threshold)
    total_pixels = magnitude.size

    if total_pixels == 0:
        return 0.0
    return float(edge_pixels / total_pixels)


# ---------------------------------------------------------------------------
# Secondary verifier for confusion pairs
# ---------------------------------------------------------------------------

class SecondaryVerifier:
    """Check detections against known confusion pairs.

    Uses edge-density and aspect-ratio heuristics to verify whether a
    detection label is plausible for the crop.

    Returns updated detections and a list of conflict entries for ``meta``.
    """

    # Approximate expected aspect-ratio ranges for common objects
    EXPECTED_ASPECT_RATIOS: Dict[str, Tuple[float, float]] = {
        "bottle": (0.2, 0.6),       # tall, narrow
        "smartphone": (0.4, 0.7),   # tall, medium width
        "cup": (0.6, 1.2),          # roughly square-ish
        "bowl": (1.0, 2.5),         # wide, short
        "remote": (0.15, 0.45),     # tall, very narrow
        "phone": (0.4, 0.75),       # tall, medium
        "mouse": (0.6, 1.4),        # wide, low
    }

    def __init__(self, config: Optional[CascadeConfig] = None):
        self.config = config or CascadeConfig()

    def verify(
        self,
        detections: List[Dict[str, Any]],
        image: Optional[np.ndarray] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Run secondary verification on detections.

        Returns (updated_detections, conflicts).
        """
        conflicts: List[Dict[str, Any]] = []

        for det in detections:
            label = det.get("label", det.get("class_name", ""))
            if label not in CONFUSION_PAIRS:
                continue

            alt_label = CONFUSION_PAIRS[label]
            conf = det.get("conf", det.get("confidence", 0.0))
            bbox = det.get("bbox", [])

            # Aspect ratio check
            ar_mismatch = self._check_aspect_ratio(label, bbox)

            # Edge density check (if image available)
            edge_mismatch = False
            edge_density = 0.0
            if image is not None and len(bbox) == 4:
                crop = self._extract_crop(image, bbox)
                edge_density = compute_edge_density(crop)
                det["edge_density"] = edge_density
                edge_mismatch = edge_density < self.config.edge_density_min

            if ar_mismatch or edge_mismatch:
                penalty = self.config.confusion_pair_penalty
                new_conf = max(0.0, conf - penalty)
                conflict = {
                    "original_label": label,
                    "alternative": alt_label,
                    "original_conf": round(conf, 3),
                    "adjusted_conf": round(new_conf, 3),
                    "reason": [],
                }
                if ar_mismatch:
                    conflict["reason"].append("aspect_ratio_mismatch")
                if edge_mismatch:
                    conflict["reason"].append(f"low_edge_density ({edge_density:.3f})")

                det["conf"] = new_conf
                det["confidence"] = new_conf
                conflicts.append(conflict)
                logger.debug(
                    "Confusion pair (%s↔%s): conf %.2f → %.2f",
                    label, alt_label, conf, new_conf,
                )

        return detections, conflicts

    def _check_aspect_ratio(self, label: str, bbox: List[float]) -> bool:
        """Return True if aspect ratio is outside expected range for label."""
        if len(bbox) != 4:
            return False

        x1, y1, x2, y2 = bbox
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        if h == 0:
            return False

        ar = w / h
        expected = self.EXPECTED_ASPECT_RATIOS.get(label)
        if expected is None:
            return False

        lo, hi = expected
        return ar < lo or ar > hi

    @staticmethod
    def _extract_crop(image: np.ndarray, bbox: List[float]) -> np.ndarray:
        """Extract crop from image using bbox [x1, y1, x2, y2]."""
        h, w = image.shape[:2]
        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(w, int(bbox[2]))
        y2 = min(h, int(bbox[3]))
        return image[y1:y2, x1:x2]


# ---------------------------------------------------------------------------
# Robustness heuristics
# ---------------------------------------------------------------------------

def apply_robustness_heuristics(
    detections: List[Dict[str, Any]],
    image: Optional[np.ndarray] = None,
    depth_map: Any = None,
    config: Optional[CascadeConfig] = None,
) -> List[Dict[str, Any]]:
    """Apply aspect-ratio, edge-density, small-crop, and depth-range heuristics.

    Modifies detections in-place and returns them.
    """
    if config is None:
        config = CascadeConfig()

    for det in detections:
        conf = det.get("conf", det.get("confidence", 0.0))
        bbox = det.get("bbox", [])

        # --- Small crop penalty ---
        if len(bbox) == 4:
            w = abs(bbox[2] - bbox[0])
            h = abs(bbox[3] - bbox[1])
            area = w * h
            if area < config.small_crop_min_area and area > 0:
                conf = max(0.0, conf - config.small_crop_penalty)
                det["conf"] = conf
                det["confidence"] = conf
                logger.debug(
                    "Small crop penalty for %s (area=%.0f): conf → %.2f",
                    det.get("label", "?"), area, conf,
                )

        # --- Edge density penalty ---
        if image is not None and len(bbox) == 4:
            if "edge_density" not in det:
                crop = SecondaryVerifier._extract_crop(image, bbox)
                det["edge_density"] = compute_edge_density(crop)

            if det["edge_density"] < config.edge_density_min:
                conf = max(0.0, conf - config.edge_density_penalty)
                det["conf"] = conf
                det["confidence"] = conf

        # --- Depth range sanity (if depth map available) ---
        if depth_map is not None and len(bbox) == 4:
            _apply_depth_sanity(det, depth_map)

    return detections


def _apply_depth_sanity(det: Dict[str, Any], depth_map: Any) -> None:
    """Check if depth is unreasonably close/far for common objects."""
    distance = det.get("distance_m")
    if distance is None:
        return

    label = det.get("label", "")
    # Reasonable distance ranges (metres) per category
    reasonable_ranges = {
        "person": (0.3, 50.0),
        "car": (1.0, 100.0),
        "chair": (0.3, 15.0),
        "bottle": (0.1, 5.0),
        "cup": (0.1, 3.0),
    }

    rng = reasonable_ranges.get(label)
    if rng is None:
        return

    lo, hi = rng
    if distance < lo or distance > hi:
        conf = det.get("conf", det.get("confidence", 0.0))
        penalty = 0.15
        det["conf"] = max(0.0, conf - penalty)
        det["confidence"] = det["conf"]
        logger.debug(
            "Depth sanity: %s at %.1fm outside [%.1f, %.1f], conf → %.2f",
            label, distance, lo, hi, det["conf"],
        )
