# application/AGENTS.md
Use-case orchestration layer: manages pipeline lifecycle, coordinates engines, and handles the request/response flow.
**Constraint**: Layer may only import from `core/` and `shared/`. NEVER from `infrastructure/` or `apps/`.

## WHERE TO LOOK
| Module | Purpose | Deep Dive |
|--------|---------|-----------|
| `pipelines/` | Production pipeline components (cancellation, managers, samplers). | [AGENTS.md](pipelines/AGENTS.md) |
| `frame_processing/` | Per-frame fusion engine and LiveFrame management. | [AGENTS.md](frame_processing/AGENTS.md) |
| `event_bus/` | (Stub) Central event dispatch for decoupled communication. | - |
| `session_management/` | (Stub) Session state persistence and lifecycle. | - |

## KEY ENTRY POINT
`application.pipelines.integration.create_pipeline_components()`
Call this at startup to initialize all 8 production pipeline components and wire them into a `PipelineComponents` container.

## INTEGRATION PATTERNS
### Wiring
```python
from application.pipelines import create_pipeline_components, wrap_entrypoint_with_pipeline

# Initialize components with required engine instances and callbacks
components = create_pipeline_components(perception_pipeline, tts_func, speak_func)

# Wrap an entrypoint function (e.g., LiveKit agent callback) to enable the pipeline
wrap_entrypoint_with_pipeline(entrypoint_fn, components)
```

### Cancellation
On a new user query: Use `on_new_user_query(components, query)` to:
- Cancel all active `CancellationScopes`.
- Interrupt current TTS output.
- Clear the perception cache.

### Audio Priority
**NEVER** call `agent_session.say()` directly. Use `speak_with_priority(components, text, priority)` to ensure the `AudioOutputManager` can properly queue and preempt audio (e.g., critical hazard warnings).

## TELEMETRY
Every component in this layer exposes `.health()` and `.stats()` methods. Use the `PipelineMonitor` to aggregate these for real-time observability and SLO tracking.
