---
id: ISSUE-025
title: QR Cache TTL — No In-Memory Expiry, Stale Reads on Clock Skew
severity: medium
source_artifact: data_flows.md
architecture_layer: core
---

## Description
The QR cache (`core/qr/cache_manager.py`) uses file-based JSON storage with a configurable TTL (default 86400 seconds). However, TTL enforcement is based on file timestamps with no in-memory expiry mechanism. Clock skew between writes and reads can cause stale cache entries to be served.

## Root Cause
The cache was implemented as a simple file-based JSON store. TTL is checked by comparing the cached timestamp against the current system time. If the system clock changes (NTP sync, timezone change, DST), stale entries may be served or valid entries may be prematurely expired.

## Impact
- Stale QR scan results served to the user (e.g., outdated bus schedule, changed WiFi password)
- On clock-forward skew: valid cache entries prematurely expired, causing unnecessary re-scans
- On clock-backward skew: expired entries served as fresh

## Reproducibility
possible

## Remediation Plan
1. Use monotonic clock (`time.monotonic()`) for TTL tracking instead of wall clock.
2. Add in-memory TTL tracking alongside file-based storage.
3. Implement a cache invalidation method for manual override.
4. Add unit tests for clock skew scenarios.

## Implementation Suggestion
```python
import time

class CacheManager:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl = ttl_seconds
        self._memory_cache: Dict[str, Tuple[float, Any]] = {}  # key -> (monotonic_ts, value)

    def get(self, key: str) -> Optional[Any]:
        if key in self._memory_cache:
            ts, value = self._memory_cache[key]
            if time.monotonic() - ts < self.ttl:
                return value
            del self._memory_cache[key]
        return self._load_from_disk(key)  # fallback to file
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] Cache TTL uses monotonic clock for in-memory entries
- [ ] Clock skew does not cause stale reads or premature expiry
- [ ] Manual cache invalidation method available
- [ ] Unit test covers TTL enforcement under simulated clock skew
