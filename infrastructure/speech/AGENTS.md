1. Folder Purpose
- This folder encapsulates speech interfaces used for STT and TTS.
- It exposes providers for real-time transcription (Deepgram) and voice synthesis (ElevenLabs).
- The design aims to provide swap-ready bridges with minimal changes to callers.

2. Contained Components
- infrastructure/speech/deepgram/AGENTS.md (STT adapter)
- infrastructure/speech/elevenlabs/AGENTS.md (TTS adapter)
- Common logging and config helpers living in shared/ assist both adapters.

3. Dependency Graph
- Shared layer -> infrastructure/speech -> apps/api or apps/realtime
- STT and TTS adapters depend on core logging and config; no provider-level circuit-breakers by default.
- Data leaves adapters through the infrastructure layer into memory and action pipelines.

4. Task Tracking
- Implement baseline request/response wrappers for STT and TTS calls.
- Add simple latency metrics and error classification for each provider.
- Ensure STT/TTS calls honor privacy scrubbing rules in logs.

5. Design Thinking
- Prioritize deterministic latency for critical paths (STT ~100ms, TTS ~100ms).
- Maintain a clean API surface to simplify orchestration in the speech pipeline.
- Avoid tight coupling to any single provider; document migration notes for future changes.

6. Research Notes
- Deepgram is a strong base for real-time STT, but network variability must be accounted for.
- ElevenLabs provides natural-sounding voices; monitor cost and latency under load.
- Consider fallback paths for latency outliers and log-only fallbacks when offline.

7. Risk Assessment
- SPOF risk: providers lack built-in fallbacks; monitor for outages.
- Logging of sensitive audio transcripts must be minimized or redacted.
- Configuration drift could affect language models and voice characteristics.

8. Improvement Suggestions
- Add per-provider health checks and auto-retry with backoff caps.
- Introduce per-user voice preferences in memory for consistent experiences.
- Prepare a non-networked fallback TTS option for offline scenarios if feasible.

9. Folder Change Log
- Created infrastructure/speech/AGENTS.md with nine-section structure.
- Documented provider roles and expectations for STT and TTS adapters.
- Noted privacy considerations and SLA targets for latency.
