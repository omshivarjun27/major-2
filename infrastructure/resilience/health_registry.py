"""Centralized service health registry for circuit breaker aggregation.

Aggregates circuit breaker states from all external services into a single queryable
interface. Provides a health summary, degradation status, and system health score.

Architecture constraint: imports from ``shared/`` only.

Usage::

    from infrastructure.resilience.health_registry import ServiceHealthRegistry

    registry = ServiceHealthRegistry()

    # Get overall health summary
    summary = registry.get_health_summary()

    # Check if system is degraded
    if registry.is_degraded():
        degraded = registry.get_degraded_services()
        print(f"Degraded services: {degraded}")

    # Get health score (0-100%)
    score = registry.get_health_score()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerState,
    get_all_breakers,
    get_circuit_breaker,
)

logger = logging.getLogger("resilience.health_registry")


class ServiceStatus(Enum):
    """Service health status levels."""

    HEALTHY = "healthy"  # Circuit CLOSED, no recent failures
    DEGRADED = "degraded"  # Circuit HALF_OPEN, recovering
    UNHEALTHY = "unhealthy"  # Circuit OPEN, service unavailable
    UNKNOWN = "unknown"  # No circuit breaker registered


@dataclass
class ServiceHealth:
    """Health status for a single service."""

    service_name: str
    status: ServiceStatus
    circuit_state: str
    failure_count: int
    success_count: int
    last_failure_time: Optional[float] = None
    uptime_percentage: float = 100.0
    response_time_ms: Optional[float] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "circuit_state": self.circuit_state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "uptime_percentage": round(self.uptime_percentage, 2),
            "response_time_ms": self.response_time_ms,
            "config": self.config,
        }


@dataclass
class HealthSummary:
    """Aggregated health summary for all services."""

    timestamp: float
    overall_status: ServiceStatus
    health_score: float
    total_services: int
    healthy_count: int
    degraded_count: int
    unhealthy_count: int
    services: Dict[str, ServiceHealth]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "health_score": round(self.health_score, 1),
            "total_services": self.total_services,
            "healthy_count": self.healthy_count,
            "degraded_count": self.degraded_count,
            "unhealthy_count": self.unhealthy_count,
            "services": {
                name: health.to_dict() for name, health in self.services.items()
            },
        }


class ServiceHealthRegistry:
    """Centralized registry for aggregating service health from circuit breakers.

    This is a read-only registry that queries circuit breaker states on demand.
    It does not maintain its own state but derives health from the circuit breakers.
    """

    # Known services that should be monitored
    KNOWN_SERVICES = [
        "deepgram",
        "elevenlabs",
        "ollama",
        "livekit",
        "tavus",
        "duckduckgo",
    ]

    def __init__(self, known_services: Optional[List[str]] = None) -> None:
        """Initialize the health registry.

        Args:
            known_services: List of service names to monitor. Defaults to KNOWN_SERVICES.
        """
        self._known_services = known_services if known_services is not None else self.KNOWN_SERVICES.copy()
        self._start_time = time.time()
        logger.info(
            "ServiceHealthRegistry initialized (monitoring %d services)",
            len(self._known_services),
        )

    def get_service_health(self, service_name: str) -> ServiceHealth:
        """Get health status for a single service.

        Args:
            service_name: Name of the service to check.

        Returns:
            ServiceHealth with current status.
        """
        cb = get_circuit_breaker(service_name)

        if cb is None:
            return ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.UNKNOWN,
                circuit_state="not_registered",
                failure_count=0,
                success_count=0,
            )

        snapshot = cb.snapshot()
        state = cb.state

        # Map circuit state to service status
        if state is CircuitBreakerState.CLOSED:
            status = ServiceStatus.HEALTHY
        elif state is CircuitBreakerState.HALF_OPEN:
            status = ServiceStatus.DEGRADED
        else:  # OPEN
            status = ServiceStatus.UNHEALTHY

        return ServiceHealth(
            service_name=service_name,
            status=status,
            circuit_state=state.value,
            failure_count=snapshot.get("failure_count", 0),
            success_count=snapshot.get("success_count", 0),
            last_failure_time=getattr(cb, "_last_failure_time", None),
            config=snapshot.get("config", {}),
        )

    def get_health_summary(self) -> HealthSummary:
        """Get aggregated health summary for all monitored services.

        Returns:
            HealthSummary with per-service status and overall metrics.
        """
        services: Dict[str, ServiceHealth] = {}
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0

        for service_name in self._known_services:
            health = self.get_service_health(service_name)
            services[service_name] = health

            if health.status is ServiceStatus.HEALTHY:
                healthy_count += 1
            elif health.status is ServiceStatus.DEGRADED:
                degraded_count += 1
            elif health.status is ServiceStatus.UNHEALTHY:
                unhealthy_count += 1
            # UNKNOWN doesn't count toward any category

        # Also include any registered services not in known_services
        all_breakers = get_all_breakers()
        for service_name in all_breakers:
            if service_name not in services:
                health = self.get_service_health(service_name)
                services[service_name] = health

                if health.status is ServiceStatus.HEALTHY:
                    healthy_count += 1
                elif health.status is ServiceStatus.DEGRADED:
                    degraded_count += 1
                elif health.status is ServiceStatus.UNHEALTHY:
                    unhealthy_count += 1

        total_services = len(services)
        health_score = self._compute_health_score(
            healthy_count, degraded_count, unhealthy_count, total_services
        )
        overall_status = self._compute_overall_status(
            healthy_count, degraded_count, unhealthy_count
        )

        return HealthSummary(
            timestamp=time.time(),
            overall_status=overall_status,
            health_score=health_score,
            total_services=total_services,
            healthy_count=healthy_count,
            degraded_count=degraded_count,
            unhealthy_count=unhealthy_count,
            services=services,
        )

    def is_degraded(self) -> bool:
        """Check if any service is degraded or unhealthy.

        Returns:
            True if any circuit breaker is OPEN or HALF_OPEN.
        """
        for service_name in self._known_services:
            cb = get_circuit_breaker(service_name)
            if cb is not None:
                state = cb.state
                if state in (CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN):
                    return True

        # Also check dynamically registered breakers
        for cb in get_all_breakers().values():
            state = cb.state
            if state in (CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN):
                return True

        return False

    def get_degraded_services(self) -> List[str]:
        """Get list of services that are currently degraded or unhealthy.

        Returns:
            List of service names with OPEN or HALF_OPEN circuits.
        """
        degraded: List[str] = []

        for service_name, cb in get_all_breakers().items():
            state = cb.state
            if state in (CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN):
                degraded.append(service_name)

        return degraded

    def get_healthy_services(self) -> List[str]:
        """Get list of services that are currently healthy.

        Returns:
            List of service names with CLOSED circuits.
        """
        healthy: List[str] = []

        for service_name, cb in get_all_breakers().items():
            if cb.state is CircuitBreakerState.CLOSED:
                healthy.append(service_name)

        return healthy

    def get_health_score(self) -> float:
        """Calculate overall system health score (0-100%).

        Scoring:
        - HEALTHY services contribute 100% of their weight
        - DEGRADED services contribute 50% of their weight
        - UNHEALTHY services contribute 0% of their weight
        - UNKNOWN services are excluded from calculation

        Returns:
            Health score as percentage (0.0 to 100.0).
        """
        summary = self.get_health_summary()
        return summary.health_score

    def _compute_health_score(
        self,
        healthy: int,
        degraded: int,
        unhealthy: int,
        total: int,
    ) -> float:
        """Compute health score from service counts.

        Args:
            healthy: Count of healthy services.
            degraded: Count of degraded services.
            unhealthy: Count of unhealthy services.
            total: Total service count.

        Returns:
            Health score as percentage (0.0 to 100.0).
        """
        # Exclude unknown services from scoring
        scored_count = healthy + degraded + unhealthy

        if scored_count == 0:
            return 100.0  # No services to score = fully healthy

        # Weight: healthy=1.0, degraded=0.5, unhealthy=0.0
        weighted_sum = (healthy * 1.0) + (degraded * 0.5) + (unhealthy * 0.0)
        return (weighted_sum / scored_count) * 100.0

    def _compute_overall_status(
        self,
        healthy: int,
        degraded: int,
        unhealthy: int,
    ) -> ServiceStatus:
        """Compute overall system status.

        Args:
            healthy: Count of healthy services.
            degraded: Count of degraded services.
            unhealthy: Count of unhealthy services.

        Returns:
            Overall system status.
        """
        if unhealthy > 0:
            return ServiceStatus.UNHEALTHY
        if degraded > 0:
            return ServiceStatus.DEGRADED
        if healthy > 0:
            return ServiceStatus.HEALTHY
        return ServiceStatus.UNKNOWN

    def add_service(self, service_name: str) -> None:
        """Add a service to the known services list.

        Args:
            service_name: Name of the service to monitor.
        """
        if service_name not in self._known_services:
            self._known_services.append(service_name)
            logger.info("Added service to health registry: %s", service_name)

    def remove_service(self, service_name: str) -> None:
        """Remove a service from the known services list.

        Args:
            service_name: Name of the service to stop monitoring.
        """
        if service_name in self._known_services:
            self._known_services.remove(service_name)
            logger.info("Removed service from health registry: %s", service_name)

    def get_uptime(self) -> float:
        """Get registry uptime in seconds.

        Returns:
            Seconds since registry initialization.
        """
        return time.time() - self._start_time

    def health(self) -> Dict[str, Any]:
        """Get health snapshot for the registry itself.

        Returns:
            Dictionary with registry health info.
        """
        summary = self.get_health_summary()
        return {
            "registry_uptime_s": round(self.get_uptime(), 1),
            "overall_status": summary.overall_status.value,
            "health_score": round(summary.health_score, 1),
            "total_services": summary.total_services,
            "healthy": summary.healthy_count,
            "degraded": summary.degraded_count,
            "unhealthy": summary.unhealthy_count,
            "is_degraded": self.is_degraded(),
        }


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

_registry: Optional[ServiceHealthRegistry] = None


def get_health_registry() -> ServiceHealthRegistry:
    """Get or create the singleton health registry instance.

    Returns:
        The global ServiceHealthRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = ServiceHealthRegistry()
    return _registry


def reset_health_registry() -> None:
    """Reset the singleton health registry (for testing)."""
    global _registry
    _registry = None


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def get_service_health(service_name: str) -> Dict[str, Any]:
    """Get health status for a single service.

    Args:
        service_name: Name of the service.

    Returns:
        Dictionary with service health info.
    """
    registry = get_health_registry()
    return registry.get_service_health(service_name).to_dict()


async def async_get_health_summary() -> Dict[str, Any]:
    """Async wrapper for getting health summary.

    Returns:
        Dictionary with full health summary.
    """
    registry = get_health_registry()
    return registry.get_health_summary().to_dict()


def is_system_degraded() -> bool:
    """Check if the system is currently degraded.

    Returns:
        True if any service circuit is OPEN or HALF_OPEN.
    """
    return get_health_registry().is_degraded()


def get_system_health_score() -> float:
    """Get the overall system health score.

    Returns:
        Health score (0-100%).
    """
    return get_health_registry().get_health_score()
