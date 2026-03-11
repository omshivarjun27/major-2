"""Tests for DuckDuckGo circuit breaker integration.

Validates that InternetSearch correctly wires the circuit breaker for
graceful degradation when DuckDuckGo is unavailable.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.llm.internet_search import (
    _CB_OPEN_MESSAGE,
    InternetSearch,
)
from infrastructure.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
    clear_registry,
    get_circuit_breaker,
    register_circuit_breaker,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the global circuit breaker registry between tests."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def mock_search_tools():
    """Mock langchain search tools to avoid real HTTP calls."""
    with patch(
        "infrastructure.llm.internet_search.InternetSearch._initialize_search_tools"
    ):
        yield


# ---------------------------------------------------------------------------
# Tests — Initialization
# ---------------------------------------------------------------------------


class TestDuckDuckGoCircuitBreakerInit:
    """Circuit breaker registration on search init."""

    async def test_cb_registered_on_init(self, mock_search_tools) -> None:
        """Circuit breaker is registered when InternetSearch is created."""
        search = InternetSearch()
        assert search._cb is not None
        cb = get_circuit_breaker("duckduckgo")
        assert cb is not None
        assert cb.state is CircuitBreakerState.CLOSED

    async def test_cb_config_values(self, mock_search_tools) -> None:
        """Circuit breaker uses correct thresholds."""
        search = InternetSearch()
        assert search._cb.config.failure_threshold == 3
        assert search._cb.config.reset_timeout_s == 60.0


# ---------------------------------------------------------------------------
# Tests — Search with circuit breaker
# ---------------------------------------------------------------------------


class TestSearchWithCircuitBreaker:
    """Search method respects circuit breaker state."""

    async def test_search_open_circuit_returns_degraded(
        self, mock_search_tools
    ) -> None:
        """Search returns degraded response when circuit is open."""
        search = InternetSearch()
        await search._cb.trip()
        assert search._is_circuit_open() is True

        results = await search.search("test query")

        assert results["circuit_breaker_open"] is True
        assert _CB_OPEN_MESSAGE in results["general_info"]

    async def test_search_success_records_success(self, mock_search_tools) -> None:
        """Successful search resets failure count."""
        search = InternetSearch()
        search._cb._failure_count = 2

        # Mock the search tools
        search._search = MagicMock()
        search._search.invoke = MagicMock(return_value="Search results")
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(return_value=[{"title": "Test", "snippet": "Test", "link": "http://test.com"}])
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(return_value="")

        results = await search.search("test query", include_news=False)

        assert "general_info" in results
        assert search._cb._failure_count == 0

    async def test_search_all_failures_records_failure(
        self, mock_search_tools
    ) -> None:
        """All search failures increment failure count."""
        search = InternetSearch()
        assert search._cb._failure_count == 0

        # Mock all searches to fail
        search._search = MagicMock()
        search._search.invoke = MagicMock(side_effect=Exception("Search error"))
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(side_effect=Exception("Search error"))
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(side_effect=Exception("Search error"))

        await search.search("test query")

        assert search._cb._failure_count == 1

    async def test_search_repeated_failures_trip_circuit(
        self, mock_search_tools
    ) -> None:
        """Repeated search failures trip the circuit."""
        search = InternetSearch()

        # Mock all searches to fail
        search._search = MagicMock()
        search._search.invoke = MagicMock(side_effect=Exception("Search error"))
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(side_effect=Exception("Search error"))
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(side_effect=Exception("Search error"))

        # Three failures should trip the circuit
        await search.search("test 1")
        await search.search("test 2")
        await search.search("test 3")

        assert search._cb.state is CircuitBreakerState.OPEN

    async def test_partial_success_does_not_update_cb(
        self, mock_search_tools
    ) -> None:
        """Mixed success/failure does not update circuit breaker."""
        search = InternetSearch()
        search._cb._failure_count = 1

        # Mock partial success: general succeeds, detailed fails
        search._search = MagicMock()
        search._search.invoke = MagicMock(return_value="Success")
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(side_effect=Exception("Error"))
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(side_effect=Exception("Error"))

        await search.search("test query")

        # Failure count should not change on mixed results
        assert search._cb._failure_count == 1


# ---------------------------------------------------------------------------
# Tests — Degraded results
# ---------------------------------------------------------------------------


class TestDegradedResults:
    """Graceful degradation when circuit is open."""

    async def test_degraded_results_structure(self, mock_search_tools) -> None:
        """Degraded results have expected structure."""
        search = InternetSearch()
        results = search._get_degraded_results()

        assert "general_info" in results
        assert "detailed_results" in results
        assert "news_articles" in results
        assert results["circuit_breaker_open"] is True
        assert _CB_OPEN_MESSAGE in results["general_info"]

    async def test_format_results_shows_degraded_message(
        self, mock_search_tools
    ) -> None:
        """format_results shows degraded message when CB is open."""
        search = InternetSearch()
        results = search._get_degraded_results()
        formatted = search.format_results(results)

        assert _CB_OPEN_MESSAGE in formatted


# ---------------------------------------------------------------------------
# Tests — Health endpoint
# ---------------------------------------------------------------------------


class TestHealthWithCircuitBreaker:
    """Health endpoint includes circuit breaker state."""

    async def test_health_includes_cb_snapshot(self, mock_search_tools) -> None:
        """Health includes circuit breaker snapshot."""
        search = InternetSearch()
        health = search.health()

        assert "circuit_breaker" in health
        assert health["circuit_breaker"] is not None
        assert health["circuit_breaker"]["state"] == "closed"
        assert health["circuit_breaker"]["service"] == "duckduckgo"

    async def test_health_reflects_open_state(self, mock_search_tools) -> None:
        """Health reflects open circuit state."""
        search = InternetSearch()
        await search._cb.trip()

        health = search.health()
        assert health["circuit_breaker"]["state"] == "open"


# ---------------------------------------------------------------------------
# Tests — Circuit recovery
# ---------------------------------------------------------------------------


class TestCircuitRecovery:
    """Circuit breaker recovery behavior."""

    async def test_circuit_recovers_after_timeout(self, mock_search_tools) -> None:
        """Circuit transitions to half-open after reset timeout."""
        # Clear and register with fast timeout
        clear_registry()
        fast_cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_s=0.1,  # 100ms for testing
        )
        cb = register_circuit_breaker("duckduckgo", config=fast_cb_config)

        search = InternetSearch()
        search._cb = cb

        # Trip the circuit
        await search._cb.trip()
        assert search._cb.state is CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)
        assert search._cb.state is CircuitBreakerState.HALF_OPEN

    async def test_success_in_half_open_closes_circuit(
        self, mock_search_tools
    ) -> None:
        """Success while half-open closes the circuit."""
        clear_registry()
        fast_cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            reset_timeout_s=0.1,
        )
        cb = register_circuit_breaker("duckduckgo", config=fast_cb_config)

        search = InternetSearch()
        search._cb = cb

        # Trip and wait for half-open
        await search._cb.trip()
        await asyncio.sleep(0.15)
        assert search._cb.state is CircuitBreakerState.HALF_OPEN

        # Mock successful search
        search._search = MagicMock()
        search._search.invoke = MagicMock(return_value="Success")
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(return_value=[])
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(return_value="")

        await search.search("test", include_news=False)

        assert search._cb.state is CircuitBreakerState.CLOSED


# ---------------------------------------------------------------------------
# Tests — Individual search protection
# ---------------------------------------------------------------------------


class TestIndividualSearchProtection:
    """Each search type is individually protected."""

    async def test_general_search_failure_isolated(self, mock_search_tools) -> None:
        """General search failure doesn't block other searches."""
        search = InternetSearch()

        search._search = MagicMock()
        search._search.invoke = MagicMock(side_effect=Exception("General error"))
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(return_value=[{"title": "OK"}])
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(return_value="")

        results = await search.search("test")

        assert "Error" in results["general_info"]
        assert results["detailed_results"] == [{"title": "OK"}]

    async def test_detailed_search_failure_isolated(self, mock_search_tools) -> None:
        """Detailed search failure doesn't block other searches."""
        search = InternetSearch()

        search._search = MagicMock()
        search._search.invoke = MagicMock(return_value="General OK")
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(side_effect=Exception("Detailed error"))
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(return_value="")

        results = await search.search("test", include_news=False)

        assert results["general_info"] == "General OK"
        assert "Error" in results["detailed_results"][0]["snippet"]

    async def test_news_search_failure_isolated(self, mock_search_tools) -> None:
        """News search failure doesn't block other searches."""
        search = InternetSearch()

        search._search = MagicMock()
        search._search.invoke = MagicMock(return_value="General OK")
        search._search_detailed = MagicMock()
        search._search_detailed.invoke = MagicMock(return_value=[{"title": "Detailed OK"}])
        search._news_search = MagicMock()
        search._news_search.invoke = MagicMock(side_effect=Exception("News error"))

        results = await search.search("test")

        assert results["general_info"] == "General OK"
        assert results["detailed_results"] == [{"title": "Detailed OK"}]
        assert "Error" in results["news_articles"][0]["snippet"]
