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

from .streaming_tts import StreamingTTSCoordinator, SentenceBuffer
from .perception_pool import PerceptionWorkerPool
from .audio_manager import AudioOutputManager
from .frame_sampler import AdaptiveFrameSampler
from .pipeline_monitor import PipelineMonitor
from .cancellation import CancellationScope, ScopedTask
from .integration import (
    PipelineComponents,
    create_pipeline_components,
    wrap_entrypoint_with_pipeline,
    on_new_user_query,
    speak_with_priority,
    run_perception_off_event_loop,
)

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
