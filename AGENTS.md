# AGENTS.md — Voice & Vision Assistant for Blind
**Commit: 723bfc7 | Branch: main**

## Project Overview
Python monorepo (>= 3.10) implementing a real-time accessibility assistant. Combines computer vision, NLP, and audio processing into a seamless experience for blind and visually impaired users. Uses a strict layered architecture: shared → core → application → infrastructure → apps.

## Build & Install
```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -e ".[dev]"
pip install -r requirements.txt
pip install -r requirements-extras.txt  # Optional (GPU, OCR)
```

## Test Commands
- `pytest tests/ --timeout=180` — all tests
- `pytest tests/unit/ -v --tb=short -q --timeout=60` — unit only
- `pytest tests/integration/ -v --tb=short -q --timeout=120` — integration
- `pytest tests/performance/ --timeout=300` — performance/NFR
- Single file: `pytest tests/unit/test_perception.py -v`
- Single class: `pytest tests/unit/test_perception.py::TestPerceptionPipeline -v`
- Single function: `pytest tests/unit/test_perception.py::TestPerceptionPipeline::test_create_pipeline -v`
- Keyword: `pytest tests/ -k "test_qr" -v`
- Coverage: `pytest tests/ --cov=. --cov-report=xml --timeout=180`
- Markers: `pytest tests/ -m slow` / `pytest tests/ -m integration`
- Note: async mode is `auto` — no `@pytest.mark.asyncio` needed.

## Lint & Format
- `ruff check .` / `ruff check . --fix`
- `ruff format .`
- `lint-imports` — architecture boundary enforcement (config in pyproject.toml)
- Config: line-length=120, target-version=py310, rules E/F/W/I, E501 ignored.

## Architecture Constraints
| Layer | Forbidden Imports | Enforcement |
|-------|-------------------|-------------|
| `shared` | `core`, `application`, `infrastructure`, `apps` | import-linter |
| `core` | `application`, `infrastructure`, `apps` | import-linter |
| `application` | `infrastructure`, `apps` | import-linter |
| `infrastructure`| `apps` | import-linter |

## Code Style Guidelines
- **Imports**: Absolute imports required. Relative only within same package. Lazy-import heavy deps.
- **Type Annotations**: Mandatory for all function signatures and class members. Use `Optional`, `Union`.
- **Naming**: `PascalCase` classes, `snake_case` functions, `_prefix` private, `UPPER_SNAKE` constants.
- **Error Handling**: NEVER crash pipeline. Use defensive `try/except` with fallbacks and logging.
- **Async Patterns**: `async/await` for I/O. `asyncio.gather()` for parallel. `wait_for()` for timeouts.
- **Logging**: Use structured JSON logging. Scrub PII (faces, names) from logs unless in debug mode.
- **Configuration**: Access via `shared.config.settings`. NEVER hardcode credentials or paths.
- **Docstrings**: Required for public classes/methods. Use Google style or telegraphic summaries.
- **Factories**: Use `create_detector()`, `create_pipeline()` factories over direct instantiation.

## Shared Types (shared/schemas/__init__.py)
| Type | Purpose |
|------|---------|
| `BoundingBox` | [x1,y1,x2,y2] pixel coords. Aliases for x_min/max. |
| `Detection` | id, class_name, confidence, bbox. Canonical object result. |
| `SegmentationMask`| detection_id, mask (numpy), boundary_confidence, edge_pixels. |
| `DepthMap` | HxW array. `get_region_depth()` returns (min, median, max). |
| `PerceptionResult`| detections, masks, depth_map, image_size, latency_ms, frame_id. |
| `ObstacleRecord`| Fused detection+segmentation+depth. distance_m, direction, priority. |
| `NavigationOutput`| short_cue, verbose_description, telemetry, has_critical. |
| `Priority` | Enum: CRITICAL (<1m), NEAR_HAZARD (<2m), FAR_HAZARD (<5m), SAFE (>5m). |
| `Direction` | Enum: FAR_LEFT to FAR_RIGHT. Center is "ahead". |
| `SpatialRelation`| Enum: LEFT_OF, RIGHT_OF, BLOCKING, etc. |

## Feature Flags (shared/config/settings.py)
| Flag Function | Purpose |
|---------------|---------|
| `spatial_enabled()` | Real-time obstacle detection & depth estimation. |
| `qr_enabled()` | QR / AR tag scanning and offline TTL cache. |
| `face_enabled()` | Face detection, tracking, and recognition engine. |
| `audio_enabled()` | Sound source localization and event detection. |
| `action_enabled()` | CLIP-based action/intent recognition from video clips. |
| `tavus_enabled()` | Virtual avatar integration for video call presence. |
| `cloud_sync_enabled()`| Cloud event synchronization & auto-summarization. |

## Latency SLAs
| Target | Value | Source |
|--------|-------|--------|
| STT | 100ms | Deepgram real-time |
| VQA | 300ms | Ollama / SiliconFlow |
| TTS | 100ms | ElevenLabs / Edge |
| Total | 500ms | End-to-end hot path |
| Pipeline timeout | 300ms | Hardware enforcement |
| Hot path | 500ms | Max acceptable E2E |

## Key Directories
| Directory | Purpose |
|-----------|---------|
| `core/vqa/` | Visual Q&A: perception, scene graph, reasoning. |
| `core/vision/` | Spatial perception, object detection, depth (YOLO/MiDaS). |
| `core/memory/` | RAG memory: FAISS indexer, Ollama embeddings, SQLite. |
| `core/ocr/` | 3-tier fallback OCR (EasyOCR -> Tesseract -> MSER). |
| `core/braille/` | Braille capture, segmentation, and classification. |
| `core/face/` | Face detection, embeddings, tracking (RetinaFace/MTCNN). |
| `core/speech/` | Voice pipeline, TTS bridge, voice router. |
| `core/audio/` | Audio event detection and sound source localization. |
| `core/qr/` | QR/AR scanning, decoding, and offline TTL cache. |
| `apps/api/` | FastAPI REST server (`server.py`). |
| `apps/realtime/` | LiveKit WebRTC agent (`agent.py`). |
| `infrastructure/`| Adapters: Ollama, Deepgram, ElevenLabs, Tavus. |
| `shared/` | Schemas, config, logging, encryption, utils. |
| `tests/` | 429+ tests: unit, integration, performance. |
| `deployments/` | Dockerfiles and Compose configurations. |

## Test Conventions
- **Class Grouping**: Group related tests in classes (e.g., `TestPerceptionPipeline`).
- **Fixtures**: Use `conftest.py` for shared fixtures (mock images, sample detections).
- **Local Mocks**: Use `unittest.mock` or `pytest-mock` to isolate external services.
- **Assert Style**: Use plain `assert` statements. Prefer `pytest.approx` for floats.
- **Markers**: Mark slow tests with `@pytest.mark.slow` and integration with `@pytest.mark.integration`.
- **Verify Guarantees**: Every new feature must include a performance test in `tests/performance/`.

## CI Pipeline
1. `secrets-scan`: verifies `.env` has no real API keys or sensitive tokens.
2. `test`: runs unit, integration, and full suites across Python 3.10–3.12.
3. `lint`: runs `ruff check` and `lint-imports` for architectural compliance.
4. `docker`: builds the production image and runs smoke tests on the main branch.

## Docker
```bash
# Build production image
docker build -t voice-vision-assistant -f deployments/docker/Dockerfile .
# Run via compose for local integration testing
docker compose -f docker-compose.test.yml up
```
- **Canonical Dockerfile**: `deployments/docker/Dockerfile`
- **Default Ports**: 8000 (API), 8081 (Agent)

## Anti-patterns
- **Never** use relative imports across module boundaries; always use absolute paths.
- **Never** define local types for data exchange; use `shared.schemas` as the source of truth.
- **Never** ignore async timeouts; wrap I/O and external calls in `asyncio.wait_for()`.
- **Never** swallow exceptions silently; log at `ERROR` level with stack trace if necessary.
- **Never** block the event loop with CPU-bound tasks; use `run_in_executor()`.
- **Never** bypass the `AudioOutputManager` for speech; use `speak_with_priority()`.
- **Never** repeat content from the root `AGENTS.md` in subdirectory `AGENTS.md` files.
- **Never** use `print()` for logging; use the structured `logging` module.
- **Never** commit `.env` or files containing secrets to the repository.

## Notes & Gotchas
- `DepthMap.get_region_depth()` returns `(min, median, max)`, NOT `(min, max, mean)`.
- `MEMORY_ENABLED` defaults to `false`. Requires explicit opt-in consent for RAG.
- OCR engine fallbacks (EasyOCR -> Tesseract) are auto-probed and cached at startup.
- Vision processing must complete in ≤300ms to stay within the hot path SLA.
- All fused results for a single interaction MUST belong to the same `frame_id`.
- LiveKit agent requires valid `.env` variables for all configured providers (Deepgram, ElevenLabs, etc.).
- Async mode for pytest is set to `auto` in `pyproject.toml`.

## Summary
| Statistic | Value |
|-----------|-------|
| Line Count | ~210 |
| Sections | 16 |
| Target Python | 3.10+ |
| SLA Hot Path | 500ms |
| Test Count | 429+ |
| Layers | 5 |
