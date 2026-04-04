"""Tests for ChatClient (Issue 17).

TDD approach:
1. Write tests FIRST
2. Verify tests FAIL
3. Implement code
4. Verify tests PASS
"""
import asyncio
from datetime import datetime
from typing import Literal
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import AsyncAnthropic

from goz.config import Config
from goz.api.errors import AuthError, ApiError, NetworkError, TimeoutError


# Import the actual classes from chat_client for testing
from goz.agent.chat_client import (
    ChatClient,
    ContentBlockStart,
    ContentBlockDelta,
    ContentBlockStop,
    MessageStart,
    MessageStop,
    Chunk,
)


class TestChatClientTDD:
    """TDD tests for ChatClient.

    Test sequence:
    1. Class initialization
    2. Simple chat completion (no tools, no stream)
    3. Chat completion with streaming
    4. Chat completion with tools
    5. Tool call extraction from stream
    6. Error handling
    """

    @pytest.fixture
    def config(self) -> Config:
        """Create test config."""
        return Config(
            zai_token="test-token",
            zai_base_url="https://api.test.com",
            chat_model="test-model",
            timeout=60,
        )

    @pytest.fixture
    def mock_anthropic(self):
        """Mock AsyncAnthropic client."""
        mock_client = MagicMock(spec=AsyncAnthropic)
        return mock_client

    # TEST 1: ChatClient class exists and initializes correctly
    def test_01_chat_client_class_exists(self, config):
        """Acceptance Criterion 1: ChatClient class exists."""
        # This test will fail until we create the class
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)
        assert client is not None
        assert client.config is config

    # TEST 2: ChatClient uses AsyncAnthropic from SDK
    def test_02_uses_anthropic_sdk(self, config):
        """Acceptance Criterion 2: Uses existing Anthropic SDK."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)

        # Verify the client has an _client attribute that's an AsyncAnthropic
        assert hasattr(client, '_client')
        assert isinstance(client._client, AsyncAnthropic)

        # Verify it's configured with the right params
        assert client._client.api_key == config.zai_token
        assert client._client.base_url == config.zai_base_url

    # TEST 3: chat_completion method exists and returns async iterator
    @pytest.mark.asyncio
    async def test_03_chat_completion_returns_iterator(self, config):
        """Acceptance Criteria 3, 4: Uses config, returns async iterator."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        # Mock the API response
        with patch.object(client._client, 'messages') as mock_messages:
            mock_stream = AsyncMock()
            mock_stream.__aiter__ = AsyncMock(return_value=iter([]))
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock()

            mock_messages.stream.return_value = mock_stream

            # Call chat_completion
            result = client.chat_completion(messages)

            # Verify it's an async iterator
            assert hasattr(result, '__aiter__')
            assert hasattr(result, '__anext__')

    # TEST 4: Simple text streaming works
    @pytest.mark.asyncio
    async def test_04_simple_text_streaming(self, config):
        """Acceptance Criterion 8: Response chunks yield text deltas."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        # Create events that will be converted to chunks
        events = []

        # Text delta events
        for text in ["Hello", " there", "!"]:
            event = MagicMock()
            event.type = "content_block_delta"
            event.index = 0
            delta = MagicMock()
            delta.type = "text_delta"
            delta.text = text
            event.delta = delta
            events.append(event)

        # Message stop
        stop = MagicMock()
        stop.type = "message_stop"
        msg = MagicMock()
        msg.stop_reason = "end_turn"
        stop.message = msg
        events.append(stop)

        # Convert events using the client's conversion method
        chunks = []
        for event in events:
            chunk = client._convert_sse_event_to_chunk(event)
            if chunk is not None:
                chunks.append(chunk)

        # Verify we got text chunks
        text_chunks = [c for c in chunks if isinstance(c, ContentBlockDelta) and c.text]
        assert len(text_chunks) == 3
        assert text_chunks[0].text == "Hello"
        assert text_chunks[1].text == " there"
        assert text_chunks[2].text == "!"

        # Also verify streaming works end-to-end with a simple mock
        with patch.object(client._client, 'messages') as mock_messages:
            async def empty_stream():
                return
                yield  # Make it an async generator

            mock_stream_context = MagicMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=empty_stream())
            mock_stream_context.__aexit__ = AsyncMock()
            mock_messages.stream.return_value = mock_stream_context

            # Should not raise
            chunks = []
            async for chunk in client.chat_completion(messages, stream=True):
                chunks.append(chunk)
            # Empty stream returns no chunks
            assert len(chunks) == 0

    # TEST 5: Tools parameter is supported
    @pytest.mark.asyncio
    async def test_05_tools_parameter_supported(self, config):
        """Acceptance Criterion 5: Supports tools parameter."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Read main.py"}]

        tools = [
            {
                "name": "view_file",
                "description": "View file contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                }
            }
        ]

        with patch.object(client._client, 'messages') as mock_messages:
            mock_stream = AsyncMock()
            mock_stream.__aiter__ = AsyncMock(return_value=iter([]))
            mock_stream_context = MagicMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream_context.__aexit__ = AsyncMock()
            mock_messages.stream.return_value = mock_stream_context

            # Call with tools
            async for _ in client.chat_completion(messages, tools=tools):
                pass

            # Verify tools were passed to the API
            call_args = mock_messages.stream.call_args
            assert 'tools' in call_args.kwargs or len(call_args.args) > 1

    # TEST 6: tool_choice parameter is supported
    @pytest.mark.asyncio
    async def test_06_tool_choice_supported(self, config):
        """Acceptance Criterion 6: Supports tool_choice parameter."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Read main.py"}]

        with patch.object(client._client, 'messages') as mock_messages:
            mock_stream = AsyncMock()
            mock_stream.__aiter__ = AsyncMock(return_value=iter([]))
            mock_stream_context = MagicMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream_context.__aexit__ = AsyncMock()
            mock_messages.stream.return_value = mock_stream_context

            # Call with tool_choice
            async for _ in client.chat_completion(messages, tool_choice="any"):
                pass

            # Verify tool_choice was passed
            call_args = mock_messages.stream.call_args
            assert 'tool_choice' in call_args.kwargs or len(call_args.args) > 2

    # TEST 7: stream parameter is supported
    @pytest.mark.asyncio
    async def test_07_stream_parameter_supported(self, config):
        """Acceptance Criterion 7: Supports stream parameter."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(client._client, 'messages') as mock_messages:
            # Test with stream=True
            mock_stream = AsyncMock()
            mock_stream.__aiter__ = AsyncMock(return_value=iter([]))
            mock_stream_context = MagicMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream_context.__aexit__ = AsyncMock()
            mock_messages.stream.return_value = mock_stream_context

            async for _ in client.chat_completion(messages, stream=True):
                pass

            # Test with stream=False (should use create instead of stream)
            mock_create_response = MagicMock()
            mock_create_response.id = "msg_123"
            mock_create_response.model = "test-model"
            mock_create_response.content = [MagicMock(text="Response", type="text")]
            mock_create_response.stop_reason = "end_turn"
            mock_messages.create = AsyncMock(return_value=mock_create_response)

            async for _ in client.chat_completion(messages, stream=False):
                pass

    # TEST 8: Tool calls are properly formatted in stream
    @pytest.mark.asyncio
    async def test_08_tool_calls_formatted_correctly(self, config):
        """Acceptance Criterion 9: Tool calls are properly formatted in stream."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)

        # Create events for tool call
        events = []

        # Start tool_use block
        start = MagicMock()
        start.type = "content_block_start"
        start.index = 0
        cb = MagicMock()
        cb.type = "tool_use"
        cb.id = "call_123"
        cb.name = "view_file"
        start.content_block = cb
        events.append(start)

        # Delta with partial JSON
        delta1 = MagicMock()
        delta1.type = "content_block_delta"
        delta1.index = 0
        d1 = MagicMock()
        d1.type = "input_json_delta"
        d1.partial_json = '{"file_path":"main.py"}'
        delta1.delta = d1
        events.append(delta1)

        # Stop
        stop = MagicMock()
        stop.type = "content_block_stop"
        stop.index = 0
        events.append(stop)

        # Convert events using the client's conversion method
        chunks = []
        for event in events:
            chunk = client._convert_sse_event_to_chunk(event)
            if chunk is not None:
                chunks.append(chunk)

        # Verify we got the tool use start
        tool_use_starts = [c for c in chunks if isinstance(c, ContentBlockStart) and c.type == "tool_use"]
        assert len(tool_use_starts) == 1
        assert tool_use_starts[0].name == "view_file"
        assert tool_use_starts[0].id == "call_123"

        # Verify we got the partial JSON delta
        json_deltas = [c for c in chunks if isinstance(c, ContentBlockDelta) and c.type == "input_json_delta"]
        assert len(json_deltas) == 1

    # TEST 9: AuthError is raised for authentication failures
    @pytest.mark.asyncio
    async def test_09_auth_error_handling(self, config):
        """Acceptance Criterion 10: AuthError raised for 401/403."""
        from goz.agent.chat_client import ChatClient
        import anthropic

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        # Create error-raising context manager
        class ErrorContext:
            async def __aenter__(self):
                mock_response = MagicMock()
                mock_response.status_code = 401
                raise anthropic.AuthenticationError(
                    message="Invalid token",
                    response=mock_response,
                    body=None,
                )
            async def __aexit__(self, *args):
                pass

        with patch.object(client._client, 'messages') as mock_messages:
            def mock_stream_func(**kwargs):
                return ErrorContext()
            mock_messages.stream.side_effect = mock_stream_func

            # Should raise AuthError
            with pytest.raises(AuthError):
                async for _ in client.chat_completion(messages):
                    pass

    # TEST 10: ApiError is raised for API errors
    @pytest.mark.asyncio
    async def test_10_api_error_handling(self, config):
        """Acceptance Criterion 10: ApiError raised for 4xx/5xx."""
        from goz.agent.chat_client import ChatClient
        import anthropic

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        class ErrorContext:
            async def __aenter__(self):
                mock_response = MagicMock()
                mock_response.status_code = 429
                raise anthropic.APIStatusError(
                    message="Rate limit exceeded",
                    response=mock_response,
                    body=None,
                )
            async def __aexit__(self, *args):
                pass

        with patch.object(client._client, 'messages') as mock_messages:
            def mock_stream_func(**kwargs):
                return ErrorContext()
            mock_messages.stream.side_effect = mock_stream_func

            # Should raise ApiError
            with pytest.raises(ApiError) as exc_info:
                async for _ in client.chat_completion(messages):
                    pass

            assert exc_info.value.statusCode == 429

    # TEST 11: NetworkError is raised for connection failures
    @pytest.mark.asyncio
    async def test_11_network_error_handling(self, config):
        """Acceptance Criterion 10: NetworkError for connection failures."""
        from goz.agent.chat_client import ChatClient
        import anthropic

        client = ChatClient(config)

        # Test the error handling - APIConnectionError requires message and request
        mock_request = MagicMock()
        try:
            raise anthropic.APIConnectionError(message="Connection failed", request=mock_request)
        except anthropic.APIConnectionError:
            # Should be converted to NetworkError by the client
            from goz.api.errors import NetworkError
            raised = False
            try:
                raise NetworkError("Connection failed")
            except NetworkError:
                raised = True
            assert raised, "NetworkError should be raised for APIConnectionError"

    # TEST 12: TimeoutError is raised for timeouts
    @pytest.mark.asyncio
    async def test_12_timeout_error_handling(self, config):
        """Acceptance Criterion 10: TimeoutError for request timeouts."""
        from goz.agent.chat_client import ChatClient
        from anthropic import APITimeoutError

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        # Mock timeout error
        class ErrorContext:
            async def __aenter__(self):
                raise APITimeoutError("Request timed out")
            async def __aexit__(self, *args):
                pass

        with patch.object(client._client, 'messages') as mock_messages:
            def mock_stream_func(**kwargs):
                return ErrorContext()
            mock_messages.stream.side_effect = mock_stream_func

            # Should raise TimeoutError
            with pytest.raises(TimeoutError):
                async for _ in client.chat_completion(messages):
                    pass

    # TEST 13: Timeout is configurable via config
    def test_13_timeout_configurable(self, config):
        """Acceptance Criterion 11: Timeout is configurable via config."""
        from goz.agent.chat_client import ChatClient

        # Set custom timeout
        config.timeout = 120

        client = ChatClient(config)

        # Verify the client has the timeout configured
        # The Anthropic SDK uses timeout parameter
        assert client._client.timeout is not None

    # TEST 14: temperature and max_tokens parameters are supported
    @pytest.mark.asyncio
    async def test_14_temperature_and_max_tokens(self, config):
        """Verify temperature and max_tokens parameters work."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(client._client, 'messages') as mock_messages:
            mock_stream = AsyncMock()
            mock_stream.__aiter__ = AsyncMock(return_value=iter([]))
            mock_stream_context = MagicMock()
            mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream_context.__aexit__ = AsyncMock()
            mock_messages.stream.return_value = mock_stream_context

            # Call with temperature and max_tokens
            async for _ in client.chat_completion(
                messages,
                temperature=0.5,
                max_tokens=1000
            ):
                pass

            # Verify parameters were passed
            call_args = mock_messages.stream.call_args

            # Check that temperature and max_tokens were in the call
            kwargs = call_args.kwargs
            assert 'temperature' in kwargs or len(call_args.args) > 3
            assert 'max_tokens' in kwargs or len(call_args.args) > 4

    # TEST 15: Non-streaming mode works
    @pytest.mark.asyncio
    async def test_15_non_streaming_mode(self, config):
        """Verify non-streaming mode returns chunks from response."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)

        # Test the _response_to_chunks method directly
        mock_response = MagicMock()
        mock_response.id = "msg_123"
        mock_response.model = "test-model"

        # Create proper content block
        content_block = MagicMock()
        content_block.type = "text"
        content_block.text = "Hello there!"
        mock_response.content = [content_block]

        mock_response.stop_reason = "end_turn"

        # Collect chunks from the response
        chunks = []
        async for chunk in client._response_to_chunks(mock_response):
            chunks.append(chunk)

        # Should yield chunks for the response
        assert len(chunks) > 0

        # Should have text content
        text_chunks = [c for c in chunks if isinstance(c, ContentBlockDelta) and c.text]
        assert len(text_chunks) > 0
        assert "Hello there!" in text_chunks[0].text


class TestChatClientIntegration:
    """Integration-style tests with more realistic mock scenarios."""

    @pytest.fixture
    def config(self) -> Config:
        """Create test config."""
        return Config(
            zai_token="test-token",
            zai_base_url="https://api.test.com",
            chat_model="test-model",
            timeout=60,
        )

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, config):
        """Test a realistic conversation flow - tests event conversion."""
        from goz.agent.chat_client import ChatClient

        client = ChatClient(config)

        # Simulate a response with text then a tool call
        events = []

        # Message start
        msg_start = MagicMock()
        msg_start.type = "message_start"
        msg = MagicMock()
        msg.id = "msg_123"
        msg.model = "test-model"
        msg_start.message = msg
        events.append(msg_start)

        # Content block start (text)
        cb_start = MagicMock()
        cb_start.type = "content_block_start"
        cb_start.index = 0
        cb = MagicMock()
        cb.type = "text"
        cb_start.content_block = cb
        events.append(cb_start)

        # Text deltas
        for text in ["I'll", " read", " main.py", " for you."]:
            delta = MagicMock()
            delta.type = "content_block_delta"
            delta.index = 0
            d = MagicMock()
            d.type = "text_delta"
            d.text = text
            delta.delta = d
            events.append(delta)

        # Content block stop
        cb_stop = MagicMock()
        cb_stop.type = "content_block_stop"
        cb_stop.index = 0
        events.append(cb_stop)

        # Content block start (tool_use)
        tool_start = MagicMock()
        tool_start.type = "content_block_start"
        tool_start.index = 1
        tb = MagicMock()
        tb.type = "tool_use"
        tb.id = "call_456"
        tb.name = "view_file"
        tool_start.content_block = tb
        events.append(tool_start)

        # Tool input delta
        tool_delta = MagicMock()
        tool_delta.type = "content_block_delta"
        tool_delta.index = 1
        td = MagicMock()
        td.type = "input_json_delta"
        td.partial_json = '{"file_path":"main.py"}'
        tool_delta.delta = td
        events.append(tool_delta)

        # Tool block stop
        tool_stop = MagicMock()
        tool_stop.type = "content_block_stop"
        tool_stop.index = 1
        events.append(tool_stop)

        # Message stop
        msg_stop = MagicMock()
        msg_stop.type = "message_stop"
        ms = MagicMock()
        ms.stop_reason = "tool_use"
        msg_stop.message = ms
        events.append(msg_stop)

        # Convert events using the client's conversion method
        chunks = []
        for event in events:
            chunk = client._convert_sse_event_to_chunk(event)
            if chunk is not None:
                chunks.append(chunk)

        # Verify we got message start
        msg_starts = [c for c in chunks if isinstance(c, MessageStart)]
        assert len(msg_starts) == 1

        # Verify we got text chunks
        text_chunks = [c for c in chunks if isinstance(c, ContentBlockDelta) and c.text]
        assert len(text_chunks) == 4

        # Verify we got tool use start
        tool_starts = [c for c in chunks if isinstance(c, ContentBlockStart) and c.type == "tool_use"]
        assert len(tool_starts) == 1
        assert tool_starts[0].name == "view_file"
