"""Unit tests for Vision Tool (Issue 20).

Tests for DescribeImageTool that wraps the VisionClient for image/video analysis.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from goz.agent.tools.vision_tool import DescribeImageTool
from goz.agent.tools.base import ToolInputError


def _make_mock_config():
    """Create a mock config with required string attributes for VisionClient."""
    config = MagicMock()
    config.zai_token = "test-token"
    config.zai_base_url = "https://api.example.com"
    config.timeout = 30
    return config


def _make_tool():
    """Create a DescribeImageTool with VisionClient patched out."""
    with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value = mock_client
        tool = DescribeImageTool(config=_make_mock_config())
    return tool


# ========== Test DescribeImageTool ==========


class TestDescribeImageTool:
    """Unit Tests: DescribeImageTool class."""

    def test_tool_exists(self):
        """Test DescribeImageTool class can be imported."""
        assert DescribeImageTool is not None

    def test_tool_name(self):
        """Test DescribeImageTool has correct name."""
        tool = _make_tool()
        assert tool.name == "describe_image"

    def test_tool_description(self):
        """Test DescribeImageTool has description."""
        tool = _make_tool()
        assert tool.description
        assert "image" in tool.description.lower() or "video" in tool.description.lower()

    def test_tool_input_schema(self):
        """Test DescribeImageTool has correct input_schema."""
        tool = _make_tool()
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "source" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "task" in schema["properties"]
        assert schema["required"] == ["source"]
        assert set(schema["properties"]["task"]["enum"]) == {
            "describe", "extract_text", "diagnose_error", "ui_to_code"
        }

    def test_tool_init_with_config(self):
        """Test DescribeImageTool initializes with config."""
        mock_config = _make_mock_config()
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            MockClient.return_value = AsyncMock()
            tool = DescribeImageTool(config=mock_config)
        assert tool.config is mock_config
        assert tool.client is not None

    @pytest.mark.asyncio
    async def test_execute_describe_task(self):
        """Test DescribeImageTool.execute with describe task (default)."""
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.analyze.return_value = "This image shows a cat."
            MockClient.return_value = mock_client

            tool = DescribeImageTool(config=_make_mock_config())
            result = await tool.execute(source="https://example.com/cat.jpg")

            mock_client.analyze.assert_called_once_with(
                "https://example.com/cat.jpg",
                prompt=None,
            )
            assert result == "This image shows a cat."

    @pytest.mark.asyncio
    async def test_execute_describe_task_with_custom_prompt(self):
        """Test DescribeImageTool.execute with custom prompt."""
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.analyze.return_value = "Detailed analysis."
            MockClient.return_value = mock_client

            tool = DescribeImageTool(config=_make_mock_config())
            result = await tool.execute(
                source="https://example.com/cat.jpg",
                prompt="Describe the colors in this image",
            )

            mock_client.analyze.assert_called_once_with(
                "https://example.com/cat.jpg",
                prompt="Describe the colors in this image",
            )
            assert result == "Detailed analysis."

    @pytest.mark.asyncio
    async def test_execute_extract_text_task(self):
        """Test DescribeImageTool.execute with extract_text task."""
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.extract_text.return_value = "Extracted text from image"
            MockClient.return_value = mock_client

            tool = DescribeImageTool(config=_make_mock_config())
            result = await tool.execute(
                source="https://example.com/screenshot.png",
                task="extract_text",
            )

            mock_client.extract_text.assert_called_once_with(
                "https://example.com/screenshot.png"
            )
            assert result == "Extracted text from image"

    @pytest.mark.asyncio
    async def test_execute_diagnose_error_task(self):
        """Test DescribeImageTool.execute with diagnose_error task."""
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.diagnose_error.return_value = "This is a TypeError on line 42."
            MockClient.return_value = mock_client

            tool = DescribeImageTool(config=_make_mock_config())
            result = await tool.execute(
                source="https://example.com/error.png",
                task="diagnose_error",
            )

            mock_client.diagnose_error.assert_called_once_with(
                "https://example.com/error.png"
            )
            assert result == "This is a TypeError on line 42."

    @pytest.mark.asyncio
    async def test_execute_ui_to_code_task(self):
        """Test DescribeImageTool.execute with ui_to_code task."""
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.ui_to_code.return_value = "<html>...</html>"
            MockClient.return_value = mock_client

            tool = DescribeImageTool(config=_make_mock_config())
            result = await tool.execute(
                source="https://example.com/ui.png",
                task="ui_to_code",
            )

            mock_client.ui_to_code.assert_called_once_with(
                "https://example.com/ui.png"
            )
            assert result == "<html>...</html>"

    @pytest.mark.asyncio
    async def test_execute_rejects_empty_source(self):
        """Test DescribeImageTool rejects empty source."""
        tool = _make_tool()

        with pytest.raises(ToolInputError, match="source"):
            await tool.execute(source="   ")

    @pytest.mark.asyncio
    async def test_execute_rejects_invalid_task(self):
        """Test DescribeImageTool rejects invalid task values."""
        tool = _make_tool()

        with pytest.raises(ToolInputError, match="task"):
            await tool.execute(source="https://example.com/img.jpg", task="invalid_task")

    @pytest.mark.asyncio
    async def test_execute_rejects_empty_prompt(self):
        """Test DescribeImageTool rejects empty prompt when provided."""
        tool = _make_tool()

        with pytest.raises(ToolInputError, match="prompt"):
            await tool.execute(source="https://example.com/img.jpg", prompt="   ")

    @pytest.mark.asyncio
    async def test_execute_handles_file_not_found(self):
        """Test DescribeImageTool handles missing local files."""
        tool = _make_tool()
        result = await tool.execute(source="/nonexistent/path/image.jpg")

        assert "Error" in result or "not found" in result.lower() or "No such file" in result

    @pytest.mark.asyncio
    async def test_execute_handles_api_error(self):
        """Test DescribeImageTool handles API errors gracefully."""
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.analyze.side_effect = Exception("API failure")
            MockClient.return_value = mock_client

            tool = DescribeImageTool(config=_make_mock_config())
            result = await tool.execute(source="https://example.com/img.jpg")

            assert "Image analysis failed" in result

    @pytest.mark.asyncio
    async def test_execute_url_source_passes_validation(self):
        """Test DescribeImageTool passes validation for URL sources."""
        with patch("goz.agent.tools.vision_tool.VisionClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.analyze.return_value = "Result"
            MockClient.return_value = mock_client

            tool = DescribeImageTool(config=_make_mock_config())
            result = await tool.execute(source="https://example.com/img.png")

            assert result == "Result"
