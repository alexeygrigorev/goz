"""Z.AI API client for vision, search, and reader.

Following TDD: tests are written first, then implementation follows.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx

from goz.api.errors import ApiError, AuthError, NetworkError, TimeoutError, ZaiError
from goz.config import Config, load_config


# Logger for API requests
logger = logging.getLogger(__name__)


def with_retry(max_retries: int = 2, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 2)
        base_delay: Base delay in seconds (default: 1.0)

    Returns:
        Decorator function
    """
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            last_error: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except AuthError:
                    # Don't retry auth errors
                    raise
                except Exception as e:
                    last_error = e

                    # Don't retry on last attempt
                    if attempt == max_retries:
                        break

                    # Exponential backoff
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

            raise last_error
        return wrapper
    return decorator


class ZaiApiClient:
    """Z.AI API client.

    This client handles HTTP requests to the Z.AI API with retry logic,
    error handling, and optional logging.
    """

    def __init__(
        self,
        config: Config | None = None,
        enable_logging: bool | None = None,
    ) -> None:
        """Initialize ZaiApiClient.

        Args:
            config: Optional Config object. If not provided, loads from default location.
            enable_logging: Optional flag to enable logging. If not provided, checks
                GOZ_API_LOG environment variable.
        """
        self.config = config or load_config()

        # Enable logging if explicitly set or GOZ_API_LOG env var is set
        if enable_logging is None:
            enable_logging = os.getenv("GOZ_API_LOG", "").lower() in ("1", "true", "yes")
        self.enable_logging = enable_logging

    @with_retry(max_retries=2, base_delay=1.0)
    async def request(
        self,
        endpoint: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Make an HTTP POST request to the API.

        Args:
            endpoint: API endpoint path (e.g., '/chat/completions')
            body: Request body as dictionary

        Returns:
            Parsed JSON response as dictionary

        Raises:
            AuthError: For 401/403 responses
            ApiError: For other 4xx/5xx responses
            TimeoutError: For request timeouts
            NetworkError: For network failures
        """
        url = f"{self.config.zai_base_url}{endpoint}"
        timeout_ms = self.config.timeout * 1000

        if self.enable_logging:
            logger.debug("-> POST %s (%d bytes)", endpoint, len(json.dumps(body)))

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
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

                # Return parsed JSON
                return response.json()

        except asyncio.TimeoutError as e:
            if self.enable_logging:
                logger.error("! TimeoutError: Request timed out after %dms", timeout_ms)
            raise TimeoutError(timeout_ms) from e
        except httpx.TimeoutException as e:
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
        except AuthError:
            # Re-raise AuthError as-is
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

        # Try to parse error message from JSON
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

        Handles nested error structures like:
        - {"error": {"message": "..."}}
        - {"message": "..."}
        - {"error": "..."}

        Args:
            response: HTTP response object

        Returns:
            Extracted error message
        """
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
