---
id: ISSUE-016
title: Bare except Clauses Mask Critical Exceptions
severity: low
source_artifact: architecture_risks.md
architecture_layer: core
---

## Description
6 bare `except:` clauses found across the codebase: `core/memory/rag_reasoner.py` (lines 178, 237), `tests/realtime/calibrate_depth.py` (line 189), and `tests/realtime/session_logger.py` (lines 298, 321, 335). These catch all exceptions including `KeyboardInterrupt` and `SystemExit`.

## Root Cause
Defensive coding pattern applied without specificity. Developers used `except:` instead of `except Exception:` for maximum safety, inadvertently catching non-recoverable exceptions.

## Impact
May mask critical errors during development and debugging. `KeyboardInterrupt` (Ctrl+C) and `SystemExit` are silently swallowed, making it hard to terminate the process cleanly.

## Reproducibility
possible

## Remediation Plan
1. Replace all `except:` with `except Exception:` at minimum.
2. Where possible, catch specific exceptions (e.g., `except (ValueError, KeyError):`).
3. Add logging for caught exceptions to maintain observability.

## Implementation Suggestion
```python
# Before:
try:
    result = parse_timestamp(ts)
except:
    result = None

# After:
try:
    result = parse_timestamp(ts)
except (ValueError, TypeError) as e:
    logger.debug("Timestamp parse failed: %s", e)
    result = None
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] All 6 bare `except:` clauses replaced with specific exception types
- [ ] `ruff check . --select E722` reports 0 issues
- [ ] Caught exceptions are logged at appropriate level
