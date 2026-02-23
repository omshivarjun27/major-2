# application/frame_processing/AGENTS.md
Per-frame fusion engine: collects parallel worker results to build a canonical SceneGraph.
**Key Invariant**: Every result in a `FusedFrameResult` MUST belong to the same `frame_id`.

## WHERE TO LOOK
- `frame_orchestrator.py` (598 LOC): Central logic for `process_frame()`. Manages the collection and fusion of parallel worker outputs.
- `live_frame_manager.py`: Manages the frame ring buffer (30 frames) and coordinates backpressure.
- `confidence_cascade.py`: 3-tier filtering (Detected/Possible/LogOnly) and secondary object verification.
- `freshness.py`: Enforces max frame age (default: 500ms). Frames older than this are rejected before processing.

## CONFIDENCE CASCADE THRESHOLDS
These are defined in `confidence_cascade.py` (overridden via `config.yaml`):
- `detected_threshold = 0.60`: Reported to user.
- `low_confidence_threshold = 0.30`: Tracked but not immediately reported.
- **SecondaryVerifier**: Applies penalties to "confusion pairs" (e.g., bottle/phone, cup/bowl) to reduce false positives.

## FRAME LIFECYCLE
1. `LiveFrameManager`: Captures frame from stream → assigns `frame_id` + `epoch_ms` → places in ring buffer.
2. `FrameOrchestrator`: Grabs latest "fresh" frame → dispatches parallel workers (detect/depth/segment) via `PerceptionWorkerPool`.
3. `Fusion`: Joins worker results on `frame_id`. If any worker fails/times out, a degraded placeholder is used.
4. `Filtering`: Applies confidence cascade and secondary verification.
5. `Output`: Produces a `FusedFrameResult` containing `SceneGraph` + `NavigationOutput`.

## NEVER-RAISE GUARANTEE
`FrameOrchestrator.process_frame()` is designed to **never raise an exception**.
- If a detector fails: Returns empty detections.
- If depth is unavailable: Uses a synthetic "safe" 5m depth map.
- If a timeout occurs (300ms): Returns the partial results collected so far.
