"""Reader API client for Z.AI.

This module provides the ReaderClient class for fetching and converting
web pages to markdown/text format using the Z.AI Web Reader API.
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


# Logger for reader API requests
logger = logging.getLogger(__name__)


# Default timeout matching reference implementation
DEFAULT_TIMEOUT = 20

# Valid format values
VALID_FORMATS = ("markdown", "text")


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


def validate_url(url: str) -> str:
    """Validate URL format.

    Args:
        url: URL to validate

    Returns:
        The validated URL

    Raises:
        ValidationError: If URL format is invalid
    """
    if not url or not url.strip():
        raise ValidationError("URL cannot be empty")

    url = url.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValidationError(
            f"Invalid URL protocol: URL must start with http:// or https://. "
            f"Got: {url[:50]}{'...' if len(url) > 50 else ''}"
        )

    return url


def validate_format(format_value: str) -> str:
    """Validate and normalize format value.

    Args:
        format_value: Format string to validate

    Returns:
        Normalized format value (lowercase)

    Raises:
        ValidationError: If format is invalid
    """
    if not isinstance(format_value, str):
        raise ValidationError(
            f"Invalid format: must be a string. Got: {type(format_value).__name__}"
        )

    normalized = format_value.lower().strip()

    if normalized not in VALID_FORMATS:
        raise ValidationError(
            f"Invalid format: '{format_value}'. Must be one of: {', '.join(VALID_FORMATS)}"
        )

    return normalized


def validate_timeout(timeout: int) -> int:
    """Validate timeout value.

    Args:
        timeout: Timeout value in seconds

    Returns:
        Validated timeout value

    Raises:
        ValidationError: If timeout is invalid
    """
    if not isinstance(timeout, int):
        raise ValidationError(
            f"Invalid timeout: must be an integer. Got: {type(timeout).__name__}"
        )

    if timeout <= 0:
        raise ValidationError(
            f"Invalid timeout: must be a positive integer. Got: {timeout}"
        )

    return timeout


class ReaderClient:
    """Client for Z.AI Web Reader API operations.

    This client provides methods for fetching and parsing web page content
    from URLs, with support for markdown/text conversion, cache control,
    and various other options.
    """

    def __init__(
        self,
        config: Config | None = None,
        enable_logging: bool | None = None,
    ) -> None:
        """Initialize ReaderClient.

        Args:
            config: Optional Config object. If not provided, loads from default location.
            enable_logging: Optional flag to enable logging. If not provided, checks
                GOZ_API_LOG environment variable.
        """
        self.config = config or load_config()

        # Enable logging if explicitly set or GOZ_API_LOG env var is set
        import os
        if enable_logging is None:
            enable_logging = os.getenv("GOZ_API_LOG", "").lower() in ("1", "true", "yes")
        self.enable_logging = enable_logging

    async def read(
        self,
        url: str,
        format: Literal["markdown", "text"] = "markdown",
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
            ValidationError: If URL format is invalid or parameters are invalid
            AuthError: For authentication failures (401/403)
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        # Validate inputs
        url = validate_url(url)
        format = validate_format(format)
        timeout = validate_timeout(timeout)

        # Build request body
        body = {
            "url": url,
            "return_format": format,
            "timeout": timeout,
            "no_cache": no_cache,
            "retain_images": retain_images,
            "with_links_summary": with_links_summary,
        }

        return await self._request("/reader", body)

    async def _request(
        self,
        endpoint: str,
        body: dict[str, Any],
    ) -> ReaderResult:
        """Make HTTP request to reader API.

        Args:
            endpoint: API endpoint path
            body: Request body dict

        Returns:
            ReaderResult with parsed content

        Raises:
            AuthError: For 401/403 responses
            ApiError: For other 4xx/5xx responses
            TimeoutError: For request timeouts
            NetworkError: For network failures
        """
        url = f"{self.config.zai_base_url}{endpoint}"

        if self.enable_logging:
            logger.debug("-> POST %s (%d bytes)", endpoint, len(str(body)))

        # Get timeout from body for httpx client
        request_timeout = body.get("timeout", DEFAULT_TIMEOUT)

        try:
            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.post(
                    url,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {self.config.zai_token}",
                        "Content-Type": "application/json",
                        "Accept-Language": "en-US,en",
                    },
                )

                if self.enable_logging:
                    logger.debug(
                        "<- %d %d bytes",
                        response.status_code,
                        len(response.content),
                    )

                # Handle error responses
                if not response.is_success:
                    self._handle_error_response(response)

                # Parse and return result
                return self._parse_reader_response(response.json(), body["url"])

        except asyncio.TimeoutError as e:
            timeout_ms = body.get("timeout", DEFAULT_TIMEOUT) * 1000
            if self.enable_logging:
                logger.error("! TimeoutError: Request timed out after %dms", timeout_ms)
            raise TimeoutError(timeout_ms) from e
        except httpx.TimeoutException as e:
            timeout_ms = body.get("timeout", DEFAULT_TIMEOUT) * 1000
            if self.enable_logging:
                logger.error("! TimeoutException: Request timed out after %dms", timeout_ms)
            raise TimeoutError(timeout_ms) from e
        except httpx.ConnectError as e:
            if self.enable_logging:
                logger.error("! NetworkError: %s", e)
            raise NetworkError(str(e)) from e
        except httpx.NetworkError as e:
            if self.enable_logging:
                logger.error("! NetworkError: %s", e)
            raise NetworkError(str(e)) from e
        except (AuthError, ApiError):
            # Re-raise these as-is
            raise
        except ZaiError:
            # Re-raise other ZaiErrors as-is
            raise
        except Exception as e:
            if self.enable_logging:
                logger.error("! %s: %s", type(e).__name__, e)
            raise

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error response from API.

        Args:
            response: HTTP response object

        Raises:
            AuthError: For 401/403 responses
            ApiError: For other error responses
        """
        status_code = response.status_code
        error_message = self._parse_error_message(response)

        if self.enable_logging:
            logger.error("! %d: %s", status_code, error_message)

        # Raise appropriate error based on status code
        if status_code in (401, 403):
            raise AuthError(error_message, statusCode=status_code)
        else:
            raise ApiError(error_message, statusCode=status_code)

    def _parse_error_message(self, response: httpx.Response) -> str:
        """Parse error message from response.

        Args:
            response: HTTP response object

        Returns:
            Extracted error message
        """
        import json

        try:
            data = response.json()

            # Try nested error.message
            if isinstance(data.get("error"), dict):
                msg = data["error"].get("message")
                if msg:
                    return msg if isinstance(msg, str) else json.dumps(msg)

            # Try top-level message
            if "message" in data:
                msg = data["message"]
                return msg if isinstance(msg, str) else json.dumps(msg)

            # Try error field
            if "error" in data:
                msg = data["error"]
                return msg if isinstance(msg, str) else json.dumps(msg)

        except (json.JSONDecodeError, ValueError):
            # Not JSON, use text as-is
            pass

        return response.text or f"HTTP {response.status_code}"

    def _parse_reader_response(
        self,
        data: dict[str, Any],
        original_url: str,
    ) -> ReaderResult:
        """Parse reader API response into ReaderResult.

        Args:
            data: Response JSON data
            original_url: The original URL requested

        Returns:
            ReaderResult with parsed content

        Raises:
            ApiError: If response format is invalid
        """
        try:
            reader_result = data["reader_result"]

            return ReaderResult(
                content=reader_result["content"],
                title=reader_result["title"],
                url=reader_result.get("url", original_url),
                description=reader_result.get("description"),
            )
        except (KeyError, TypeError) as e:
            raise ApiError(f"Invalid response format: {e}") from e
