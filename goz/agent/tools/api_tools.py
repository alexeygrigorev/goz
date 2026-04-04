"""API tools for goz interactive coding agent (Issue 21).

This module provides tools that wrap existing API clients:
- SearchTool: Wraps SearchClient for web search
- ReadTool: Wraps ReaderClient for web page reading
- RepoSearchTool: Wraps RepoClient.search() for repo search
- RepoTreeTool: Wraps RepoClient.tree() for repo structure
- RepoReadTool: Wraps RepoClient.read() for reading repo files
"""
from __future__ import annotations

from typing import Any

from goz.agent.tools.base import BaseTool
from goz.api.search import SearchClient
from goz.api.reader import ReaderClient
from goz.api.repo import RepoClient


class SearchTool(BaseTool):
    """Tool for web search using SearchClient.

    Wraps the existing SearchClient to provide web search functionality
    with support for domain filtering and result count limiting.
    """

    name = "search"
    description = (
        "Search the web for current information. "
        "Use for finding documentation, examples, news, and troubleshooting."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "count": {
                "type": "integer",
                "description": "Number of results (default: 10, max: 50)"
            },
            "domain": {
                "type": "string",
                "description": "Filter to specific domain (optional)"
            }
        },
        "required": ["query"]
    }

    def __init__(self, config: Any) -> None:
        """Initialize SearchTool.

        Args:
            config: Configuration object for API clients
        """
        super().__init__()
        self.config = config
        self.client = SearchClient(config)

    async def execute(
        self,
        query: str,
        count: int | None = None,
        domain: str | None = None,
    ) -> str:
        """Search the web.

        Args:
            query: Search query string
            count: Number of results to return
            domain: Optional domain filter

        Returns:
            Formatted search results as string
        """
        self.validate_input(self.input_schema, {"query": query})

        try:
            results = await self.client.search(
                query=query,
                count=count,
                domain_filter=domain,
                recency_filter=None,
            )
        except Exception as e:
            return f"Error searching: {e}"

        if not results:
            return f"No results found for query: {query}"

        # Format output
        output = [f"Found {len(results)} results for \"{query}\""]
        output.append("=" * 60)

        for result in results:
            output.append(f"\n{result.rank}. {result.title}")
            output.append(f"   {result.url}")
            if result.summary:
                # Truncate long summaries
                summary = result.summary[:200] + "..." if len(result.summary) > 200 else result.summary
                output.append(f"   {summary}")

        return "\n".join(output)


class ReadTool(BaseTool):
    """Tool for reading web pages using ReaderClient.

    Wraps the existing ReaderClient to fetch and convert web pages
    to readable markdown format.
    """

    name = "read"
    description = (
        "Fetch and convert a web page to readable markdown. "
        "Use for reading documentation, articles, blog posts, and news."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch and parse"
            }
        },
        "required": ["url"]
    }

    def __init__(self, config: Any) -> None:
        """Initialize ReadTool.

        Args:
            config: Configuration object for API clients
        """
        super().__init__()
        self.config = config
        self.client = ReaderClient(config)

    async def execute(self, url: str) -> str:
        """Fetch and parse web page.

        Args:
            url: URL to fetch

        Returns:
            Formatted page content as string
        """
        self.validate_input(self.input_schema, {"url": url})

        try:
            result = await self.client.read(
                url=url,
                format="markdown",
                timeout=20,
                no_cache=False,
                retain_images=True,
                with_links_summary=False,
            )
        except Exception as e:
            return f"Error fetching page: {e}"

        # Format output
        output = [f"Fetched: {url}"]
        output.append("=" * 60)

        if result.title:
            output.append(f"\n# {result.title}")

        output.append(f"\n{result.content}")

        return "\n".join(output)


class RepoSearchTool(BaseTool):
    """Tool for searching GitHub repositories using RepoClient.

    Wraps the existing RepoClient.search() to search code and
    documentation in GitHub repositories.
    """

    name = "repo_search"
    description = (
        "Search code and documentation in a GitHub repository. "
        "Use for finding specific code patterns, functions, or topics in a repo."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format (e.g., 'vercel/next.js')"
            },
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "language": {
                "type": "string",
                "enum": ["en", "zh"],
                "description": "Result language"
            }
        },
        "required": ["repo", "query"]
    }

    def __init__(self, config: Any) -> None:
        """Initialize RepoSearchTool.

        Args:
            config: Configuration object for API clients
        """
        super().__init__()
        self.config = config
        self.client = RepoClient(config)

    async def execute(
        self,
        repo: str,
        query: str,
        language: str | None = None,
    ) -> str:
        """Search repository.

        Args:
            repo: Repository in "owner/repo" format
            query: Search query string
            language: Optional language filter

        Returns:
            Formatted search results as string
        """
        self.validate_input(self.input_schema, {"repo": repo, "query": query})

        try:
            results = await self.client.search(
                repo=repo,
                query=query,
                language=language,
            )
        except Exception as e:
            return f"Error searching repository: {e}"

        # Format output
        output = [f"Search results for \"{query}\" in {repo}"]
        output.append("=" * 60)

        if not results:
            output.append("\nNo results found.")
            return "\n".join(output)

        for i, result in enumerate(results, 1):
            output.append(f"\n{i}. {result.title or 'Untitled'}")
            if result.url:
                output.append(f"   URL: {result.url}")
            if result.content:
                # Truncate long content
                content = result.content[:300] + "..." if len(result.content) > 300 else result.content
                output.append(f"   {content}")

        return "\n".join(output)


class RepoTreeTool(BaseTool):
    """Tool for getting repository structure using RepoClient.

    Wraps the existing RepoClient.tree() to get the directory
    structure of GitHub repositories.
    """

    name = "repo_tree"
    description = (
        "Get the directory structure of a GitHub repository. "
        "Use for understanding project layout and finding files."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format"
            },
            "path": {
                "type": "string",
                "description": "Directory path (default: repo root)"
            },
            "depth": {
                "type": "integer",
                "description": "Depth for subdirectory expansion (default: 1)"
            }
        },
        "required": ["repo"]
    }

    def __init__(self, config: Any) -> None:
        """Initialize RepoTreeTool.

        Args:
            config: Configuration object for API clients
        """
        super().__init__()
        self.config = config
        self.client = RepoClient(config)

    async def execute(
        self,
        repo: str,
        path: str | None = None,
        depth: int = 1,
    ) -> str:
        """Get repository tree.

        Args:
            repo: Repository in "owner/repo" format
            path: Optional directory path
            depth: Depth for subdirectory expansion

        Returns:
            Formatted tree structure as string
        """
        self.validate_input(self.input_schema, {"repo": repo})

        try:
            result = await self.client.tree(
                repo=repo,
                path=path,
                depth=depth,
            )
        except Exception as e:
            return f"Error getting repository structure: {e}"

        # Return the tree structure directly
        # The RepoClient already formats it nicely
        return f"{repo}\n{'=' * 60}\n{result}"


class RepoReadTool(BaseTool):
    """Tool for reading repository files using RepoClient.

    Wraps the existing RepoClient.read() to read files from
    GitHub repositories.
    """

    name = "repo_read"
    description = (
        "Read a file from a GitHub repository. "
        "Use for viewing source code, READMEs, configs, etc."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format"
            },
            "file_path": {
                "type": "string",
                "description": "Path to the file (relative to repo root)"
            }
        },
        "required": ["repo", "file_path"]
    }

    def __init__(self, config: Any) -> None:
        """Initialize RepoReadTool.

        Args:
            config: Configuration object for API clients
        """
        super().__init__()
        self.config = config
        self.client = RepoClient(config)

    async def execute(self, repo: str, file_path: str) -> str:
        """Read file from repository.

        Args:
            repo: Repository in "owner/repo" format
            file_path: Path to the file

        Returns:
            File contents as string
        """
        self.validate_input(self.input_schema, {"repo": repo, "file_path": file_path})

        try:
            content = await self.client.read(
                repo=repo,
                file_path=file_path,
            )
        except Exception as e:
            return f"Error reading file: {e}"

        # Format output
        output = [f"File: {repo}/{file_path}"]
        output.append("=" * 60)
        output.append(f"\n{content}")

        return "\n".join(output)
