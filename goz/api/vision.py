"""Vision API client for Z.AI.

This module provides the VisionClient class for analyzing images and videos
using the Z.AI Anthropic-compatible API.
"""
import asyncio
import logging
from typing import Any

import anthropic
from anthropic import Anthropic, AsyncAnthropic

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


# Helper functions for backward compatibility with tests
def build_vision_message(
    source: str,
    prompt: str | None,
    media_type: str = "image",
) -> list[dict[str, Any]]:
    """Build a multimodal message for vision API (legacy helper for tests).

    Args:
        source: Image/video URL or base64 data URI
        prompt: Text prompt to send with the media
        media_type: Type of media ("image" or "video")

    Returns:
        List of message content parts for the API request (OpenAI-style for test compatibility)
    """
    if prompt is None:
        prompt = DEFAULT_ANALYZE_PROMPT

    url_key = f"{media_type}_url"

    return [
        {"type": "text", "text": prompt},
        {f"type": url_key, url_key: {"url": source}}
    ]


def parse_vision_response(response: dict[str, Any]) -> str:
    """Extract content from vision API response (legacy helper).

    Args:
        response: API response dict

    Returns:
        Content string from the response
    """
    # Handle Anthropic-style response
    if "content" in response:
        content = response["content"]
        if isinstance(content, list) and len(content) > 0:
            return content[0].get("text", "")
        return str(content)
    # Handle OpenAI-style response (legacy)
    if "choices" in response:
        return response["choices"][0]["message"]["content"]
    return str(response)


class VisionClient:
    """Client for Z.AI Vision API operations using Anthropic SDK.

    This client provides methods for analyzing images and videos using
    the Z.AI Anthropic-compatible API.
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialize VisionClient.

        Args:
            config: Optional config object. If not provided, loads from default location.
        """
        self.config = config or load_config()
        self.enable_logging = False

        # Initialize async Anthropic client
        self._client = AsyncAnthropic(
            api_key=self.config.zai_token,
            base_url=self.config.zai_base_url,
            timeout=self.config.timeout,
        )

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
            if any(source.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                media_type = "video"
                validate_video_source(source)
                processed_source = process_video_source(source)
            else:
                media_type = "image"
                validate_image_source(source)
                processed_source = process_image_source(source)
        else:
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

        # Build content for Anthropic API
        if prompt is None:
            prompt = DEFAULT_ANALYZE_PROMPT

        content = [
            {"type": "text", "text": prompt},
        ]

        if media_type == "image":
            content.append({
                "type": "image",
                "source": {"type": "url", "url": processed_source}
            })
        else:  # video
            content.append({
                "type": "video",
                "source": {"type": "url", "url": processed_source}
            })

        try:
            response = await self._client.messages.create(
                model=self.config.vision_model,
                max_tokens=self.config.max_tokens,
                messages=[{"role": "user", "content": content}],
            )
            return response.content[0].text
        except anthropic.AuthenticationError as e:
            raise AuthError(str(e))
        except anthropic.APITimeoutError as e:
            raise TimeoutError(timeoutMs=int(self.config.timeout * 1000))
        except anthropic.APIConnectionError as e:
            raise NetworkError(str(e))
        except anthropic.APIStatusError as e:
            raise ApiError(str(e), statusCode=e.status_code)
        except Exception as e:
            raise ZaiError(f"Unexpected error: {e}")

    async def analyze_stream(
        self,
        source: str,
        prompt: str | None = None,
    ):
        """Analyze an image or video with streaming response.

        Yields chunks of the response as they arrive.

        Args:
            source: Image/video file path or URL
            prompt: Optional custom prompt for analysis

        Yields:
            Chunks of response text as they arrive

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
            if any(source.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                media_type = "video"
                validate_video_source(source)
                processed_source = process_video_source(source)
            else:
                media_type = "image"
                validate_image_source(source)
                processed_source = process_image_source(source)
        else:
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

        # Build content for Anthropic API
        if prompt is None:
            prompt = DEFAULT_ANALYZE_PROMPT

        content = [
            {"type": "text", "text": prompt},
        ]

        if media_type == "image":
            content.append({
                "type": "image",
                "source": {"type": "url", "url": processed_source}
            })
        else:  # video
            content.append({
                "type": "video",
                "source": {"type": "url", "url": processed_source}
            })

        try:
            async with self._client.messages.stream(
                model=self.config.vision_model,
                max_tokens=self.config.max_tokens,
                messages=[{"role": "user", "content": content}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError as e:
            raise AuthError(str(e))
        except anthropic.APITimeoutError as e:
            raise TimeoutError(timeoutMs=int(self.config.timeout * 1000))
        except anthropic.APIConnectionError as e:
            raise NetworkError(str(e))
        except anthropic.APIStatusError as e:
            raise ApiError(str(e), statusCode=e.status_code)
        except Exception as e:
            raise ZaiError(f"Unexpected error: {e}")

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
