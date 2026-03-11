"""
Production Pipeline — Real-Time Voice-Vision Architecture
==========================================================

Replaces the blocking, race-condition-prone pipeline with:
  1. StreamingTTSCoordinator — sentence-level LLM→TTS bridge with cancellation
  2. PerceptionWorkerPool — thread-pool-based frame processing off the event loop
  3. AudioOutputManager — single-writer TTS output with interrupt/resume
  4. FrameSampler — adaptive frame throttling with backpressure
  5. PipelineMonitor — real-time perf counters and alerting
"""

from .audio_manager import AudioOutputManager
from .cancellation import CancellationScope, ScopedTask
from .frame_sampler import AdaptiveFrameSampler
from .integration import (
    PipelineComponents,
    create_pipeline_components,
    on_new_user_query,
    run_perception_off_event_loop,
    speak_with_priority,
    wrap_entrypoint_with_pipeline,
)
from .perception_pool import PerceptionWorkerPool
from .pipeline_monitor import PipelineMonitor
from .streaming_tts import SentenceBuffer, StreamingTTSCoordinator

__all__ = [
    "StreamingTTSCoordinator",
    "SentenceBuffer",
    "PerceptionWorkerPool",
    "AudioOutputManager",
    "AdaptiveFrameSampler",
    "PipelineMonitor",
    "CancellationScope",
    "ScopedTask",
    "PipelineComponents",
    "create_pipeline_components",
    "wrap_entrypoint_with_pipeline",
    "on_new_user_query",
    "speak_with_priority",
    "run_perception_off_event_loop",
]
