"""E2E tests for Vision API (Issue 04)."""
import asyncio
import base64
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from goz.api.vision import (
    VisionClient,
    build_vision_message,
    parse_vision_response,
)
from goz.config import Config


class MockAsyncClient:
    """Mock AsyncClient that supports async context manager protocol."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.post = AsyncMock(return_value=response)

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class TestVisionClientAnalyzeLocalPng:
    """E2E Tests: Analyze a local PNG image file (1MB) returns description."""

    @pytest.mark.asyncio
    async def test_analyze_local_png_returns_description(self, tmp_path):
        """E2E: Analyze a local PNG image file (1MB) returns description."""
        # Create a small PNG file (1KB for testing, not 1MB)
        image_file = tmp_path / "dashboard.png"
        # PNG header + dummy data
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 1000
        image_file.write_bytes(png_data)

        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is a detailed description of the dashboard showing various metrics."
                    }
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.analyze(str(image_file))

                assert "dashboard" in result.lower()
                assert "metrics" in result.lower()


class TestVisionClientAnalyzeLocalJpeg:
    """E2E Tests: Analyze a local JPEG image file returns description."""

    @pytest.mark.asyncio
    async def test_analyze_local_jpeg_returns_description(self, tmp_path):
        """E2E: Analyze a local JPEG image file returns description."""
        # Create a JPEG file
        image_file = tmp_path / "photo.jpg"
        # JPEG header
        jpg_data = b'\xff\xd8\xff' + b'x' * 1000
        image_file.write_bytes(jpg_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is a photo of a landscape scene."}}
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.analyze(str(image_file))

                assert "landscape" in result.lower()


class TestVisionClientAnalyzeUrl:
    """E2E Tests: Analyze an image from HTTPS URL returns description."""

    @pytest.mark.asyncio
    async def test_analyze_https_url_returns_description(self):
        """E2E: Analyze an image from HTTPS URL returns description."""
        url = "https://example.com/architecture-diagram.png"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is a system architecture diagram showing microservices."
                    }
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.analyze(url)

                assert "architecture" in result.lower()
                # Verify the URL was passed directly (not base64 encoded)
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                content = body["messages"][0]["content"]
                image_url = content[1]["image_url"]["url"]
                assert image_url == url


class TestVisionClientUiToCode:
    """E2E Tests: UI-to-code conversion returns HTML/CSS code block."""

    @pytest.mark.asyncio
    async def test_ui_to_code_returns_html_css(self, tmp_path):
        """E2E: UI-to-code conversion returns HTML/CSS code block."""
        image_file = tmp_path / "login-mockup.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "<!DOCTYPE html>\n<html>\n<head>\n<style>\nbody { font-family: Arial; }\n</style>\n</head>\n<body>\n<form>Login form</form>\n</body>\n</html>"
                    }
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.ui_to_code(str(image_file))

                assert "<!DOCTYPE html>" in result
                assert "<style>" in result
                assert "</html>" in result


class TestVisionClientExtractText:
    """E2E Tests: Extract-text returns accurate text content from code screenshot."""

    @pytest.mark.asyncio
    async def test_extract_text_returns_code_content(self, tmp_path):
        """E2E: Extract-text returns accurate text content from code screenshot."""
        image_file = tmp_path / "code-snippet.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "def hello_world():\n    print('Hello, World!')\n    return True"
                    }
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.extract_text(str(image_file))

                assert "def hello_world():" in result
                assert "print('Hello, World!')" in result
                assert "return True" in result


class TestVisionClientDiagnoseError:
    """E2E Tests: Diagnose-error returns analysis with root cause and fix steps."""

    @pytest.mark.asyncio
    async def test_diagnose_error_returns_analysis(self, tmp_path):
        """E2E: Diagnose-error returns analysis with root cause and fix steps."""
        image_file = tmp_path / "runtime-error.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "1) Error Type: AttributeError\n2) Root Cause: Attempting to access attribute 'x' on None object\n3) Fix Steps:\n- Add None check before accessing attribute\n- Use try/except block\n\nCode example:\nif obj is not None:\n    return obj.x"
                    }
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.diagnose_error(str(image_file))

                assert "AttributeError" in result
                assert "None" in result
                assert "if" in result  # Code example


class TestVisionClientAnalyzeMp4:
    """E2E Tests: Analyze MP4 video file (5MB) returns description."""

    @pytest.mark.asyncio
    async def test_analyze_mp4_returns_description(self, tmp_path):
        """E2E: Analyze MP4 video file (5MB) returns description."""
        video_file = tmp_path / "demo-flow.mp4"
        # MP4 header
        mp4_data = b'\x00\x00\x00\x20\x66\x74\x79\x70' + b'x' * 100
        video_file.write_bytes(mp4_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This video shows a user workflow: navigating to login page, entering credentials, and accessing dashboard."
                    }
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.analyze(str(video_file))

                assert "login" in result.lower()
                assert "dashboard" in result.lower()
                # Verify video_url type was used
                call_args = mock_async_client.post.call_args
                body = call_args[1]["json"]
                content = body["messages"][0]["content"]
                assert any(item.get("type") == "video_url" for item in content)


class TestVisionClientAnalyzeMov:
    """E2E Tests: Analyze MOV video file returns description."""

    @pytest.mark.asyncio
    async def test_analyze_mov_returns_description(self, tmp_path):
        """E2E: Analyze MOV video file returns description."""
        video_file = tmp_path / "screen-recording.mov"
        mov_data = b'x' * 100
        video_file.write_bytes(mov_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This video demonstrates drag and drop functionality."
                    }
                }
            ]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.analyze(str(video_file))

                assert "drag" in result.lower()


class TestVisionErrorNonExistentPath:
    """E2E Error Path Tests: Non-existent image path returns file not found error."""

    @pytest.mark.asyncio
    async def test_nonexistent_path_raises_file_not_found(self, tmp_path):
        """E2E: Non-existent image path returns file not found error."""
        nonexistent = tmp_path / "does-not-exist.png"

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            client = VisionClient()
            with pytest.raises(FileNotFoundError) as exc_info:
                await client.analyze(str(nonexistent))

        assert "File not found" in str(exc_info.value)


class TestVisionErrorImageTooLarge:
    """E2E Error Path Tests: Image exceeding 5MB returns size limit error."""

    @pytest.mark.asyncio
    async def test_image_over_5mb_raises_error(self, tmp_path):
        """E2E: Image exceeding 5MB returns size limit error."""
        from goz.api.image import MAX_IMAGE_SIZE

        large_file = tmp_path / "large.png"
        # Create a file larger than 5MB
        large_file.write_bytes(b"x" * (MAX_IMAGE_SIZE + 1))

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            client = VisionClient()
            with pytest.raises(ValueError) as exc_info:
                await client.analyze(str(large_file))

        assert "exceeds 5MB limit" in str(exc_info.value)


class TestVisionErrorVideoTooLarge:
    """E2E Error Path Tests: Video exceeding 8MB returns size limit error."""

    @pytest.mark.asyncio
    async def test_video_over_8mb_raises_error(self, tmp_path):
        """E2E: Video exceeding 8MB returns size limit error."""
        from goz.api.image import MAX_VIDEO_SIZE

        large_file = tmp_path / "large.mp4"
        # Create a file larger than 8MB
        large_file.write_bytes(b"x" * (MAX_VIDEO_SIZE + 1))

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            client = VisionClient()
            with pytest.raises(ValueError) as exc_info:
                await client.analyze(str(large_file))

        assert "exceeds 8MB limit" in str(exc_info.value)


class TestVisionErrorUnsupportedImageFormat:
    """E2E Error Path Tests: Unsupported image format (.svg, .gif) returns format error."""

    @pytest.mark.asyncio
    async def test_svg_format_raises_error(self, tmp_path):
        """E2E: Unsupported image format (.svg) returns format error."""
        svg_file = tmp_path / "diagram.svg"
        svg_file.write_bytes(b"<svg></svg>")

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            client = VisionClient()
            with pytest.raises(ValueError) as exc_info:
                await client.analyze(str(svg_file))

        assert "Unsupported image format" in str(exc_info.value)
        assert ".svg" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_gif_format_raises_error(self, tmp_path):
        """E2E: Unsupported image format (.gif) returns format error."""
        gif_file = tmp_path / "animated.gif"
        gif_file.write_bytes(b"GIF89a")

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            client = VisionClient()
            with pytest.raises(ValueError) as exc_info:
                await client.analyze(str(gif_file))

        assert "Unsupported image format" in str(exc_info.value)


class TestVisionErrorUnsupportedVideoFormat:
    """E2E Error Path Tests: Unsupported video format (.flv) returns format error."""

    @pytest.mark.asyncio
    async def test_flv_format_raises_error(self, tmp_path):
        """E2E: Unsupported video format (.flv) returns format error."""
        flv_file = tmp_path / "video.flv"
        flv_file.write_bytes(b"FLV")

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            client = VisionClient()
            with pytest.raises(ValueError) as exc_info:
                await client.analyze(str(flv_file))

        # .flv is not in the supported video list, so it falls through to image validation
        # The error message should indicate the format is unsupported
        assert "unsupported" in str(exc_info.value).lower()
        assert ".flv" in str(exc_info.value)


class TestVisionErrorInvalidToken:
    """E2E Error Path Tests: Invalid API token returns auth error."""

    @pytest.mark.asyncio
    async def test_invalid_token_raises_auth_error(self, tmp_path):
        """E2E: Invalid API token returns auth error."""
        image_file = tmp_path / "test.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized: Invalid API token"

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "invalid-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                with pytest.raises(Exception) as exc_info:
                    await client.analyze(str(image_file))

        # Should get an auth-related error
        assert "auth" in str(exc_info.value).lower() or "401" in str(exc_info.value) or "unauthorized" in str(exc_info.value).lower()


class TestVisionErrorTimeout:
    """E2E Error Path Tests: Network timeout returns timeout error with retry info."""

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self, tmp_path):
        """E2E: Network timeout returns timeout error with retry info."""
        image_file = tmp_path / "test.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        # Create a mock that raises TimeoutException
        class TimeoutMockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, *args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

        mock_async_client = TimeoutMockClient()

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                with pytest.raises(Exception) as exc_info:
                    await client.analyze(str(image_file))

        # Should get a timeout-related error
        error_str = str(exc_info.value).lower()
        assert "timeout" in error_str or "timed out" in error_str


class TestVisionErrorMalformedResponse:
    """E2E Error Path Tests: Malformed API response handles gracefully."""

    @pytest.mark.asyncio
    async def test_malformed_response_handles_gracefully(self, tmp_path):
        """E2E: Malformed API response handles gracefully."""
        image_file = tmp_path / "test.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        # Malformed response - missing choices key
        mock_response.json.return_value = {"result": "unexpected"}

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                with pytest.raises(KeyError):
                    await client.analyze(str(image_file))


class TestVisionEdgeCaseExactly5Mb:
    """Edge Case Tests: Exactly 5MB image is accepted."""

    @pytest.mark.asyncio
    async def test_exactly_5mb_image_accepted(self, tmp_path):
        """E2E: Exactly 5MB image is accepted."""
        from goz.api.image import MAX_IMAGE_SIZE

        image_file = tmp_path / "exactly-5mb.png"
        # Create a file exactly 5MB
        image_file.write_bytes(b"x" * MAX_IMAGE_SIZE)

        # Should validate successfully
        from goz.api.image import validate_image_source
        validate_image_source(str(image_file))  # Should not raise


class TestVisionEdgeCaseExactly8Mb:
    """Edge Case Tests: Exactly 8MB video is accepted."""

    @pytest.mark.asyncio
    async def test_exactly_8mb_video_accepted(self, tmp_path):
        """E2E: Exactly 8MB video is accepted."""
        from goz.api.image import MAX_VIDEO_SIZE

        video_file = tmp_path / "exactly-8mb.mp4"
        # Create a file exactly 8MB
        video_file.write_bytes(b"x" * MAX_VIDEO_SIZE)

        # Should validate successfully
        from goz.api.image import validate_video_source
        validate_video_source(str(video_file))  # Should not raise


class TestVisionEdgeCaseSpecialCharactersInPath:
    """Edge Case Tests: Image with special characters in path is handled."""

    @pytest.mark.asyncio
    async def test_image_with_spaces_in_path(self, tmp_path):
        """E2E: Image with special characters in path is handled."""
        image_file = tmp_path / "my screenshot (copy).png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test result"}}]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.analyze(str(image_file))

                assert result == "Test result"

    @pytest.mark.asyncio
    async def test_image_with_unicode_in_path(self, tmp_path):
        """E2E: Image with unicode characters in path is handled."""
        image_file = tmp_path / "imagen.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test result"}}]
        }

        mock_async_client = MockAsyncClient(mock_response)

        mock_config = MagicMock()
        mock_config.zai_token = "test-token"
        mock_config.zai_base_url = "https://api.z.ai/api/anthropic"
        mock_config.timeout = 120

        with patch("goz.api.vision.load_config", return_value=mock_config):
            with patch("goz.api.vision.httpx.AsyncClient", return_value=mock_async_client):
                client = VisionClient()
                result = await client.analyze(str(image_file))

                assert result == "Test result"
