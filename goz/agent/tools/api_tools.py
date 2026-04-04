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

from goz.agent.tools.base import BaseTool, ToolInputError
from goz.api.search import SearchClient
from goz.api.reader import ReaderClient
from goz.api.repo import RepoClient


def _require_non_empty_string(value: str, field_name: str) -> str:
    """Validate a required string argument."""
    if not value.strip():
        raise ToolInputError(f"Field '{field_name}' cannot be empty")
    return value.strip()


def _validate_repo_name(repo: str) -> str:
    """Validate GitHub repo name format at the tool boundary."""
    repo = _require_non_empty_string(repo, "repo")
    parts = repo.split("/")
    if len(parts) != 2 or not all(parts):
        raise ToolInputError(
            f"Field 'repo': expected 'owner/repo' format, got {repo!r}"
        )
    return repo


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
        data = {"query": query}
        if count is not None:
            data["count"] = count
        if domain is not None:
            data["domain"] = domain
        self.validate_input(self.input_schema, data)

        query = _require_non_empty_string(query, "query")
        if count is not None and not 1 <= count <= 50:
            raise ToolInputError("Field 'count' must be between 1 and 50")
        if domain is not None:
            domain = _require_non_empty_string(domain, "domain")

        try:
            results = await self.client.search(
                query=query,
                count=count,
                domain_filter=domain,
                recency_filter=None,
            )
        except Exception as e:
            return f"Search Failed for {query!r}: {e}"

        if not results:
            return f"Search results for {query!r}\n{'=' * 60}\nNo results found."

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
        url = _require_non_empty_string(url, "url")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ToolInputError(
                "Field 'url' must start with 'http://' or 'https://'"
            )

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
            return f"Read Failed for {url}: {e}"

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
        data = {"repo": repo, "query": query}
        if language is not None:
            data["language"] = language
        self.validate_input(self.input_schema, data)

        repo = _validate_repo_name(repo)
        query = _require_non_empty_string(query, "query")
        if language is not None and language not in {"en", "zh"}:
            raise ToolInputError("Field 'language' must be one of: en, zh")

        try:
            results = await self.client.search(
                repo=repo,
                query=query,
                language=language,
            )
        except Exception as e:
            return f"Repository Search Failed for {repo} ({query!r}): {e}"

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
        data = {"repo": repo}
        if path is not None:
            data["path"] = path
        if depth is not None:
            data["depth"] = depth
        self.validate_input(self.input_schema, data)

        repo = _validate_repo_name(repo)
        if path is not None:
            path = _require_non_empty_string(path, "path")
        if depth < 1:
            raise ToolInputError("Field 'depth' must be at least 1")

        try:
            result = await self.client.tree(
                repo=repo,
                path=path,
                depth=depth,
            )
        except Exception as e:
            return f"Repository Tree Failed for {repo}: {e}"

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
        repo = _validate_repo_name(repo)
        file_path = _require_non_empty_string(file_path, "file_path")

        try:
            content = await self.client.read(
                repo=repo,
                file_path=file_path,
            )
        except Exception as e:
            return f"Repository Read Failed for {repo}/{file_path}: {e}"

        # Format output
        output = [f"File: {repo}/{file_path}"]
        output.append("=" * 60)
        output.append(f"\n{content}")

        return "\n".join(output)
