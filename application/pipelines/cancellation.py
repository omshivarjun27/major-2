"""
Cancellation Scope
==================

Structured cancellation for the real-time pipeline.
When a new user query arrives, all in-flight work for the previous
query must be cancelled cleanly — LLM streaming, TTS synthesis,
frame processing, and audio playback.

Usage::

    scope = CancellationScope("user_query_42")
    async with scope:
        task = scope.spawn(some_coro())
        ...
    # All tasks cancelled when scope exits or scope.cancel() is called
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Coroutine, List, Optional

logger = logging.getLogger("cancellation")


@dataclass
class ScopedTask:
    """A task tracked by a CancellationScope."""
    name: str
    task: asyncio.Task
    created_at: float = field(default_factory=time.monotonic)
    cancelled: bool = False

    @property
    def age_ms(self) -> float:
        return (time.monotonic() - self.created_at) * 1000

    @property
    def done(self) -> bool:
        return self.task.done()


class CancellationScope:
    """Structured concurrency scope with cancellation propagation.

    All tasks spawned within a scope are cancelled when the scope
    is cancelled or exits. This prevents stale LLM/TTS work from
    previous queries from interfering with new ones.

    Thread-safe: can be cancelled from any coroutine.
    """

    def __init__(self, scope_id: str):
        self.scope_id = scope_id
        self._tasks: List[ScopedTask] = []
        self._cancelled = False
        self._cancel_event = asyncio.Event()
        self._created_at = time.monotonic()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def cancel_event(self) -> asyncio.Event:
        """Event that is set when cancellation is requested.

        Workers can await this to detect cancellation without polling.
        """
        return self._cancel_event

    def spawn(self, coro: Coroutine, name: str = "") -> ScopedTask:
        """Spawn a task within this scope.

        The task will be automatically cancelled when the scope
        is cancelled or exits.
        """
        if self._cancelled:
            raise RuntimeError(f"Cannot spawn in cancelled scope {self.scope_id}")

        task_name = name or f"{self.scope_id}_t{len(self._tasks)}"
        task = asyncio.create_task(coro, name=task_name)
        scoped = ScopedTask(name=task_name, task=task)
        self._tasks.append(scoped)
        return scoped

    def cancel(self, reason: str = "") -> int:
        """Cancel all tasks in this scope.

        Returns the number of tasks cancelled.
        """
        if self._cancelled:
            return 0

        self._cancelled = True
        self._cancel_event.set()
        cancelled_count = 0

        for st in self._tasks:
            if not st.task.done() and not st.cancelled:
                st.task.cancel()
                st.cancelled = True
                cancelled_count += 1

        if cancelled_count > 0:
            logger.info(
                "CancellationScope '%s' cancelled %d tasks (reason: %s)",
                self.scope_id, cancelled_count, reason or "scope_exit"
            )
        return cancelled_count

    async def wait_all(self, timeout: Optional[float] = None) -> None:
        """Wait for all spawned tasks to complete or be cancelled."""
        if not self._tasks:
            return
        tasks = [st.task for st in self._tasks if not st.task.done()]
        if tasks:
            done, pending = await asyncio.wait(
                tasks, timeout=timeout, return_when=asyncio.ALL_COMPLETED
            )
            # Force-cancel any remaining if timeout hit
            for t in pending:
                t.cancel()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cancel(reason="scope_exit")
        # Wait briefly for cleanup
        await self.wait_all(timeout=1.0)
        # Suppress CancelledError from tasks
        return False

    def health(self) -> dict:
        return {
            "scope_id": self.scope_id,
            "cancelled": self._cancelled,
            "age_ms": round((time.monotonic() - self._created_at) * 1000, 1),
            "total_tasks": len(self._tasks),
            "active_tasks": sum(1 for t in self._tasks if not t.done),
            "cancelled_tasks": sum(1 for t in self._tasks if t.cancelled),
        }


class ScopeManager:
    """Manages the lifecycle of CancellationScopes.

    Ensures only one active scope exists at a time for a given pipeline.
    When a new scope is created, the previous one is automatically cancelled.
    """

    def __init__(self):
        self._current_scope: Optional[CancellationScope] = None
        self._scope_history: List[dict] = []  # bounded
        self._total_created = 0
        self._total_cancelled = 0

    @property
    def current(self) -> Optional[CancellationScope]:
        return self._current_scope

    def new_scope(self, scope_id: str) -> CancellationScope:
        """Create a new scope, cancelling the previous one."""
        # Cancel previous scope
        if self._current_scope is not None and not self._current_scope.is_cancelled:
            n = self._current_scope.cancel(reason="superseded")
            self._total_cancelled += n
            self._scope_history.append(self._current_scope.health())
            # Keep history bounded
            if len(self._scope_history) > 50:
                self._scope_history = self._scope_history[-50:]

        self._total_created += 1
        scope = CancellationScope(scope_id)
        self._current_scope = scope
        return scope

    def cancel_current(self, reason: str = "external") -> int:
        """Cancel the current scope if one exists."""
        if self._current_scope and not self._current_scope.is_cancelled:
            return self._current_scope.cancel(reason=reason)
        return 0

    def health(self) -> dict:
        return {
            "total_scopes_created": self._total_created,
            "total_tasks_cancelled": self._total_cancelled,
            "current_scope": self._current_scope.health() if self._current_scope else None,
        }
