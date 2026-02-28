1. Folder Purpose
- Voice interaction pipeline and intent routing for the core speech module. This AGENTS.md documents governance, scope, and design intent for voice-driven user interactions within the system.

2. Contained Components
- VoiceAskPipeline: End-to-end voice processing chain (Speech-To-Text -> Visual Question Answering -> Text-To-Speech) with a target SLA of 500ms.
- VoiceRouter: Dispatches intents into specialized handlers based on type (visual, search, QR, general chat).

3. Dependency Graph
- Depends on: shared/ (config, logging, schemas, utilities)
- Consumed by: apps/realtime/ (voice-enabled real-time agent)

4. Task Tracking
- Current status: Feature complete and stable in the core speech domain.
- Scope: VoiceAskPipeline and VoiceRouter implemented with baseline latency targets, validated against the 500ms SLA under typical conditions.

5. Design Thinking
- End-to-end voice experience: capture spoken input, classify intent, route to appropriate handler (visual QA, search, QR scan, chat), synthesize natural response, deliver audio within 500ms.
- Emphasis on minimizing end-to-end latency by efficient model selection and lightweight orchestration.

6. Research Notes
- Binding constraint: 500ms end-to-end SLA.
- Sub-path timings: STT ~100ms, VQA ~300ms, TTS ~100ms (targeted).
- Considerations: bias towards fast primitives, jitter tolerance, and deterministic routing logic.

7. Risk Assessment
- Stability risk: Low (well-bounded interface and deterministic flow).
- Performance risk: Moderate due to the tight 500ms SLA; requires careful scheduling and streaming I/O.
- External dependencies: STT/VQA/TTS components; network conditions can influence latency.

8. Improvement Suggestions
- Integrate voice activity detection to optimize wake-word and idle times.
- Support multiple languages and accents; implement language negotiation defaults.
- Add monitoring hooks for latency per stage and end-to-end p95 metrics.
- Explore on-device fallbacks for STT where available to reduce network variance.

9. Folder Change Log
- 2026-02-23: Initial creation
