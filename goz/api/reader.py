"""Reader API client for Z.AI.

This module provides the ReaderClient class for fetching and converting
web pages to markdown/text format using the Z.AI Web Reader API via direct HTTP.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from goz.api.errors import (
    ApiError,
    AuthError,
    NetworkError,
    TimeoutError,
    ValidationError,
    ZaiError,
)
from goz.config import Config, load_config


# Type definitions
ReturnFormat = Literal["markdown", "text"]


# Constants
VALID_FORMATS = ["markdown", "text"]
DEFAULT_TIMEOUT = 20
RETRY_COUNT = 0
BASE_DELAY = 1.0

# Direct HTTP endpoint (uses coding/paas base URL)
CODING_PAAS_BASE = "https://api.z.ai/api/coding/paas/v4"
READER_API_ENDPOINT = f"{CODING_PAAS_BASE}/reader"


# Logger for reader requests
logger = logging.getLogger(__name__)


@dataclass
class ReaderResult:
    """Result from web reader API.

    Attributes:
        content: The main page content as markdown/text
        title: Page title
        url: Original URL
        description: Page meta description (if available)
    """
    content: str
    title: str
    url: str
    description: str | None = None

    def __repr__(self) -> str:
        """Return readable string representation."""
        return f"ReaderResult(title={self.title!r}, url={self.url!r})"


def validate_reader_params(
    url: str,
    format: ReturnFormat | None = None,
    timeout: int | None = None,
) -> None:
    """Validate reader parameters.

    Args:
        url: URL to fetch
        format: Optional return format
        timeout: Optional timeout value

    Raises:
        ValueError: If any parameter is invalid
    """
    if not url or not url.strip():
        raise ValueError("URL cannot be empty")

    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(
            f"Invalid URL protocol: URL must start with http:// or https://. Got: {url[:50]}..."
        )

    if format is not None and format not in VALID_FORMATS:
        raise ValueError(
            f"Invalid format: {format}. Valid options: {', '.join(VALID_FORMATS)}"
        )

    if timeout is not None and timeout <= 0:
        raise ValueError("Timeout must be a positive integer")


class ReaderClient:
    """Web reader client using Z.AI Web Reader API.

    This client provides web page fetching functionality with support for
    markdown/text conversion, cache control, and various other options.
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialize ReaderClient.

        Args:
            config: Optional config object. If not provided, loads from default location.
        """
        self.config = config or load_config()
        self.enable_logging = False

    async def _http_request(
        self,
        body: dict[str, Any],
    ) -> Any:
        """Make HTTP request to Reader API.

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
                        logger.info(f"-> POST {READER_API_ENDPOINT}")

                    response = await client.post(READER_API_ENDPOINT, json=body, headers=headers)

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

    async def read(
        self,
        url: str,
        format: ReturnFormat = "markdown",
        timeout: int = DEFAULT_TIMEOUT,
        no_cache: bool = False,
        retain_images: bool = True,
        with_links_summary: bool = False,
    ) -> ReaderResult:
        """Fetch and parse web page content.

        Args:
            url: The URL to fetch (must start with http:// or https://)
            format: Output format - "markdown" or "text" (default: "markdown")
            timeout: Request timeout in seconds (default: 20)
            no_cache: Bypass server cache (default: False)
            retain_images: Include images in output (default: True)
            with_links_summary: Include links summary (default: False)

        Returns:
            ReaderResult with parsed content

        Raises:
            ValueError: If URL is empty or parameters are invalid
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        validate_reader_params(url, format, timeout)

        # Build request body
        body: dict[str, Any] = {
            "url": url,
            "return_format": format,
            "timeout": timeout,
            "no_cache": no_cache,
            "retain_images": retain_images,
            "with_links_summary": with_links_summary,
        }

        # Make HTTP request
        result_data = await self._http_request(body)

        # Parse result into ReaderResult
        if isinstance(result_data, dict):
            reader_result = result_data.get("reader_result", result_data)
            return ReaderResult(
                content=reader_result.get("content", ""),
                title=reader_result.get("title", ""),
                url=reader_result.get("url", url),
                description=reader_result.get("description"),
            )

        # Fallback for non-dict responses
        return ReaderResult(
            content=str(result_data),
            title="",
            url=url,
            description=None,
        )
