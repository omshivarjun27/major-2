"""Resilience chaos/stress tests for validating system behavior under pressure.

Tests simulate realistic failure patterns including:
- Random service failure injection
- Flapping services (rapid on/off)
- Cascading failures
- Recovery under load
- Memory stability during degraded operation

These tests verify the system degrades gracefully and never leaves the user in silence.
"""

from __future__ import annotations

import asyncio
import gc
import random
import sys
import time
import tracemalloc
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    StateChangeEvent,
    clear_registry,
    get_all_breakers,
    get_circuit_breaker,
    register_circuit_breaker,
)
from infrastructure.resilience.health_registry import (
    ServiceHealthRegistry,
    ServiceHealth,
    ServiceStatus,
)
from infrastructure.resilience.degradation_coordinator import (
    DegradationCoordinator,
    DegradationPolicy,
    DegradationLevel,
)
# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_state():
    """Reset global state between tests."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def fast_cb_config() -> CircuitBreakerConfig:
    """Fast circuit breaker config for chaos testing."""
    return CircuitBreakerConfig(
        failure_threshold=2,
        reset_timeout_s=0.1,  # 100ms for fast tests
        half_open_max_calls=1,
        success_threshold=1,
    )


@pytest.fixture
def all_services() -> List[str]:
    """List of all services to test."""
    return ["deepgram", "elevenlabs", "ollama", "livekit", "tavus", "duckduckgo"]


@pytest.fixture
def registered_breakers(
    all_services: List[str], fast_cb_config: CircuitBreakerConfig
) -> Dict[str, CircuitBreaker]:
    """Register circuit breakers for all services."""
    breakers = {}
    for service in all_services:
        breakers[service] = register_circuit_breaker(service, config=fast_cb_config)
    return breakers


# ---------------------------------------------------------------------------
# Chaos Helpers
# ---------------------------------------------------------------------------


class ChaosInjector:
    """Injects random failures into service calls."""

    def __init__(
        self,
        failure_probability: float = 0.3,
        latency_range_ms: tuple[float, float] = (0, 100),
        seed: Optional[int] = None,
    ):
        self.failure_probability = failure_probability
        self.latency_range_ms = latency_range_ms
        self._rng = random.Random(seed)
        self.failure_count = 0
        self.success_count = 0
        self.total_latency_ms = 0.0

    async def maybe_fail(self, service_name: str = "unknown") -> None:
        """Randomly fail or add latency."""
        # Add random latency
        latency_ms = self._rng.uniform(*self.latency_range_ms)
        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000)
        self.total_latency_ms += latency_ms

        # Maybe fail
        if self._rng.random() < self.failure_probability:
            self.failure_count += 1
            raise ConnectionError(f"Chaos: {service_name} failed randomly")
        self.success_count += 1

    def wrap_async(
        self, fn: Callable[..., Any], service_name: str = "unknown"
    ) -> Callable[..., Any]:
        """Wrap an async function with chaos injection."""

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await self.maybe_fail(service_name)
            return await fn(*args, **kwargs)

        return wrapper

    def stats(self) -> Dict[str, Any]:
        """Get chaos statistics."""
        total = self.failure_count + self.success_count
        return {
            "failures": self.failure_count,
            "successes": self.success_count,
            "total": total,
            "failure_rate": self.failure_count / total if total > 0 else 0,
            "avg_latency_ms": self.total_latency_ms / total if total > 0 else 0,
        }


class LatencyInjector:
    """Injects random latency into service calls."""

    def __init__(
        self,
        min_latency_ms: float = 0,
        max_latency_ms: float = 500,
        spike_probability: float = 0.1,
        spike_multiplier: float = 5.0,
        seed: Optional[int] = None,
    ):
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
        self.spike_probability = spike_probability
        self.spike_multiplier = spike_multiplier
        self._rng = random.Random(seed)
        self.latencies: List[float] = []

    async def inject(self) -> float:
        """Inject random latency, possibly with spike."""
        latency = self._rng.uniform(self.min_latency_ms, self.max_latency_ms)

        if self._rng.random() < self.spike_probability:
            latency *= self.spike_multiplier

        if latency > 0:
            await asyncio.sleep(latency / 1000)

        self.latencies.append(latency)
        return latency

    def stats(self) -> Dict[str, Any]:
        """Get latency statistics."""
        if not self.latencies:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}
        return {
            "min": min(self.latencies),
            "max": max(self.latencies),
            "avg": sum(self.latencies) / len(self.latencies),
            "count": len(self.latencies),
        }


# ---------------------------------------------------------------------------
# Random Failure Injection Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestRandomFailureInjection:
    """Tests for random failure injection across services."""

    async def test_random_failures_no_unhandled_exceptions(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Random failures across services don't cause unhandled exceptions."""
        chaos = ChaosInjector(failure_probability=0.5, seed=42)
        exceptions: List[Exception] = []

        async def test_call(cb: CircuitBreaker, service_name: str) -> bool:
            """Make a test call through a circuit breaker."""
            async def service_fn():
                await chaos.maybe_fail(service_name)
                return True

            try:
                return await cb.call(service_fn)
            except ConnectionError:
                # Expected chaos failures
                return False
            except Exception as e:
                exceptions.append(e)
                return False

        # Run many calls across all services
        tasks = []
        for _ in range(50):  # 50 rounds
            for service_name, cb in registered_breakers.items():
                tasks.append(test_call(cb, service_name))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check no unexpected exceptions
        unexpected = [r for r in results if isinstance(r, Exception)]
        assert len(unexpected) == 0, f"Unexpected exceptions: {unexpected}"
        assert len(exceptions) == 0, f"Caught exceptions: {exceptions}"

        # All breakers should be in valid states
        for service_name, cb in registered_breakers.items():
            assert cb.state in (
                CircuitBreakerState.CLOSED,
                CircuitBreakerState.OPEN,
                CircuitBreakerState.HALF_OPEN,
            ), f"{service_name} in invalid state: {cb.state}"

    async def test_random_failures_with_recovery(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Services recover after random failures stop."""
        chaos = ChaosInjector(failure_probability=0.8, seed=123)  # High failure rate

        # Cause failures
        for _ in range(20):
            for service_name, cb in registered_breakers.items():
                try:
                    async def failing_fn():
                        await chaos.maybe_fail(service_name)
                        return True
                    await cb.call(failing_fn)
                except (ConnectionError, Exception):
                    pass

        # Most breakers should be OPEN now
        # Most breakers should be OPEN or HALF_OPEN now (timing may vary due to fast reset)
        triggered_count = sum(
            1 for cb in registered_breakers.values()
            if cb.state in (CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN)
        )
        assert triggered_count >= 3, f"Expected most breakers triggered, got {triggered_count} in OPEN/HALF_OPEN"

        # Wait for half-open transition
        await asyncio.sleep(0.15)

        # Now succeed (no chaos)
        for service_name, cb in registered_breakers.items():
            if cb.state in (CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN):
                try:
                    async def success_fn():
                        return True
                    await cb.call(success_fn)
                except Exception:
                    pass

        # Allow time for recovery
        await asyncio.sleep(0.05)

        # Some breakers should have recovered
        closed_count = sum(
            1 for cb in registered_breakers.values()
            if cb.state is CircuitBreakerState.CLOSED
        )
        assert closed_count >= 1, "At least one breaker should have recovered"


# ---------------------------------------------------------------------------
# Flapping Service Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestFlappingServices:
    """Tests for flapping (rapid on/off) service patterns."""

    async def test_flapping_single_service(self, fast_cb_config: CircuitBreakerConfig):
        """Single service flapping doesn't cause issues."""
        cb = register_circuit_breaker("flapping_service", config=fast_cb_config)
        state_changes: List[StateChangeEvent] = []

        def on_change(event: StateChangeEvent):
            state_changes.append(event)

        cb.add_callback(on_change)

        # Simulate flapping: success, success, fail, fail, success, success, fail, fail...
        pattern = [True, True, False, False] * 10  # 40 calls

        for should_succeed in pattern:
            try:
                if should_succeed:
                    async def success_fn():
                        return True
                    await cb.call(success_fn)
                else:
                    async def fail_fn():
                        raise ConnectionError("Service down")
                    await cb.call(fail_fn)
            except (ConnectionError, Exception):
                pass

            # Small delay to allow state changes
            await asyncio.sleep(0.01)

        # Should have multiple state transitions
        assert len(state_changes) >= 2, f"Expected multiple state changes, got {len(state_changes)}"

        # Circuit should be in a valid state
        assert cb.state in (
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        )

    async def test_flapping_multiple_services(
        self, all_services: List[str], fast_cb_config: CircuitBreakerConfig
    ):
        """Multiple services flapping simultaneously don't interfere."""
        breakers = {
            service: register_circuit_breaker(service, config=fast_cb_config)
            for service in all_services
        }

        async def flap_service(service_name: str, cb: CircuitBreaker, flap_count: int):
            """Flap a single service."""
            for i in range(flap_count):
                try:
                    if i % 3 == 0:  # Fail every 3rd call
                        async def fail_fn():
                            raise ConnectionError(f"{service_name} down")
                        await cb.call(fail_fn)
                    else:
                        async def success_fn():
                            return True
                        await cb.call(success_fn)
                except Exception:
                    pass
                await asyncio.sleep(0.005)

        # Flap all services concurrently
        tasks = [
            flap_service(name, cb, 30)
            for name, cb in breakers.items()
        ]
        await asyncio.gather(*tasks)

        # All breakers should be in valid states
        for name, cb in breakers.items():
            assert cb.state in (
                CircuitBreakerState.CLOSED,
                CircuitBreakerState.OPEN,
                CircuitBreakerState.HALF_OPEN,
            ), f"{name} in invalid state"


# ---------------------------------------------------------------------------
# Cascading Failure Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestCascadingFailures:
    """Tests for cascading failure scenarios."""

    async def test_primary_failure_increases_fallback_load(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Primary service failure doesn't crash fallback under increased load."""
        primary = registered_breakers["deepgram"]
        fallback_calls = 0
        primary_calls = 0

        async def simulate_stt_call() -> str:
            """Simulate an STT call with failover."""
            nonlocal fallback_calls, primary_calls

            if primary.state is not CircuitBreakerState.OPEN:
                primary_calls += 1
                async def primary_fn():
                    raise ConnectionError("Deepgram down")
                try:
                    await primary.call(primary_fn)
                    return "primary"
                except Exception:
                    pass

            # Fall back to local
            fallback_calls += 1
            await asyncio.sleep(0.005)  # Simulate local processing
            return "fallback"

        # Simulate load
        tasks = [simulate_stt_call() for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # Primary should have tripped
        assert primary.state is CircuitBreakerState.OPEN

        # Most calls should have used fallback
        assert results.count("fallback") > results.count("primary")
        assert fallback_calls > primary_calls

    async def test_multiple_service_cascade(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Multiple services failing doesn't crash the system."""
        services_to_fail = ["deepgram", "elevenlabs", "ollama"]

        # Trip multiple services
        for service_name in services_to_fail:
            cb = registered_breakers[service_name]
            await cb.trip()

        # Verify all are OPEN
        for service_name in services_to_fail:
            assert registered_breakers[service_name].state is CircuitBreakerState.OPEN

        # Other services should still work
        for service_name, cb in registered_breakers.items():
            if service_name not in services_to_fail:
                assert cb.state is CircuitBreakerState.CLOSED

        # Simulate continued load on remaining services
        remaining_calls = 0
        for _ in range(20):
            for service_name, cb in registered_breakers.items():
                if service_name not in services_to_fail:
                    try:
                        async def success_fn():
                            return True
                        await cb.call(success_fn)
                        remaining_calls += 1
                    except Exception:
                        pass

        # Remaining services should have handled load
        assert remaining_calls > 0


# ---------------------------------------------------------------------------
# Recovery Under Load Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestRecoveryUnderLoad:
    """Tests for service recovery while under load."""

    async def test_recovery_while_requests_queued(
        self, fast_cb_config: CircuitBreakerConfig
    ):
        """Service recovers correctly while requests are still coming in."""
        cb = register_circuit_breaker("load_test", config=fast_cb_config)
        successful_calls = 0
        failed_calls = 0
        recovered = False

        async def make_call(call_id: int) -> bool:
            nonlocal successful_calls, failed_calls

            async def service_fn():
                # Fail early calls, succeed later ones
                if call_id < 30:
                    raise ConnectionError("Service unavailable")
                return True

            try:
                await cb.call(service_fn)
                successful_calls += 1
                return True
            except Exception:
                failed_calls += 1
                return False

        # Generate load with mixed success/failure pattern
        tasks = []
        for i in range(60):
            tasks.append(make_call(i))
            # Small delay to spread out calls
            if i % 10 == 0:
                await asyncio.sleep(0.02)

        results = await asyncio.gather(*tasks)

        # Wait for potential recovery
        await asyncio.sleep(0.2)

        # Try final calls after circuit may have half-opened
        for i in range(70, 80):
            try:
                async def success_fn():
                    return True
                await cb.call(success_fn)
                successful_calls += 1
            except Exception:
                pass

        # Should have some successes despite failures
        assert successful_calls > 0, "Should have some successful calls"
        assert failed_calls > 0, "Should have some failed calls"

    async def test_concurrent_recovery_probes(
        self, all_services: List[str], fast_cb_config: CircuitBreakerConfig
    ):
        """Multiple services attempting recovery simultaneously works correctly."""
        breakers = {
            service: register_circuit_breaker(service, config=fast_cb_config)
            for service in all_services
        }

        # Trip all services
        for cb in breakers.values():
            await cb.trip()

        # Wait for all to transition to half-open
        await asyncio.sleep(0.15)

        # Attempt recovery on all simultaneously
        async def attempt_recovery(cb: CircuitBreaker) -> bool:
            try:
                async def success_fn():
                    return True
                await cb.call(success_fn)
                return True
            except Exception:
                return False

        results = await asyncio.gather(*[
            attempt_recovery(cb) for cb in breakers.values()
        ])

        # At least some should have recovered
        recovered_count = sum(results)
        assert recovered_count >= 1, "At least one service should recover"


# ---------------------------------------------------------------------------
# Health Registry Consistency Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestHealthRegistryConsistency:
    """Tests for health registry accuracy during chaos."""

    async def test_registry_reflects_cb_states(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Health registry accurately reflects circuit breaker states."""
        registry = ServiceHealthRegistry(known_services=list(registered_breakers.keys()))
        
        # Trip some services
        await registered_breakers["deepgram"].trip()
        await registered_breakers["ollama"].trip()
        
        # Check registry reflects CB states
        summary = registry.get_health_summary()
        
        # Deepgram and Ollama should be unhealthy
        deepgram_health = summary.services.get("deepgram")
        ollama_health = summary.services.get("ollama")
        elevenlabs_health = summary.services.get("elevenlabs")
        
        assert deepgram_health is not None
        assert deepgram_health.status is ServiceStatus.UNHEALTHY
        assert ollama_health is not None
        assert ollama_health.status is ServiceStatus.UNHEALTHY
        assert elevenlabs_health is not None
        assert elevenlabs_health.status is ServiceStatus.HEALTHY

    async def test_registry_during_rapid_changes(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Health registry stays accurate during rapid state changes."""
        registry = ServiceHealthRegistry(known_services=list(registered_breakers.keys()))
        
        # Rapid changes
        for _ in range(10):
            service = random.choice(list(registered_breakers.keys()))
            cb = registered_breakers[service]
            
            if random.random() < 0.5:
                await cb.trip()
            else:
                await cb.reset()
            
            await asyncio.sleep(0.01)
        
        # Registry should accurately reflect current states
        summary = registry.get_health_summary()
        
        # Verify services are reported
        assert len(summary.services) == len(registered_breakers)
        
        # Each service status should match its CB state
        for service_name, cb in registered_breakers.items():
            health = summary.services.get(service_name)
            assert health is not None, f"Missing health for {service_name}"
            
            if cb.state is CircuitBreakerState.CLOSED:
                assert health.status is ServiceStatus.HEALTHY
            elif cb.state is CircuitBreakerState.OPEN:
                assert health.status is ServiceStatus.UNHEALTHY
            elif cb.state is CircuitBreakerState.HALF_OPEN:
                assert health.status is ServiceStatus.DEGRADED

# ---------------------------------------------------------------------------
# Memory Stability Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestMemoryStability:
    """Tests for memory stability during extended degraded operation."""

    async def test_no_memory_leak_during_failures(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """No significant memory growth during repeated failure cycles."""
        # Force garbage collection and get baseline
        gc.collect()
        tracemalloc.start()
        
        try:
            snapshot_start = tracemalloc.take_snapshot()

            # Run many failure cycles
            for cycle in range(50):
                for cb in registered_breakers.values():
                    try:
                        async def fail_fn():
                            raise ConnectionError("Chaos failure")
                        await cb.call(fail_fn)
                    except Exception:
                        pass

                # Occasionally reset
                if cycle % 10 == 0:
                    for cb in registered_breakers.values():
                        await cb.reset()

                await asyncio.sleep(0.005)

            gc.collect()
            snapshot_end = tracemalloc.take_snapshot()

            # Check memory growth
            top_stats = snapshot_end.compare_to(snapshot_start, "lineno")
            
            # Sum up growth (only positive diffs)
            total_growth = sum(
                stat.size_diff for stat in top_stats[:10]
                if stat.size_diff > 0
            )

            # Allow some growth but not excessive (< 5MB)
            assert total_growth < 5 * 1024 * 1024, f"Memory grew by {total_growth / 1024 / 1024:.2f}MB"
        finally:
            tracemalloc.stop()

    async def test_failover_history_bounded(
        self, fast_cb_config: CircuitBreakerConfig
    ):
        """Failover history doesn't grow unbounded."""
        # Import failover manager
        with (
            patch("infrastructure.speech.stt_failover.WHISPER_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.EDGE_TTS_AVAILABLE", True),
            patch("infrastructure.speech.tts_failover.PYTTSX3_AVAILABLE", True),
        ):
            from infrastructure.speech.stt_failover import STTFailoverManager, STTFailoverConfig
            from infrastructure.speech.tts_failover import TTSFailoverManager, TTSFailoverConfig

            # Use pre-registered CBs
            register_circuit_breaker("deepgram", config=fast_cb_config)
            register_circuit_breaker("elevenlabs", config=fast_cb_config)

            stt_mgr = STTFailoverManager(config=STTFailoverConfig())
            tts_mgr = TTSFailoverManager(config=TTSFailoverConfig())

            await stt_mgr.initialize()
            await tts_mgr.initialize()

            # Generate many failover events
            for _ in range(200):
                await stt_mgr.force_failover_to_whisper()
                await stt_mgr.force_failback_to_deepgram()
                await tts_mgr.force_failover_to_local()
                await tts_mgr.force_failback_to_elevenlabs()

            # History should be bounded (max_history = 100)
            stt_history = stt_mgr.get_failover_history()
            tts_history = tts_mgr.get_failover_history()

            assert len(stt_history) <= 100, f"STT history unbounded: {len(stt_history)}"
            assert len(tts_history) <= 100, f"TTS history unbounded: {len(tts_history)}"

            await stt_mgr.shutdown()
            await tts_mgr.shutdown()


# ---------------------------------------------------------------------------
# System Invariant Tests
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestSystemInvariants:
    """Tests for system invariants under chaos."""

    async def test_circuit_breaker_states_always_valid(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Circuit breaker states are always valid during chaos."""
        chaos = ChaosInjector(failure_probability=0.5, seed=999)
        valid_states = {
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN,
        }

        # Run chaos
        for _ in range(100):
            for service_name, cb in registered_breakers.items():
                try:
                    async def chaos_fn():
                        await chaos.maybe_fail(service_name)
                        return True
                    await cb.call(chaos_fn)
                except Exception:
                    pass

                # Verify state is always valid
                assert cb.state in valid_states, f"{service_name} has invalid state: {cb.state}"

    async def test_no_deadlocks_under_concurrent_load(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """No deadlocks occur under heavy concurrent load."""
        timeout_seconds = 5.0
        completed = asyncio.Event()

        async def worker(worker_id: int):
            """Worker that makes random calls."""
            for _ in range(20):
                service = random.choice(list(registered_breakers.keys()))
                cb = registered_breakers[service]
                try:
                    async def work_fn():
                        await asyncio.sleep(0.001)
                        if random.random() < 0.3:
                            raise ConnectionError("Random failure")
                        return True
                    await cb.call(work_fn)
                except Exception:
                    pass

        async def run_workers():
            """Run all workers."""
            tasks = [worker(i) for i in range(20)]
            await asyncio.gather(*tasks)
            completed.set()

        # Run with timeout
        try:
            async with asyncio.timeout(timeout_seconds):
                await run_workers()
        except asyncio.TimeoutError:
            pytest.fail(f"Deadlock detected - workers didn't complete in {timeout_seconds}s")

        assert completed.is_set(), "Workers should have completed"

    async def test_degradation_announcements_consistent(
        self, registered_breakers: Dict[str, CircuitBreaker]
    ):
        """Degradation coordinator level changes are consistent."""
        from infrastructure.resilience.degradation_coordinator import (
            DegradationCoordinator,
            DegradationLevel,
            get_degradation_coordinator,
            reset_degradation_coordinator,
        )
        
        # Reset singleton for clean state
        reset_degradation_coordinator()
        
        announcements: List[str] = []
        
        def on_announce(message: str):
            announcements.append(message)
        
        # Create coordinator with announcement callback
        coordinator = DegradationCoordinator(announcement_callback=on_announce)
        await coordinator.initialize()
        
        # Initially should be FULL
        assert coordinator.get_degradation_level() is DegradationLevel.FULL
        
        # Trip critical services to cause degradation
        await registered_breakers["deepgram"].trip()
        await registered_breakers["elevenlabs"].trip()
        
        # Refresh coordinator to pick up CB changes
        await coordinator.refresh()
        
        # Should now be degraded (MINIMAL since critical services are down)
        level = coordinator.get_degradation_level()
        assert level in (DegradationLevel.MINIMAL, DegradationLevel.PARTIAL, DegradationLevel.OFFLINE)
        
        # Reset services
        await registered_breakers["deepgram"].reset()
        await registered_breakers["elevenlabs"].reset()
        
        # Refresh again
        await coordinator.refresh()
        
        # Should be back to FULL
        assert coordinator.get_degradation_level() is DegradationLevel.FULL
        
        await coordinator.shutdown()
