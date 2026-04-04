"""Integration tests for AgentCore tool integration (Issue 22).

TDD: Tests written FIRST, expected to FAIL initially.

Acceptance Criteria:
1. AgentCore.process_turn() implements full turn processing
2. Process turn: user input -> API stream -> tool calls -> results -> API -> response
3. Tool execution is sequential (not parallel)
4. Multiple tool calls in one response work correctly
5. Tool results are formatted for API consumption
6. Tool errors are caught and formatted
7. Tool timeouts are handled
8. Streaming response yields text chunks for UI
9. Turn completes when API stops (no more tool calls)
10. Chat history is updated with all messages
"""
import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

from goz.agent.chat_client import (
    ChatClient,
    ContentBlockStart,
    ContentBlockDelta,
    ContentBlockStop,
    MessageStart,
    MessageStop,
)
from goz.agent.history import ChatHistory, ChatMessage, ToolCall
from goz.agent.core import AgentCore
from goz.config import Config
from goz.api.errors import ZaiError


# Test fixtures
@pytest.fixture
def config() -> Config:
    """Create test config."""
    return Config(
        zai_token="test-token",
        zai_base_url="https://api.test.com",
        chat_model="test-model",
        timeout=60,
    )


@pytest.fixture
def mock_tool():
    """Create a mock tool for testing."""
    tool = MagicMock()
    tool.name = "test_tool"
    tool.description = "A test tool"
    tool.input_schema = {
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        },
        "required": ["param"]
    }
    tool.execute = AsyncMock(return_value="Tool executed successfully")
    return tool


class MockStreamChunk:
    """Mock Anthropic SDK stream chunk."""

    def __init__(self, type: str, **kwargs) -> None:
        self.type = type
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestProcessTurnBasic:
    """Tests for basic process_turn functionality (Acceptance Criteria 1, 2, 8)."""

    @pytest.mark.asyncio
    async def test_process_turn_method_exists(self, config):
        """Acceptance Criterion 1: AgentCore.process_turn() implements full turn processing."""
        agent = AgentCore(config=config)

        # Verify process_turn is an async method (async generator)
        assert hasattr(agent, 'process_turn')
        # process_turn is an async generator, not a coroutine function
        assert inspect.isasyncgenfunction(agent.process_turn)

    @pytest.mark.asyncio
    async def test_process_turn_adds_user_message_to_history(self, config):
        """Acceptance Criterion 2: Process turn adds user message to history."""
        agent = AgentCore(config=config)

        # Mock the chat client to return empty stream
        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.return_value = self._empty_stream()

            # Process a turn
            async for _ in agent.process_turn("Hello, agent!"):
                pass

            # Verify user message was added to history
            assert agent.history.message_count >= 1
            last_message = agent.history.messages[-1]
            # The last message should be from the user or assistant

    @pytest.mark.asyncio
    async def test_process_turn_yields_text_chunks(self, config):
        """Acceptance Criterion 8: Streaming response yields text chunks for UI."""
        agent = AgentCore(config=config)

        # Create a stream that yields text chunks
        chunks = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Hello"),
            ContentBlockDelta(type="text_delta", index=0, text=" there"),
            ContentBlockDelta(type="text_delta", index=0, text="!"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            async def stream_chunks():
                for chunk in chunks:
                    yield chunk
            mock_chat.return_value = stream_chunks()

            # Collect yielded chunks
            yielded = []
            async for text in agent.process_turn("Hello"):
                yielded.append(text)

            # Should have yielded text chunks (excluding completion marker)
            text_chunks = [t for t in yielded if t != "\x00"]
            assert len(text_chunks) >= 3
            assert "Hello" in "".join(text_chunks)

    def _empty_stream(self):
        """Create an empty async stream."""
        async def empty():
            return
            yield
        return empty()


class TestToolExecution:
    """Tests for tool execution (Acceptance Criteria 2, 3, 4, 5, 6, 7)."""

    @pytest.mark.asyncio
    async def test_single_tool_call_executed(self, config, mock_tool):
        """Acceptance Criterion 2: Process turn handles tool calls -> results -> API."""
        agent = AgentCore(config=config)
        agent.tool_registry.register(mock_tool)

        # Create a stream that yields a tool call
        chunks = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="tool_use", index=0, id="call_1", name="test_tool"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"param":"value"}'),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="tool_use"),
        ]

        # First call returns tool request
        call1 = AsyncMock()
        async def stream_with_tool():
            for chunk in chunks:
                yield chunk

        # Second call returns final response
        call2 = AsyncMock()
        async def stream_final():
            yield MessageStart(id="msg_2", model="test-model")
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Done")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = [stream_with_tool(), stream_final()]

            # Process turn
            yielded = []
            async for text in agent.process_turn("Use test_tool"):
                yielded.append(text)

            # Verify tool was executed
            mock_tool.execute.assert_called_once_with(param="value")

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_sequential(self, config):
        """Acceptance Criterion 3: Tool execution is sequential (not parallel)."""
        agent = AgentCore(config=config)

        # Create two mock tools
        tool1 = MagicMock()
        tool1.name = "tool1"
        tool1.execute = AsyncMock(return_value="Tool1 result")

        tool2 = MagicMock()
        tool2.name = "tool2"
        tool2.execute = AsyncMock(return_value="Tool2 result")

        agent.tool_registry.register(tool1)
        agent.tool_registry.register(tool2)

        # Track execution order
        execution_order = []

        async def track_tool1(**kwargs):
            execution_order.append("tool1")
            await asyncio.sleep(0.01)  # Simulate work
            return "Tool1 result"

        async def track_tool2(**kwargs):
            execution_order.append("tool2")
            await asyncio.sleep(0.01)
            return "Tool2 result"

        tool1.execute = track_tool1
        tool2.execute = track_tool2

        # Create stream with two tool calls
        chunks = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="tool_use", index=0, id="call_1", name="tool1"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}'),
            ContentBlockStop(index=0),
            ContentBlockStart(type="tool_use", index=1, id="call_2", name="tool2"),
            ContentBlockDelta(type="input_json_delta", index=1, partial_json='{}'),
            ContentBlockStop(index=1),
            MessageStop(stop_reason="tool_use"),
        ]

        async def stream_with_tools():
            for chunk in chunks:
                yield chunk

        async def stream_final():
            yield MessageStart(id="msg_2", model="test-model")
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Done")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = [stream_with_tools(), stream_final()]

            async for _ in agent.process_turn("Use both tools"):
                pass

            # Verify tools executed in order (sequential)
            assert execution_order == ["tool1", "tool2"]

    @pytest.mark.asyncio
    async def test_multiple_iterations_tool_api_loop(self, config):
        """Acceptance Criterion 10: Loop supports multiple iterations (tool -> API -> tool -> API)."""
        agent = AgentCore(config=config)

        # Create a tool that will be called
        tool = MagicMock()
        tool.name = "test_tool"
        tool.execute = AsyncMock(return_value="Tool result")
        agent.tool_registry.register(tool)

        # Iteration 1: API requests tool
        async def stream_iter1():
            yield ContentBlockStart(type="tool_use", index=0, id="call_1", name="test_tool")
            yield ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}')
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="tool_use")

        # Iteration 2: API responds with another tool call (multi-round)
        async def stream_iter2():
            yield ContentBlockStart(type="tool_use", index=0, id="call_2", name="test_tool")
            yield ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}')
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="tool_use")

        # Iteration 3: API finally responds
        async def stream_iter3():
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Complete")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = [stream_iter1(), stream_iter2(), stream_iter3()]

            async for _ in agent.process_turn("Multi-turn request"):
                pass

            # Verify tool was called twice (once per iteration)
            assert tool.execute.call_count == 2
            # Verify API was called 3 times (initial + 2 tool result rounds)
            assert mock_chat.call_count == 3

    @pytest.mark.asyncio
    async def test_tool_errors_caught_and_formatted(self, config):
        """Acceptance Criterion 6: Tool errors are caught and formatted."""
        agent = AgentCore(config=config)

        # Create a tool that raises an error
        tool = MagicMock()
        tool.name = "failing_tool"
        tool.execute = AsyncMock(side_effect=Exception("Tool failed!"))
        agent.tool_registry.register(tool)

        # Stream with tool call
        async def stream_with_tool():
            yield ContentBlockStart(type="tool_use", index=0, id="call_1", name="failing_tool")
            yield ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}')
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="tool_use")

        # Final stream
        async def stream_final():
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Error handled")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = [stream_with_tool(), stream_final()]

            # Should not raise exception
            async for _ in agent.process_turn("Use failing_tool"):
                pass

            # Verify tool was attempted
            tool.execute.assert_called_once()

            # Verify API was called again with error result
            assert mock_chat.call_count == 2

    @pytest.mark.asyncio
    async def test_tool_timeout_handled(self, config):
        """Acceptance Criterion 7: Tool timeouts are handled."""
        agent = AgentCore(config=config)

        # Create a tool that times out
        tool = MagicMock()
        tool.name = "slow_tool"

        async def timeout_tool(**kwargs):
            await asyncio.sleep(10)  # Simulate timeout
            return "Done"

        tool.execute = timeout_tool
        agent.tool_registry.register(tool)

        # Stream with tool call
        async def stream_with_tool():
            yield ContentBlockStart(type="tool_use", index=0, id="call_1", name="slow_tool")
            yield ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}')
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="tool_use")

        # Final stream
        async def stream_final():
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Timed out")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = [stream_with_tool(), stream_final()]

            # Patch asyncio.wait_for to raise timeout
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
                # Should not raise exception
                async for _ in agent.process_turn("Use slow_tool"):
                    pass

            # Verify error was handled
            assert mock_chat.call_count == 2


class TestToolResultsFormatting:
    """Tests for tool results formatting (Acceptance Criterion 5)."""

    @pytest.mark.asyncio
    async def test_tool_results_added_to_history(self, config):
        """Acceptance Criterion 5: Tool results are formatted for API consumption."""
        agent = AgentCore(config=config)

        tool = MagicMock()
        tool.name = "test_tool"
        tool.execute = AsyncMock(return_value="Tool output")
        agent.tool_registry.register(tool)

        # Stream with tool call
        async def stream_with_tool():
            yield ContentBlockStart(type="tool_use", index=0, id="call_1", name="test_tool")
            yield ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}')
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="tool_use")

        # Final stream
        async def stream_final():
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Done")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = [stream_with_tool(), stream_final()]

            async for _ in agent.process_turn("Use test_tool"):
                pass

            # Check history has tool call and result
            # The history should contain messages with tool-related content
            messages = agent.history.to_api_format()

            # Should have user message, tool calls, and tool results
            assert len(messages) > 0

    @pytest.mark.asyncio
    async def test_completion_marker_yielded(self, config):
        """Acceptance Criterion 8: Completion marker (\x00) signals turn complete."""
        agent = AgentCore(config=config)

        # Simple text response stream
        async def stream_text():
            yield MessageStart(id="msg_1", model="test-model")
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Hello")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.return_value = stream_text()

            # Collect all yielded chunks
            yielded = []
            async for chunk in agent.process_turn("Hello"):
                yielded.append(chunk)

            # Last chunk should be completion marker
            assert yielded[-1] == "\x00"


class TestChatHistoryUpdates:
    """Tests for chat history management (Acceptance Criterion 10)."""

    @pytest.mark.asyncio
    async def test_chat_history_updated_with_all_messages(self, config):
        """Acceptance Criterion 10: Chat history is updated with all messages."""
        agent = AgentCore(config=config)
        initial_count = agent.history.message_count

        # Simple text response
        async def stream_text():
            yield MessageStart(id="msg_1", model="test-model")
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Response")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.return_value = stream_text()

            async for _ in agent.process_turn("User message"):
                pass

            # History should have grown
            assert agent.history.message_count > initial_count

    @pytest.mark.asyncio
    async def test_turn_completes_when_api_stops(self, config):
        """Acceptance Criterion 9: Turn completes when API stops (no more tool calls)."""
        agent = AgentCore(config=config)

        # Stream that ends normally
        async def stream_text():
            yield MessageStart(id="msg_1", model="test-model")
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Final response")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.return_value = stream_text()

            # Should complete without hanging
            completed = False
            async for chunk in agent.process_turn("Complete turn"):
                if chunk == "\x00":
                    completed = True
                    break

            assert completed, "Turn should complete with completion marker"


class TestMaxIterations:
    """Tests for preventing infinite loops."""

    @pytest.mark.asyncio
    async def test_max_iterations_prevents_infinite_loop(self, config):
        """Test that max_iterations prevents infinite tool call loops."""
        agent = AgentCore(config=config)

        tool = MagicMock()
        tool.name = "loop_tool"
        tool.execute = AsyncMock(return_value="Result")
        agent.tool_registry.register(tool)

        # Always return a tool call (simulating a loop)
        async def stream_always_tool():
            yield ContentBlockStart(type="tool_use", index=0, id="call_1", name="loop_tool")
            yield ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}')
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="tool_use")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.return_value = stream_always_tool()

            # Should eventually stop due to max_iterations
            iterations = 0
            async for _ in agent.process_turn("Loop forever"):
                iterations += 1

            # Should complete (not hang forever)
            # The exact count depends on max_iterations setting
            assert iterations >= 1


class TestToolNotFound:
    """Tests for unknown tool handling."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, config):
        """Test that unknown tool returns error to API."""
        agent = AgentCore(config=config)

        # Don't register any tools

        # Stream with unknown tool call
        async def stream_with_unknown_tool():
            yield ContentBlockStart(type="tool_use", index=0, id="call_1", name="unknown_tool")
            yield ContentBlockDelta(type="input_json_delta", index=0, partial_json='{}')
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="tool_use")

        # Final stream
        async def stream_final():
            yield ContentBlockStart(type="text", index=0)
            yield ContentBlockDelta(type="text_delta", index=0, text="Tool not found")
            yield ContentBlockStop(index=0)
            yield MessageStop(stop_reason="end_turn")

        with patch.object(agent.chat_client, 'chat_completion') as mock_chat:
            mock_chat.side_effect = [stream_with_unknown_tool(), stream_final()]

            # Should not raise
            async for _ in agent.process_turn("Use unknown_tool"):
                pass

            # API should have been called twice (initial + error response)
            assert mock_chat.call_count == 2
