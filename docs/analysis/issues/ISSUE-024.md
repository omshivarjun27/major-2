---
id: ISSUE-024
title: No TTS Audio Caching by Text Fingerprint
severity: medium
source_artifact: data_flows.md
architecture_layer: application
---

## Description
The system prompt specifies TTS audio caching by text fingerprint, but this is not implemented in the codebase. Every TTS request (even for identical text like repeated navigation cues) makes a fresh API call to ElevenLabs.

## Root Cause
TTS caching was planned in the system design but never implemented. The TTS pipeline sends every text string directly to the ElevenLabs API without checking for previously generated audio.

## Impact
- Unnecessary cloud API calls and associated costs
- Increased latency for repeated phrases (navigation cues, greetings, error messages)
- Higher ElevenLabs API quota consumption
- Missed opportunity for instant playback of common phrases

## Reproducibility
always

## Remediation Plan
1. Implement a TTS cache using text hash (SHA-256 or xxhash) as key.
2. Store cached audio in an LRU cache (memory) with optional disk persistence.
3. Add cache hit/miss metrics for monitoring.
4. Set TTL and max cache size to prevent unbounded growth.

## Implementation Suggestion
```python
import hashlib
from functools import lru_cache

class TTSCache:
    def __init__(self, max_size=100):
        self._cache = {}
        self.max_size = max_size

    def get(self, text: str) -> Optional[bytes]:
        key = hashlib.sha256(text.encode()).hexdigest()
        return self._cache.get(key)

    def put(self, text: str, audio: bytes) -> None:
        key = hashlib.sha256(text.encode()).hexdigest()
        if len(self._cache) >= self.max_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = audio
```

## GPU Impact
N/A

## Cloud Impact
Reduces ElevenLabs API calls for repeated phrases. Estimated 20-40% reduction in TTS API usage based on navigation cue repetition patterns.

## Acceptance Criteria
- [ ] TTS cache implemented with text fingerprint as key
- [ ] Cache hit rate > 20% during typical navigation session
- [ ] Repeated navigation cues served from cache within 5ms
- [ ] Cache size bounded (LRU eviction) to prevent memory growth
