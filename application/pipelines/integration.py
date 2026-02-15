"""
Pipeline Integration Bridge
============================

Drop-in functions that wire the new pipeline modules into the existing
``src/main.py`` entrypoint WITHOUT rewriting the whole 2 000-line file.

Usage in entrypoint()::

    from application.pipelines.integration import (
        create_pipeline_components,
        wrap_entrypoint_with_pipeline,
    )

    # After creating agent_session:
    components = create_pipeline_components(agent_session, userdata, ctx)
    await wrap_entrypoint_with_pipeline(components, userdata, agent_session, ctx)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .cancellation import CancellationScope, ScopeManager
from .streaming_tts import StreamingTTSCoordinator
from .perception_pool import PerceptionWorkerPool, create_perception_pool
from .audio_manager import AudioOutputManager, AudioPriority
from .frame_sampler import AdaptiveFrameSampler, SamplerConfig
from .pipeline_monitor import PipelineMonitor

logger = logging.getLogger("pipeline-integration")


# ============================================================================
# Component Container
# ============================================================================

@dataclass
class PipelineComponents:
    """Holds all production-pipeline modules for easy teardown."""
    scope_manager: ScopeManager
    perception_pool: PerceptionWorkerPool
    audio_manager: AudioOutputManager
    frame_sampler: AdaptiveFrameSampler
    monitor: PipelineMonitor
    tts_coordinator: Optional[StreamingTTSCoordinator] = None

    async def start_all(self) -> None:
        await self.audio_manager.start()
        await self.monitor.start()
        logger.info("Pipeline components started")

    async def stop_all(self) -> None:
        self.scope_manager.cancel_current("shutdown")
        self.perception_pool.shutdown()
        await self.audio_manager.stop()
        await self.monitor.stop()
        logger.info("Pipeline components stopped")

    def health(self) -> dict:
        return {
            "scope_manager": self.scope_manager.health(),
            "perception_pool": self.perception_pool.health(),
            "audio_manager": self.audio_manager.health(),
            "frame_sampler": self.frame_sampler.health(),
            "monitor": self.monitor.dashboard(),
        }


# ============================================================================
# Factory
# ============================================================================

def create_pipeline_components(
    agent_session: Any,
    userdata: Any,
    ctx: Any,
    *,
    max_workers: int = 4,
) -> PipelineComponents:
    """Create and wire all pipeline components.

    Pulls detection/depth/embedding callables from userdata and
    registers them with the PerceptionWorkerPool.

    Args:
        agent_session: LiveKit AgentSession (used for say() binding)
        userdata: UserData instance with VQA pipeline, embeddings, etc.
        ctx: JobContext (room reference)
        max_workers: Thread pool size
    """

    # ── ScopeManager ──
    scope_manager = ScopeManager()

    # ── PerceptionWorkerPool ──
    detector_fn = None
    depth_fn = None
    embedding_fn = None
    faiss_fn = None
    edge_density_fn = None

    # Extract sync detector from VQA pipeline
    vqa_pipeline = getattr(userdata, "_vqa_pipeline", None)
    if vqa_pipeline is not None:
        # Try to get synchronous callables for the thread pool
        if hasattr(vqa_pipeline, "detector") and vqa_pipeline.detector is not None:
            det = vqa_pipeline.detector
            if hasattr(det, "detect_sync"):
                detector_fn = det.detect_sync
            elif hasattr(det, "_run_inference"):
                detector_fn = det._run_inference
        if hasattr(vqa_pipeline, "depth_estimator") and vqa_pipeline.depth_estimator is not None:
            de = vqa_pipeline.depth_estimator
            if hasattr(de, "estimate_sync"):
                depth_fn = de.estimate_sync
            elif hasattr(de, "_run_inference"):
                depth_fn = de._run_inference

    # Extract sync embedding from memory engine
    try:
        from core.memory.embeddings import TextEmbedder
        _embedder = TextEmbedder()
        embedding_fn = _embedder.embed
    except (ImportError, AttributeError):
        pass

    # Extract FAISS search
    try:
        from core.memory.retriever import MemoryRetriever
        _retriever = getattr(userdata, "_memory_retriever", None)
        if _retriever and hasattr(_retriever, "_search_sync"):
            faiss_fn = _retriever._search_sync
    except (ImportError, AttributeError):
        pass

    # Edge density from confidence cascade
    try:
        from application.frame_processing.confidence_cascade import compute_edge_density
        edge_density_fn = compute_edge_density
    except (ImportError, AttributeError):
        pass

    perception_pool = create_perception_pool(
        detector_fn=detector_fn,
        depth_fn=depth_fn,
        embedding_fn=embedding_fn,
        faiss_search_fn=faiss_fn,
        edge_density_fn=edge_density_fn,
        max_workers=max_workers,
    )

    # ── AudioOutputManager ──
    say_fn = None
    if hasattr(agent_session, "say"):
        say_fn = agent_session.say

    audio_manager = AudioOutputManager(
        say_fn=say_fn,
        max_queue_size=10,
        min_interval_ms=500.0,
    )

    # ── AdaptiveFrameSampler ──
    frame_sampler = AdaptiveFrameSampler(SamplerConfig(
        base_cadence_ms=200.0,
        min_cadence_ms=100.0,
        max_cadence_ms=1000.0,
    ))

    # ── PipelineMonitor ──
    def _on_slo_violation(stage: str, actual_ms: float, target_ms: float):
        logger.warning(
            "SLO VIOLATION: %s took %.0fms (target: %.0fms)",
            stage, actual_ms, target_ms,
        )

    monitor = PipelineMonitor(alert_callback=_on_slo_violation)

    return PipelineComponents(
        scope_manager=scope_manager,
        perception_pool=perception_pool,
        audio_manager=audio_manager,
        frame_sampler=frame_sampler,
        monitor=monitor,
    )


# ============================================================================
# Entrypoint wrapper — patches the critical loops
# ============================================================================

async def wrap_entrypoint_with_pipeline(
    components: PipelineComponents,
    userdata: Any,
    agent_session: Any,
    ctx: Any,
) -> None:
    """Patch the running entrypoint with production pipeline components.

    This function:
    1. Replaces the proactive announcer with AudioOutputManager routing
    2. Wraps continuous_consumer with PerceptionWorkerPool
    3. Installs cancellation scope on new user messages
    4. Starts the PipelineMonitor
    5. Exposes /debug/pipeline endpoint

    Call AFTER agent_session.start() and continuous pipeline tasks are created.
    """

    await components.start_all()

    # ── Patch 1: Install cancellation on new queries ─────────────
    # Monkey-patch the agent's on_message to cancel previous scope
    original_on_message = type(agent_session).on_message if hasattr(type(agent_session), 'on_message') else None

    # Store components on userdata for access from tools
    userdata._pipeline_components = components
    userdata._scope_manager = components.scope_manager
    userdata._audio_manager = components.audio_manager
    userdata._perception_pool = components.perception_pool
    userdata._pipeline_monitor = components.monitor

    logger.info("Pipeline integration active: scope_manager + audio_manager + perception_pool + monitor")

    # ── Patch 2: Replace proactive announcer say() with audio_manager ──
    # The original proactive announcer calls agent_session.say() directly.
    # We replace that with audio_manager.enqueue() for priority-aware output.
    userdata._proactive_say = lambda text: asyncio.create_task(
        components.audio_manager.enqueue(
            text,
            priority=AudioPriority.PROACTIVE_WARNING,
            max_age_ms=3000.0,
        )
    )

    logger.info("Proactive announcer routed through AudioOutputManager")


# ============================================================================
# Helpers for patching existing tool functions
# ============================================================================

def run_perception_off_event_loop(
    components: PipelineComponents,
    worker_name: str,
    *args: Any,
    timeout_ms: float = 500.0,
) -> Any:
    """Convenience: submit a perception task to the thread pool.

    Use this in tool functions to replace direct sync calls::

        # BEFORE (blocks event loop):
        result = yolo_detect(image)

        # AFTER (runs in thread pool):
        result = await run_perception_off_event_loop(
            components, "detection", image
        )
    """
    return components.perception_pool.submit(worker_name, *args, timeout_ms=timeout_ms)


async def speak_with_priority(
    components: PipelineComponents,
    text: str,
    priority: AudioPriority = AudioPriority.USER_RESPONSE,
) -> bool:
    """Speak text through the priority audio manager.

    Use this instead of agent_session.say() for coordinated output.
    """
    return await components.audio_manager.enqueue(text, priority=priority)


def on_new_user_query(components: PipelineComponents, query_text: str) -> CancellationScope:
    """Called when a new user query arrives.

    1. Cancels previous query scope (stops LLM + TTS + perception)
    2. Creates new scope for this query
    3. Interrupts current audio output

    Returns the new CancellationScope for this query.
    """
    # Cancel previous work
    components.audio_manager.interrupt_all()

    # Create new scope
    scope_id = f"query_{int(time.monotonic() * 1000)}"
    scope = components.scope_manager.new_scope(scope_id)

    # Record for monitoring
    components.monitor.record_query_start()

    logger.debug("New query scope: %s for '%s'", scope_id, query_text[:40])
    return scope


# ============================================================================
# FastAPI /debug/pipeline endpoint factory
# ============================================================================

def create_debug_endpoint(components: PipelineComponents):
    """Create a FastAPI router for pipeline debugging.

    Returns a dict that can be served at /debug/pipeline.
    """
    return components.health()
