"""Unit tests for Vision API client (Issue 04)."""
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Any

import pytest

from goz.api.vision import (
    VisionClient,
    build_vision_message,
    parse_vision_response,
)


# Helper function to create a proper AsyncClient mock
def create_mock_async_client(response: Mock) -> Mock:
    """Create a mock AsyncClient that works with async context manager."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)

    # Create the async context manager
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    return mock_cm


class MockAsyncClient:
    """Mock AsyncClient that supports async context manager protocol."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.post = AsyncMock(return_value=response)

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class TestBuildVisionMessage:
    """Unit Tests: build_vision_message() creates correct multimodal message structure."""

    def test_build_vision_message_with_image_url(self):
        """Test build_vision_message with image URL."""
        content = build_vision_message(
            source="https://example.com/image.png",
            prompt="Analyze this image",
            media_type="image"
        )

        assert content == [
            {"type": "text", "text": "Analyze this image"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}
        ]

    def test_build_vision_message_with_image_base64(self):
        """Test build_vision_message with base64 image data."""
        content = build_vision_message(
            source="data:image/png;base64,iVBORw0KG...",
            prompt="What is this?",
            media_type="image"
        )

        assert content == [
            {"type": "text", "text": "What is this?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KG..."}}
        ]

    def test_build_vision_message_with_video_url(self):
        """Test build_vision_message with video URL."""
        content = build_vision_message(
            source="https://example.com/video.mp4",
            prompt="Analyze this video",
            media_type="video"
        )

        assert content == [
            {"type": "text", "text": "Analyze this video"},
            {"type": "video_url", "video_url": {"url": "https://example.com/video.mp4"}}
        ]

    def test_build_vision_message_with_video_base64(self):
        """Test build_vision_message with base64 video data."""
        content = build_vision_message(
            source="data:video/mp4;base64,AAAAHGZ0eXBN...",
            prompt="What happens in this video?",
            media_type="video"
        )

        assert content == [
            {"type": "text", "text": "What happens in this video?"},
            {"type": "video_url", "video_url": {"url": "data:video/mp4;base64,AAAAHGZ0eXBN..."}}
        ]

    def test_build_vision_message_with_default_prompt(self):
        """Test build_vision_message with default prompt."""
        content = build_vision_message(
            source="https://example.com/image.png",
            prompt=None,
            media_type="image"
        )

        assert content == [
            {"type": "text", "text": "Analyze this image in detail. Describe the content, layout, colors, and any text you can see."},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}
        ]


class TestParseVisionResponse:
    """Unit Tests: parse_vision_response() extracts content from response."""

    def test_parse_vision_response_extracts_content(self):
        """Test parse_vision_response extracts content from response."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": "This is a detailed analysis of the image."
                    }
                }
            ]
        }

        result = parse_vision_response(response)
        assert result == "This is a detailed analysis of the image."

    def test_parse_vision_response_handles_nested_structure(self):
        """Test parse_vision_response handles nested API response."""
        response = {
            "id": "msg-123",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Here's the code you requested."
                    }
                }
            ]
        }

        result = parse_vision_response(response)
        assert result == "Here's the code you requested."

    def test_parse_vision_response_handles_multiline_content(self):
        """Test parse_vision_response preserves multiline content."""
        response = {
            "choices": [
                {
                    "message": {
                        "content": "Line 1\nLine 2\nLine 3"
                    }
                }
            ]
        }

        result = parse_vision_response(response)
        assert result == "Line 1\nLine 2\nLine 3"


class TestVisionClientAnalyze:
    """Tests for VisionClient.analyze() method."""

    @pytest.mark.asyncio
    async def test_analyze_with_image_url(self, tmp_path):
        """Test analyze with image URL."""
        # Create a mock config
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This image shows a dashboard with metrics."}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.validate_image_source") as mock_validate:
                with patch("goz.api.vision.process_image_source", return_value="https://example.com/image.png") as mock_process:
                    with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                        client = VisionClient()
                        result = await client.analyze("https://example.com/image.png")

                        assert result == "This image shows a dashboard with metrics."
                        mock_validate.assert_called_once_with("https://example.com/image.png")
                        mock_process.assert_called_once_with("https://example.com/image.png")

    @pytest.mark.asyncio
    async def test_analyze_with_local_image(self, tmp_path):
        """Test analyze with local image file."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is a screenshot of code."}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.validate_image_source"):
                with patch("goz.api.vision.process_image_source", return_value="data:image/png;base64,ABC123"):
                    with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                        client = VisionClient()
                        result = await client.analyze("/path/to/screenshot.png")

                        assert result == "This is a screenshot of code."

    @pytest.mark.asyncio
    async def test_analyze_with_custom_prompt(self, tmp_path):
        """Test analyze with custom prompt."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Custom analysis result."}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.validate_image_source"):
                with patch("goz.api.vision.process_image_source"):
                    with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                        client = VisionClient()
                        result = await client.analyze("image.png", prompt="Describe the colors used")

                        assert result == "Custom analysis result."


class TestVisionClientUiToCode:
    """Tests for VisionClient.ui_to_code() method."""

    @pytest.mark.asyncio
    async def test_ui_to_code_uses_specialized_prompt(self, tmp_path):
        """Test ui_to_code uses specialized prompt for UI to code."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "<html>...</html>"}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.validate_image_source"):
                with patch("goz.api.vision.process_image_source"):
                    with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                        client = VisionClient()
                        result = await client.ui_to_code("mockup.png")

                        assert result == "<html>...</html>"
                        # Verify the specialized prompt was used
                        call_args = mock_async_client.post.call_args
                        body = call_args[1]["json"]
                        prompt = body["messages"][0]["content"][0]["text"]
                        assert "Describe in detail the layout structure" in prompt
                        assert "production-ready HTML/CSS code" in prompt


class TestVisionClientExtractText:
    """Tests for VisionClient.extract_text() method."""

    @pytest.mark.asyncio
    async def test_extract_text_uses_specialized_prompt(self, tmp_path):
        """Test extract_text uses specialized prompt for text extraction."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "def hello():\n    print('world')"}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.validate_image_source"):
                with patch("goz.api.vision.process_image_source"):
                    with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                        client = VisionClient()
                        result = await client.extract_text("screenshot.png")

                        assert result == "def hello():\n    print('world')"
                        # Verify the specialized prompt was used
                        call_args = mock_async_client.post.call_args
                        body = call_args[1]["json"]
                        prompt = body["messages"][0]["content"][0]["text"]
                        assert "Extract all text content" in prompt
                        assert "Preserve code formatting" in prompt


class TestVisionClientDiagnoseError:
    """Tests for VisionClient.diagnose_error() method."""

    @pytest.mark.asyncio
    async def test_diagnose_error_uses_specialized_prompt(self, tmp_path):
        """Test diagnose_error uses specialized prompt for error diagnosis."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Error: TypeError\nCause: NoneType has no attribute\nFix: Check if variable is None"}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.validate_image_source"):
                with patch("goz.api.vision.process_image_source"):
                    with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                        client = VisionClient()
                        result = await client.diagnose_error("error.png")

                        assert "Error: TypeError" in result
                        # Verify the specialized prompt was used
                        call_args = mock_async_client.post.call_args
                        body = call_args[1]["json"]
                        prompt = body["messages"][0]["content"][0]["text"]
                        assert "Analyze this error screenshot" in prompt
                        assert "root cause" in prompt
                        assert "fix steps" in prompt


class TestVisionClientWithVideo:
    """Tests for VisionClient with video files."""

    @pytest.mark.asyncio
    async def test_analyze_video_file(self, tmp_path):
        """Test analyze with video file."""
        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This video shows a user clicking through a form."}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.validate_video_source"):
                with patch("goz.api.vision.process_video_source", return_value="data:video/mp4;base64,ABC123"):
                    with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                        client = VisionClient()
                        result = await client.analyze("demo.mp4")

                        assert result == "This video shows a user clicking through a form."
                        # Verify video_url type was used in the request
                        call_args = mock_async_client.post.call_args
                        body = call_args[1]["json"]
                        content = body["messages"][0]["content"]
                        assert any(item.get("type") == "video_url" for item in content)
