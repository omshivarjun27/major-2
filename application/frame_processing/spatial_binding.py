"""
Spatial Binding
===============
Thin integration shim that wraps ``SpatialProcessor`` components from
``core.vision.spatial`` into the callable interface expected by
``FrameOrchestrator.process_frame()``.

Provides:
- ``create_frame_bindings()`` — returns a dict of async callables
  keyed by ``detector``, ``depth_estimator``, and ``segmenter``.
- ``create_wired_orchestrator()`` — returns a ready-to-use
  ``FrameOrchestrator`` pre-wired with spatial bindings and a
  ``SceneGraphBuilder``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from shared.schemas import DepthMap, Detection, SegmentationMask

from .frame_orchestrator import FrameOrchestrator, FrameOrchestratorConfig

logger = logging.getLogger("spatial-binding")


def create_frame_bindings(
    processor: Optional[Any] = None,
) -> Dict[str, Any]:
    """Return a dict of callables suitable for ``FrameOrchestrator.process_frame()``.

    Keys returned: ``detector``, ``depth_estimator``, ``segmenter``.

    Each callable accepts a single ``image`` argument and returns the
    appropriate result type.  The segmenter binding caches detection
    results from the most recent ``detect`` call so that detections do
    not need to be run twice when both detector and segmenter are active.

    Parameters
    ----------
    processor : SpatialProcessor, optional
        An existing processor instance.  When *None* a new one is
        created via ``create_spatial_processor()``.
    """
    from core.vision.spatial import SpatialProcessor, create_spatial_processor

    proc: SpatialProcessor = processor or create_spatial_processor()

    # Shared mutable cache so the segmenter can reuse detector output
    _detection_cache: Dict[str, List[Detection]] = {"latest": []}

    async def detect(image: Any) -> List[Detection]:
        """Run object detection and cache results for the segmenter."""
        detections = await proc._detector.detect(image)
        _detection_cache["latest"] = detections
        return detections

    async def estimate_depth(image: Any) -> DepthMap:
        """Run depth estimation."""
        return await proc._depth_estimator.estimate_depth(image)

    async def segment(image: Any) -> List[SegmentationMask]:
        """Run segmentation using cached detections.

        If no cached detections are available (e.g. detector was not
        invoked), performs a detection pass first.
        """
        dets = _detection_cache.get("latest") or []
        if not dets:
            dets = await proc._detector.detect(image)
            _detection_cache["latest"] = dets
        if not dets:
            return []
        return await proc._segmenter.segment(image, dets)

    return {
        "detector": detect,
        "depth_estimator": estimate_depth,
        "segmenter": segment,
    }


def create_wired_orchestrator(
    config: Optional[FrameOrchestratorConfig] = None,
    processor: Optional[Any] = None,
) -> FrameOrchestrator:
    """Return a ``FrameOrchestrator`` pre-wired with spatial bindings.

    The orchestrator is configured with a ``SceneGraphBuilder`` from
    ``core.vqa.scene_graph`` and the ``MicroNavFormatter`` from
    ``core.vision.spatial``, so that ``process_frame()`` can be called
    with *only* a ``TimestampedFrame`` — no extra callables required.

    Parameters
    ----------
    config : FrameOrchestratorConfig, optional
        Custom orchestrator configuration.  Defaults enable depth and
        segmentation.
    processor : SpatialProcessor, optional
        An existing ``SpatialProcessor``.  When *None*, a fresh one is
        created via the factory.
    """
    from core.vision.spatial import MicroNavFormatter
    from core.vqa.scene_graph import SceneGraphBuilder

    cfg = config or FrameOrchestratorConfig(
        enable_depth=True,
        enable_segmentation=True,
    )

    bindings = create_frame_bindings(processor)

    scene_builder = SceneGraphBuilder()
    nav_formatter = MicroNavFormatter()

    orchestrator = FrameOrchestrator(
        config=cfg,
        scene_graph_builder=scene_builder,
        nav_formatter=nav_formatter,
    )

    # Store bindings so callers can invoke process_frame without args
    orchestrator._default_bindings = bindings  # type: ignore[attr-defined]

    logger.info(
        "Wired orchestrator created (depth=%s, segmentation=%s)",
        cfg.enable_depth,
        cfg.enable_segmentation,
    )

    return orchestrator
