# shared/AGENTS.md
Cross-cutting utilities: the single source of truth for all data types, configuration, and logging.
**Constraint**: Imports from standard library only. NEVER from other project layers.

## WHERE TO LOOK
| Module | Purpose |
|--------|---------|
| `schemas/` | Definitive type definitions and ABCs for the entire project. |
| `config/` | Centralized environment-based settings and feature flags. |
| `logging/` | Structured JSON logging with PII scrubbing. |
| `debug/` | Real-time session logging and debug visualization. |
| `utils/` | Helpers: startup guards, timing, encryption, timing. |

## SCHEMAS & TYPES
**DO NOT redefine these in other modules.** Always import from `shared.schemas`.
- `BoundingBox`: x1, y1, x2, y2. Methods: `center`, `area`, `clamp()`, `to_xywh()`.
- `Detection`: id, class_name, confidence, bbox.
- `DepthMap`: H×W depth array. **`get_region_depth(bbox)` → `(min, median, max)`**.
- `ObstacleRecord`: Combined object + spatial data (distance, direction, priority).
- `PerceptionResult`: Canonical result for a single frame (detections, masks, depth).
- `Priority`: Enum (CRITICAL <1m, NEAR_HAZARD 1-2m, FAR_HAZARD 2-5m, SAFE >5m).
- `Direction`: Enum mapping degrees to cues (e.g., FAR_LEFT, AHEAD, FAR_RIGHT).

## CONFIG ACCESSORS
Configuration should be accessed via helper functions in `shared.config.settings`:
```python
from shared.config.settings import get_spatial_config, get_live_frame_config, get_worker_config

spatial = get_spatial_config()  # Access thresholds, model paths, etc.
frame_cfg = get_live_frame_config()  # Access timing/freshness constraints.
```

## LOGGING & PII
- **Setup**: Call `configure_logging()` at the entrypoint of any service.
- **PII Scrubbing**: `PIIScrubFilter` automatically redacts emails, IPs, face IDs, and API keys.
- **Structured Logs**: Use `log_event("component", "event", **kwargs)` for JSON-ready logs.

## DEBUG TOOLS
- **SessionLogger**: Captures per-turn system states into a local ring buffer for inspection.
- **Visualizer**: (CLI) Renders frame results with bboxes and depth maps for offline debugging.
