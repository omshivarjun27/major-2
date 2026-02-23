---
id: ISSUE-004
title: Single Points of Failure for External Cloud Services
severity: high
source_artifact: architecture_risks.md
architecture_layer: infrastructure
---

## Description
Three critical external services have no fallback implementation:
- **Ollama cloud runtime** (qwen3.5:cloud): Required for all LLM reasoning (VQA, memory RAG). No local LLM fallback for inference.
- **Deepgram**: Sole STT provider. VOSK is mentioned in the system prompt but not implemented.
- **ElevenLabs**: Primary TTS. Fallback to local TTS relies on LiveKit plugin behavior, not explicit implementation.

## Root Cause
The system was designed with cloud-first assumptions. Fallback providers were documented in the system prompt but never implemented in code.

## Impact
Loss of any single cloud service degrades or fully disables core functionality. Deepgram outage = no voice input. Ollama cloud outage = no reasoning. ElevenLabs outage = degraded or no audio output.

## Reproducibility
likely

## Remediation Plan
1. Implement explicit STT fallback using Whisper or VOSK for offline/degraded mode.
2. Add health-check probes for each cloud service with circuit-breaker pattern.
3. Implement retry with exponential backoff for all cloud HTTP calls.
4. Add a local LLM fallback (e.g., small quantized model) for basic reasoning during Ollama cloud outages.
5. Implement explicit local TTS fallback (e.g., pyttsx3 or espeak).

## Implementation Suggestion
```python
# Circuit breaker pattern for cloud services
class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = recovery_timeout
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, fallback=None, **kwargs):
        if self.state == "open":
            if fallback:
                return await fallback(*args, **kwargs)
            raise ServiceUnavailableError()
        try:
            result = await func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = "open"
            if fallback:
                return await fallback(*args, **kwargs)
            raise
```

## GPU Impact
Local LLM fallback would consume additional VRAM (~2-4GB for a small quantized model). Must respect 8GB VRAM budget.

## Cloud Impact
Directly affects all cloud service interactions: Deepgram (STT), ElevenLabs (TTS), Ollama cloud (LLM), LiveKit (transport), DuckDuckGo (search).

## Acceptance Criteria
- [ ] Health check probes implemented for Deepgram, ElevenLabs, and Ollama cloud
- [ ] Circuit breaker or retry-with-backoff implemented for all cloud calls
- [ ] At least one fallback STT provider operational when Deepgram is down
- [ ] System logs clear degradation alerts when falling back to secondary providers
