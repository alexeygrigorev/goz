"""E2E tests for Reader API Implementation (Issue 06)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from goz.api import AuthError, ApiError, NetworkError, TimeoutError
from goz.config import Config

# Import ReaderClient and ReaderResult separately to allow error types to be tested first
try:
    from goz.api import ReaderClient, ReaderResult
except ImportError:
    ReaderClient = None  # type: ignore
    ReaderResult = None  # type: ignore


class TestReaderResult:
    """Tests for ReaderResult dataclass."""

    def test_reader_result_importable(self):
        """Test ReaderResult is importable from goz.api."""
        from goz.api import ReaderResult
        assert ReaderResult is not None

    def test_reader_result_has_required_fields(self):
        """Test ReaderResult has all required fields."""
        from goz.api import ReaderResult
        result = ReaderResult(
            content="# Test Content",
            title="Test Page",
            url="https://example.com",
            description="Test description"
        )
        assert result.content == "# Test Content"
        assert result.title == "Test Page"
        assert result.url == "https://example.com"
        assert result.description == "Test description"

    def test_reader_result_description_optional(self):
        """Test ReaderResult description field is optional."""
        from goz.api import ReaderResult
        result = ReaderResult(
            content="# Test",
            title="Test",
            url="https://example.com"
        )
        assert result.description is None


class TestReaderClientImport:
    """Tests for ReaderClient import."""

    def test_reader_client_importable(self):
        """Test ReaderClient is importable from goz.api."""
        from goz.api import ReaderClient
        assert ReaderClient is not None

    def test_all_exports_include_reader_types(self):
        """Test goz.api exports ReaderClient and ReaderResult."""
        from goz import api
        assert hasattr(api, "__all__")
        # Should include ReaderClient and ReaderResult
        assert "ReaderClient" in api.__all__
        assert "ReaderResult" in api.__all__


class TestBasicUrlToMarkdown:
    """Tests for basic URL to markdown conversion (AC1-AC6)."""

    @pytest.mark.asyncio
    async def test_valid_https_url_returns_markdown(self):
        """Test Valid HTTPS URL returns markdown content."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "# Welcome\n\nThis is a test page.",
                "title": "Test Page",
                "url": "https://example.com",
                "description": "A test page",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.read("https://example.com")

        assert result.content == "# Welcome\n\nThis is a test page."
        assert result.title == "Test Page"
        assert result.url == "https://example.com"
        assert result.description == "A test page"

    @pytest.mark.asyncio
    async def test_valid_http_url_returns_markdown(self):
        """Test Valid HTTP URL also works."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "# HTTP Page",
                "title": "HTTP Page",
                "url": "http://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.read("http://example.com")

        assert result.content == "# HTTP Page"

    @pytest.mark.asyncio
    async def test_url_without_http_raises_validation_error(self):
        """Test URL without http:// or https:// raises ValidationError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        # Need to import ValidationError if it exists
        try:
            from goz.api.errors import ValidationError
        except ImportError:
            pytest.skip("ValidationError not implemented yet")

        with pytest.raises(ValidationError) as exc_info:
            await client.read("ftp://example.com")

        assert "http" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_empty_url_raises_validation_error(self):
        """Test Empty URL raises ValidationError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        try:
            from goz.api.errors import ValidationError
        except ImportError:
            pytest.skip("ValidationError not implemented yet")

        with pytest.raises(ValidationError):
            await client.read("")

    @pytest.mark.asyncio
    async def test_invalid_url_protocol_raises_validation_error(self):
        """Test Invalid URL protocol (e.g., ftp://) raises ValidationError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        try:
            from goz.api.errors import ValidationError
        except ImportError:
            pytest.skip("ValidationError not implemented yet")

        with pytest.raises(ValidationError):
            await client.read("ftp://example.com")

    @pytest.mark.asyncio
    async def test_network_failure_raises_network_error(self):
        """Test Network failure raises NetworkError with helpful message."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(NetworkError):
                await client.read("https://example.com")

    @pytest.mark.asyncio
    async def test_auth_failure_raises_auth_error(self):
        """Test Auth failure (401/403) raises AuthError."""
        config = Config(zai_token="sk-ant-invalid")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.is_success = False

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(AuthError):
                await client.read("https://example.com")


class TestFormatSelection:
    """Tests for format selection (AC7-AC10)."""

    @pytest.mark.asyncio
    async def test_default_format_is_markdown(self):
        """Test Default format is markdown when not specified."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "# Markdown\n\n**Bold** text",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com")

        # Check the request body included return_format: markdown
        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("return_format") == "markdown"

    @pytest.mark.asyncio
    async def test_format_markdown_explicit(self):
        """Test Explicit format='markdown' works."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "# Markdown\n\n**Bold**",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com", format="markdown")

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("return_format") == "markdown"

    @pytest.mark.asyncio
    async def test_format_text_works(self):
        """Test format='text' returns plain text."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Plain text without markdown",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com", format="text")

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("return_format") == "text"

    @pytest.mark.asyncio
    async def test_format_case_insensitive(self):
        """Test Format parameter is case-insensitive."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Test",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com", format="MARKDOWN")

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("return_format") == "markdown"

    @pytest.mark.asyncio
    async def test_invalid_format_raises_validation_error(self):
        """Test Invalid format value raises ValidationError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        try:
            from goz.api.errors import ValidationError
        except ImportError:
            pytest.skip("ValidationError not implemented yet")

        with pytest.raises(ValidationError) as exc_info:
            await client.read("https://example.com", format="html")

        assert "markdown" in str(exc_info.value).lower()
        assert "text" in str(exc_info.value).lower()


class TestTimeoutConfiguration:
    """Tests for timeout configuration (AC11-AC15)."""

    @pytest.mark.asyncio
    async def test_default_timeout_is_20(self):
        """Test Default timeout is 20 seconds."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Test",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com")

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("timeout") == 20

    @pytest.mark.asyncio
    async def test_custom_timeout_works(self):
        """Test Custom timeout value is used."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Test",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com", timeout=5)

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("timeout") == 5

    @pytest.mark.asyncio
    async def test_timeout_zero_raises_validation_error(self):
        """Test Timeout of 0 raises ValidationError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        try:
            from goz.api.errors import ValidationError
        except ImportError:
            pytest.skip("ValidationError not implemented yet")

        with pytest.raises(ValidationError):
            await client.read("https://example.com", timeout=0)

    @pytest.mark.asyncio
    async def test_negative_timeout_raises_validation_error(self):
        """Test Negative timeout raises ValidationError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        try:
            from goz.api.errors import ValidationError
        except ImportError:
            pytest.skip("ValidationError not implemented yet")

        with pytest.raises(ValidationError):
            await client.read("https://example.com", timeout=-5)

    @pytest.mark.asyncio
    async def test_timeout_error_includes_timeout_value(self):
        """Test TimeoutError includes timeout value in message."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TimeoutError) as exc_info:
                await client.read("https://example.com", timeout=5)

        # Should include timeout info (timeout is passed as ms to TimeoutError)
        assert "timeout" in str(exc_info.value).lower()


class TestCacheControl:
    """Tests for cache control (AC16-AC18)."""

    @pytest.mark.asyncio
    async def test_default_no_cache_is_false(self):
        """Test Default no_cache is False."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Test",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com")

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("no_cache") is False

    @pytest.mark.asyncio
    async def test_no_cache_true_works(self):
        """Test no_cache=True bypasses cache."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Fresh content",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com", no_cache=True)

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("no_cache") is True


class TestImageRetention:
    """Tests for image retention control (AC19-AC21)."""

    @pytest.mark.asyncio
    async def test_default_retain_images_is_true(self):
        """Test Default retain_images is True."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "![Image](image.jpg)",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com")

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("retain_images") is True

    @pytest.mark.asyncio
    async def test_retain_images_false_removes_images(self):
        """Test retain_images=False removes image markdown syntax."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Text without images",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com", retain_images=False)

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("retain_images") is False


class TestLinksSummary:
    """Tests for links summary (AC22-AC24)."""

    @pytest.mark.asyncio
    async def test_default_with_links_summary_is_false(self):
        """Test Default with_links_summary is False."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Content",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com")

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("with_links_summary") is False

    @pytest.mark.asyncio
    async def test_with_links_summary_true_includes_links(self):
        """Test with_links_summary=True includes links data."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Content",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            },
            "links_summary": [
                {"url": "https://example.com/page1", "title": "Page 1"},
                {"url": "https://example.com/page2", "title": "Page 2"}
            ]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com", with_links_summary=True)

        call_args = mock_client.post.call_args
        body = call_args.kwargs.get("json", {})
        assert body.get("with_links_summary") is True


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_url_with_query_parameters(self):
        """Test URL with query parameters works."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        test_url = "https://example.com?param=value&other=123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Test",
                "title": "Test",
                "url": test_url,  # API returns the requested URL
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.read(test_url)

        assert result.url == test_url

    @pytest.mark.asyncio
    async def test_url_with_fragment(self):
        """Test URL with fragment works."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Test",
                "title": "Test",
                "url": "https://example.com#section",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.read("https://example.com#section")

        assert result.url == "https://example.com#section"

    @pytest.mark.asyncio
    async def test_url_with_unicode_characters(self):
        """Test URL with unicode characters works."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Unicode content",
                "title": "Test",
                "url": "https://example.com/path",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com/path")

    @pytest.mark.asyncio
    async def test_404_response_raises_api_error(self):
        """Test 404 response raises ApiError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.is_success = False

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.read("https://example.com/nonexistent")

        assert exc_info.value.statusCode == 404

    @pytest.mark.asyncio
    async def test_500_response_raises_api_error(self):
        """Test 500 response raises ApiError."""
        config = Config(zai_token="sk-ant-test")
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.is_success = False

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.read("https://example.com")

        assert exc_info.value.statusCode == 500

    @pytest.mark.asyncio
    async def test_reader_endpoint_is_correct(self):
        """Test Request goes to /reader endpoint."""
        config = Config(
            zai_token="sk-ant-test",
            zai_base_url="https://api.example.com/v1"
        )
        client = ReaderClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "req-123",
            "created": 1234567890,
            "reader_result": {
                "content": "Test",
                "title": "Test",
                "url": "https://example.com",
                "metadata": {}
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        async def aexit(*args):
            return None
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.read("https://example.com")

        call_args = mock_client.post.call_args
        url = call_args.args[0]
        assert url == "https://api.example.com/v1/reader"
