"""E2E tests for API Client Foundation (Issue 03)."""
import asyncio
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from goz.api import ZaiError, AuthError, ApiError, NetworkError, TimeoutError
from goz.config import Config

# Import ZaiApiClient separately to allow error types to be tested first
try:
    from goz.api import ZaiApiClient
except ImportError:
    ZaiApiClient = None  # type: ignore


class TestErrorTypes:
    """Tests for error types (Acceptance Criteria AC-ERRORS)."""

    def test_zai_error_base_class_has_all_attributes(self):
        """Test ZaiError base class has all required attributes."""
        error = ZaiError(
            message="Test error",
            code="TEST_ERROR",
            statusCode=500,
            help="This is a test error"
        )
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.statusCode == 500
        assert error.help == "This is a test error"

    def test_zai_error_string_representation(self):
        """Test ZaiError string representation shows code and message."""
        error = ZaiError(message="Test error", code="TEST_ERROR")
        error_str = str(error)
        assert "TEST_ERROR" in error_str
        assert "Test error" in error_str

    def test_auth_error_attributes(self):
        """Test AuthError has correct code and statusCode."""
        error = AuthError("Invalid token")
        assert error.code == "AUTH_ERROR"
        assert error.statusCode == 401
        assert error.message == "Invalid token"
        assert error.help is not None

    def test_api_error_attributes(self):
        """Test ApiError accepts and stores statusCode."""
        error = ApiError("Bad request", 400)
        assert error.code == "API_ERROR"
        assert error.statusCode == 400
        assert error.message == "Bad request"

    def test_network_error_attributes(self):
        """Test NetworkError has correct code and help text."""
        error = NetworkError("Connection failed")
        assert error.code == "NETWORK_ERROR"
        assert error.message == "Connection failed"
        assert error.help is not None
        assert "internet" in error.help.lower()

    def test_timeout_error_attributes(self):
        """Test TimeoutError includes timeout value in message."""
        error = TimeoutError(10000)
        assert error.code == "TIMEOUT_ERROR"
        assert error.message == "Request timed out after 10000ms"
        assert error.help is not None
        assert "timeout" in error.help.lower()

    def test_all_errors_catchable_via_base_error(self):
        """Test all error types are catchable via base ZaiError."""
        errors = [
            AuthError("auth"),
            ApiError("api", 500),
            NetworkError("network"),
            TimeoutError(5000),
        ]
        for error in errors:
            assert isinstance(error, ZaiError)


class TestClientInstantiation:
    """Tests for client instantiation (Acceptance Criteria AC-BASE, AC-MODULE)."""

    def test_zai_api_client_importable(self):
        """Test ZaiApiClient is importable from goz.api."""
        from goz.api import ZaiApiClient
        assert ZaiApiClient is not None

    def test_all_exports_defined(self):
        """Test module has __all__ list defining public exports."""
        from goz import api
        assert hasattr(api, "__all__")
        expected = ["ZaiApiClient", "ZaiError", "AuthError", "ApiError", "NetworkError", "TimeoutError"]
        for name in expected:
            assert name in api.__all__

    def test_client_with_default_config(self, tmp_path):
        """Test ZaiApiClient() with no arguments loads default config."""
        # Create a test config file
        config_file = tmp_path / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump({
                "zai_token": "sk-ant-test123",
                "zai_base_url": "https://api.test.com",
                "timeout": 60,
            }, f)

        with patch("goz.config.DEFAULT_CONFIG_FILE", config_file):
            client = ZaiApiClient()
            assert client.config is not None
            assert client.config.zai_token == "sk-ant-test123"

    def test_client_with_custom_config(self):
        """Test ZaiApiClient(config=custom_config) uses provided config."""
        config = Config(
            zai_token="sk-ant-custom",
            zai_base_url="https://custom.api.com",
            timeout=300
        )
        client = ZaiApiClient(config=config)
        assert client.config == config

    def test_client_stores_config_attribute(self):
        """Test Client stores config attribute accessible after initialization."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)
        assert hasattr(client, "config")
        assert client.config.zai_token == "sk-ant-test"


class TestRequestSuccess:
    """Tests for successful requests (Acceptance Criteria AC-REQUEST)."""

    @pytest.mark.asyncio
    async def test_successful_request_returns_parsed_json(self):
        """Test Successful request to mock API returns parsed JSON dict."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        # Mock the httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success", "data": {"key": "value"}}
        mock_response.text = '{"result": "success"}'

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.request("/test/endpoint", {"test": "data"})

        assert result == {"result": "success", "data": {"key": "value"}}

    @pytest.mark.asyncio
    async def test_request_includes_authorization_header(self):
        """Test Request includes correct Authorization header with Bearer token."""
        config = Config(zai_token="sk-ant-test-token")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.request("/test", {})

        # Check the call arguments
        call_args = mock_client.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("Authorization") == "Bearer sk-ant-test-token"

    @pytest.mark.asyncio
    async def test_request_includes_content_type_and_accept_language(self):
        """Test Request includes Content-Type and Accept-Language headers."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.request("/test", {})

        call_args = mock_client.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert headers.get("Content-Type") == "application/json"
        assert headers.get("Accept-Language") == "en-US,en"

    @pytest.mark.asyncio
    async def test_full_url_is_base_url_plus_endpoint(self):
        """Test Full URL is {base_url}{endpoint}."""
        config = Config(
            zai_token="sk-ant-test",
            zai_base_url="https://api.example.com/v1"
        )
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.request("/chat/completions", {})

        call_args = mock_client.post.call_args
        url = call_args.args[0]
        assert url == "https://api.example.com/v1/chat/completions"


class TestErrorHandling:
    """Tests for error handling (Acceptance Criteria AC-REQUEST)."""

    @pytest.mark.asyncio
    async def test_401_response_raises_auth_error(self):
        """Test 401 response raises AuthError without retry."""
        config = Config(zai_token="sk-ant-invalid")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.is_success = False
        mock_response.content = b"Unauthorized"
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(AuthError) as exc_info:
                await client.request("/test", {})

        assert "Unauthorized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_403_response_raises_auth_error(self):
        """Test 403 response raises AuthError without retry."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.is_success = False
        mock_response.content = b"Forbidden"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(AuthError):
                await client.request("/test", {})

    @pytest.mark.asyncio
    async def test_400_response_raises_api_error(self):
        """Test 400 response raises ApiError with statusCode=400."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.is_success = False
        mock_response.content = b"Bad Request"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.request("/test", {})

        assert exc_info.value.statusCode == 400

    @pytest.mark.asyncio
    async def test_500_response_raises_api_error(self):
        """Test 500 response raises ApiError with statusCode=500."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.is_success = False
        mock_response.content = b"Internal Server Error"
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.request("/test", {})

        assert exc_info.value.statusCode == 500

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """Test Timeout raises TimeoutError with timeout value in message."""
        config = Config(zai_token="sk-ant-test", timeout=10)
        client = ZaiApiClient(config=config)

        mock_client = AsyncMock()
        mock_client.post.side_effect = asyncio.TimeoutError()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TimeoutError) as exc_info:
                await client.request("/test", {})

        assert "10000" in str(exc_info.value)  # 10 seconds = 10000ms

    @pytest.mark.asyncio
    async def test_connection_error_raises_network_error(self):
        """Test Connection error raises NetworkError."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(NetworkError):
                await client.request("/test", {})


class TestRetryLogic:
    """Tests for retry logic (Acceptance Criteria AC-RETRY)."""

    @pytest.mark.asyncio
    async def test_successful_request_first_attempt_no_delay(self):
        """Test Successful request on first attempt returns immediately (no delay)."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.content = b'{"result": "success"}'
        mock_response.json.return_value = {"result": "success"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.request("/test", {})

        assert result == {"result": "success"}
        # Should be called only once
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_failed_request_retries_two_times(self):
        """Test Failed request retries 2 times (3 total attempts)."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(NetworkError):
                await client.request("/test", {})

        # Should be called 3 times (initial + 2 retries)
        assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_auth_error_not_retried(self):
        """Test AuthError is not retried (fails immediately on 401)."""
        config = Config(zai_token="sk-ant-invalid")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.is_success = False

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(AuthError):
                await client.request("/test", {})

        # Should be called only once (no retries for auth errors)
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """Test Retry succeeds on second attempt after transient failure."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"result": "success"}

        mock_client = AsyncMock()
        # First attempt fails, second succeeds
        mock_client.post.side_effect = [
            httpx.ConnectError("Connection failed"),
            mock_response_success,
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.request("/test", {})

        assert result == {"result": "success"}
        assert mock_client.post.call_count == 2


class TestErrorParsing:
    """Tests for error parsing (Acceptance Criteria AC-PARSING)."""

    @pytest.mark.asyncio
    async def test_error_response_nested_error_message(self):
        """Test Error response with nested error.message extracts message correctly."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error": {"message": "Invalid request: missing field"}}'
        mock_response.is_success = False
        mock_response.json.return_value = {"error": {"message": "Invalid request: missing field"}}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.request("/test", {})

        assert "Invalid request: missing field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_top_level_message(self):
        """Test Error response with top-level message extracts message correctly."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.is_success = False
        mock_response.json.return_value = {"message": "Top level error message"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.request("/test", {})

        assert "Top level error message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_plain_text_uses_text_as_message(self):
        """Test Error response with plain text (non-JSON) uses text as message."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.is_success = False
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.request("/test", {})

        assert "Internal Server Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_response_object_message_stringifies(self):
        """Test Error response with object message stringifies to JSON."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config)

        error_obj = {"field": "value", "nested": {"key": "val"}}
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.is_success = False
        mock_response.json.return_value = {"error": error_obj}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ApiError) as exc_info:
                await client.request("/test", {})

        # Should contain JSON stringified version
        assert "field" in str(exc_info.value)


class TestLogging:
    """Tests for logging (Acceptance Criteria AC-LOGGING)."""

    @pytest.mark.asyncio
    async def test_logging_enabled_logs_request_to_stderr(self, caplog):
        """Test With logging enabled, request logs to stderr."""
        caplog.set_level(logging.DEBUG)

        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config, enable_logging=True)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.content = b'{"result": "success"}'
        mock_response.json.return_value = {"result": "success"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.request("/test", {"data": "test"})

        # Check that logs were created
        assert any("/test" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_logging_disabled_no_log_output(self, caplog):
        """Test With logging disabled, no log output occurs."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config, enable_logging=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.request("/test", {})

        # Should have no logs from our client
        client_logs = [r for r in caplog.records if "goz" in r.name.lower()]
        assert len(client_logs) == 0

    @pytest.mark.asyncio
    async def test_error_logs_include_type_and_message(self, caplog):
        """Test Error logs include error type and message."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config, enable_logging=True)

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(NetworkError):
                await client.request("/test", {})

        # Check that error was logged
        assert any("NetworkError" in record.message or "error" in record.message.lower()
                   for record in caplog.records)

    @pytest.mark.asyncio
    async def test_logs_go_to_stderr(self, capsys):
        """Test Logs go to stderr, not stdout."""
        config = Config(zai_token="sk-ant-test")
        client = ZaiApiClient(config=config, enable_logging=True)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ propagate exceptions
        async def aexit(*args):
            return None  # Don't suppress exception
        mock_client.__aexit__ = aexit

        with patch("httpx.AsyncClient", return_value=mock_client):
            await client.request("/test", {})

        captured = capsys.readouterr()
        # Nothing should be in stdout
        # (We can't easily test stderr with capsys, but we verify no stdout output)
        assert "/test" not in captured.out
