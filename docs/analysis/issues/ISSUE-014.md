---
id: ISSUE-014
title: 13 Tests Broken Due to Stale Import Path
severity: low
source_artifact: architecture_risks.md
architecture_layer: cross-cutting
---

## Description
`tests/unit/test_debug_endpoints.py` contains `import api_server` which references a stale module path from a pre-restructure codebase. All 13 tests in this file fail with `ModuleNotFoundError: No module named 'api_server'`.

## Root Cause
The codebase was restructured to use the layered architecture (`apps/api/server.py`) but the test file was not updated to reflect the new import path.

## Impact
13 tests are not running, reducing coverage confidence. Debug endpoint functionality is untested.

## Reproducibility
always

## Remediation Plan
1. Update the import in `test_debug_endpoints.py` from `import api_server` to `from apps.api.server import app`.
2. Update any references to `api_server.app` to use the new import.
3. Verify all 13 tests pass with the corrected import.

## Implementation Suggestion
```python
# Before:
import api_server

# After:
from apps.api.server import app
```

## GPU Impact
N/A

## Cloud Impact
N/A

## Acceptance Criteria
- [ ] Import path corrected in `test_debug_endpoints.py`
- [ ] All 13 previously-broken tests pass
- [ ] No new import errors introduced
