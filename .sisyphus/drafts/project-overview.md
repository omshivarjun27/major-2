# Draft: Project overview / explanation

## Requirements (confirmed)
- User wants: **Explain this project** (high-level walkthrough).

## Technical Decisions
- None yet (waiting on desired depth and focus areas).

## Research Findings
- Source: `AGENTS.md` (repo root)
  - Architecture: **Modular Monolith** with strict 5-layer hierarchy: `shared → core → application → infrastructure → apps` (enforced by import-linter).
  - Primary interfaces:
    - **FastAPI REST API** (management/state/async processing)
    - **LiveKit WebRTC agent** (real-time multimodal interaction)
  - Core capabilities: vision (YOLO/MiDaS/segmentation), VQA (Qwen-VL), OCR fallback, RAG memory (FAISS + Ollama embeddings), speech (Deepgram STT + ElevenLabs TTS).

## Open Questions
- What depth do you want: 2-minute overview vs deep dive?
- Which area matters most right now (API, realtime agent, vision pipeline, memory/RAG, speech, deployments/CI)?

## Scope Boundaries
- INCLUDE: architecture, module map, key runtime flows, how pieces connect.
- EXCLUDE: implementation changes (planning only) unless you ask for a work plan.
