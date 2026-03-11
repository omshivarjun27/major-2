# Root Directory Context

## Overall Project Purpose and Architecture
This is the root directory of the Voice-Vision-Assistant-for-Blind project. It contains the primary configuration, orchestration, and documentation for the entire application. The architecture relies on various modules for audio, vision, reasoning, and speech.

## Tech Stack and Major Dependencies
- Python (Core application)
- Containerization (Docker/Compose)
- Various ML/AI APIs (LLM, Speech, Vision)
- Infrastructure components (Grafana, Prometheus, Loki)

## Build, Run, and Test Instructions
- Run: Use `docker-compose` or equivalent deployment scripts in `deployments/`.
- Test: Run `pytest tests/`.
- Build: Refer to `Dockerfile` and setup guides in `docs/`.

## High-Level Folder Structure Overview
.benchmarks, .gemini, .github, .import_linter_cache, .opencode, .pytest_cache, .ruff_cache, .runtime, .sisyphus, application, apps, conductor, configs, core, data, deployments, docs, failures, fixes, infrastructure, logs, models, my-first-extension, Papers, qr_cache, reports, research, scripts, shared, tests, voice_vision_assistant.egg-info

## Immediate Subdirectories
- [.benchmarks](./.benchmarks/AGENTS.md)
- [.gemini](./.gemini/AGENTS.md)
- [.github](./.github/AGENTS.md)
- [.import_linter_cache](./.import_linter_cache/AGENTS.md)
- [.opencode](./.opencode/AGENTS.md)
- [.pytest_cache](./.pytest_cache/AGENTS.md)
- [.ruff_cache](./.ruff_cache/AGENTS.md)
- [.runtime](./.runtime/AGENTS.md)
- [.sisyphus](./.sisyphus/AGENTS.md)
- [application](./application/AGENTS.md)
- [apps](./apps/AGENTS.md)
- [conductor](./conductor/AGENTS.md)
- [configs](./configs/AGENTS.md)
- [core](./core/AGENTS.md)
- [data](./data/AGENTS.md)
- [deployments](./deployments/AGENTS.md)
- [docs](./docs/AGENTS.md)
- [failures](./failures/AGENTS.md)
- [fixes](./fixes/AGENTS.md)
- [infrastructure](./infrastructure/AGENTS.md)
- [logs](./logs/AGENTS.md)
- [models](./models/AGENTS.md)
- [my-first-extension](./my-first-extension/AGENTS.md)
- [Papers](./Papers/AGENTS.md)
- [qr_cache](./qr_cache/AGENTS.md)
- [reports](./reports/AGENTS.md)
- [research](./research/AGENTS.md)
- [scripts](./scripts/AGENTS.md)
- [shared](./shared/AGENTS.md)
- [tests](./tests/AGENTS.md)
- [voice_vision_assistant.egg-info](./voice_vision_assistant.egg-info/AGENTS.md)
