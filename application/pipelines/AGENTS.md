# application/pipelines/AGENTS.md
Production pipeline orchestration: managing concurrency, latency, and system health.
**Context**: Replaces simple blocking calls with high-performance, non-blocking asynchronous components.

## CORE COMPONENTS (The "Big 8")
| Component | Class | Purpose |
|-----------|-------|---------|
| `streaming_tts.py` | `StreamingTTSCoordinator` | High-performance, sentence-level LLM-to-TTS with cancellation. |
| `perception_pool.py` | `PerceptionWorkerPool` | ThreadPoolExecutor off the event loop (detect, depth, embed, OCR, QR). |
| `audio_manager.py` | `AudioOutputManager` | Priority-based audio queue with preemption. |
| `frame_sampler.py` | `AdaptiveFrameSampler` | Dynamic cadence (100–1000ms) based on scene changes and system load. |
| `pipeline_monitor.py` | `PipelineMonitor` | Per-stage latency tracking and SLO compliance monitoring. |
| `cancellation.py` | `CancellationScope` | Context-aware cancellation of all tasks associated with a query. |
| `debouncer.py` | `Debouncer` | Prevents redundant cues (5s window) unless scene-graph changes. |
| `watchdog.py` | `Watchdog` | Detects camera/worker stalls; spoken alerts on critical failures. |

## OTHER UTILS
- `worker_pool.py`: Generic base class for Thread/Process worker pools.
- `perception_telemetry.py`: Data structures for per-frame JSON logging (`FrameLog`, `DetectionEntry`).

## KEY PATTERNS
### Worker Registration
```python
pool = PerceptionWorkerPool()
pool.register("detect", num_workers=2)
pool.register("depth", num_workers=1)
# Future usage: future = await pool.submit("detect", fn, args, timeout_ms=300)
```

### Audio Priority Enum
Defined in `AudioOutputManager`:
- `0 (CRITICAL_HAZARD)`: Preempts all other audio.
- `1 (USER_RESPONSE)`: Standard answer to a user query.
- `2 (PROACTIVE)`: Periodic updates ("The path is clear").
- `3 (SYSTEM)`: Status alerts (watchdog warnings).
- `4 (AMBIENT)`: Low-priority contextual information.

### Debouncer Keying
Deduplicates messages based on `SpokenRecord` history (50 item FIFO).
**Condition**: Deduplicates if `short_cue` and `scene_graph_hash` are identical within the window.
