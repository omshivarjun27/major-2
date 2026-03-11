# Voice & Vision Assistant for Blind - Agent Context

## Project Overview
**Ally Vision Assistant** is an advanced AI-powered voice and vision assistant designed to help blind and visually impaired users understand their surroundings and navigate the world more independently. 

**Main Technologies:**
*   **Language & Runtime:** Python 3.10+
*   **Real-time Communication:** LiveKit (WebRTC)
*   **Speech Services:** Deepgram (STT) and ElevenLabs (TTS)
*   **Vision & AI:** Ollama (`qwen3-vl` for scene analysis), YOLO/ONNX (Object Detection), MiDaS (Depth Estimation), EasyOCR/Tesseract (OCR)
*   **Memory & Storage:** FAISS (Vector Indexing), SQLite

**Architecture:**
The project follows a strict 5-layer architectural design, managed top-to-bottom to ensure clean separation of concerns:
1.  **`apps/`**: Entry points (LiveKit realtime agent, FastAPI REST server, CLI).
2.  **`application/`**: Use-case orchestration, pipeline management, and frame processing.
3.  **`infrastructure/`**: External service adapters (LLMs, Speech, Storage, Avatars).
4.  **`core/`**: Pure domain logic and engines (Vision, Memory, OCR, QR, Action, Speech).
5.  **`shared/`**: Cross-cutting utilities, base schemas, configuration, and logging.

*Dependency Rule:* A layer may only import from layers beneath it. `shared` can only import standard libraries.

## Building and Running

**Setup:**
```bash
python -m venv .venv
# Activate virtual environment (.venv/bin/activate on Unix, .venv\Scripts\activate on Windows)
pip install -U pip
pip install -e ".[dev]"  # Editable install with dev extras
```

**Environment Configuration:**
Create a `.env` file based on `.env.example` containing necessary API keys (`LIVEKIT_API_KEY`, `DEEPGRAM_API_KEY`, `OLLAMA_API_KEY`, `ELEVEN_API_KEY`, etc.).

**Running the Application:**
*   **Real-time Agent (Development):** `python -m apps.realtime.entrypoint dev`
*   **Real-time Agent (Standard):** `python -m apps.realtime.entrypoint start`
*   **REST API:** `uvicorn apps.api.server:app --host 0.0.0.0 --port 8000`

**Testing:**
*   **Run all tests:** `python -m pytest tests/ -v`
*   **Run unit tests only:** `python -m pytest tests/unit/ -v`

## Development Conventions

*   **Code Style & Linting:** The project uses `ruff` for linting and formatting. Line length is set to 120 characters. 
*   **Imports Sorting:** `ruff` is configured to sort imports with `core`, `application`, `infrastructure`, `shared`, and `apps` treated as first-party modules.
*   **Architectural Enforcement:** Strict import boundaries are enforced using `import-linter`. Run `lint-imports` to verify that architectural boundaries are maintained. Do not introduce circular dependencies.
*   **Testing Practices:** Tests are organized into `unit`, `integration`, `realtime`, and `performance`. The test suite uses `pytest-asyncio` and custom markers (`slow`, `integration`). Ensure new features are accompanied by corresponding tests.
*   **Security:** `bandit` is configured for Python SAST to check for security vulnerabilities.
*   **Latency & Performance:** Strict latency budgets exist for different pipeline stages (e.g., Obstacle detection < 200ms, Scene analysis < 500ms). Use `PipelineProfiler` (from `shared.utils.timing`) to measure and adhere to these constraints.
