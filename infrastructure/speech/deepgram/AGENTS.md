1. Folder Purpose
- Deepgram adapter for real-time speech-to-text. Provides fast, streaming STT with a default SLA target around 100ms.
- This surface is the entry point for transcribing user speech into intents for the planner.
- It is a critical SPOF by design; plan for resilience through monitoring and graceful degradation when possible.

2. Contained Components
- Streaming STT bridge (Deepgram)
- Optional post-processing hooks (noise suppression, speaker diarization stubs)
- Config helpers for API keys, timeouts, and language settings

3. Dependency Graph
- Shared logging/config utilities feed into the STT path.
- The STT result flows to the intent router and core perception pipeline.
- No alternate STT provider is wired here by default.

4. Task Tracking
- Establish a baseline streaming session and test with a synthetic audio source.
- Attach latency metrics and error categorization for STT calls.
- Integrate basic keyword-spotting hooks for intent signaling.

5. Design Thinking
- Minimize buffering delay; streaming must stay responsive under variable network latency.
- Keep the API aligned with other speech adapters for ease of orchestration.
- Ensure data privacy by avoiding unnecessary logging of raw audio chunks.

6. Research Notes
- Real-time STT depends heavily on network quality; plan for retries with backoff.
- Consider future fallback to a local Whisper-based module if required for offline mode.

7. Risk Assessment
- SPOF risk if external provider experiences outages or rate limits.
- Privacy risk: ensure transcripts are stored securely and scrubbed if logged.
- Changes in API terms may require quick iteration in orchestration code.

8. Improvement Suggestions
- Add simple replay protection and transcript validation to catch alignment errors.
- Document supported languages and model update cadence.
- Prepare a light-weight offline fallback plan for critical deployments.

9. Folder Change Log
- Created infrastructure/speech/deepgram/AGENTS.md detailing the STT adapter plan.
- Noted streaming latency targets and privacy considerations.
