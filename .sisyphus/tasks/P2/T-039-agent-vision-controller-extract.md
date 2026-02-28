# T-039: agent-vision-controller-extract

> Phase: P2 | Cluster: CL-APV | Risk: Critical | State: completed | created_at: 2026-02-25T14:00:00Z | completed_at: 2026-02-25T16:00:00Z

## Objective

Extract vision processing logic from agent.py into `apps/realtime/vision_controller.py`. This module owns frame capture orchestration, model dispatch (YOLO, MiDaS, segmentation), and result aggregation for the real-time pipeline. The vision controller interfaces with `core/vision/` engines and `application/frame_processing/` components. It must support both synchronous single-frame analysis and streaming multi-frame workflows. All vision-related function routing, frame caching, and model selection logic currently embedded in agent.py moves here.

## Current State (Codebase Audit 2026-02-27)

- **COMPLETED** during the P2 architecture remediation work.
- `apps/realtime/vision_controller.py` exists as a fully functional module.
- Handles frame capture orchestration, model dispatch (YOLO, MiDaS, segmentation), and result aggregation.
- Interfaces with `core/vision/` and `application/frame_processing/`.
- All vision-related function routing and frame caching logic extracted from agent.py.

## Implemented Files

| File | Purpose |
|------|---------|
| `apps/realtime/vision_controller.py` | Vision processing dispatch and result aggregation |

## Evidence of Completion

- `apps/realtime/vision_controller.py` exists with full vision processing implementation.
- `apps/realtime/agent.py` imports and delegates vision work to vision_controller.
- No vision processing logic remains in agent.py.

## Acceptance Criteria

- [x] `apps/realtime/vision_controller.py` created with vision processing logic
- [x] Frame capture orchestration extracted
- [x] Model dispatch (YOLO, MiDaS, segmentation) extracted
- [x] Result aggregation for real-time pipeline extracted
- [x] Interfaces with `core/vision/` and `application/frame_processing/`
- [x] Supports single-frame and streaming multi-frame workflows
- [x] Agent coordinator delegates vision work to this module
- [x] `ruff check .` clean
- [x] `lint-imports` clean

## Upstream Dependencies

T-038 (session manager extraction must complete first).

## Downstream Unblocks

T-041, T-042

## Estimated Scope

- New code: ~400+ LOC (vision_controller.py)
- Modified code: agent.py further reduced after this extraction
- Risk: Critical (vision is the most complex extraction, touches perception pipeline)
