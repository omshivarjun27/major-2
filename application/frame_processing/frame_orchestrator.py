"""
Frame Orchestrator
==================
Per-frame fusion engine: collects parallel worker results, validates
timestamps, builds canonical SceneGraph, triggers downstream modules.

Key invariant: all fused results belong to the SAME frame_id.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .live_frame_manager import TimestampedFrame

try:
    from shared.logging.logging_config import log_event as _log_event
except ImportError:
    def _log_event(*a, **kw): pass

# ── Perception Controller integrations ────────────────────────────────
try:
    from application.pipelines.perception_telemetry import (
        DetectionEntry,
        FrameLog,
        MetaEntry,
        QREntry,
        emit_frame_log,
        get_metrics,
        get_misclass_tracker,
    )
    _TELEMETRY_AVAILABLE = True
except ImportError:
    _TELEMETRY_AVAILABLE = False

try:
    from .confidence_cascade import (
        CascadeConfig,
        SecondaryVerifier,
        apply_robustness_heuristics,
        config_from_yaml,
        filter_by_confidence,
    )
    _CASCADE_AVAILABLE = True
except ImportError:
    _CASCADE_AVAILABLE = False

try:
    from shared.utils.startup_guards import get_startup_info
except ImportError:
    def get_startup_info(): return {}

logger = logging.getLogger("frame-orchestrator")


# ============================================================================
# Per-Frame Telemetry
# ============================================================================

@dataclass
class FrameTelemetry:
    """Structured telemetry for a single frame's processing pipeline."""
    frame_id: str
    frame_ts: float
    processing_start: float = 0.0
    processing_end: float = 0.0
    latencies_per_module: Dict[str, float] = field(default_factory=dict)
    scene_graph_id: Optional[str] = None
    modules_failed: List[str] = field(default_factory=list)
    modules_succeeded: List[str] = field(default_factory=list)

    @property
    def total_ms(self) -> float:
        if self.processing_end > 0 and self.processing_start > 0:
            return (self.processing_end - self.processing_start) * 1000
        return 0.0

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "frame_ts": self.frame_ts,
            "processing_start": self.processing_start,
            "processing_end": self.processing_end,
            "total_ms": round(self.total_ms, 1),
            "latencies_per_module": {k: round(v, 1) for k, v in self.latencies_per_module.items()},
            "scene_graph_id": self.scene_graph_id,
            "modules_failed": self.modules_failed,
            "modules_succeeded": self.modules_succeeded,
        }


# ============================================================================
# Fused Frame Result
# ============================================================================

@dataclass
class FusedFrameResult:
    """Canonical output for a single frame after all perception workers finish."""
    frame_id: str
    frame_timestamp_ms: float
    detections: List[Any] = field(default_factory=list)
    depth_map: Any = None
    segmentation_masks: List[Any] = field(default_factory=list)
    ocr_results: List[Any] = field(default_factory=list)
    qr_results: List[Any] = field(default_factory=list)
    face_results: List[Any] = field(default_factory=list)
    action_results: List[Any] = field(default_factory=list)
    scene_graph: Any = None
    scene_graph_hash: str = ""
    short_cue: str = ""
    navigation_output: Any = None
    telemetry: Optional[FrameTelemetry] = None

    def is_fresh(self, max_age_ms: float = 500.0) -> bool:
        """Check if this result is still within the freshness window."""
        age = (time.time() * 1000) - self.frame_timestamp_ms
        return age <= max_age_ms

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "frame_timestamp_ms": self.frame_timestamp_ms,
            "age_ms": round((time.time() * 1000) - self.frame_timestamp_ms, 1),
            "num_detections": len(self.detections),
            "has_depth": self.depth_map is not None,
            "num_masks": len(self.segmentation_masks),
            "num_ocr": len(self.ocr_results),
            "num_qr": len(self.qr_results),
            "num_faces": len(self.face_results),
            "num_actions": len(self.action_results),
            "qr_results": [
                r.to_dict() if hasattr(r, "to_dict") else {"raw_data": str(r)}
                for r in self.qr_results
            ] if self.qr_results else [],
            "has_scene_graph": self.scene_graph is not None,
            "scene_graph_hash": self.scene_graph_hash,
            "short_cue": self.short_cue,
            "telemetry": self.telemetry.to_dict() if self.telemetry else None,
        }


# ============================================================================
# Orchestrator Config
# ============================================================================

@dataclass
class FrameOrchestratorConfig:
    """Configuration for the frame orchestrator."""
    live_frame_max_age_ms: float = 500.0
    hot_path_timeout_ms: float = 500.0
    pipeline_timeout_ms: float = 300.0
    enable_ocr: bool = False
    enable_qr: bool = True
    enable_depth: bool = True
    enable_segmentation: bool = False
    enable_face: bool = True
    enable_action: bool = True
    max_telemetry_history: int = 100


# ============================================================================
# Frame Orchestrator
# ============================================================================

class FrameOrchestrator:
    """Collects per-frame results, validates frame_id consistency,
    fuses into canonical SceneGraph, triggers downstream modules.

    Usage::

        orch = FrameOrchestrator(config, scene_builder, nav_formatter)
        result = await orch.process_frame(timestamped_frame,
            detector=det_fn, depth_estimator=depth_fn, ...)
    """

    def __init__(
        self,
        config: Optional[FrameOrchestratorConfig] = None,
        scene_graph_builder: Any = None,
        nav_formatter: Any = None,
        priority_analyzer: Any = None,
    ):
        self.config = config or FrameOrchestratorConfig()
        self._scene_builder = scene_graph_builder
        self._nav_formatter = nav_formatter
        self._priority_analyzer = priority_analyzer
        self._telemetry_history: List[FrameTelemetry] = []
        self._result_callbacks: List[Callable] = []

        # Counters
        self.total_frames: int = 0
        self.stale_aborts: int = 0
        self.timeout_count: int = 0
        self.success_count: int = 0

    def on_result(self, callback: Callable) -> None:
        """Register callback for each fused result."""
        self._result_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def process_frame(
        self,
        frame: TimestampedFrame,
        detector: Optional[Callable] = None,
        depth_estimator: Optional[Callable] = None,
        segmenter: Optional[Callable] = None,
        ocr_fn: Optional[Callable] = None,
        qr_fn: Optional[Callable] = None,
        face_fn: Optional[Callable] = None,
        action_fn: Optional[Callable] = None,
    ) -> FusedFrameResult:
        """Run all perception workers concurrently for a single frame.

        All results are validated to belong to the same frame_id.
        Returns FusedFrameResult — never raises.
        """
        self.total_frames += 1
        telemetry = FrameTelemetry(
            frame_id=frame.frame_id,
            frame_ts=frame.timestamp_epoch_ms,
            processing_start=time.time(),
        )

        result = FusedFrameResult(
            frame_id=frame.frame_id,
            frame_timestamp_ms=frame.timestamp_epoch_ms,
            telemetry=telemetry,
        )

        # ── Freshness gate ────────────────────────────────────────────
        if not frame.is_fresh(self.config.live_frame_max_age_ms):
            self.stale_aborts += 1
            result.short_cue = "I can't see clearly right now — please hold the camera steady."
            telemetry.modules_failed.append("freshness_gate")
            telemetry.processing_end = time.time()
            return result

        image = frame.image

        # ── Launch parallel workers ───────────────────────────────────
        tasks: Dict[str, asyncio.Task] = {}

        if detector:
            tasks["detection"] = asyncio.create_task(
                self._timed_call("detection", detector, image, telemetry)
            )
        if depth_estimator and self.config.enable_depth:
            tasks["depth"] = asyncio.create_task(
                self._timed_call("depth", depth_estimator, image, telemetry)
            )
        if segmenter and self.config.enable_segmentation:
            tasks["segmentation"] = asyncio.create_task(
                self._timed_call("segmentation", segmenter, image, telemetry)
            )
        if ocr_fn and self.config.enable_ocr:
            tasks["ocr"] = asyncio.create_task(
                self._timed_call("ocr", ocr_fn, image, telemetry)
            )
        if qr_fn and self.config.enable_qr:
            tasks["qr"] = asyncio.create_task(
                self._timed_call("qr", qr_fn, image, telemetry)
            )
        if face_fn and self.config.enable_face:
            tasks["face"] = asyncio.create_task(
                self._timed_call("face", face_fn, image, telemetry)
            )
        if action_fn and self.config.enable_action:
            tasks["action"] = asyncio.create_task(
                self._timed_call("action", action_fn, image, telemetry)
            )

        # Wait with global timeout
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks.values(), return_exceptions=True),
                    timeout=self.config.pipeline_timeout_ms / 1000.0,
                )
            except asyncio.TimeoutError:
                self.timeout_count += 1
                telemetry.modules_failed.append("global_timeout")
                logger.warning("Frame %s: pipeline timeout (%.0fms)",
                               frame.frame_id, self.config.pipeline_timeout_ms)

        # ── Collect results ───────────────────────────────────────────
        for module_name, task in tasks.items():
            if task.done() and not task.cancelled():
                exc = task.exception()
                if exc:
                    telemetry.modules_failed.append(module_name)
                else:
                    module_result = task.result()
                    self._assign_result(result, module_name, module_result)
                    telemetry.modules_succeeded.append(module_name)
            else:
                telemetry.modules_failed.append(module_name)

        # ── Build SceneGraph ──────────────────────────────────────────
        if self._scene_builder and result.detections:
            try:
                import numpy as np

                from shared.schemas import DepthMap, PerceptionResult

                depth = result.depth_map
                if depth is None:
                    depth = DepthMap(
                        depth_array=np.full((frame.height // 4 or 120, frame.width // 4 or 160), 5.0, dtype=np.float32),
                        min_depth=5.0, max_depth=5.0, is_metric=False,
                    )

                perception = PerceptionResult(
                    detections=result.detections,
                    masks=result.segmentation_masks,
                    depth_map=depth,
                    image_size=(frame.width, frame.height),
                    latency_ms=telemetry.total_ms,
                    timestamp=str(frame.timestamp_epoch_ms),
                )

                sg = self._scene_builder.build(perception)
                sg.frame_id = frame.frame_id
                sg.timestamp_epoch_ms = frame.timestamp_epoch_ms
                result.scene_graph = sg
                result.scene_graph_hash = self._hash_scene_graph(sg)
                telemetry.scene_graph_id = result.scene_graph_hash

                # Generate short_cue via nav formatter or scene summary
                if self._nav_formatter and hasattr(sg, "obstacles"):
                    result.short_cue = sg.summary or "Scene analyzed."
                    result.navigation_output = sg
                elif sg.summary:
                    result.short_cue = sg.summary

            except Exception as exc:
                logger.error("SceneGraph build failed for frame %s: %s", frame.frame_id, exc)
                telemetry.modules_failed.append("scene_graph")

        # ── Finalize ──────────────────────────────────────────────────
        telemetry.processing_end = time.time()
        self.success_count += 1

        # ── Confidence cascade & robustness heuristics ────────────────
        meta_conflicts: list = []
        meta_alerts: list = []
        degraded_latency = False

        if _CASCADE_AVAILABLE and result.detections:
            try:
                # Convert image to numpy for cascade heuristics (edge-density, crops)
                np_image = self._to_numpy(image)

                # Normalise detections to dicts for cascade processing
                det_dicts = []
                for d in result.detections:
                    if hasattr(d, 'to_dict'):
                        dd = d.to_dict()
                    elif isinstance(d, dict):
                        dd = d
                    else:
                        dd = {'label': str(d), 'conf': 0.5, 'bbox': []}
                    det_dicts.append(dd)

                # Apply heuristics (np_image may be None — heuristics skip image checks gracefully)
                det_dicts = apply_robustness_heuristics(
                    det_dicts, np_image, result.depth_map,
                )
                # Secondary verifier for confusion pairs
                verifier = SecondaryVerifier()
                det_dicts, meta_conflicts = verifier.verify(det_dicts, np_image)

                # 3-tier confidence filter
                reported, log_only = filter_by_confidence(det_dicts)
                result.detections = reported

                # Log-only detections are silently dropped from result
                if log_only:
                    logger.debug("Dropped %d below-threshold detections", len(log_only))
            except Exception as exc:
                logger.warning("Confidence cascade error: %s", exc)

        # ── Degraded latency check ────────────────────────────────────
        if telemetry.total_ms > 250:
            degraded_latency = True
            logger.info(
                "Frame %s: latency %.0fms > 250ms budget → degraded mode",
                frame.frame_id, telemetry.total_ms,
            )

        # ── Misclassification tracking ────────────────────────────────
        if _TELEMETRY_AVAILABLE and meta_conflicts:
            tracker = get_misclass_tracker()
            for conflict in meta_conflicts:
                alert = tracker.record(
                    conflict.get("original_label", "unknown"),
                    frame.frame_id,
                )
                if alert:
                    meta_alerts.append(alert)

        # ── Emit per-frame JSON telemetry ─────────────────────────────
        if _TELEMETRY_AVAILABLE:
            try:
                sinfo = get_startup_info()
                det_entries = []
                for d in (result.detections or []):
                    if isinstance(d, dict):
                        det_entries.append(DetectionEntry(
                            label=d.get('label', d.get('class_name', '')),
                            conf=d.get('conf', d.get('confidence', 0.0)),
                            bbox=d.get('bbox', []),
                            edge_density=d.get('edge_density', 0.0),
                            distance_m=d.get('distance_m'),
                        ))

                qr_entry = QREntry()
                if result.qr_results:
                    qr0 = result.qr_results[0]
                    if hasattr(qr0, 'to_dict'):
                        qd = qr0.to_dict()
                    elif isinstance(qr0, dict):
                        qd = qr0
                    else:
                        qd = {}
                    qr_entry = QREntry(
                        found=True,
                        decoded=qd.get('decoded', qd.get('data')),
                        method=qd.get('method'),
                        confidence=qd.get('confidence'),
                    )

                frame_log = FrameLog(
                    frame_id=frame.frame_id,
                    device=sinfo.get('device', 'cpu'),
                    venv=sinfo.get('venv', True),
                    num_dets=len(result.detections or []),
                    detections=det_entries,
                    qr=qr_entry,
                    errors=[],
                    meta=MetaEntry(
                        conflicts=meta_conflicts,
                        alerts=meta_alerts,
                        degraded_latency=degraded_latency,
                    ),
                )
                emit_frame_log(frame_log)

                # Update metrics accumulator
                metrics = get_metrics()
                metrics.record_frame(telemetry.total_ms, degraded=degraded_latency)
            except Exception as exc:
                logger.warning("Telemetry emission error: %s", exc)

        # Structured event log (existing)
        _log_event(
            "frame-orchestrator", "frame_processed",
            component="orchestrator",
            frame_id=frame.frame_id,
            latency_ms=telemetry.total_ms,
            detections_count=len(result.detections) if result.detections else 0,
            modules_ok=len(telemetry.modules_succeeded),
            modules_failed=len(telemetry.modules_failed),
        )
        # Store telemetry
        self._telemetry_history.append(telemetry)
        if len(self._telemetry_history) > self.config.max_telemetry_history:
            self._telemetry_history = self._telemetry_history[-self.config.max_telemetry_history:]

        # Notify callbacks
        for cb in self._result_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(result)
                else:
                    cb(result)
            except Exception as exc:
                logger.warning("Result callback error: %s", exc)

        return result

    # ------------------------------------------------------------------
    # Freshness validation (public, for use at output time)
    # ------------------------------------------------------------------

    def validate_freshness(self, result: FusedFrameResult, max_age_ms: Optional[float] = None) -> bool:
        """Assert that a result is still fresh at the point of output."""
        budget = max_age_ms or self.config.live_frame_max_age_ms
        return result.is_fresh(budget)

    def get_safe_output(self, result: FusedFrameResult, max_age_ms: Optional[float] = None) -> str:
        """Return short_cue if fresh, else fallback message."""
        if self.validate_freshness(result, max_age_ms):
            return result.short_cue or "Scene analyzed."
        self.stale_aborts += 1
        return "I can't see clearly right now — please hold the camera steady."

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _timed_call(self, module: str, fn: Callable, image: Any, telemetry: FrameTelemetry) -> Any:
        """Call a module function and record latency."""
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(fn):
                result = await fn(image)
            else:
                result = fn(image)
            return result
        finally:
            elapsed = (time.time() - start) * 1000
            telemetry.latencies_per_module[module] = elapsed

    def _assign_result(self, fused: FusedFrameResult, module: str, result: Any) -> None:
        """Assign a module result to the appropriate slot in FusedFrameResult."""
        if module == "detection":
            fused.detections = result if isinstance(result, list) else []
        elif module == "depth":
            fused.depth_map = result
        elif module == "segmentation":
            fused.segmentation_masks = result if isinstance(result, list) else []
        elif module == "ocr":
            fused.ocr_results = result if isinstance(result, list) else []
        elif module == "qr":
            fused.qr_results = result if isinstance(result, list) else []
        elif module == "face":
            fused.face_results = result if isinstance(result, list) else []
        elif module == "action":
            fused.action_results = result if isinstance(result, list) else []

    def _hash_scene_graph(self, sg: Any) -> str:
        """Produce a content hash for detecting meaningful scene changes."""
        try:
            data = sg.to_dict() if hasattr(sg, "to_dict") else str(sg)
            raw = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        except Exception:
            return ""

    @staticmethod
    def _to_numpy(image: Any) -> Any:
        """Convert an image to a numpy ndarray for cascade heuristics.

        Handles LiveKit VideoFrame, PIL Image, and already-numpy arrays.
        Returns None if conversion is not possible (heuristics will skip
        image-based checks gracefully).
        """
        import numpy as np

        # Already numpy
        if isinstance(image, np.ndarray):
            return image

        # LiveKit rtc.VideoFrame — has .convert() or .data attribute
        try:
            from livekit import rtc
            if isinstance(image, rtc.VideoFrame):
                argb = image.convert(rtc.VideoBufferType.RGBA)
                arr = np.frombuffer(argb.data, dtype=np.uint8)
                arr = arr.reshape((image.height, image.width, 4))
                return arr[:, :, :3]  # drop alpha → RGB
        except (ImportError, AttributeError, Exception):
            pass

        # PIL Image
        if hasattr(image, "convert") and hasattr(image, "size"):
            try:
                return np.array(image.convert("RGB"))
            except Exception:
                pass

        # Generic: try np.asarray
        try:
            arr = np.asarray(image)
            if arr.ndim >= 2:
                return arr
        except Exception:
            pass

        return None

    # ------------------------------------------------------------------
    # Telemetry / Health
    # ------------------------------------------------------------------

    def get_recent_telemetry(self, n: int = 10) -> List[dict]:
        return [t.to_dict() for t in self._telemetry_history[-n:]]

    def health(self) -> dict:
        return {
            "total_frames": self.total_frames,
            "success_count": self.success_count,
            "stale_aborts": self.stale_aborts,
            "timeout_count": self.timeout_count,
            "recent_latencies_ms": [
                round(t.total_ms, 1) for t in self._telemetry_history[-10:]
            ],
        }
