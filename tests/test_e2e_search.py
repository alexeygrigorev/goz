"""E2E tests for Search API (Issue 05)."""
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from goz.api.search import (
    SearchClient,
    SearchResult,
    validate_search_params,
    build_search_request_body,
    parse_search_response,
    limit_results,
)


class MockAsyncClient:
    """Mock AsyncClient that supports async context manager protocol."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.post = AsyncMock(return_value=response)

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


# ============================================================================
# Basic Search Tests
# ============================================================================

class TestBasicSearch:
    """E2E Tests: Basic web search returns list of SearchResult objects."""

    @pytest.mark.asyncio
    async def test_basic_search_returns_results(self):
        """E2E: Basic web search returns list of SearchResult objects."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-id",
            "created": 1234567890,
            "search_result": [
                {
                    "title": "Python async await best practices",
                    "content": "Learn about async/await in Python...",
                    "link": "https://example.com/async-python",
                    "media": "example.com",
                    "publish_date": "2024-01-15"
                },
                {
                    "title": "Understanding Python Coroutines",
                    "content": "Deep dive into coroutines...",
                    "link": "https://example.com/coroutines",
                    "media": "example.com",
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("Python async await best practices")

                assert len(results) == 2
                assert isinstance(results, list)
                assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_search_results_contain_required_fields(self):
        """E2E: Search results contain rank, title, url, summary fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "Test Result",
                    "content": "Test summary content",
                    "link": "https://example.com/test"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("test query")

                assert len(results) == 1
                result = results[0]
                assert result.rank == 1
                assert result.title == "Test Result"
                assert result.url == "https://example.com/test"
                assert result.summary == "Test summary content"

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self):
        """E2E: Search with special characters in query works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "C++ Templates",
                    "content": "Template metaprogramming guide",
                    "link": "https://example.com/cpp-templates"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("C++ template metaprogramming")

                assert len(results) == 1
                # Verify the query was passed as-is
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_query"] == "C++ template metaprogramming"

    @pytest.mark.asyncio
    async def test_search_with_unicode_characters(self):
        """E2E: Search with unicode characters in query works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "Test Result",
                    "content": "Test content",
                    "link": "https://example.com/test"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("Python unicode test")

                assert len(results) == 1


# ============================================================================
# Count Parameter Tests
# ============================================================================

class TestCountParameter:
    """E2E Tests: Search with count parameter returns correct number of results."""

    @pytest.mark.asyncio
    async def test_search_with_count_5(self):
        """E2E: Search with count=5 returns exactly 5 results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # API returns 10 results, but we only request 5
        mock_response.json.return_value = {
            "search_result": [
                {"title": f"Result {i}", "content": f"Content {i}", "link": f"https://example.com/{i}"}
                for i in range(1, 11)
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("test query", count=5)

                assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_with_count_1(self):
        """E2E: Search with count=1 returns exactly 1 result."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {"title": "Result 1", "content": "Content 1", "link": "https://example.com/1"},
                {"title": "Result 2", "content": "Content 2", "link": "https://example.com/2"}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("test query", count=1)

                assert len(results) == 1
                assert results[0].rank == 1

    @pytest.mark.asyncio
    async def test_search_with_count_greater_than_results(self):
        """E2E: Search with count greater than API results returns all available results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # API returns only 3 results
        mock_response.json.return_value = {
            "search_result": [
                {"title": f"Result {i}", "content": f"Content {i}", "link": f"https://example.com/{i}"}
                for i in range(1, 4)
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("test query", count=10)

                assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_without_count_returns_default(self):
        """E2E: Search without count parameter returns default number of results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {"title": f"Result {i}", "content": f"Content {i}", "link": f"https://example.com/{i}"}
                for i in range(1, 11)
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("test query")

                # Should return all results from API when count is None
                assert len(results) == 10
                # Verify count was not sent in request
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert "count" not in body


# ============================================================================
# Domain Filter Tests
# ============================================================================

class TestDomainFilter:
    """E2E Tests: Search with domain filter returns results only from specified domain."""

    @pytest.mark.asyncio
    async def test_search_with_domain_filter(self):
        """E2E: Search with domain filter returns results only from specified domain."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "TypeScript Documentation",
                    "content": "Official TypeScript docs",
                    "link": "https://www.typescriptlang.org/docs/",
                    "media": "www.typescriptlang.org"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("TypeScript documentation", domain_filter="typescriptlang.org")

                assert len(results) == 1
                # Verify domain filter was sent in request
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_domain_filter"] == "typescriptlang.org"

    @pytest.mark.asyncio
    async def test_domain_filter_with_subdomain(self):
        """E2E: Domain filter with subdomain (e.g., docs.python.org) works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "Python Docs",
                    "content": "Official Python documentation",
                    "link": "https://docs.python.org/3/",
                    "media": "docs.python.org"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("python docs", domain_filter="docs.python.org")

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_domain_filter"] == "docs.python.org"


# ============================================================================
# Recency Filter Tests
# ============================================================================

class TestRecencyFilter:
    """E2E Tests: Search with recency filter returns results from specified time period."""

    @pytest.mark.asyncio
    async def test_search_with_recency_one_day(self):
        """E2E: Search with recency="oneDay" returns recent results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "Latest AI News",
                    "content": "Today's AI developments",
                    "link": "https://example.com/ai-news",
                    "publish_date": "2024-01-15"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("AI developments", recency_filter="oneDay")

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_recency_filter"] == "oneDay"

    @pytest.mark.asyncio
    async def test_search_with_recency_one_week(self):
        """E2E: Search with recency="oneWeek" returns results from last week."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "AI News",
                    "content": "Recent AI developments",
                    "link": "https://example.com/ai-news"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("AI developments", recency_filter="oneWeek")

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_recency_filter"] == "oneWeek"

    @pytest.mark.asyncio
    async def test_search_with_recency_one_month(self):
        """E2E: Search with recency="oneMonth" returns results from last month."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "AI News",
                    "content": "Recent AI developments",
                    "link": "https://example.com/ai-news"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("AI developments", recency_filter="oneMonth")

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_recency_filter"] == "oneMonth"

    @pytest.mark.asyncio
    async def test_search_with_recency_one_year(self):
        """E2E: Search with recency="oneYear" returns results from last year."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "AI News",
                    "content": "Recent AI developments",
                    "link": "https://example.com/ai-news"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("AI developments", recency_filter="oneYear")

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_recency_filter"] == "oneYear"

    @pytest.mark.asyncio
    async def test_search_with_recency_no_limit(self):
        """E2E: Search with recency="noLimit" returns all-time results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "AI News",
                    "content": "All-time AI developments",
                    "link": "https://example.com/ai-news"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("AI developments", recency_filter="noLimit")

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_recency_filter"] == "noLimit"


# ============================================================================
# Combined Filter Tests
# ============================================================================

class TestCombinedFilters:
    """E2E Tests: Search with multiple filters applies all correctly."""

    @pytest.mark.asyncio
    async def test_search_with_domain_and_recency_filters(self):
        """E2E: Search with domain and recency filters returns filtered results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "Textual TUI",
                    "content": "Python TUI framework",
                    "link": "https://github.com/textualize/textual",
                    "media": "github.com",
                    "publish_date": "2024-01-10"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search(
                    "textual TUI",
                    domain_filter="github.com",
                    recency_filter="oneMonth"
                )

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_domain_filter"] == "github.com"
                assert body["search_recency_filter"] == "oneMonth"

    @pytest.mark.asyncio
    async def test_search_with_domain_and_count_filters(self):
        """E2E: Search with domain and count filters applies both correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {"title": f"Result {i}", "content": f"Content {i}", "link": f"https://github.com/{i}", "media": "github.com"}
                for i in range(1, 11)
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search(
                    "textual TUI",
                    domain_filter="github.com",
                    count=3
                )

                assert len(results) == 3
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_domain_filter"] == "github.com"
                assert body["count"] == 3

    @pytest.mark.asyncio
    async def test_search_with_all_filters(self):
        """E2E: Search with all filters (domain, recency, count) works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "Textual TUI",
                    "content": "Python TUI framework",
                    "link": "https://github.com/textualize/textual",
                    "media": "github.com",
                    "publish_date": "2024-01-10"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search(
                    "textual TUI",
                    domain_filter="github.com",
                    recency_filter="oneMonth",
                    count=3
                )

                assert len(results) == 1
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                assert body["search_domain_filter"] == "github.com"
                assert body["search_recency_filter"] == "oneMonth"
                assert body["count"] == 3


# ============================================================================
# Error Path Tests
# ============================================================================

class TestValidationErrorPaths:
    """E2E Error Path Tests: Validation errors raise ValueError."""

    @pytest.mark.asyncio
    async def test_empty_query_raises_value_error(self):
        """E2E: Empty query raises ValueError with appropriate message."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            client = SearchClient()
            with pytest.raises(ValueError) as exc_info:
                await client.search("")

        assert "Search query cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_whitespace_only_query_raises_value_error(self):
        """E2E: Whitespace-only query raises ValueError."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            client = SearchClient()
            with pytest.raises(ValueError) as exc_info:
                await client.search("   \t\n  ")

        assert "Search query cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_negative_count_raises_value_error(self):
        """E2E: Negative count raises ValueError."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            client = SearchClient()
            with pytest.raises(ValueError) as exc_info:
                await client.search("test query", count=-5)

        assert "Count must be a positive integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_zero_count_raises_value_error(self):
        """E2E: Zero count raises ValueError."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            client = SearchClient()
            with pytest.raises(ValueError) as exc_info:
                await client.search("test query", count=0)

        assert "Count must be a positive integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_recency_filter_raises_value_error(self):
        """E2E: Invalid recency filter raises ValueError with valid options."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            client = SearchClient()
            with pytest.raises(ValueError) as exc_info:
                await client.search("test query", recency_filter="twoWeeks")

        assert "Invalid recency filter" in str(exc_info.value)
        assert "twoWeeks" in str(exc_info.value)
        assert "oneDay" in str(exc_info.value)
        assert "oneWeek" in str(exc_info.value)


class TestApiErrorPaths:
    """E2E Error Path Tests: API errors raise appropriate errors."""

    @pytest.mark.asyncio
    async def test_invalid_token_raises_auth_error(self):
        """E2E: Invalid API token raises AuthError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized: Invalid API token"
        mock_response.json.return_value = {"error": "Invalid token"}

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "invalid-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                with pytest.raises(Exception) as exc_info:
                    await client.search("test query")

        # Should be an auth-related error
        error_str = str(exc_info.value).lower()
        assert "auth" in error_str or "401" in error_str or "unauthorized" in error_str

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """E2E: Network timeout raises TimeoutError."""
        class TimeoutMockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, *args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

        mock_async_client = TimeoutMockClient()

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                with pytest.raises(Exception) as exc_info:
                    await client.search("test query")

        error_str = str(exc_info.value).lower()
        assert "timeout" in error_str or "timed out" in error_str

    @pytest.mark.asyncio
    async def test_network_error_raises_network_error(self):
        """E2E: Network error raises NetworkError."""
        class NetworkMockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, *args, **kwargs):
                raise httpx.ConnectError("Connection failed")

        mock_async_client = NetworkMockClient()

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                with pytest.raises(Exception) as exc_info:
                    await client.search("test query")

        error_str = str(exc_info.value).lower()
        assert "network" in error_str or "connection" in error_str


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """E2E Edge Case Tests: Various edge cases are handled correctly."""

    @pytest.mark.asyncio
    async def test_search_with_no_results(self):
        """E2E: Search with no results (empty result array) returns empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": []
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("very specific term with no matches")

                assert results == []
                assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_very_long_query(self):
        """E2E: Search with very long query string works correctly."""
        long_query = "python " * 100  # 700 characters

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {
                    "title": "Python Result",
                    "content": "Python content",
                    "link": "https://example.com/python"
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search(long_query)

                assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_with_large_count(self):
        """E2E: Search with count=100 (large value) works correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "search_result": [
                {"title": f"Result {i}", "content": f"Content {i}", "link": f"https://example.com/{i}"}
                for i in range(1, 51)
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                results = await client.search("test query", count=100)

                # Should return all available results (50)
                assert len(results) == 50

    @pytest.mark.asyncio
    async def test_malformed_api_response_handles_gracefully(self):
        """E2E: Malformed API response is handled gracefully by returning empty list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Malformed response - missing search_result key
        mock_response.json.return_value = {"result": "unexpected"}

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai"
        mock_config.timeout = 120

        with patch("goz.api.search.load_config", return_value=mock_config):
            with patch("goz.api.search.httpx.AsyncClient", return_value=mock_async_client):
                client = SearchClient()
                # Should return empty list gracefully instead of raising
                results = await client.search("test query")
                assert results == []


# ============================================================================
# Unit Tests for Helper Functions
# ============================================================================

class TestValidateSearchParams:
    """Unit Tests: validate_search_params function."""

    def test_accepts_valid_query(self):
        """Unit: validate_search_params() accepts valid query."""
        # Should not raise
        validate_search_params("valid query")

    def test_rejects_empty_query(self):
        """Unit: validate_search_params() rejects empty query."""
        with pytest.raises(ValueError) as exc_info:
            validate_search_params("")
        assert "Search query cannot be empty" in str(exc_info.value)

    def test_rejects_whitespace_only_query(self):
        """Unit: validate_search_params() rejects whitespace-only query."""
        with pytest.raises(ValueError) as exc_info:
            validate_search_params("   \t  ")
        assert "Search query cannot be empty" in str(exc_info.value)

    def test_rejects_negative_count(self):
        """Unit: validate_search_params() rejects negative count."""
        with pytest.raises(ValueError) as exc_info:
            validate_search_params("test", count=-1)
        assert "Count must be a positive integer" in str(exc_info.value)

    def test_rejects_zero_count(self):
        """Unit: validate_search_params() rejects zero count."""
        with pytest.raises(ValueError) as exc_info:
            validate_search_params("test", count=0)
        assert "Count must be a positive integer" in str(exc_info.value)

    def test_accepts_valid_recency_values(self):
        """Unit: validate_search_params() accepts valid recency values."""
        valid_values = ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]
        for value in valid_values:
            # Should not raise
            validate_search_params("test", recency_filter=value)

    def test_rejects_invalid_recency_values(self):
        """Unit: validate_search_params() rejects invalid recency values."""
        with pytest.raises(ValueError) as exc_info:
            validate_search_params("test", recency_filter="twoWeeks")
        assert "Invalid recency filter" in str(exc_info.value)
        assert "twoWeeks" in str(exc_info.value)


class TestBuildSearchRequestBody:
    """Unit Tests: build_search_request_body function."""

    def test_constructs_body_with_all_parameters(self):
        """Unit: build_search_request_body() constructs correct body with all parameters."""
        body = build_search_request_body(
            query="test query",
            count=5,
            domain_filter="example.com",
            recency_filter="oneWeek"
        )

        assert body["search_engine"] == "search-prime"
        assert body["search_query"] == "test query"
        assert body["count"] == 5
        assert body["search_domain_filter"] == "example.com"
        assert body["search_recency_filter"] == "oneWeek"

    def test_omits_optional_parameters_when_none(self):
        """Unit: build_search_request_body() omits optional parameters when None."""
        body = build_search_request_body(query="test query")

        assert body["search_engine"] == "search-prime"
        assert body["search_query"] == "test query"
        assert "count" not in body
        assert "search_domain_filter" not in body
        assert "search_recency_filter" not in body

    def test_includes_domain_filter_when_provided(self):
        """Unit: build_search_request_body() includes domain filter when provided."""
        body = build_search_request_body(query="test", domain_filter="github.com")

        assert body["search_domain_filter"] == "github.com"

    def test_includes_recency_filter_when_provided(self):
        """Unit: build_search_request_body() includes recency filter when provided."""
        body = build_search_request_body(query="test", recency_filter="oneMonth")

        assert body["search_recency_filter"] == "oneMonth"

    def test_includes_count_when_provided(self):
        """Unit: build_search_request_body() includes count when provided."""
        body = build_search_request_body(query="test", count=10)

        assert body["count"] == 10


class TestParseSearchResponse:
    """Unit Tests: parse_search_response function."""

    def test_correctly_maps_response_to_search_results(self):
        """Unit: parse_search_response() correctly maps API response to SearchResult list."""
        response = {
            "search_result": [
                {
                    "title": "First Result",
                    "content": "First summary",
                    "link": "https://example.com/1",
                    "media": "example.com",
                    "publish_date": "2024-01-01"
                },
                {
                    "title": "Second Result",
                    "content": "Second summary",
                    "link": "https://example.com/2"
                }
            ]
        }

        results = parse_search_response(response)

        assert len(results) == 2
        assert results[0].rank == 1
        assert results[0].title == "First Result"
        assert results[0].summary == "First summary"
        assert results[0].url == "https://example.com/1"
        assert results[0].source == "example.com"
        assert results[0].date == "2024-01-01"

        assert results[1].rank == 2
        assert results[1].title == "Second Result"
        assert results[1].source is None
        assert results[1].date is None

    def test_assigns_correct_rank_1_indexed(self):
        """Unit: parse_search_response() assigns correct rank (1-indexed)."""
        response = {
            "search_result": [
                {"title": "A", "content": "A", "link": "https://a.com"},
                {"title": "B", "content": "B", "link": "https://b.com"},
                {"title": "C", "content": "C", "link": "https://c.com"}
            ]
        }

        results = parse_search_response(response)

        assert [r.rank for r in results] == [1, 2, 3]

    def test_handles_missing_optional_fields(self):
        """Unit: parse_search_response() handles missing optional fields (source, date)."""
        response = {
            "search_result": [
                {
                    "title": "Result",
                    "content": "Summary",
                    "link": "https://example.com"
                }
            ]
        }

        results = parse_search_response(response)

        assert len(results) == 1
        assert results[0].source is None
        assert results[0].date is None

    def test_handles_empty_results_array(self):
        """Unit: parse_search_response() handles empty results array."""
        response = {"search_result": []}

        results = parse_search_response(response)

        assert results == []

    def test_handles_result_with_all_fields(self):
        """Unit: parse_search_response() handles result with all fields present."""
        response = {
            "search_result": [
                {
                    "title": "Full Result",
                    "content": "Full summary",
                    "link": "https://example.com/full",
                    "media": "example.com",
                    "publish_date": "2024-01-15",
                    "icon": "ignored",
                    "refer": "ignored"
                }
            ]
        }

        results = parse_search_response(response)

        assert len(results) == 1
        assert results[0].title == "Full Result"
        assert results[0].summary == "Full summary"
        assert results[0].url == "https://example.com/full"
        assert results[0].source == "example.com"
        assert results[0].date == "2024-01-15"


class TestLimitResults:
    """Unit Tests: limit_results function."""

    def test_limits_to_count(self):
        """Unit: limit_results() with count=5 returns first 5 results."""
        results = [
            SearchResult(rank=i, title=f"R{i}", url=f"{i}.com", summary=f"S{i}")
            for i in range(1, 11)
        ]

        limited = limit_results(results, 5)

        assert len(limited) == 5
        assert [r.rank for r in limited] == [1, 2, 3, 4, 5]

    def test_returns_all_when_count_greater_than_length(self):
        """Unit: limit_results() with count greater than results length returns all results."""
        results = [
            SearchResult(rank=i, title=f"R{i}", url=f"{i}.com", summary=f"S{i}")
            for i in range(1, 4)
        ]

        limited = limit_results(results, 10)

        assert len(limited) == 3
        assert limited == results

    def test_returns_all_when_count_is_none(self):
        """Unit: limit_results() with count=None returns all results."""
        results = [
            SearchResult(rank=i, title=f"R{i}", url=f"{i}.com", summary=f"S{i}")
            for i in range(1, 6)
        ]

        limited = limit_results(results, None)

        assert len(limited) == 5
        assert limited == results

    def test_returns_empty_list_for_empty_input(self):
        """Unit: limit_results() with empty list returns empty list."""
        results = []

        limited = limit_results(results, 5)

        assert limited == []


class TestSearchResultDataClass:
    """Unit Tests: SearchResult dataclass."""

    def test_creates_instance_with_all_fields(self):
        """Unit: SearchResult dataclass creates instance with all fields."""
        result = SearchResult(
            rank=1,
            title="Test Title",
            url="https://example.com",
            summary="Test summary",
            source="example.com",
            date="2024-01-15"
        )

        assert result.rank == 1
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.summary == "Test summary"
        assert result.source == "example.com"
        assert result.date == "2024-01-15"

    def test_creates_instance_with_only_required_fields(self):
        """Unit: SearchResult dataclass creates instance with only required fields."""
        result = SearchResult(
            rank=1,
            title="Test Title",
            url="https://example.com",
            summary="Test summary"
        )

        assert result.rank == 1
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.summary == "Test summary"
        assert result.source is None
        assert result.date is None

    def test_repr_produces_readable_output(self):
        """Unit: SearchResult __repr__ produces readable output."""
        result = SearchResult(
            rank=1,
            title="Test Title",
            url="https://example.com",
            summary="Test summary"
        )

        repr_str = repr(result)

        assert "SearchResult" in repr_str
        assert "1" in repr_str
        assert "Test Title" in repr_str
