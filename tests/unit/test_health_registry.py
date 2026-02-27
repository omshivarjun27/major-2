"""Unit tests for Service Health Registry.

Tests cover:
- ServiceHealthRegistry initialization
- Per-service health status queries
- Aggregated health summary
- Degradation detection
- Health score computation
- Singleton access
- Convenience functions
"""

import time
from unittest.mock import MagicMock, patch
import pytest


class TestServiceStatus:
    """Tests for ServiceStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        from infrastructure.resilience.health_registry import ServiceStatus

        assert ServiceStatus.HEALTHY.value == "healthy"
        assert ServiceStatus.DEGRADED.value == "degraded"
        assert ServiceStatus.UNHEALTHY.value == "unhealthy"
        assert ServiceStatus.UNKNOWN.value == "unknown"


class TestServiceHealth:
    """Tests for ServiceHealth dataclass."""

    def test_service_health_creation(self):
        """Test creating a service health record."""
        from infrastructure.resilience.health_registry import ServiceHealth, ServiceStatus

        health = ServiceHealth(
            service_name="deepgram",
            status=ServiceStatus.HEALTHY,
            circuit_state="closed",
            failure_count=0,
            success_count=10,
        )
        assert health.service_name == "deepgram"
        assert health.status == ServiceStatus.HEALTHY
        assert health.circuit_state == "closed"
        assert health.failure_count == 0
        assert health.success_count == 10

    def test_service_health_to_dict(self):
        """Test converting service health to dictionary."""
        from infrastructure.resilience.health_registry import ServiceHealth, ServiceStatus

        health = ServiceHealth(
            service_name="elevenlabs",
            status=ServiceStatus.DEGRADED,
            circuit_state="half_open",
            failure_count=2,
            success_count=5,
            last_failure_time=1234567890.0,
            uptime_percentage=95.5,
        )
        result = health.to_dict()

        assert result["service_name"] == "elevenlabs"
        assert result["status"] == "degraded"
        assert result["circuit_state"] == "half_open"
        assert result["failure_count"] == 2
        assert result["success_count"] == 5
        assert result["last_failure_time"] == 1234567890.0
        assert result["uptime_percentage"] == 95.5


class TestHealthSummary:
    """Tests for HealthSummary dataclass."""

    def test_health_summary_creation(self):
        """Test creating a health summary."""
        from infrastructure.resilience.health_registry import (
            HealthSummary,
            ServiceHealth,
            ServiceStatus,
        )

        summary = HealthSummary(
            timestamp=time.time(),
            overall_status=ServiceStatus.HEALTHY,
            health_score=100.0,
            total_services=3,
            healthy_count=3,
            degraded_count=0,
            unhealthy_count=0,
            services={},
        )
        assert summary.overall_status == ServiceStatus.HEALTHY
        assert summary.health_score == 100.0
        assert summary.total_services == 3

    def test_health_summary_to_dict(self):
        """Test converting health summary to dictionary."""
        from infrastructure.resilience.health_registry import (
            HealthSummary,
            ServiceHealth,
            ServiceStatus,
        )

        health = ServiceHealth(
            service_name="test",
            status=ServiceStatus.HEALTHY,
            circuit_state="closed",
            failure_count=0,
            success_count=0,
        )
        summary = HealthSummary(
            timestamp=1234567890.0,
            overall_status=ServiceStatus.HEALTHY,
            health_score=100.0,
            total_services=1,
            healthy_count=1,
            degraded_count=0,
            unhealthy_count=0,
            services={"test": health},
        )
        result = summary.to_dict()

        assert result["timestamp"] == 1234567890.0
        assert result["overall_status"] == "healthy"
        assert result["health_score"] == 100.0
        assert result["total_services"] == 1
        assert "test" in result["services"]


class TestServiceHealthRegistryInitialization:
    """Tests for ServiceHealthRegistry initialization."""

    def test_init_with_default_services(self):
        """Test initialization with default known services."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry

        registry = ServiceHealthRegistry()
        assert len(registry._known_services) == 6
        assert "deepgram" in registry._known_services
        assert "elevenlabs" in registry._known_services
        assert "ollama" in registry._known_services

    def test_init_with_custom_services(self):
        """Test initialization with custom services list."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry

        registry = ServiceHealthRegistry(known_services=["service_a", "service_b"])
        assert len(registry._known_services) == 2
        assert "service_a" in registry._known_services
        assert "service_b" in registry._known_services


class TestServiceHealthRegistryQueries:
    """Tests for service health queries."""

    def test_get_service_health_unknown_service(self):
        """Test getting health for unregistered service."""
        from infrastructure.resilience.health_registry import (
            ServiceHealthRegistry,
            ServiceStatus,
        )
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        registry = ServiceHealthRegistry()
        health = registry.get_service_health("unknown_service")

        assert health.service_name == "unknown_service"
        assert health.status == ServiceStatus.UNKNOWN
        assert health.circuit_state == "not_registered"

        clear_registry()

    def test_get_service_health_registered_service(self):
        """Test getting health for registered service."""
        from infrastructure.resilience.health_registry import (
            ServiceHealthRegistry,
            ServiceStatus,
        )
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )

        clear_registry()

        # Register a circuit breaker
        register_circuit_breaker("test_service")

        registry = ServiceHealthRegistry()
        health = registry.get_service_health("test_service")

        assert health.service_name == "test_service"
        assert health.status == ServiceStatus.HEALTHY
        assert health.circuit_state == "closed"

        clear_registry()

    def test_get_service_health_open_circuit(self):
        """Test getting health for service with open circuit."""
        from infrastructure.resilience.health_registry import (
            ServiceHealthRegistry,
            ServiceStatus,
        )
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )

        clear_registry()

        cb = register_circuit_breaker("unhealthy_service")

        async def trip_breaker():
            await cb.trip()

        import asyncio
        asyncio.get_event_loop().run_until_complete(trip_breaker())

        registry = ServiceHealthRegistry()
        health = registry.get_service_health("unhealthy_service")

        assert health.status == ServiceStatus.UNHEALTHY
        assert health.circuit_state == "open"

        clear_registry()


class TestServiceHealthRegistrySummary:
    """Tests for health summary generation."""

    def test_get_health_summary_no_services(self):
        """Test getting summary with no registered services."""
        from infrastructure.resilience.health_registry import (
            ServiceHealthRegistry,
            reset_health_registry,
        )
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()
        reset_health_registry()

        # Create registry with empty known_services and ensure no circuit breakers
        registry = ServiceHealthRegistry(known_services=[])
        summary = registry.get_health_summary()

        # With no known services and no registered breakers, should be empty
        assert summary.total_services == 0
        assert summary.health_score == 100.0

        clear_registry()
        reset_health_registry()

    def test_get_health_summary_all_healthy(self):
        """Test summary when all services are healthy."""
        from infrastructure.resilience.health_registry import (
            ServiceHealthRegistry,
            ServiceStatus,
        )
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )

        clear_registry()

        register_circuit_breaker("service_a")
        register_circuit_breaker("service_b")

        registry = ServiceHealthRegistry(known_services=["service_a", "service_b"])
        summary = registry.get_health_summary()

        assert summary.total_services == 2
        assert summary.healthy_count == 2
        assert summary.degraded_count == 0
        assert summary.unhealthy_count == 0
        assert summary.health_score == 100.0
        assert summary.overall_status == ServiceStatus.HEALTHY

        clear_registry()

    def test_get_health_summary_mixed_status(self):
        """Test summary with mixed service statuses."""
        from infrastructure.resilience.health_registry import (
            ServiceHealthRegistry,
            ServiceStatus,
        )
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        import asyncio

        clear_registry()

        cb_a = register_circuit_breaker("healthy_service")
        cb_b = register_circuit_breaker("unhealthy_service")

        async def setup():
            await cb_b.trip()

        asyncio.get_event_loop().run_until_complete(setup())

        registry = ServiceHealthRegistry(
            known_services=["healthy_service", "unhealthy_service"]
        )
        summary = registry.get_health_summary()

        assert summary.total_services == 2
        assert summary.healthy_count == 1
        assert summary.unhealthy_count == 1
        assert summary.health_score == 50.0  # 1 healthy / 2 total
        assert summary.overall_status == ServiceStatus.UNHEALTHY

        clear_registry()


class TestServiceHealthRegistryDegradation:
    """Tests for degradation detection."""

    def test_is_degraded_all_healthy(self):
        """Test is_degraded returns False when all healthy."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )

        clear_registry()

        register_circuit_breaker("service_a")
        register_circuit_breaker("service_b")

        registry = ServiceHealthRegistry(known_services=["service_a", "service_b"])
        assert registry.is_degraded() is False

        clear_registry()

    def test_is_degraded_with_open_circuit(self):
        """Test is_degraded returns True when circuit is open."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        import asyncio

        clear_registry()

        cb = register_circuit_breaker("failing_service")

        async def trip():
            await cb.trip()

        asyncio.get_event_loop().run_until_complete(trip())

        registry = ServiceHealthRegistry(known_services=["failing_service"])
        assert registry.is_degraded() is True

        clear_registry()

    def test_get_degraded_services(self):
        """Test getting list of degraded services."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        import asyncio

        clear_registry()

        cb_a = register_circuit_breaker("healthy_service")
        cb_b = register_circuit_breaker("unhealthy_service")

        async def setup():
            await cb_b.trip()

        asyncio.get_event_loop().run_until_complete(setup())

        registry = ServiceHealthRegistry()
        degraded = registry.get_degraded_services()

        assert "unhealthy_service" in degraded
        assert "healthy_service" not in degraded

        clear_registry()

    def test_get_healthy_services(self):
        """Test getting list of healthy services."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        import asyncio

        clear_registry()

        cb_a = register_circuit_breaker("healthy_service")
        cb_b = register_circuit_breaker("unhealthy_service")

        async def setup():
            await cb_b.trip()

        asyncio.get_event_loop().run_until_complete(setup())

        registry = ServiceHealthRegistry()
        healthy = registry.get_healthy_services()

        assert "healthy_service" in healthy
        assert "unhealthy_service" not in healthy

        clear_registry()


class TestServiceHealthRegistryHealthScore:
    """Tests for health score computation."""

    def test_health_score_all_healthy(self):
        """Test 100% score when all services healthy."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )

        clear_registry()

        register_circuit_breaker("a")
        register_circuit_breaker("b")
        register_circuit_breaker("c")

        registry = ServiceHealthRegistry(known_services=["a", "b", "c"])
        score = registry.get_health_score()

        assert score == 100.0

        clear_registry()

    def test_health_score_all_unhealthy(self):
        """Test 0% score when all services unhealthy."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        import asyncio

        clear_registry()

        cb_a = register_circuit_breaker("a")
        cb_b = register_circuit_breaker("b")

        async def setup():
            await cb_a.trip()
            await cb_b.trip()

        asyncio.get_event_loop().run_until_complete(setup())

        registry = ServiceHealthRegistry(known_services=["a", "b"])
        score = registry.get_health_score()

        assert score == 0.0

        clear_registry()

    def test_health_score_mixed(self):
        """Test partial score with mixed health."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import (
            clear_registry,
            register_circuit_breaker,
        )
        import asyncio

        clear_registry()

        cb_a = register_circuit_breaker("healthy")
        cb_b = register_circuit_breaker("unhealthy")

        async def setup():
            await cb_b.trip()

        asyncio.get_event_loop().run_until_complete(setup())

        registry = ServiceHealthRegistry(known_services=["healthy", "unhealthy"])
        score = registry.get_health_score()

        assert score == 50.0  # 1 healthy out of 2

        clear_registry()


class TestServiceHealthRegistryServiceManagement:
    """Tests for service list management."""

    def test_add_service(self):
        """Test adding a service to monitoring."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry

        registry = ServiceHealthRegistry(known_services=["a"])
        assert "b" not in registry._known_services

        registry.add_service("b")

        assert "b" in registry._known_services

    def test_add_service_duplicate(self):
        """Test adding duplicate service is idempotent."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry

        registry = ServiceHealthRegistry(known_services=["a"])
        registry.add_service("a")

        assert registry._known_services.count("a") == 1

    def test_remove_service(self):
        """Test removing a service from monitoring."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry

        registry = ServiceHealthRegistry(known_services=["a", "b"])
        registry.remove_service("b")

        assert "b" not in registry._known_services
        assert "a" in registry._known_services


class TestServiceHealthRegistryHealth:
    """Tests for registry health endpoint."""

    def test_health_snapshot(self):
        """Test registry health snapshot."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()

        registry = ServiceHealthRegistry(known_services=[])
        health = registry.health()

        assert "registry_uptime_s" in health
        assert "overall_status" in health
        assert "health_score" in health
        assert "total_services" in health
        assert "is_degraded" in health

        clear_registry()


class TestSingletonFunctions:
    """Tests for singleton access functions."""

    def test_get_health_registry_singleton(self):
        """Test singleton returns same instance."""
        from infrastructure.resilience.health_registry import (
            get_health_registry,
            reset_health_registry,
        )

        reset_health_registry()

        registry1 = get_health_registry()
        registry2 = get_health_registry()

        assert registry1 is registry2

        reset_health_registry()

    def test_reset_health_registry(self):
        """Test resetting creates new instance."""
        from infrastructure.resilience.health_registry import (
            get_health_registry,
            reset_health_registry,
        )

        reset_health_registry()

        registry1 = get_health_registry()
        reset_health_registry()
        registry2 = get_health_registry()

        assert registry1 is not registry2

        reset_health_registry()


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_service_health_function(self):
        """Test get_service_health convenience function."""
        from infrastructure.resilience.health_registry import (
            get_service_health,
            reset_health_registry,
        )
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()
        reset_health_registry()

        health = get_service_health("unknown")

        assert isinstance(health, dict)
        assert health["status"] == "unknown"

        clear_registry()
        reset_health_registry()

    def test_is_system_degraded_function(self):
        """Test is_system_degraded convenience function."""
        from infrastructure.resilience.health_registry import (
            is_system_degraded,
            reset_health_registry,
        )
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()
        reset_health_registry()

        assert is_system_degraded() is False

        clear_registry()
        reset_health_registry()

    def test_get_system_health_score_function(self):
        """Test get_system_health_score convenience function."""
        from infrastructure.resilience.health_registry import (
            get_system_health_score,
            reset_health_registry,
        )
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()
        reset_health_registry()

        score = get_system_health_score()

        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

        clear_registry()
        reset_health_registry()

    async def test_async_get_health_summary(self):
        """Test async health summary function."""
        from infrastructure.resilience.health_registry import (
            async_get_health_summary,
            reset_health_registry,
        )
        from infrastructure.resilience.circuit_breaker import clear_registry

        clear_registry()
        reset_health_registry()

        summary = await async_get_health_summary()

        assert isinstance(summary, dict)
        assert "timestamp" in summary
        assert "overall_status" in summary

        clear_registry()
        reset_health_registry()


class TestHealthScoreComputation:
    """Tests for health score edge cases."""

    def test_compute_health_score_internal(self):
        """Test internal health score computation."""
        from infrastructure.resilience.health_registry import ServiceHealthRegistry

        registry = ServiceHealthRegistry(known_services=[])

        # All healthy
        score = registry._compute_health_score(3, 0, 0, 3)
        assert score == 100.0

        # All degraded
        score = registry._compute_health_score(0, 3, 0, 3)
        assert score == 50.0

        # All unhealthy
        score = registry._compute_health_score(0, 0, 3, 3)
        assert score == 0.0

        # Mixed: 2 healthy, 1 degraded, 1 unhealthy
        score = registry._compute_health_score(2, 1, 1, 4)
        assert score == 62.5  # (2*1 + 1*0.5 + 1*0) / 4 * 100 = 62.5

    def test_compute_overall_status_internal(self):
        """Test internal overall status computation."""
        from infrastructure.resilience.health_registry import (
            ServiceHealthRegistry,
            ServiceStatus,
        )

        registry = ServiceHealthRegistry(known_services=[])

        # Any unhealthy = UNHEALTHY
        status = registry._compute_overall_status(2, 0, 1)
        assert status == ServiceStatus.UNHEALTHY

        # Any degraded (no unhealthy) = DEGRADED
        status = registry._compute_overall_status(2, 1, 0)
        assert status == ServiceStatus.DEGRADED

        # All healthy = HEALTHY
        status = registry._compute_overall_status(3, 0, 0)
        assert status == ServiceStatus.HEALTHY

        # None = UNKNOWN
        status = registry._compute_overall_status(0, 0, 0)
        assert status == ServiceStatus.UNKNOWN
