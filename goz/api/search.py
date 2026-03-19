"""Search API client for Z.AI.

This module provides the SearchClient class for performing web searches
using the Z.AI WebSearchPrime API via direct HTTP.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from goz.api.errors import AuthError, ApiError, NetworkError, TimeoutError, ValidationError, ZaiError
from goz.config import Config, load_config


# Type definitions
RecencyFilter = Literal["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]


# Constants
VALID_RECENCY_FILTERS = ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]
DEFAULT_COUNT = None
RETRY_COUNT = 0
BASE_DELAY = 1.0

# Direct HTTP endpoint (uses coding/paas base URL)
CODING_PAAS_BASE = "https://api.z.ai/api/coding/paas/v4"
SEARCH_API_ENDPOINT = f"{CODING_PAAS_BASE}/web_search"


# Logger for search requests
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result from web search API.

    Attributes:
        rank: Result position (1-indexed)
        title: Page title
        url: Full URL
        summary: Content snippet
        source: Domain name (optional)
        date: Publish date if available (optional)
    """
    rank: int
    title: str
    url: str
    summary: str
    source: str | None = None
    date: str | None = None

    def __repr__(self) -> str:
        """Return readable string representation."""
        return f"SearchResult(rank={self.rank}, title={self.title!r}, url={self.url!r})"


def validate_search_params(
    query: str,
    count: int | None = None,
    recency_filter: RecencyFilter | None = None,
) -> None:
    """Validate search parameters.

    Args:
        query: Search query string
        count: Optional result count limit
        recency_filter: Optional recency filter value

    Raises:
        ValueError: If any parameter is invalid
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if count is not None and count <= 0:
        raise ValueError("Count must be a positive integer")

    if recency_filter is not None and recency_filter not in VALID_RECENCY_FILTERS:
        raise ValueError(
            f"Invalid recency filter: {recency_filter}. "
            f"Valid options: {', '.join(VALID_RECENCY_FILTERS)}"
        )


class SearchClient:
    """Web search client using Z.AI WebSearchPrime API.

    This client provides web search functionality with support for
    domain filtering, recency filtering, and result count limiting.
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialize SearchClient.

        Args:
            config: Optional config object. If not provided, loads from default location.
        """
        self.config = config or load_config()
        self.enable_logging = False

    async def _http_request(
        self,
        body: dict[str, Any],
    ) -> Any:
        """Make HTTP request to Search API.

        Args:
            body: Request body

        Returns:
            Parsed response data

        Raises:
            AuthError: For 401/403 responses
            ApiError: For other 4xx/5xx responses
            NetworkError: For connection failures
            TimeoutError: For request timeouts
        """
        headers = {
            "Authorization": f"Bearer {self.config.zai_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        timeout = self.config.timeout

        last_error = None

        for attempt in range(RETRY_COUNT + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if self.enable_logging:
                        logger.info(f"-> POST {SEARCH_API_ENDPOINT}")

                    response = await client.post(SEARCH_API_ENDPOINT, json=body, headers=headers)

                    if self.enable_logging:
                        logger.info(
                            f"<- {response.status_code} {len(response.content)} bytes"
                        )

                    # Handle successful response
                    if response.status_code == 200:
                        return response.json()

                    # Handle auth errors - don't retry
                    if response.status_code in (401, 403):
                        error_msg = self._parse_error_message(response)
                        raise AuthError(error_msg, statusCode=response.status_code)

                    # Handle other errors
                    error_msg = self._parse_error_message(response)
                    raise ApiError(error_msg, statusCode=response.status_code)

            except httpx.TimeoutException:
                timeout_ms = int(timeout * 1000)
                last_error = TimeoutError(timeoutMs=timeout_ms)
                if self.enable_logging:
                    logger.error(f"! {last_error.__class__.__name__}: {last_error}")

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_error = NetworkError(f"Network error: {e}")
                if self.enable_logging:
                    logger.error(f"! {last_error.__class__.__name__}: {last_error}")

            except (AuthError, ApiError):
                # Don't retry auth or API errors
                raise

            except Exception as e:
                last_error = e
                if self.enable_logging:
                    logger.error(f"! Unexpected error: {e}")

            # Retry with exponential backoff
            if attempt < RETRY_COUNT:
                delay = BASE_DELAY * (2 ** attempt)
                if self.enable_logging:
                    logger.info(f"Retrying in {delay}s... (attempt {attempt + 1}/{RETRY_COUNT})")
                await asyncio.sleep(delay)

        # All retries exhausted
        if last_error:
            raise last_error
        raise ZaiError("Unknown error occurred")

    def _parse_error_message(self, response: httpx.Response) -> str:
        """Parse error message from API response.

        Args:
            response: HTTP response object

        Returns:
            Error message string
        """
        try:
            data = response.json()
            if "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    if "message" in error:
                        return str(error["message"])
                    return str(error)
                return str(error)
            if "message" in data:
                return str(data["message"])
        except Exception:
            pass
        return response.text

    async def search(
        self,
        query: str,
        count: int | None = None,
        domain_filter: str | None = None,
        recency_filter: RecencyFilter | None = None,
    ) -> list[SearchResult]:
        """Perform web search.

        Args:
            query: Search query string (required)
            count: Maximum number of results to return (optional)
            domain_filter: Filter results to specific domain (optional)
            recency_filter: Filter results by recency (optional)

        Returns:
            List of SearchResult objects

        Raises:
            ValueError: If query is empty or parameters are invalid
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        validate_search_params(query, count, recency_filter)

        # Build request body
        body: dict[str, Any] = {
            "search_engine": "search-prime",
            "search_query": query,
        }

        if count is not None:
            body["count"] = count

        if domain_filter is not None:
            body["search_domain_filter"] = domain_filter

        if recency_filter is not None:
            body["search_recency_filter"] = recency_filter

        # Make HTTP request
        results_data = await self._http_request(body)

        # Parse results
        results = []
        if isinstance(results_data, list):
            for idx, item in enumerate(results_data):
                results.append(SearchResult(
                    rank=idx + 1,
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    summary=item.get("content", ""),
                    source=item.get("media"),
                    date=item.get("publish_date"),
                ))
        elif isinstance(results_data, dict):
            # Single result or error response
            if "link" in results_data:
                results.append(SearchResult(
                    rank=1,
                    title=results_data.get("title", ""),
                    url=results_data.get("link", ""),
                    summary=results_data.get("content", ""),
                    source=results_data.get("media"),
                    date=results_data.get("publish_date"),
                ))

        return results
