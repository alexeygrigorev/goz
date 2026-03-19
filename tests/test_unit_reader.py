"""Unit tests for Reader API validation functions."""
import pytest

from goz.api.errors import ValidationError
from goz.api.reader import (
    validate_url,
    validate_format,
    validate_timeout,
    ReaderResult,
)


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_https_url_returns_url(self):
        """Test Valid HTTPS URL is returned as-is."""
        url = "https://example.com"
        assert validate_url(url) == url

    def test_valid_http_url_returns_url(self):
        """Test Valid HTTP URL is returned as-is."""
        url = "http://example.com"
        assert validate_url(url) == url

    def test_url_with_whitespace_is_trimmed(self):
        """Test URL with leading/trailing whitespace is trimmed."""
        assert validate_url("  https://example.com  ") == "https://example.com"

    def test_empty_url_raises_validation_error(self):
        """Test Empty URL raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("")
        assert "cannot be empty" in str(exc_info.value).lower()

    def test_whitespace_only_url_raises_validation_error(self):
        """Test Whitespace-only URL raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_url("   ")

    def test_ftp_url_raises_validation_error(self):
        """Test FTP URL raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("ftp://example.com")
        assert "http" in str(exc_info.value).lower()

    def test_file_url_raises_validation_error(self):
        """Test file:// URL raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("file:///path/to/file")
        assert "http" in str(exc_info.value).lower()

    def test_url_without_protocol_raises_validation_error(self):
        """Test URL without protocol raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_url("example.com")
        assert "http" in str(exc_info.value).lower()

    def test_very_long_url_is_valid(self):
        """Test Very long URL (within limits) is valid."""
        long_url = "https://example.com/" + "a" * 1000
        assert validate_url(long_url) == long_url

    def test_url_with_query_params_is_valid(self):
        """Test URL with query parameters is valid."""
        url = "https://example.com?param=value&other=123"
        assert validate_url(url) == url

    def test_url_with_fragment_is_valid(self):
        """Test URL with fragment is valid."""
        url = "https://example.com#section"
        assert validate_url(url) == url

    def test_url_with_port_is_valid(self):
        """Test URL with port is valid."""
        url = "https://example.com:8080"
        assert validate_url(url) == url

    def test_url_with_path_is_valid(self):
        """Test URL with path is valid."""
        url = "https://example.com/path/to/page"
        assert validate_url(url) == url


class TestValidateFormat:
    """Tests for validate_format function."""

    def test_markdown_format_normalized(self):
        """Test 'markdown' format is normalized to lowercase."""
        assert validate_format("markdown") == "markdown"

    def test_text_format_normalized(self):
        """Test 'text' format is normalized to lowercase."""
        assert validate_format("text") == "text"

    def test_uppercase_markdown_is_normalized(self):
        """Test Uppercase 'MARKDOWN' is normalized to lowercase."""
        assert validate_format("MARKDOWN") == "markdown"

    def test_uppercase_text_is_normalized(self):
        """Test Uppercase 'TEXT' is normalized to lowercase."""
        assert validate_format("TEXT") == "text"

    def test_mixed_case_format_is_normalized(self):
        """Test Mixed case format is normalized."""
        assert validate_format("Markdown") == "markdown"
        assert validate_format("TeXt") == "text"

    def test_format_with_whitespace_is_trimmed(self):
        """Test Format with whitespace is trimmed and normalized."""
        assert validate_format("  markdown  ") == "markdown"

    def test_invalid_format_raises_validation_error(self):
        """Test Invalid format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_format("html")
        assert "markdown" in str(exc_info.value).lower()
        assert "text" in str(exc_info.value).lower()

    def test_json_format_raises_validation_error(self):
        """Test 'json' format raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_format("json")

    def test_empty_format_raises_validation_error(self):
        """Test Empty format raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_format("")

    def test_non_string_format_raises_validation_error(self):
        """Test Non-string format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_format(123)
        assert "string" in str(exc_info.value).lower()


class TestValidateTimeout:
    """Tests for validate_timeout function."""

    def test_valid_timeout_returned(self):
        """Test Valid timeout is returned as-is."""
        assert validate_timeout(10) == 10
        assert validate_timeout(20) == 20
        assert validate_timeout(1) == 1

    def test_large_timeout_is_valid(self):
        """Test Large timeout value is valid."""
        assert validate_timeout(300) == 300

    def test_zero_timeout_raises_validation_error(self):
        """Test Timeout of 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_timeout(0)
        assert "positive" in str(exc_info.value).lower()

    def test_negative_timeout_raises_validation_error(self):
        """Test Negative timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_timeout(-5)
        assert "positive" in str(exc_info.value).lower()

    def test_non_integer_timeout_raises_validation_error(self):
        """Test Non-integer timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_timeout(10.5)
        assert "integer" in str(exc_info.value).lower()

    def test_string_timeout_raises_validation_error(self):
        """Test String timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_timeout("20")
        assert "integer" in str(exc_info.value).lower()

    def test_none_timeout_raises_validation_error(self):
        """Test None timeout raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_timeout(None)
        assert "integer" in str(exc_info.value).lower()


class TestReaderResult:
    """Tests for ReaderResult dataclass."""

    def test_reader_result_creation(self):
        """Test ReaderResult can be created with all fields."""
        result = ReaderResult(
            content="# Test",
            title="Test Page",
            url="https://example.com",
            description="Test description"
        )
        assert result.content == "# Test"
        assert result.title == "Test Page"
        assert result.url == "https://example.com"
        assert result.description == "Test description"

    def test_reader_result_without_description(self):
        """Test ReaderResult without description defaults to None."""
        result = ReaderResult(
            content="# Test",
            title="Test Page",
            url="https://example.com"
        )
        assert result.description is None

    def test_reader_result_equality(self):
        """Test ReaderResult equality works correctly."""
        result1 = ReaderResult(
            content="# Test",
            title="Test Page",
            url="https://example.com"
        )
        result2 = ReaderResult(
            content="# Test",
            title="Test Page",
            url="https://example.com"
        )
        assert result1 == result2

    def test_reader_result_with_different_content_not_equal(self):
        """Test ReaderResult with different content is not equal."""
        result1 = ReaderResult(
            content="# Test 1",
            title="Test Page",
            url="https://example.com"
        )
        result2 = ReaderResult(
            content="# Test 2",
            title="Test Page",
            url="https://example.com"
        )
        assert result1 != result2
