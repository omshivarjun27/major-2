---
title: "Stakeholders — Voice & Vision Assistant for Blind"
section: 03
related_artifacts:
  - docs/analysis/component_inventory.json
  - docs/analysis/architecture_risks.md
  - docs/analysis/data_flows.md
---

# 03 Stakeholders

## 1. Primary End User — Blind / Visually Impaired Person

The primary user of the system relies on voice-first interaction and real-time environmental analysis to enhance daily independence.

-   **Interaction Mode**: Voice queries via LiveKit WebRTC and live camera feeds.
-   **Core Needs**: Accurate and low-latency audio descriptions, reliable obstacle warnings, text/Braille reading, and context-aware memory recall.
-   **Key Constraints**: Absence of a visual interface requires high-quality, concise, and priority-sorted audio output.
-   **Privacy Expectation**: Explicit control over sensitive features such as face recognition and long-term memory ingestion (disabled by default).

## 2. System Maintainer / Developer

Responsible for the long-term health, performance, and feature expansion of the monorepo.

-   **Interaction Mode**: FastAPI REST debug endpoints, session logs, and CI/CD pipelines.
-   **Core Needs**: Clear visibility into pipeline health, manageable code complexity (addressing the agent.py god object), and automated testing coverage.
-   **Key Concern**: Reducing technical debt, including 3,674 lint issues and the current lack of a static type checker, to improve maintainability scores.

## 3. Infrastructure Administrator

Manages the deployment environment, resource allocation, and security posture.

-   **Interaction Mode**: Docker configurations, environment variable management, and GitHub Actions.
-   **Core Needs**: Secure handling of API secrets, non-root container execution, and reliable GPU driver compatibility.
-   **Key Concern**: Resolving critical security risks such as the presence of API keys in tracked configuration files and the need for hardened Docker images.

## 4. Cloud Service Provider (External)

External entities providing essential speech, reasoning, and transport services.

-   **Service Portfolio**: Deepgram (STT), ElevenLabs (TTS), LiveKit (WebRTC), qwen3.5:cloud (LLM), Tavus (Avatar), and DuckDuckGo (Search).
-   **System Dependency**: All cloud interactions are asynchronous; however, the system currently lacks circuit breakers and redundant fallbacks for these critical external dependencies.
-   **SLA Requirement**: High uptime for STT and LLM services is mandatory for system functionality.

## 5. ML / AI Engineer

Optimizes the local perception pipeline and model performance.

-   **Interaction Mode**: ONNX Runtime configurations, model weight management, and local Ollama runpoints.
-   **Core Needs**: Efficient VRAM utilization (~3.1GB peak on RTX 4060) and accurate performance telemetry for detection and depth estimation models.
-   **Key Concern**: Eliminating silent failures in the perception pipeline (e.g., YOLO falling back to Mock) and ensuring non-blocking execution for embedding generation.
