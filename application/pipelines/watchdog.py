"""
Watchdog
========
Monitors camera feed health, worker health, and pipeline liveness.
Produces spoken alerts when issues are detected.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("watchdog")


@dataclass
class WatchdogConfig:
    """Watchdog thresholds and settings."""
    camera_stall_threshold_ms: float = 2000.0
    worker_stall_threshold_ms: float = 5000.0
    check_interval_ms: float = 500.0
    max_consecutive_failures: int = 3
    enable_spoken_alerts: bool = True


@dataclass
class ComponentHealth:
    """Health state for a monitored component."""
    name: str
    last_activity_ms: float = 0.0
    consecutive_failures: int = 0
    is_healthy: bool = True
    last_error: Optional[str] = None
    total_checks: int = 0
    total_failures: int = 0

    def record_activity(self) -> None:
        self.last_activity_ms = time.time() * 1000
        self.consecutive_failures = 0
        self.is_healthy = True
        self.last_error = None

    def record_failure(self, error: str = "") -> None:
        self.consecutive_failures += 1
        self.total_failures += 1
        self.last_error = error

    @property
    def age_ms(self) -> float:
        if self.last_activity_ms <= 0:
            return float("inf")
        return (time.time() * 1000) - self.last_activity_ms

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "is_healthy": self.is_healthy,
            "last_activity_age_ms": round(self.age_ms, 0) if self.last_activity_ms > 0 else None,
            "consecutive_failures": self.consecutive_failures,
            "total_checks": self.total_checks,
            "total_failures": self.total_failures,
            "last_error": self.last_error,
        }


class Watchdog:
    """Monitors system health and triggers alerts.

    Usage::

        wd = Watchdog(config)
        wd.register_component("camera")
        wd.register_component("orchestrator")
        wd.on_alert(my_alert_handler)
        await wd.start()

        # In camera capture loop:
        wd.heartbeat("camera")
    """

    def __init__(self, config: Optional[WatchdogConfig] = None):
        self.config = config or WatchdogConfig()
        self._components: Dict[str, ComponentHealth] = {}
        self._alert_callbacks: List[Callable] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._suppressed_alerts: Dict[str, float] = {}  # component → last alert time
        self._alert_cooldown_ms: float = 60000.0  # Don't repeat alerts within 60s

    def register_component(self, name: str) -> None:
        """Register a component for monitoring."""
        if name not in self._components:
            self._components[name] = ComponentHealth(name=name)
            logger.info("Watchdog: registered component '%s'", name)

    def on_alert(self, callback: Callable) -> None:
        """Register an alert callback: async def handler(component_name, message)."""
        self._alert_callbacks.append(callback)

    def heartbeat(self, component: str) -> None:
        """Record that a component is alive and active."""
        if component in self._components:
            self._components[component].record_activity()

    def report_failure(self, component: str, error: str = "") -> None:
        """Report a failure for a component."""
        if component in self._components:
            self._components[component].record_failure(error)

    # -- Lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("Watchdog started (interval=%.0fms, camera_stall=%.0fms)",
                     self.config.check_interval_ms, self.config.camera_stall_threshold_ms)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # -- Health queries ------------------------------------------------------

    def is_healthy(self, component: Optional[str] = None) -> bool:
        """Check if a component (or all) is healthy."""
        if component:
            c = self._components.get(component)
            return c.is_healthy if c else False
        return all(c.is_healthy for c in self._components.values())

    def health(self) -> dict:
        """Full health report."""
        return {
            "overall_healthy": self.is_healthy(),
            "components": {n: c.to_dict() for n, c in self._components.items()},
        }

    def camera_health(self) -> dict:
        cam = self._components.get("camera")
        if not cam:
            return {"status": "not_monitored"}
        return {
            "healthy": cam.is_healthy,
            "last_frame_age_ms": round(cam.age_ms, 0) if cam.last_activity_ms > 0 else None,
            "consecutive_failures": cam.consecutive_failures,
        }

    def orchestrator_health(self) -> dict:
        orch = self._components.get("orchestrator")
        if not orch:
            return {"status": "not_monitored"}
        return {
            "healthy": orch.is_healthy,
            "last_activity_age_ms": round(orch.age_ms, 0) if orch.last_activity_ms > 0 else None,
        }

    def workers_health(self) -> dict:
        worker_comps = {n: c for n, c in self._components.items()
                        if n.startswith("worker_") or n in ("detection", "depth", "segmentation", "ocr", "qr")}
        return {
            "workers": {n: c.to_dict() for n, c in worker_comps.items()},
            "all_healthy": all(c.is_healthy for c in worker_comps.values()) if worker_comps else True,
        }

    # -- Internal check loop ------------------------------------------------

    async def _check_loop(self) -> None:
        interval_s = self.config.check_interval_ms / 1000.0
        while self._running:
            try:
                await self._run_checks()
                await asyncio.sleep(interval_s)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Watchdog check error: %s", exc)
                await asyncio.sleep(interval_s)

    async def _run_checks(self) -> None:
        now_ms = time.time() * 1000

        # Determine if there is an active user session (recent orchestrator
        # activity).  Camera alerts are only meaningful while the user is
        # actively interacting — an idle room naturally has no frames, which
        # is *not* a fault.
        orch = self._components.get("orchestrator")
        session_active = (
            orch is not None
            and orch.last_activity_ms > 0
            and orch.age_ms < self.config.worker_stall_threshold_ms
        )

        for name, comp in self._components.items():
            comp.total_checks += 1

            # Determine stall threshold
            if name == "camera":
                threshold = self.config.camera_stall_threshold_ms
            else:
                threshold = self.config.worker_stall_threshold_ms

            # ── Suppress camera checks when idle (no active session) ──
            if name == "camera" and not session_active:
                comp.is_healthy = True
                continue

            # Check staleness
            if comp.last_activity_ms > 0 and comp.age_ms > threshold:
                comp.is_healthy = False
                comp.record_failure(f"stall: {comp.age_ms:.0f}ms > {threshold:.0f}ms")
                await self._fire_alert(name, self._build_alert_message(name, comp))
            elif comp.consecutive_failures >= self.config.max_consecutive_failures:
                comp.is_healthy = False
                await self._fire_alert(name, self._build_alert_message(name, comp))
            else:
                comp.is_healthy = True

    def _build_alert_message(self, component: str, comp: ComponentHealth) -> str:
        """Build user-facing alert message."""
        if component == "camera":
            return "Camera feed interrupted — please check camera or grant permission."
        elif comp.consecutive_failures >= self.config.max_consecutive_failures:
            return f"I'm having trouble with {component}. Please try adjusting the camera angle or lighting."
        else:
            return f"{component} is experiencing issues — please hold the camera steady."

    async def _fire_alert(self, component: str, message: str) -> None:
        """Dispatch alert to registered callbacks (with dedup cooldown)."""
        now = time.time() * 1000
        last = self._suppressed_alerts.get(component, 0)
        if (now - last) < self._alert_cooldown_ms:
            return  # suppress repeated alerts
        self._suppressed_alerts[component] = now

        logger.warning("WATCHDOG ALERT [%s]: %s", component, message)
        for cb in self._alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(component, message)
                else:
                    cb(component, message)
            except Exception as exc:
                logger.error("Alert callback error: %s", exc)
