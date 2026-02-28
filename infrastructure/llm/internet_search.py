"""
Internet search module using DuckDuckGo.

Circuit breaker integration: when DuckDuckGo fails repeatedly, the search
gracefully degrades with a friendly message instead of blocking.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    register_circuit_breaker,
)
from infrastructure.resilience.retry_policy import RetryPolicy, get_retry_policy
from infrastructure.resilience.timeout_config import run_with_timeout

# Simple logger without custom handler, will use root logger's config
logger = logging.getLogger("internet-search")

# Circuit breaker config for DuckDuckGo: non-critical service
_DUCKDUCKGO_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,  # Trip after 3 failures
    reset_timeout_s=60.0,  # Wait 60s before probing
    half_open_max_calls=1,
    success_threshold=1,
)

# Error messages for graceful degradation
_CB_OPEN_MESSAGE = "Internet search is temporarily unavailable. Please try again later."
_CB_OPEN_ERROR = {"title": "Search Unavailable", "snippet": _CB_OPEN_MESSAGE, "link": ""}


def _log_duckduckgo_state_change(event: Any) -> None:
    """Log circuit breaker state transitions for DuckDuckGo."""
    logger.warning(
        "DuckDuckGo circuit breaker: %s -> %s (failures: %d)",
        event.previous_state.value,
        event.new_state.value,
        event.failure_count,
    )


class InternetSearch:
    """
    A class that handles internet searches using DuckDuckGo.
    This allows the agent to search for information on the web.

    Circuit breaker behavior:
    - When DuckDuckGo fails repeatedly (3 times), circuit trips to OPEN
    - While OPEN, returns graceful degradation message immediately
    - After 60s, circuit transitions to HALF_OPEN for probing
    - Successful probe closes the circuit
    """

    def __init__(self, max_results: int = 5):
        """Initialize the internet search tool."""
        self.max_results = max_results
        self._search = None
        self._search_detailed = None
        self._news_search = None
        self._last_query = ""
        self._last_results = ""

        # Register circuit breaker for DuckDuckGo
        self._cb: CircuitBreaker = register_circuit_breaker(
            "duckduckgo",
            config=_DUCKDUCKGO_CB_CONFIG,
            on_state_change=[_log_duckduckgo_state_change],
        )

        # Shared retry policy for DuckDuckGo
        self._retry_policy: RetryPolicy = get_retry_policy("duckduckgo")

        # Initialize search tools
        try:
            self._initialize_search_tools()
            logger.info("Initialized internet search tools with circuit breaker")
        except Exception as e:
            logger.error(f"Failed to initialize internet search tools: {e}")

    def _initialize_search_tools(self):
        """Initialize the search tools."""
        from langchain_community.tools import DuckDuckGoSearchResults, DuckDuckGoSearchRun
        from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

        # Basic search that returns a text summary
        self._search = DuckDuckGoSearchRun()

        # Detailed search that returns structured results with links
        self._search_detailed = DuckDuckGoSearchResults(output_format="list")

        # News search
        news_wrapper = DuckDuckGoSearchAPIWrapper(time="m", max_results=self.max_results)
        self._news_search = DuckDuckGoSearchResults(api_wrapper=news_wrapper, backend="news")

    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open (DuckDuckGo unavailable)."""
        return self._cb.state is CircuitBreakerState.OPEN

    async def _record_success(self) -> None:
        """Record a successful search to the circuit breaker."""
        if self._cb.state is CircuitBreakerState.HALF_OPEN:
            await self._cb.reset()
        elif self._cb._failure_count > 0:
            self._cb._failure_count = 0

    async def _record_failure(self, error: Optional[Exception] = None) -> None:
        """Record a failed search to the circuit breaker."""
        current_state = self._cb.state
        if current_state is CircuitBreakerState.CLOSED:
            self._cb._failure_count += 1
            if self._cb._failure_count >= _DUCKDUCKGO_CB_CONFIG.failure_threshold:
                await self._cb.trip()
                logger.warning(
                    "DuckDuckGo circuit tripped after %d failures",
                    self._cb._failure_count,
                )
        elif current_state is CircuitBreakerState.HALF_OPEN:
            await self._cb.trip()
            logger.warning("DuckDuckGo circuit re-tripped from half-open state")

    async def search(self, query: str, include_news: bool = True) -> Dict[str, Any]:
        """
        Comprehensive search combining basic information, detailed results, and news.

        Args:
            query: The search query
            include_news: Whether to include news results

        Returns:
            Dictionary containing general results, detailed results with links, and news
        """
        self._last_query = query

        # Circuit breaker: fast-fail if circuit is open
        if self._is_circuit_open():
            logger.debug("DuckDuckGo circuit is OPEN — returning degraded response")
            return self._get_degraded_results()

        if self._search is None:
            self._initialize_search_tools()

        results = {"general_info": "", "detailed_results": [], "news_articles": []}

        # Track if any search succeeded (to update CB state)
        any_success = False
        any_failure = False

        # Perform general search
        try:
            general_results = await run_with_timeout(
                asyncio.to_thread(self._search.invoke, query),
                service="search",
            )
            results["general_info"] = general_results
            any_success = True
        except Exception as e:
            logger.error(f"Error in general search: {e}")
            results["general_info"] = f"Error searching for general information: {str(e)}"
            any_failure = True

        # Perform detailed search
        try:
            detailed_results = await run_with_timeout(
                asyncio.to_thread(self._search_detailed.invoke, query),
                service="search",
            )
            results["detailed_results"] = detailed_results[:5]  # Limit to top 5 results
            any_success = True
        except Exception as e:
            logger.error(f"Error in detailed search: {e}")
            results["detailed_results"] = [
                {"title": "Error", "snippet": f"Error performing detailed search: {str(e)}", "link": ""}
            ]
            any_failure = True

        # Perform news search if requested
        if include_news:
            try:
                news_results = await run_with_timeout(
                    asyncio.to_thread(self._news_search.invoke, query),
                    service="search",
                )
                parsed_news = self._parse_news_results(news_results)
                results["news_articles"] = parsed_news[:3]  # Limit to top 3 news articles
                any_success = True
            except Exception as e:
                logger.error(f"Error in news search: {e}")
                results["news_articles"] = [
                    {"title": "Error", "snippet": f"Error searching for news: {str(e)}", "link": ""}
                ]
                any_failure = True

        # Update circuit breaker state based on overall result
        # If ALL searches failed, record failure; if any succeeded, record success
        if any_success and not any_failure:
            await self._record_success()
        elif any_failure and not any_success:
            await self._record_failure()
        # Mixed results: don't update CB state (partial success)

        # Store results for future reference
        self._last_results = str(results)
        return results

    def _get_degraded_results(self) -> Dict[str, Any]:
        """Return graceful degradation results when circuit is open."""
        return {
            "general_info": _CB_OPEN_MESSAGE,
            "detailed_results": [_CB_OPEN_ERROR],
            "news_articles": [_CB_OPEN_ERROR],
            "circuit_breaker_open": True,
        }

    def _parse_news_results(self, results: str) -> List[Dict[str, Any]]:
        """Parse news results from string format to structured data."""
        parsed_results = []
        if isinstance(results, str):
            # Split by commas that separate entries
            items = results.split("snippet:")
            for item in items[1:]:  # Skip the first empty item
                try:
                    parts = item.split("link:")
                    snippet = parts[0].strip().rstrip(",")

                    # Extract title
                    title_parts = snippet.split("title:")
                    if len(title_parts) > 1:
                        snippet = title_parts[0].strip().rstrip(",")
                        title = title_parts[1].split(",")[0].strip()
                    else:
                        title = "No title"

                    # Extract link
                    link = parts[1].split("date:")[0].strip().rstrip(",")

                    # Extract date if available
                    if "date:" in parts[1]:
                        date = parts[1].split("date:")[1].split("source:")[0].strip().rstrip(",")
                        source = parts[1].split("source:")[1].strip().split(",")[0]
                    else:
                        date = ""
                        source = ""

                    parsed_results.append(
                        {"title": title, "snippet": snippet, "link": link, "date": date, "source": source}
                    )
                except Exception as parse_error:
                    logger.error(f"Error parsing news result: {parse_error}")

        return parsed_results

    def format_results(self, results: Dict[str, Any]) -> str:
        """
        Format comprehensive search results into a human-readable string.

        Args:
            results: Dictionary containing search results

        Returns:
            Formatted search results as a string
        """
        # Check for circuit breaker degradation
        if results.get("circuit_breaker_open"):
            return _CB_OPEN_MESSAGE

        output = []

        # Add general information
        if results.get("general_info"):
            output.append("## General Information\n")
            output.append(results["general_info"])
            output.append("\n")

        # Add detailed results
        if results.get("detailed_results"):
            output.append("## Detailed Results\n")
            for i, result in enumerate(results["detailed_results"][:3], 1):
                output.append(f"{i}. **{result.get('title', 'No title')}**")
                output.append(f"   {result.get('snippet', 'No description')}")
                if result.get("link"):
                    output.append(f"   Link: {result['link']}")
                output.append("")
            output.append("\n")

        # Add news articles
        if results.get("news_articles"):
            output.append("## Recent News\n")
            for i, article in enumerate(results["news_articles"][:3], 1):
                output.append(f"{i}. **{article.get('title', 'No title')}**")
                output.append(f"   {article.get('snippet', 'No description')}")
                if article.get("date"):
                    output.append(f"   Published: {article['date']}")
                if article.get("source"):
                    output.append(f"   Source: {article['source']}")
                output.append("")

        return "\n".join(output)

    def get_last_results(self) -> str:
        """Get the results of the last search."""
        return self._last_results

    def health(self) -> Dict[str, Any]:
        """Health snapshot including circuit breaker state."""
        return {
            "initialized": self._search is not None,
            "last_query": self._last_query,
            "circuit_breaker": self._cb.snapshot() if self._cb else None,
        }
