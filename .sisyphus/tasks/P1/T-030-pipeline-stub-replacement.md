# T-030: pipeline-stub-replacement

> Phase: P1 | Cluster: CL-APP | Risk: Low | State: not_started

## Objective

Replace the empty event_bus and session_management stubs in `application/` with minimal
working implementations. Both directories currently contain nothing beyond a comment-only
`__init__.py` and a placeholder `AGENTS.md`. The event_bus needs an `EventBus` class
with publish/subscribe/unsubscribe semantics, and session_management needs a `SessionManager`
with create/get/destroy lifecycle methods. Both will use in-memory storage with no external
dependencies.

These are foundational building blocks for the application layer. The event bus lets
modules communicate without tight coupling, and session management tracks per-user state
across interactions. Completing this task drops the application-layer stub count from 2
to 0 and unblocks T-031 (frame-processing-integration), which needs event dispatch to
notify downstream consumers when a frame is processed.

## Current State (Codebase Audit 2026-02-25)

- `application/event_bus/__init__.py` (line 1): Single comment line
  `# application/event_bus — Inter-component event routing`. No classes, no functions.
- `application/event_bus/AGENTS.md` (27 lines): Documents planned components (EventRouter,
  MessageBus, EventListeners, MessageFormat) but nothing is implemented. States:
  "Tasks: None implemented yet; reserved for future work."
- `application/session_management/__init__.py` (line 1): Single comment line
  `# application/session_management — Session lifecycle`. No classes, no functions.
- `application/session_management/AGENTS.md` (26 lines): Documents planned components
  (SessionStore, SessionManager, SessionMiddleware). States: "Tasks: None; reserved for
  future session persistence features." Planned interfaces: create_session, get_session,
  refresh_session, end_session.
- `application/AGENTS.md` lists both modules as "(Stub)" in the WHERE TO LOOK table.
- The `application/` layer constraint: may import from `core/` and `shared/` only. Never
  from `infrastructure/` or `apps/`.
- P0 baseline shows `application` stub_inventory count at 0 in `p0_metrics.json` (line 39),
  but the module-level metric counts only code stubs, not empty directories. The directory
  stubs are tracked separately in the 11-stub total.
- No existing tests reference `application.event_bus` or `application.session_management`.
- `pyproject.toml` import-linter rules enforce that `application` cannot import from
  `infrastructure` or `apps`.

## Implementation Plan

### Step 1: Create EventBus class

Create `application/event_bus/bus.py` with a synchronous in-memory EventBus. Use a
`defaultdict(list)` to map event names to lists of callback functions. Support both
sync and async callbacks.

```python
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional
import asyncio
import logging

logger = logging.getLogger("event-bus")

class EventBus:
    """In-memory publish/subscribe event bus for decoupled communication."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_count: int = 0

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """Register a callback for the given event name."""
        ...

    def unsubscribe(self, event_name: str, callback: Callable) -> bool:
        """Remove a callback. Returns True if found and removed."""
        ...

    async def publish(self, event_name: str, data: Any = None) -> int:
        """Publish an event to all subscribers. Returns count of notified listeners."""
        ...

    def subscriber_count(self, event_name: Optional[str] = None) -> int:
        """Return number of subscribers, optionally filtered by event name."""
        ...

    def health(self) -> dict:
        """Health check for pipeline monitoring."""
        ...
```

### Step 2: Create SessionManager class

Create `application/session_management/manager.py` with an in-memory SessionManager.
Use a dict keyed by session_id. Each session stores creation time, last access time,
and a metadata dict.

```python
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class Session:
    session_id: str
    created_at: float
    last_accessed: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class SessionManager:
    """In-memory session lifecycle manager."""

    def __init__(self, max_sessions: int = 100, ttl_seconds: float = 3600.0) -> None:
        self._sessions: Dict[str, Session] = {}
        ...

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session with a unique ID."""
        ...

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve session by ID. Updates last_accessed. Returns None if expired/missing."""
        ...

    def destroy_session(self, session_id: str) -> bool:
        """Remove a session. Returns True if it existed."""
        ...

    def active_sessions(self) -> int:
        """Count of non-expired sessions."""
        ...

    def health(self) -> dict:
        """Health check for pipeline monitoring."""
        ...
```

### Step 3: Update __init__.py exports

Update both `__init__.py` files to export the new classes. Keep the existing comment
as a docstring.

### Step 4: Update AGENTS.md files

Update all three AGENTS.md files (application/, event_bus/, session_management/) to
reflect the new active status and document the public API.

### Step 5: Write unit tests

Write comprehensive tests covering subscribe/publish/unsubscribe for the event bus
and create/get/destroy for session management. Include edge cases: duplicate subscribe,
unsubscribe non-existent callback, expired session cleanup, max session limit.

## Files to Create

| File | Purpose |
|------|---------|
| `application/event_bus/bus.py` | EventBus class with publish/subscribe/unsubscribe |
| `application/session_management/manager.py` | SessionManager class with create/get/destroy |
| `tests/unit/test_event_bus.py` | Unit tests for EventBus (8+ test cases) |
| `tests/unit/test_session_management.py` | Unit tests for SessionManager (8+ test cases) |

## Files to Modify

| File | Change |
|------|--------|
| `application/event_bus/__init__.py` | Export EventBus class |
| `application/session_management/__init__.py` | Export SessionManager and Session classes |
| `application/AGENTS.md` | Change event_bus and session_management from "(Stub)" to "Active" |
| `application/event_bus/AGENTS.md` | Document EventBus API, subscriber model, health interface |
| `application/session_management/AGENTS.md` | Document SessionManager API, TTL model, health interface |

## Tests to Write

| Test File | Tests |
|-----------|-------|
| `tests/unit/test_event_bus.py` | `test_subscribe_and_publish` - subscribe a callback, publish event, verify callback invoked with correct data |
| | `test_publish_no_subscribers` - publish event with no subscribers, verify returns 0 and doesn't crash |
| | `test_multiple_subscribers` - register 3 callbacks for same event, verify all called |
| | `test_unsubscribe` - subscribe then unsubscribe, verify callback not invoked on next publish |
| | `test_unsubscribe_nonexistent` - unsubscribe callback that was never registered, verify returns False |
| | `test_async_callback` - subscribe an async callback, verify it runs correctly |
| | `test_subscriber_count` - verify subscriber_count returns correct totals per event and globally |
| | `test_health` - verify health() returns expected dict structure |
| `tests/unit/test_session_management.py` | `test_create_session` - create session, verify ID is UUID, timestamps set |
| | `test_get_session` - create then get, verify same session returned with updated last_accessed |
| | `test_get_nonexistent` - get unknown session_id, verify returns None |
| | `test_destroy_session` - create then destroy, verify returns True, subsequent get returns None |
| | `test_destroy_nonexistent` - destroy unknown ID, verify returns False |
| | `test_session_expiry` - create session with 0.01s TTL, sleep, verify get returns None |
| | `test_max_sessions` - exceed max_sessions limit, verify oldest session evicted |
| | `test_health` - verify health() returns expected dict structure with active_sessions count |

## Acceptance Criteria

- [ ] `EventBus` class exists in `application/event_bus/bus.py` with publish/subscribe/unsubscribe
- [ ] `SessionManager` class exists in `application/session_management/manager.py` with create/get/destroy
- [ ] Both classes use only in-memory storage (no disk, no external services)
- [ ] Both classes importable: `from application.event_bus import EventBus`
- [ ] Both classes importable: `from application.session_management import SessionManager`
- [ ] EventBus supports both sync and async callbacks
- [ ] SessionManager enforces TTL expiry and max session limits
- [ ] Both classes expose `.health()` for pipeline monitoring
- [ ] 16+ unit tests pass: `pytest tests/unit/test_event_bus.py tests/unit/test_session_management.py -v`
- [ ] `ruff check .` clean
- [ ] `lint-imports` clean (no architecture boundary violations)
- [ ] All three AGENTS.md files updated to reflect active status

## Upstream Dependencies

None (entry point task for the App cluster).

## Downstream Unblocks

T-031 (frame-processing-integration) depends on event_bus for frame result notification.

## Estimated Scope

- New code: ~200 LOC (bus.py ~80, manager.py ~100, __init__.py updates ~20)
- Tests: ~200 LOC (test_event_bus.py ~100, test_session_management.py ~100)
- Modified code: ~30 lines across AGENTS.md files
- Risk: Low. Pure in-memory implementations with no external dependencies. The main
  risk is API surface mismatch with future needs, mitigated by keeping the interface
  minimal and extensible.
