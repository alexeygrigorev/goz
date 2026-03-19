"""Vision API client for Z.AI.

This module provides the VisionClient class for analyzing images and videos
using the Z.AI Anthropic-compatible API.
"""
import asyncio
import logging
from typing import Any

import httpx

from goz.api.image import (
    is_url,
    validate_image_source,
    validate_video_source,
    process_image_source,
    process_video_source,
    VIDEO_EXTENSIONS,
)
from goz.api.errors import ZaiError, AuthError, ApiError, NetworkError, TimeoutError
from goz.config import load_config, Config


# Default prompt for general image analysis
DEFAULT_ANALYZE_PROMPT = (
    "Analyze this image in detail. Describe the content, layout, colors, "
    "and any text you can see."
)

# Specialized prompts for different vision tasks
UI_TO_CODE_PROMPT = (
    "Describe in detail the layout structure, color style, main components, "
    "and interactive elements of the website in this image to facilitate "
    "subsequent code generation by the model. Return production-ready HTML/CSS code."
)

EXTRACT_TEXT_PROMPT = (
    "Extract all text content from this image exactly as it appears. "
    "Preserve code formatting and indentation."
)

DIAGNOSE_ERROR_PROMPT = (
    "Analyze this error screenshot. Explain: 1) What type of error occurred, "
    "2) The root cause, 3) Specific fix steps with code examples."
)

# Retry configuration
MAX_RETRIES = 2  # Total attempts: 3 (initial + 2 retries)
BASE_DELAY = 1.0  # Base delay in seconds


def build_vision_message(
    source: str,
    prompt: str | None,
    media_type: str = "image"
) -> list[dict[str, Any]]:
    """Build a multimodal message for vision API.

    Args:
        source: Image/video URL or base64 data URI
        prompt: Text prompt to send with the media
        media_type: Type of media ("image" or "video")

    Returns:
        List of message content parts for the API request
    """
    if prompt is None:
        prompt = DEFAULT_ANALYZE_PROMPT

    url_key = f"{media_type}_url"

    return [
        {"type": "text", "text": prompt},
        {"type": url_key, url_key: {"url": source}}
    ]


def parse_vision_response(response: dict[str, Any]) -> str:
    """Extract content from vision API response.

    Args:
        response: API response dict

    Returns:
        Content string from the response
    """
    return response["choices"][0]["message"]["content"]


class VisionClient:
    """Client for Z.AI Vision API operations.

    This client provides methods for analyzing images and videos using
    the Z.AI Anthropic-compatible API.
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialize VisionClient.

        Args:
            config: Optional config object. If not provided, loads from default location.
        """
        self.config = config or load_config()
        self.enable_logging = False  # Can be set via environment variable or parameter

    async def _request(
        self,
        endpoint: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Make HTTP request to API with retry logic.

        Args:
            endpoint: API endpoint path
            body: Request body dict

        Returns:
            Parsed JSON response dict

        Raises:
            AuthError: For 401/403 responses
            ApiError: For other 4xx/5xx responses
            NetworkError: For connection failures
            TimeoutError: For request timeouts
        """
        url = f"{self.config.anthropic_base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.config.anthropic_auth_token}",
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en",
        }
        timeout = self.config.timeout

        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if self.enable_logging:
                        logging.info(f"-> POST {endpoint} ({len(str(body))} bytes)")

                    response = await client.post(url, json=body, headers=headers)

                    if self.enable_logging:
                        logging.info(
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

            except httpx.TimeoutException as e:
                timeout_ms = int(timeout * 1000)
                last_error = TimeoutError(timeoutMs=timeout_ms)
                if self.enable_logging:
                    logging.error(f"! {last_error.__class__.__name__}: {last_error}")

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_error = NetworkError(f"Network error: {e}")
                if self.enable_logging:
                    logging.error(f"! {last_error.__class__.__name__}: {last_error}")

            except (AuthError, ApiError):
                # Don't retry auth or API errors
                raise

            except Exception as e:
                last_error = e
                if self.enable_logging:
                    logging.error(f"! Unexpected error: {e}")

            # Retry with exponential backoff
            if attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** attempt)
                if self.enable_logging:
                    logging.info(f"Retrying in {delay}s... (attempt {attempt + 1}/{MAX_RETRIES})")
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

    async def analyze(
        self,
        source: str,
        prompt: str | None = None,
    ) -> str:
        """Analyze an image or video.

        Args:
            source: Image/video file path or URL
            prompt: Optional custom prompt for analysis

        Returns:
            Analysis result text

        Raises:
            FileNotFoundError: If local file doesn't exist
            ValueError: If file size exceeds limit or format is unsupported
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        # Detect media type (image vs video)
        if is_url(source):
            # For URLs, check the file extension in the URL
            if any(source.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                media_type = "video"
                validate_video_source(source)
                processed_source = process_video_source(source)
            else:
                media_type = "image"
                validate_image_source(source)
                processed_source = process_image_source(source)
        else:
            # For local files, check the actual file extension
            from pathlib import Path
            ext = Path(source).suffix.lower()
            if ext in VIDEO_EXTENSIONS:
                media_type = "video"
                validate_video_source(source)
                processed_source = process_video_source(source)
            else:
                media_type = "image"
                validate_image_source(source)
                processed_source = process_image_source(source)

        # Build message content
        content = build_vision_message(processed_source, prompt, media_type)

        # Make API request
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 4096,
        }

        response = await self._request("/chat/completions", body)
        return parse_vision_response(response)

    async def ui_to_code(self, source: str) -> str:
        """Convert UI design to production-ready HTML/CSS code.

        Args:
            source: Image file path or URL

        Returns:
            Generated HTML/CSS code

        Raises:
            FileNotFoundError: If local file doesn't exist
            ValueError: If file size exceeds limit or format is unsupported
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        return await self.analyze(source, prompt=UI_TO_CODE_PROMPT)

    async def extract_text(self, source: str) -> str:
        """Extract all text content from an image.

        Args:
            source: Image file path or URL

        Returns:
            Extracted text content

        Raises:
            FileNotFoundError: If local file doesn't exist
            ValueError: If file size exceeds limit or format is unsupported
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        return await self.analyze(source, prompt=EXTRACT_TEXT_PROMPT)

    async def diagnose_error(self, source: str) -> str:
        """Diagnose an error from a screenshot.

        Args:
            source: Image file path or URL

        Returns:
            Error diagnosis with explanation and fix steps

        Raises:
            FileNotFoundError: If local file doesn't exist
            ValueError: If file size exceeds limit or format is unsupported
            AuthError: For authentication failures
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
        return await self.analyze(source, prompt=DIAGNOSE_ERROR_PROMPT)
