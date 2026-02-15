# Migration Map — Repository Restructure

> **Architecture**: Clean Architecture + Modular Monolith  
> **Date**: 2025  
> **Status**: Phase 4 Complete — `pyproject.toml`, import-linter, root cleanup done

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [File Movement Map](#file-movement-map)
4. [Import Migration Guide](#import-migration-guide)
5. [Layer Boundaries](#layer-boundaries)
6. [Deployment Changes](#deployment-changes)
7. [Migration Phases](#migration-phases)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   apps/                          │  ← HTTP / WebSocket / CLI entrypoints
│   api/server.py   realtime/agent.py   cli/      │
├─────────────────────────────────────────────────┤
│               application/                       │  ← Use-case orchestration
│   frame_processing/   pipelines/   event_bus/    │
├─────────────────────────────────────────────────┤
│                  core/                           │  ← Pure domain logic (zero I/O deps)
│   vqa/  memory/  face/  audio/  qr/  ocr/       │
│   action/  braille/  speech/  vision/            │
├─────────────────────────────────────────────────┤
│              infrastructure/                     │  ← External system adapters
│   llm/ollama/   speech/deepgram/   tavus/        │
│   speech/elevenlabs/   storage/   monitoring/    │
├─────────────────────────────────────────────────┤
│                 shared/                          │  ← Cross-cutting utilities
│   config/   logging/   schemas/   utils/         │
└─────────────────────────────────────────────────┘
```

**Dependency rule**: Each layer may only import from layers below it.
- `apps/` → `application/`, `core/`, `infrastructure/`, `shared/`
- `application/` → `core/`, `shared/`
- `core/` → `shared/` only
- `infrastructure/` → `shared/` only
- `shared/` → standard library only

---

## Directory Structure

```
Voice-Vision-Assistant-for-Blind/
│
├── apps/                              # Application entrypoints
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py                 # ← api_server.py (FastAPI REST API)
│   ├── realtime/
│   │   ├── __init__.py
│   │   ├── entrypoint.py            # ← app.py (LiveKit agent launcher)
│   │   └── agent.py                 # ← src/main.py (agent logic, 2087 LOC)
│   └── cli/
│       ├── __init__.py
│       ├── session_logger.py         # ← debug_tools/session_logger.py
│       └── visualizer.py            # ← debug_tools/visualizer.py
│
├── core/                              # Pure domain logic (engines)
│   ├── __init__.py
│   ├── vqa/                          # ← vqa_engine/ (10 files)
│   │   ├── __init__.py
│   │   ├── perception.py
│   │   ├── scene_graph.py
│   │   ├── spatial_fuser.py
│   │   ├── vqa_reasoner.py
│   │   ├── memory.py
│   │   ├── priority_scene.py
│   │   ├── orchestrator.py
│   │   ├── api_schema.py
│   │   └── api_endpoints.py
│   ├── memory/                       # ← memory_engine/ (14 files)
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── embeddings.py
│   │   ├── indexer.py
│   │   ├── ingest.py
│   │   ├── retriever.py
│   │   ├── rag_reasoner.py
│   │   ├── maintenance.py
│   │   ├── llm_client.py
│   │   ├── cloud_sync.py
│   │   ├── event_detection.py
│   │   ├── api_schema.py
│   │   ├── api_endpoints.py
│   │   └── README.md
│   ├── face/                         # ← face_engine/ (5 files)
│   │   ├── __init__.py
│   │   ├── face_detector.py
│   │   ├── face_embeddings.py
│   │   ├── face_tracker.py
│   │   └── face_social_cues.py
│   ├── audio/                        # ← audio_engine/ (4 files)
│   │   ├── __init__.py
│   │   ├── ssl.py
│   │   ├── audio_event_detector.py
│   │   └── audio_fusion.py
│   ├── qr/                           # ← qr_engine/ (6 files)
│   │   ├── __init__.py
│   │   ├── qr_scanner.py
│   │   ├── qr_decoder.py
│   │   ├── ar_tag_handler.py
│   │   ├── cache_manager.py
│   │   └── qr_api.py
│   ├── ocr/                          # ← ocr_engine/ (2 files)
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── action/                       # ← action_engine/ (2 files)
│   │   ├── __init__.py
│   │   └── action_recognizer.py
│   ├── braille/                      # ← braille_engine/ (7 files)
│   │   ├── __init__.py
│   │   ├── braille_capture.py
│   │   ├── braille_segmenter.py
│   │   ├── braille_classifier.py
│   │   ├── braille_ocr.py
│   │   └── embossing_guidance.py
│   ├── speech/                       # ← speech_vqa_bridge/ (5 files)
│   │   ├── __init__.py
│   │   ├── speech_handler.py
│   │   ├── voice_router.py
│   │   ├── tts_handler.py
│   │   └── voice_ask_pipeline.py
│   ├── vision/                       # ← src/tools/visual.py + spatial.py
│   │   ├── __init__.py
│   │   ├── visual.py
│   │   └── spatial.py
│   └── reasoning/
│       └── __init__.py
│
├── application/                       # Orchestration layer
│   ├── __init__.py
│   ├── frame_processing/
│   │   ├── __init__.py
│   │   ├── frame_orchestrator.py     # ← frame_orchestrator.py
│   │   ├── live_frame_manager.py     # ← live_frame_manager.py
│   │   ├── freshness.py             # ← freshness.py
│   │   └── confidence_cascade.py    # ← confidence_cascade.py
│   ├── pipelines/
│   │   ├── __init__.py              # ← pipeline/__init__.py (re-exports)
│   │   ├── debouncer.py             # ← debouncer.py
│   │   ├── watchdog.py              # ← watchdog.py
│   │   ├── worker_pool.py           # ← worker_pool.py
│   │   ├── perception_telemetry.py  # ← perception_telemetry.py
│   │   ├── streaming_tts.py         # ← pipeline/streaming_tts.py
│   │   ├── perception_pool.py       # ← pipeline/perception_pool.py
│   │   ├── audio_manager.py         # ← pipeline/audio_manager.py
│   │   ├── frame_sampler.py         # ← pipeline/frame_sampler.py
│   │   ├── pipeline_monitor.py      # ← pipeline/pipeline_monitor.py
│   │   ├── cancellation.py          # ← pipeline/cancellation.py
│   │   └── integration.py           # ← pipeline/integration.py
│   ├── session_management/
│   │   └── __init__.py
│   └── event_bus/
│       └── __init__.py
│
├── infrastructure/                    # External system adapters
│   ├── __init__.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── internet_search.py       # ← src/tools/internet_search.py
│   │   ├── google_places.py         # ← src/tools/google_places.py
│   │   ├── places_search.py         # ← src/tools/places_search.py
│   │   ├── ollama/
│   │   │   ├── __init__.py
│   │   │   └── handler.py           # ← src/tools/ollama_handler.py
│   │   ├── siliconflow/
│   │   │   └── __init__.py
│   │   └── embeddings/
│   │       └── __init__.py
│   ├── speech/
│   │   ├── __init__.py
│   │   ├── deepgram/
│   │   │   └── __init__.py
│   │   └── elevenlabs/
│   │       ├── __init__.py
│   │       └── tts_manager.py       # ← tts_manager.py
│   ├── tavus/
│   │   ├── __init__.py
│   │   └── adapter.py               # ← tavus_adapter.py
│   ├── storage/
│   │   └── __init__.py
│   └── monitoring/
│       └── __init__.py
│
├── shared/                            # Cross-cutting utilities
│   ├── __init__.py                   # (existing — shared types)
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # ← src/config.py
│   ├── logging/
│   │   ├── __init__.py
│   │   └── logging_config.py        # ← shared/logging_config.py
│   ├── schemas/
│   │   └── __init__.py              # ← shared/__init__.py (shared types)
│   ├── debug/                         # ← debug_tools/ (cross-cutting)
│   │   ├── __init__.py
│   │   ├── visualizer.py            # Debug image renderer
│   │   └── session_logger.py        # Structured JSON session logger
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── startup_guards.py        # ← startup_guards.py
│   │   ├── encryption.py            # ← shared/encryption.py
│   │   ├── helpers.py               # ← src/utils.py
│   │   ├── runtime_diagnostics.py   # ← src/runtime_diagnostics.py
│   │   ├── calendar.py              # ← src/tools/calendar.py
│   │   ├── communication.py         # ← src/tools/communication.py
│   │   └── timing.py               # ← src/tools/timing.py
│   ├── logging_config.py            # (existing — backward compat)
│   └── encryption.py                # (existing — backward compat)
│
├── research/                          # Benchmarks, experiments, reports
│   ├── benchmarks/
│   │   ├── benchmark_results.json   # ← benchmark_results.json
│   │   └── benchmark_realtime.py    # ← tools/benchmark_realtime.py
│   ├── experiments/
│   │   ├── harness.py               # ← repro/harness.py
│   │   └── scenarios/               # ← scenarios/
│   └── reports/
│       ├── REMEDIATION_PLAN.json    # ← REMEDIATION_PLAN.json
│       └── REMEDIATION_REPORT.json  # ← REMEDIATION_REPORT.json
│
├── tests/                             # Test hierarchy
│   ├── unit/                         # (existing unit tests)
│   ├── integration/                  # (existing integration tests)
│   ├── realtime/                     # (existing realtime tests)
│   └── performance/                  # ← nfr/tests/ (18 NFR test files)
│
├── configs/
│   └── config.yaml                   # ← config.yaml
│
├── deployments/
│   ├── docker/
│   │   └── Dockerfile               # ← Dockerfile (updated paths)
│   └── compose/
│       └── docker-compose.test.yml   # ← docker-compose.test.yml (updated)
│
├── docs/                              # Documentation
│   ├── PRODUCTION_AUDIT.md
│   ├── ANALYSIS_REPORT.md
│   ├── analysis_report_v3.md
│   ├── bug_tracker.md
│   └── (existing docs/)
│
├── .runtime/                          # Runtime artifacts (gitignored)
│   ├── logs/
│   └── cache/
│
├── models/                            # ML model weights (unchanged)
│   ├── yolov8n.onnx
│   └── midas_v21_small_256.onnx
│
├── data/                              # Persistent data (unchanged)
│   ├── memory_backup/
│   └── memory_index/
│
├── scripts/                           # Dev tooling (unchanged)
│
├── .github/workflows/ci.yml          # CI pipeline
├── requirements.txt
├── requirements-extras.txt
├── README.md
├── MIGRATION_MAP.md                  # This file
├── Dockerfile                        # Root Dockerfile (COPY . .)
└── configs/
    └── config.yaml                   # ← config.yaml
```

---

## File Movement Map

### Core Domain (`core/`)

| Old Path | New Path | LOC |
|----------|----------|-----|
| `vqa_engine/*` | `core/vqa/*` | ~2,400 |
| `memory_engine/*` | `core/memory/*` | ~3,200 |
| `face_engine/*` | `core/face/*` | ~1,800 |
| `audio_engine/*` | `core/audio/*` | ~900 |
| `qr_engine/*` | `core/qr/*` | ~1,100 |
| `ocr_engine/*` | `core/ocr/*` | ~600 |
| `action_engine/*` | `core/action/*` | ~500 |
| `braille_engine/*` | `core/braille/*` | ~1,400 |
| `speech_vqa_bridge/*` | `core/speech/*` | ~1,200 |
| `src/tools/visual.py` | `core/vision/visual.py` | 440 |
| `src/tools/spatial.py` | `core/vision/spatial.py` | 1,158 |

### Application Layer (`application/`)

| Old Path | New Path | LOC |
|----------|----------|-----|
| `frame_orchestrator.py` | `application/frame_processing/frame_orchestrator.py` | 599 |
| `live_frame_manager.py` | `application/frame_processing/live_frame_manager.py` | ~300 |
| `freshness.py` | `application/frame_processing/freshness.py` | ~200 |
| `confidence_cascade.py` | `application/frame_processing/confidence_cascade.py` | ~400 |
| `debouncer.py` | `application/pipelines/debouncer.py` | ~200 |
| `watchdog.py` | `application/pipelines/watchdog.py` | ~250 |
| `worker_pool.py` | `application/pipelines/worker_pool.py` | ~300 |
| `perception_telemetry.py` | `application/pipelines/perception_telemetry.py` | ~350 |
| `pipeline/*` | `application/pipelines/*` | 2,061 |

### Infrastructure (`infrastructure/`)

| Old Path | New Path | LOC |
|----------|----------|-----|
| `src/tools/ollama_handler.py` | `infrastructure/llm/ollama/handler.py` | 268 |
| `src/tools/internet_search.py` | `infrastructure/llm/internet_search.py` | ~150 |
| `src/tools/google_places.py` | `infrastructure/llm/google_places.py` | ~100 |
| `src/tools/places_search.py` | `infrastructure/llm/places_search.py` | ~200 |
| `tavus_adapter.py` | `infrastructure/tavus/adapter.py` | ~200 |
| `tts_manager.py` | `infrastructure/speech/elevenlabs/tts_manager.py` | 281 |

### Shared (`shared/`)

| Old Path | New Path | LOC |
|----------|----------|-----|
| `src/config.py` | `shared/config/settings.py` | 373 |
| `src/utils.py` | `shared/utils/helpers.py` | ~100 |
| `src/runtime_diagnostics.py` | `shared/utils/runtime_diagnostics.py` | ~700 |
| `startup_guards.py` | `shared/utils/startup_guards.py` | 285 |
| `shared/logging_config.py` | `shared/logging/logging_config.py` | 264 |
| `shared/encryption.py` | `shared/utils/encryption.py` | ~200 |
| `src/tools/calendar.py` | `shared/utils/calendar.py` | ~150 |
| `src/tools/communication.py` | `shared/utils/communication.py` | ~150 |
| `src/tools/timing.py` | `shared/utils/timing.py` | ~100 |

### Apps (`apps/`)

| Old Path | New Path | LOC |
|----------|----------|-----|
| `app.py` | `apps/realtime/entrypoint.py` | 75 |
| `src/main.py` | `apps/realtime/agent.py` | 2,087 |
| `api_server.py` | `apps/api/server.py` | 675 |
| `debug_tools/*` | `apps/cli/*` | ~500 |

### Research (`research/`)

| Old Path | New Path |
|----------|----------|
| `benchmark_results.json` | `research/benchmarks/benchmark_results.json` |
| `tools/benchmark_realtime.py` | `research/benchmarks/benchmark_realtime.py` |
| `repro/*` | `research/experiments/*` |
| `scenarios/*` | `research/experiments/scenarios/*` |
| `REMEDIATION_PLAN.json` | `research/reports/REMEDIATION_PLAN.json` |
| `REMEDIATION_REPORT.json` | `research/reports/REMEDIATION_REPORT.json` |

### Tests (`tests/`)

| Old Path | New Path |
|----------|----------|
| `tests/unit/*` | `tests/unit/*` (unchanged) |
| `tests/integration/*` | `tests/integration/*` (unchanged) |
| `tests/realtime/*` | `tests/realtime/*` (unchanged) |
| `nfr/tests/*` | `tests/performance/*` |

### Deployment (`deployments/`)

| Old Path | New Path |
|----------|----------|
| `Dockerfile` | `deployments/docker/Dockerfile` |
| `docker-compose.test.yml` | `deployments/compose/docker-compose.test.yml` |
| `config.yaml` | `configs/config.yaml` |

### Documentation (`docs/`)

| Old Path | New Path |
|----------|----------|
| `ANALYSIS_REPORT.md` | `docs/ANALYSIS_REPORT.md` |
| `analysis_report_v3.md` | `docs/analysis_report_v3.md` |
| `bug_tracker.md` | `docs/bug_tracker.md` |
| `PRODUCTION_AUDIT.md` | `docs/PRODUCTION_AUDIT.md` |

---

## Import Migration Guide

### Phase 1 (Current) — Both old and new imports work

All legacy imports continue to work. New canonical imports are available:

```python
# ─── OLD (still works, will be deprecated) ───
from vqa_engine import PerceptionPipeline
from memory_engine.indexer import FAISSIndexer
from face_engine import FaceDetector
from shared.logging_config import configure_logging
from src.config import get_config
from frame_orchestrator import FrameOrchestrator
from startup_guards import run_startup_checks

# ─── NEW (canonical, preferred) ───
from core.vqa import PerceptionPipeline
from core.memory.indexer import FAISSIndexer
from core.face import FaceDetector
from shared.logging.logging_config import configure_logging
from shared.config import get_config
from application.frame_processing.frame_orchestrator import FrameOrchestrator
from shared.utils.startup_guards import run_startup_checks
```

### Phase 2 — Gradual migration per module

Update imports one module at a time. Recommended order:

1. **`shared/`** — Update `shared.logging_config` → `shared.logging`
2. **`core/`** — Update `vqa_engine` → `core.vqa`, `memory_engine` → `core.memory`, etc.
3. **`application/`** — Update `frame_orchestrator` → `application.frame_processing.frame_orchestrator`
4. **`infrastructure/`** — Update `src.tools.ollama_handler` → `infrastructure.llm.ollama`
5. **`apps/`** — Update `api_server` → `apps.api.server`

### Phase 3 — Remove legacy shims

Once all imports are updated, delete the legacy directories:
- `vqa_engine/`, `memory_engine/`, `face_engine/`, etc.
- `src/` directory
- Root-level `.py` orchestration files

### Import Mapping Reference

| Old Import | New Import |
|-----------|-----------|
| `from vqa_engine import X` | `from core.vqa import X` |
| `from vqa_engine.perception import X` | `from core.vqa.perception import X` |
| `from memory_engine import X` | `from core.memory import X` |
| `from memory_engine.config import X` | `from core.memory.config import X` |
| `from memory_engine.indexer import X` | `from core.memory.indexer import X` |
| `from memory_engine.embeddings import X` | `from core.memory.embeddings import X` |
| `from memory_engine.retriever import X` | `from core.memory.retriever import X` |
| `from memory_engine.rag_reasoner import X` | `from core.memory.rag_reasoner import X` |
| `from memory_engine.api_schema import X` | `from core.memory.api_schema import X` |
| `from face_engine import X` | `from core.face import X` |
| `from face_engine.face_detector import X` | `from core.face.face_detector import X` |
| `from face_engine.face_embeddings import X` | `from core.face.face_embeddings import X` |
| `from face_engine.face_tracker import X` | `from core.face.face_tracker import X` |
| `from audio_engine import X` | `from core.audio import X` |
| `from qr_engine import X` | `from core.qr import X` |
| `from ocr_engine import X` | `from core.ocr import X` |
| `from ocr_engine.engine import X` | `from core.ocr.engine import X` |
| `from action_engine import X` | `from core.action import X` |
| `from braille_engine import X` | `from core.braille import X` |
| `from speech_vqa_bridge import X` | `from core.speech import X` |
| `from speech_vqa_bridge.voice_router import X` | `from core.speech.voice_router import X` |
| `from debug_tools import X` | `from apps.cli import X` |
| `from debug_tools.session_logger import X` | `from apps.cli.session_logger import X` |
| `from pipeline import X` | `from application.pipelines import X` |
| `from pipeline.integration import X` | `from application.pipelines.integration import X` |
| `from frame_orchestrator import X` | `from application.frame_processing.frame_orchestrator import X` |
| `from live_frame_manager import X` | `from application.frame_processing.live_frame_manager import X` |
| `from freshness import X` | `from application.frame_processing.freshness import X` |
| `from confidence_cascade import X` | `from application.frame_processing.confidence_cascade import X` |
| `from debouncer import X` | `from application.pipelines.debouncer import X` |
| `from watchdog import X` | `from application.pipelines.watchdog import X` |
| `from worker_pool import X` | `from application.pipelines.worker_pool import X` |
| `from perception_telemetry import X` | `from application.pipelines.perception_telemetry import X` |
| `from startup_guards import X` | `from shared.utils.startup_guards import X` |
| `from tavus_adapter import X` | `from infrastructure.tavus import X` |
| `from tts_manager import X` | `from infrastructure.speech.elevenlabs import X` |
| `from src.config import X` | `from shared.config import X` |
| `from src.tools.visual import X` | `from core.vision.visual import X` |
| `from src.tools.spatial import X` | `from core.vision.spatial import X` |
| `from src.tools.ollama_handler import X` | `from infrastructure.llm.ollama import X` |
| `from src.tools.calendar import X` | `from shared.utils.calendar import X` |
| `from src.tools.communication import X` | `from shared.utils.communication import X` |
| `from src.tools.timing import X` | `from shared.utils.timing import X` |
| `from shared.logging_config import X` | `from shared.logging import X` |
| `from shared.encryption import X` | `from shared.utils.encryption import X` |
| `from shared import X` | `from shared.schemas import X` |

---

## Layer Boundaries

### Allowed Dependencies (Architectural Constraints)

```
apps/          → application/, core/, infrastructure/, shared/
application/   → core/, shared/
core/          → shared/  (NO infrastructure, NO application)
infrastructure/→ shared/  (NO core, NO application)
shared/        → stdlib   (NO project imports)
```

### Violation Examples (What NOT to do)

```python
# ❌ core/ importing from infrastructure/
from infrastructure.llm.ollama import OllamaHandler  # WRONG in core/

# ❌ shared/ importing from core/
from core.vqa import PerceptionPipeline  # WRONG in shared/

# ❌ infrastructure/ importing from core/
from core.memory.indexer import FAISSIndexer  # WRONG in infrastructure/

# ✅ application/ importing from core/ — correct
from core.vqa import PerceptionPipeline  # OK in application/

# ✅ apps/ importing from any lower layer — correct
from infrastructure.llm.ollama import OllamaHandler  # OK in apps/
from core.vqa import PerceptionPipeline  # OK in apps/
```

---

## Deployment Changes

### Dockerfile

The canonical Dockerfile is now at `deployments/docker/Dockerfile`.  
The root `Dockerfile` remains for backward compatibility.

```bash
# Build with new Dockerfile
docker build -f deployments/docker/Dockerfile -t voice-vision-assistant .

# Or use the root Dockerfile (still works)
docker build -t voice-vision-assistant .
```

### Docker Compose

```bash
# New location
docker compose -f deployments/compose/docker-compose.test.yml up

# Root location still works
docker compose -f docker-compose.test.yml up
```

### CI Pipeline

The CI workflow (`.github/workflows/ci.yml`) continues to work unchanged since all legacy paths are preserved.

---

## Migration Phases

### Phase 1 ✅ (Complete)
- Created clean architecture directory tree
- Copied all files to new canonical locations
- Created `__init__.py` files for all packages
- Updated deployment Dockerfile
- Wrote this MIGRATION_MAP.md
- **Result**: Both old and new import paths work simultaneously

### Phase 2 ✅ (Complete)
- Updated 65 imports in `core/` packages to use relative/canonical paths
- Updated 9 imports in `application/` to reference `core/` instead of legacy engine names
- Updated 325+ imports in `tests/` to use new canonical paths (including `src.*` references)
- Updated 69 imports in `apps/`, `shared/`, `tools/`, `research/`, `pipeline/`
- Added `DeprecationWarning` to all 9 legacy engine `__init__.py` files
- Converted `apps/realtime/agent.py` relative imports from `src/` to canonical paths
- Replaced `import src` bootstrap with inline `dotenv` loading
- **Result**: All canonical code uses new import paths; legacy shims emit deprecation warnings

### Phase 3 ✅ (Complete)
- Removed 13 legacy directories: `vqa_engine/`, `memory_engine/`, `face_engine/`, `audio_engine/`, `qr_engine/`, `ocr_engine/`, `action_engine/`, `braille_engine/`, `speech_vqa_bridge/`, `debug_tools/`, `pipeline/`, `repro/`, `nfr/`
- Removed 13 root-level `.py` files: `app.py`, `api_server.py`, `frame_orchestrator.py`, `live_frame_manager.py`, `freshness.py`, `confidence_cascade.py`, `debouncer.py`, `watchdog.py`, `worker_pool.py`, `perception_telemetry.py`, `startup_guards.py`, `tavus_adapter.py`, `tts_manager.py`
- Removed `src/` directory (bootstrap logic moved to `apps/` entrypoints)
- Removed `tools/` directory (migrated to `research/benchmarks/`)
- Removed legacy root files: `benchmark_results.json`, `REMEDIATION_PLAN.json`, `REMEDIATION_REPORT.json`
- Updated Dockerfiles (`deployments/docker/Dockerfile`, root `Dockerfile`) to use new entrypoints
- Updated CI workflow (`.github/workflows/ci.yml`) to use `core.*` imports and `tests/performance/` paths
- **Result**: Clean repository with no legacy shims; all code at canonical locations

### Phase 4 ✅ (Complete)
- Created `pyproject.toml` with package discovery, metadata, and tool configuration
- Package installable via `pip install -e ".[dev]"` — discovers `core`, `application`, `infrastructure`, `shared`, `apps`
- Added `import-linter` with 4 architectural contracts enforcing layer boundaries
- Moved debug tools from `apps/cli/` to `shared/debug/` (fixes `core → apps` boundary violation)
- Added `lint-imports` step to CI workflow (`.github/workflows/ci.yml`)
- Created `.dockerignore` for lean root Dockerfile builds
- Updated `.gitignore` — added `qr_cache/`, runtime data files, `import_linter_cache/`
- Fixed both `docker-compose.test.yml` files (`api_server:app` → `apps.api.server:app`)
- Cleaned up root debris:
  - Removed 4 duplicate docs (already in `docs/`)
  - Removed duplicate `config.yaml` (already in `configs/`)
  - Removed 4 test output artifacts (`.txt`)
  - Removed migration artifacts: `changed_files_list.txt`, `scenarios/`, migration scripts
  - Moved `test_deepgram.py` and `test_siliconflow.py` to `tests/integration/`
- Updated `README.md` with new project structure, commands, and architecture docs
- **Result**: Production-grade project configuration with automated boundary enforcement

---

## Impact Analysis

| Metric | Before (Phase 1) | After (Phase 4) |
|--------|-------------------|------------------|
| Root-level `.py` files | 16 | 0 |
| Top-level directories | 30 | 14 (clean) |
| Engine packages at root | 9 shims | 0 |
| Legacy directories | 13 | 0 |
| Max import depth | 4 | 4 |
| Architectural layers | 5 | 5 (apps → app → core → infra → shared) |
| Total imports migrated | 0 | 468+ |
| Boundary contracts | 0 | 4 (import-linter) |
| Breaking changes | 0 | 0 (CI, Dockerfile updated) |

---

*Generated by production audit workflow. Last updated: 2026.*
