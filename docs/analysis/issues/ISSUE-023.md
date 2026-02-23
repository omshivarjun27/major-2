---
id: ISSUE-023
title: No Fallback STT Provider — Deepgram Is Single Point of Failure
severity: high
source_artifact: data_flows.md
architecture_layer: infrastructure
---

## Description
Deepgram is the sole speech-to-text (STT) provider. The system prompt mentions VOSK as a fallback, but VOSK is not implemented in the codebase. When Deepgram is unavailable (outage, network issue, API key revoked), the system has no voice input capability.

## Root Cause
The STT pipeline was implemented with only the Deepgram LiveKit plugin. VOSK was mentioned as a planned fallback in the system prompt but was never implemented.

## Impact
Complete loss of voice input when Deepgram is unavailable. For a blind user who depends entirely on voice interaction, this is a total system failure — no alternative input method exists.

## Reproducibility
likely

## Remediation Plan
1. Implement a local STT fallback using Whisper (via `faster-whisper` for CPU efficiency) or VOSK.
2. Add STT health monitoring with automatic failover.
3. Implement the fallback as a LiveKit STT plugin or standalone adapter.
4. Log clear alerts when falling back to secondary STT.

## Implementation Suggestion
```python
# infrastructure/speech/fallback_stt.py
class FallbackSTT:
    def __init__(self):
        self.primary = DeepgramSTT()
        self.fallback = WhisperLocalSTT()

    async def transcribe(self, audio_stream):
        try:
            return await self.primary.transcribe(audio_stream)
        except (ConnectionError, TimeoutError) as e:
            logger.warning("Deepgram STT unavailable, falling back to local Whisper: %s", e)
            return await self.fallback.transcribe(audio_stream)
```

## GPU Impact
Local Whisper/VOSK fallback would use ~500MB-1GB additional VRAM (or CPU-only mode). Must be accounted for in the 8GB VRAM budget.

## Cloud Impact
Reduces dependency on Deepgram cloud service. Enables offline/degraded mode operation.

## Acceptance Criteria
- [ ] At least one local STT fallback implemented and tested
- [ ] Automatic failover triggered when Deepgram is unreachable
- [ ] Fallback latency within 2x of primary STT latency
- [ ] Clear log message when fallback is activated
