"""Repo/ZRead API client for Z.AI.

This module provides the RepoClient class for GitHub repository exploration
using the Z.AI ZRead API via direct HTTP calls (not MCP).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from goz.api.errors import AuthError, ApiError, NetworkError, TimeoutError, ZaiError, ValidationError
from goz.config import Config, load_config


# Logger for repo requests
logger = logging.getLogger(__name__)


# Constants
ZREAD_MCP_ENDPOINT = "https://api.z.ai/api/mcp/zread/mcp"
RETRY_COUNT = 2
BASE_DELAY = 1.0


@dataclass
class RepoSearchResult:
    """A single search result from ZRead search.

    Attributes:
        title: Result title
        content: Result content
        url: Optional URL
        type: Optional result type
    """
    title: str
    content: str
    url: str | None = None
    type: str | None = None


def validate_repo_format(repo: str) -> None:
    """Validate repository format.

    Args:
        repo: Repository string (e.g., "owner/repo")

    Raises:
        ValidationError: If format is invalid
    """
    if not repo or not repo.strip():
        raise ValidationError("Repository cannot be empty")

    if "/" not in repo:
        raise ValidationError(
            f'Invalid repository format: "{repo}". Use "owner/repo" format (e.g., "facebook/react")'
        )

    parts = repo.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValidationError(
            f'Invalid repository format: "{repo}". Use "owner/repo" format (e.g., "facebook/react")'
        )


class RepoClient:
    """GitHub repository exploration client using Z.AI ZRead API.

    This client provides repository search, tree structure, and file reading
    capabilities for public GitHub repositories.
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialize RepoClient.

        Args:
            config: Optional config object. If not provided, loads from default location.
        """
        self.config = config or load_config()
        self.enable_logging = False

    async def _mcp_request(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> str:
        """Make MCP-style request to ZRead API.

        Args:
            tool_name: MCP tool name (e.g., "zai.zread.search_doc")
            args: Tool arguments

        Returns:
            Result content as string

        Raises:
            AuthError: For 401/403 responses
            ApiError: For other 4xx/5xx responses
            NetworkError: For connection failures
            TimeoutError: For request timeouts
        """
        headers = {
            "Authorization": f"Bearer {self.config.zai_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        timeout = self.config.timeout

        # MCP JSON-RPC format
        body = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args,
            },
        }

        last_error = None

        for attempt in range(RETRY_COUNT + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if self.enable_logging:
                        logger.info(f"-> POST {ZREAD_MCP_ENDPOINT} tool={tool_name}")

                    response = await client.post(ZREAD_MCP_ENDPOINT, json=body, headers=headers)

                    if self.enable_logging:
                        logger.info(f"<- {response.status_code} {len(response.content)} bytes")

                    # Handle successful response
                    if response.status_code == 200:
                        data = response.json()
                        # MCP response format: {"result": {"content": [{"type": "text", "text": "..."}]}}
                        if "result" in data:
                            result = data["result"]
                            if isinstance(result, dict):
                                if "content" in result:
                                    content = result["content"]
                                    if isinstance(content, list) and len(content) > 0:
                                        if isinstance(content[0], dict) and "text" in content[0]:
                                            return content[0]["text"]
                                if "output" in result:
                                    return str(result["output"])
                            return str(result)
                        return str(data)

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
            # Try various error message locations
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
            # If parsing fails, use raw text
            pass
        return response.text

    async def search(
        self,
        repo: str,
        query: str,
        language: str | None = None,
    ) -> list[RepoSearchResult]:
        """Search documentation and code in a GitHub repository.

        Args:
            repo: Repository in "owner/repo" format
            query: Search query string
            language: Optional language filter ("en" or "zh")

        Returns:
            List of search results

        Raises:
            ValidationError: If repo format is invalid
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        validate_repo_format(repo)

        if not query or not query.strip():
            raise ValidationError("Search query cannot be empty")

        args: dict[str, Any] = {
            "repo_name": repo,
            "query": query,
        }

        if language:
            if language not in ("en", "zh"):
                raise ValidationError('Language must be "en" or "zh"')
            args["language"] = language

        result = await self._mcp_request("zai.zread.search_doc", args)

        # Parse results - format may vary, try to handle as JSON array
        try:
            import json
            data = json.loads(result)
            if isinstance(data, list):
                return [
                    RepoSearchResult(
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        url=item.get("url"),
                        type=item.get("type"),
                    )
                    for item in data
                ]
        except (json.JSONDecodeError, TypeError):
            pass

        # Return as single result if parsing fails
        return [RepoSearchResult(title="", content=result)]

    async def tree(
        self,
        repo: str,
        path: str | None = None,
        depth: int = 1,
    ) -> str:
        """Get the directory structure of a GitHub repository.

        Args:
            repo: Repository in "owner/repo" format
            path: Optional directory path (default: repo root)
            depth: Depth for expanding subdirectories (default: 1)

        Returns:
            Directory structure as formatted string

        Raises:
            ValidationError: If repo format is invalid
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        validate_repo_format(repo)

        if depth < 1:
            raise ValidationError("Depth must be at least 1")

        args: dict[str, Any] = {
            "repo_name": repo,
        }

        if path:
            args["dir_path"] = path

        result = await self._mcp_request("zai.zread.get_repo_structure", args)
        return result

    async def read(
        self,
        repo: str,
        file_path: str,
    ) -> str:
        """Read a file from a GitHub repository.

        Args:
            repo: Repository in "owner/repo" format
            file_path: Path to the file (relative to repo root)

        Returns:
            File contents as string

        Raises:
            ValidationError: If repo format is invalid
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        validate_repo_format(repo)

        if not file_path or not file_path.strip():
            raise ValidationError("File path cannot be empty")

        args: dict[str, Any] = {
            "repo_name": repo,
            "file_path": file_path,
        }

        result = await self._mcp_request("zai.zread.read_file", args)
        return result
