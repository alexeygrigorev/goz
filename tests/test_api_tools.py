"""Unit tests for API Tools (Issue 21).

Tests for SearchTool, ReadTool, RepoSearchTool, RepoTreeTool, RepoReadTool
that wrap existing API clients.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from goz.agent.tools.api_tools import (
    SearchTool,
    ReadTool,
    RepoSearchTool,
    RepoTreeTool,
    RepoReadTool,
)
from goz.agent.tools.base import ToolInputError
from goz.api.search import SearchResult
from goz.api.reader import ReaderResult
from goz.api.repo import RepoSearchResult


# ========== Test SearchTool ==========


class TestSearchTool:
    """Unit Tests: SearchTool class."""

    def test_search_tool_exists(self):
        """Test SearchTool class can be imported."""
        assert SearchTool is not None

    def test_search_tool_name(self):
        """Test SearchTool has correct name."""
        tool = SearchTool(config=MagicMock())
        assert tool.name == "search"

    def test_search_tool_description(self):
        """Test SearchTool has description."""
        tool = SearchTool(config=MagicMock())
        assert tool.description
        assert "search" in tool.description.lower()

    def test_search_tool_input_schema(self):
        """Test SearchTool has correct input_schema."""
        tool = SearchTool(config=MagicMock())
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert schema["required"] == ["query"]
        assert "count" in schema["properties"]
        assert "domain" in schema["properties"]

    def test_search_tool_init_with_config(self):
        """Test SearchTool initializes with config."""
        mock_config = MagicMock()
        tool = SearchTool(config=mock_config)
        assert tool.config is mock_config
        assert tool.client is not None

    @pytest.mark.asyncio
    async def test_search_tool_execute_basic(self):
        """Test SearchTool.execute with basic query."""
        mock_config = MagicMock()
        mock_result = SearchResult(
            rank=1,
            title="Test Result",
            url="https://example.com",
            summary="A test result",
        )

        with patch("goz.agent.tools.api_tools.SearchClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = [mock_result]
            MockClient.return_value = mock_client

            tool = SearchTool(config=mock_config)
            result = await tool.execute(query="test query")

            mock_client.search.assert_called_once_with(
                query="test query",
                count=None,
                domain_filter=None,
                recency_filter=None,
            )
            assert "Test Result" in result
            assert "https://example.com" in result

    @pytest.mark.asyncio
    async def test_search_tool_execute_with_count(self):
        """Test SearchTool.execute with count parameter."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.SearchClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = []
            MockClient.return_value = mock_client

            tool = SearchTool(config=mock_config)
            await tool.execute(query="test", count=5)

            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs["count"] == 5

    @pytest.mark.asyncio
    async def test_search_tool_execute_with_domain(self):
        """Test SearchTool.execute with domain filter."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.SearchClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = []
            MockClient.return_value = mock_client

            tool = SearchTool(config=mock_config)
            await tool.execute(query="test", domain="example.com")

            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs["domain_filter"] == "example.com"

    @pytest.mark.asyncio
    async def test_search_tool_format_output(self):
        """Test SearchTool formats output correctly."""
        mock_config = MagicMock()
        mock_results = [
            SearchResult(
                rank=1,
                title="First Result",
                url="https://example.com/1",
                summary="First summary",
            ),
            SearchResult(
                rank=2,
                title="Second Result",
                url="https://example.com/2",
                summary="Second summary",
            ),
        ]

        with patch("goz.agent.tools.api_tools.SearchClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = mock_results
            MockClient.return_value = mock_client

            tool = SearchTool(config=mock_config)
            result = await tool.execute(query="test")

            assert "Found 2 results" in result
            assert "First Result" in result
            assert "https://example.com/1" in result
            assert "Second Result" in result
            assert "https://example.com/2" in result

    @pytest.mark.asyncio
    async def test_search_tool_empty_results(self):
        """Test SearchTool handles empty results gracefully."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.SearchClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = []
            MockClient.return_value = mock_client

            tool = SearchTool(config=mock_config)
            result = await tool.execute(query="test")

            assert "No results found" in result


# ========== Test ReadTool ==========


class TestReadTool:
    """Unit Tests: ReadTool class."""

    def test_read_tool_exists(self):
        """Test ReadTool class can be imported."""
        assert ReadTool is not None

    def test_read_tool_name(self):
        """Test ReadTool has correct name."""
        tool = ReadTool(config=MagicMock())
        assert tool.name == "read"

    def test_read_tool_description(self):
        """Test ReadTool has description."""
        tool = ReadTool(config=MagicMock())
        assert tool.description
        assert "fetch" in tool.description.lower() or "read" in tool.description.lower()

    def test_read_tool_input_schema(self):
        """Test ReadTool has correct input_schema."""
        tool = ReadTool(config=MagicMock())
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "url" in schema["properties"]
        assert schema["required"] == ["url"]

    def test_read_tool_init_with_config(self):
        """Test ReadTool initializes with config."""
        mock_config = MagicMock()
        tool = ReadTool(config=mock_config)
        assert tool.config is mock_config
        assert tool.client is not None

    @pytest.mark.asyncio
    async def test_read_tool_execute_basic(self):
        """Test ReadTool.execute with basic URL."""
        mock_config = MagicMock()
        mock_result = ReaderResult(
            content="# Test Content\n\nThis is test content.",
            title="Test Page",
            url="https://example.com",
        )

        with patch("goz.agent.tools.api_tools.ReaderClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.read.return_value = mock_result
            MockClient.return_value = mock_client

            tool = ReadTool(config=mock_config)
            result = await tool.execute(url="https://example.com")

            mock_client.read.assert_called_once_with(
                url="https://example.com",
                format="markdown",
                timeout=20,
                no_cache=False,
                retain_images=True,
                with_links_summary=False,
            )
            assert "# Test Content" in result
            assert "This is test content" in result

    @pytest.mark.asyncio
    async def test_read_tool_format_output(self):
        """Test ReadTool formats output correctly."""
        mock_config = MagicMock()
        mock_result = ReaderResult(
            content="Page content here",
            title="Example Page",
            url="https://example.com/article",
        )

        with patch("goz.agent.tools.api_tools.ReaderClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.read.return_value = mock_result
            MockClient.return_value = mock_client

            tool = ReadTool(config=mock_config)
            result = await tool.execute(url="https://example.com/article")

            assert "https://example.com/article" in result
            assert "Example Page" in result
            assert "Page content here" in result

    @pytest.mark.asyncio
    async def test_read_tool_handles_errors(self):
        """Test ReadTool handles fetch errors gracefully."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.ReaderClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.read.side_effect = Exception("Network error")
            MockClient.return_value = mock_client

            tool = ReadTool(config=mock_config)
            result = await tool.execute(url="https://example.com")

            assert "Error" in result or "Failed" in result


# ========== Test RepoSearchTool ==========


class TestRepoSearchTool:
    """Unit Tests: RepoSearchTool class."""

    def test_repo_search_tool_exists(self):
        """Test RepoSearchTool class can be imported."""
        assert RepoSearchTool is not None

    def test_repo_search_tool_name(self):
        """Test RepoSearchTool has correct name."""
        tool = RepoSearchTool(config=MagicMock())
        assert tool.name == "repo_search"

    def test_repo_search_tool_description(self):
        """Test RepoSearchTool has description."""
        tool = RepoSearchTool(config=MagicMock())
        assert tool.description
        assert "repo" in tool.description.lower()

    def test_repo_search_tool_input_schema(self):
        """Test RepoSearchTool has correct input_schema."""
        tool = RepoSearchTool(config=MagicMock())
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "repo" in schema["properties"]
        assert "query" in schema["properties"]
        assert set(schema["required"]) == {"repo", "query"}
        assert "language" in schema["properties"]

    def test_repo_search_tool_init_with_config(self):
        """Test RepoSearchTool initializes with config."""
        mock_config = MagicMock()
        tool = RepoSearchTool(config=mock_config)
        assert tool.config is mock_config
        assert tool.client is not None

    @pytest.mark.asyncio
    async def test_repo_search_tool_execute_basic(self):
        """Test RepoSearchTool.execute with basic parameters."""
        mock_config = MagicMock()
        mock_result = RepoSearchResult(
            title="test.py",
            content="def test(): pass",
            url="/src/test.py",
        )

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = [mock_result]
            MockClient.return_value = mock_client

            tool = RepoSearchTool(config=mock_config)
            result = await tool.execute(repo="owner/repo", query="test")

            mock_client.search.assert_called_once_with(
                repo="owner/repo",
                query="test",
                language=None,
            )
            assert "test.py" in result
            assert "def test()" in result

    @pytest.mark.asyncio
    async def test_repo_search_tool_execute_with_language(self):
        """Test RepoSearchTool.execute with language parameter."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = []
            MockClient.return_value = mock_client

            tool = RepoSearchTool(config=mock_config)
            await tool.execute(repo="owner/repo", query="test", language="en")

            mock_client.search.assert_called_once()
            call_kwargs = mock_client.search.call_args.kwargs
            assert call_kwargs["language"] == "en"

    @pytest.mark.asyncio
    async def test_repo_search_tool_format_output(self):
        """Test RepoSearchTool formats output correctly."""
        mock_config = MagicMock()
        mock_results = [
            RepoSearchResult(
                title="file1.py",
                content="Content 1",
                url="/src/file1.py",
            ),
            RepoSearchResult(
                title="file2.py",
                content="Content 2",
                url="/src/file2.py",
            ),
        ]

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.search.return_value = mock_results
            MockClient.return_value = mock_client

            tool = RepoSearchTool(config=mock_config)
            result = await tool.execute(repo="owner/repo", query="test")

            assert "Search results" in result
            assert "owner/repo" in result
            assert "file1.py" in result
            assert "Content 1" in result


# ========== Test RepoTreeTool ==========


class TestRepoTreeTool:
    """Unit Tests: RepoTreeTool class."""

    def test_repo_tree_tool_exists(self):
        """Test RepoTreeTool class can be imported."""
        assert RepoTreeTool is not None

    def test_repo_tree_tool_name(self):
        """Test RepoTreeTool has correct name."""
        tool = RepoTreeTool(config=MagicMock())
        assert tool.name == "repo_tree"

    def test_repo_tree_tool_description(self):
        """Test RepoTreeTool has description."""
        tool = RepoTreeTool(config=MagicMock())
        assert tool.description
        assert "tree" in tool.description.lower() or "structure" in tool.description.lower()

    def test_repo_tree_tool_input_schema(self):
        """Test RepoTreeTool has correct input_schema."""
        tool = RepoTreeTool(config=MagicMock())
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "repo" in schema["properties"]
        assert schema["required"] == ["repo"]
        assert "path" in schema["properties"]
        assert "depth" in schema["properties"]

    def test_repo_tree_tool_init_with_config(self):
        """Test RepoTreeTool initializes with config."""
        mock_config = MagicMock()
        tool = RepoTreeTool(config=mock_config)
        assert tool.config is mock_config
        assert tool.client is not None

    @pytest.mark.asyncio
    async def test_repo_tree_tool_execute_basic(self):
        """Test RepoTreeTool.execute with basic parameters."""
        mock_config = MagicMock()
        tree_output = "owner/repo\n├── src\n│   └── main.py\n└── README.md"

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.tree.return_value = tree_output
            MockClient.return_value = mock_client

            tool = RepoTreeTool(config=mock_config)
            result = await tool.execute(repo="owner/repo")

            mock_client.tree.assert_called_once_with(
                repo="owner/repo",
                path=None,
                depth=1,
            )
            assert "owner/repo" in result

    @pytest.mark.asyncio
    async def test_repo_tree_tool_execute_with_path(self):
        """Test RepoTreeTool.execute with path parameter."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.tree.return_value = ""
            MockClient.return_value = mock_client

            tool = RepoTreeTool(config=mock_config)
            await tool.execute(repo="owner/repo", path="src/")

            mock_client.tree.assert_called_once()
            call_kwargs = mock_client.tree.call_args.kwargs
            assert call_kwargs["path"] == "src/"

    @pytest.mark.asyncio
    async def test_repo_tree_tool_execute_with_depth(self):
        """Test RepoTreeTool.execute with depth parameter."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.tree.return_value = ""
            MockClient.return_value = mock_client

            tool = RepoTreeTool(config=mock_config)
            await tool.execute(repo="owner/repo", depth=3)

            mock_client.tree.assert_called_once()
            call_kwargs = mock_client.tree.call_args.kwargs
            assert call_kwargs["depth"] == 3


# ========== Test RepoReadTool ==========


class TestRepoReadTool:
    """Unit Tests: RepoReadTool class."""

    def test_repo_read_tool_exists(self):
        """Test RepoReadTool class can be imported."""
        assert RepoReadTool is not None

    def test_repo_read_tool_name(self):
        """Test RepoReadTool has correct name."""
        tool = RepoReadTool(config=MagicMock())
        assert tool.name == "repo_read"

    def test_repo_read_tool_description(self):
        """Test RepoReadTool has description."""
        tool = RepoReadTool(config=MagicMock())
        assert tool.description
        assert "read" in tool.description.lower() or "file" in tool.description.lower()

    def test_repo_read_tool_input_schema(self):
        """Test RepoReadTool has correct input_schema."""
        tool = RepoReadTool(config=MagicMock())
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "repo" in schema["properties"]
        assert "file_path" in schema["properties"]
        assert set(schema["required"]) == {"repo", "file_path"}

    def test_repo_read_tool_init_with_config(self):
        """Test RepoReadTool initializes with config."""
        mock_config = MagicMock()
        tool = RepoReadTool(config=mock_config)
        assert tool.config is mock_config
        assert tool.client is not None

    @pytest.mark.asyncio
    async def test_repo_read_tool_execute_basic(self):
        """Test RepoReadTool.execute with basic parameters."""
        mock_config = MagicMock()
        file_content = "# README\n\nThis is a readme file."

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.read.return_value = file_content
            MockClient.return_value = mock_client

            tool = RepoReadTool(config=mock_config)
            result = await tool.execute(repo="owner/repo", file_path="README.md")

            mock_client.read.assert_called_once_with(
                repo="owner/repo",
                file_path="README.md",
            )
            assert "# README" in result
            assert "This is a readme file" in result

    @pytest.mark.asyncio
    async def test_repo_read_tool_format_output(self):
        """Test RepoReadTool formats output correctly."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.read.return_value = "File content here"
            MockClient.return_value = mock_client

            tool = RepoReadTool(config=mock_config)
            result = await tool.execute(repo="owner/repo", file_path="src/main.py")

            assert "owner/repo" in result
            assert "src/main.py" in result
            assert "File content here" in result

    @pytest.mark.asyncio
    async def test_repo_read_tool_handles_errors(self):
        """Test RepoReadTool handles errors gracefully."""
        mock_config = MagicMock()

        with patch("goz.agent.tools.api_tools.RepoClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.read.side_effect = Exception("Read error")
            MockClient.return_value = mock_client

            tool = RepoReadTool(config=mock_config)
            result = await tool.execute(repo="owner/repo", file_path="nonexistent.py")

            assert "Error" in result or "Failed" in result
