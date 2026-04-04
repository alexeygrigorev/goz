"""Unit tests for StreamProcessor (Issue 16).

TDD: Tests written FIRST, expected to FAIL initially.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any
import json

import pytest

from goz.agent.stream_processor import (
    StreamProcessor,
    ToolCall,
    ProcessedStream,
)


class MockStreamChunk:
    """Mock Anthropic SDK stream chunk."""

    def __init__(self, type: str, **kwargs) -> None:
        self.type = type
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"MockStreamChunk(type={self.type})"


class TestToolCall:
    """Tests for ToolCall dataclass (Acceptance Criteria 8)."""

    def test_tool_call_dataclass_exists(self):
        """Test ToolCall dataclass exists with required fields."""
        tool_call = ToolCall(
            id="call_123",
            name="test_tool",
            arguments={"param": "value"}
        )

        assert tool_call.id == "call_123"
        assert tool_call.name == "test_tool"
        assert tool_call.arguments == {"param": "value"}

    def test_tool_call_with_empty_arguments(self):
        """Test ToolCall with empty arguments."""
        tool_call = ToolCall(
            id="call_456",
            name="simple_tool",
            arguments={}
        )

        assert tool_call.id == "call_456"
        assert tool_call.name == "simple_tool"
        assert tool_call.arguments == {}


class TestProcessedStream:
    """Tests for ProcessedStream dataclass (Acceptance Criteria 9)."""

    def test_processed_stream_dataclass_exists(self):
        """Test ProcessedStream dataclass exists with required fields."""
        tool_calls = [
            ToolCall(id="call_1", name="tool1", arguments={"x": 1})
        ]

        result = ProcessedStream(
            full_text="Hello world",
            tool_calls=tool_calls,
            raw_chunks=["chunk1", "chunk2"]
        )

        assert result.full_text == "Hello world"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "tool1"
        assert result.raw_chunks == ["chunk1", "chunk2"]

    def test_processed_stream_with_no_tool_calls(self):
        """Test ProcessedStream with no tool calls."""
        result = ProcessedStream(
            full_text="Just text response",
            tool_calls=[],
            raw_chunks=["chunk1"]
        )

        assert result.full_text == "Just text response"
        assert result.tool_calls == []
        assert result.raw_chunks == ["chunk1"]


class TestStreamProcessorClass:
    """Tests for StreamProcessor class (Acceptance Criteria 1)."""

    def test_stream_processor_class_exists(self):
        """Test StreamProcessor class exists."""
        mock_config = MagicMock()
        mock_config.timeout = 120

        processor = StreamProcessor(config=mock_config)

        assert processor is not None
        assert hasattr(processor, 'config')
        assert processor.config == mock_config

    def test_stream_processor_has_process_stream_method(self):
        """Test StreamProcessor has process_stream method (Acceptance Criteria 2)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        assert hasattr(processor, 'process_stream')
        assert callable(processor.process_stream)

    def test_stream_processor_has_get_result_method(self):
        """Test StreamProcessor has get_result method."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        assert hasattr(processor, 'get_result')
        assert callable(processor.get_result)

    def test_stream_processor_has_extract_tool_calls_method(self):
        """Test StreamProcessor has extract_tool_calls method (Acceptance Criteria 4)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        assert hasattr(processor, 'extract_tool_calls')
        assert callable(processor.extract_tool_calls)


class TestProcessStream:
    """Tests for process_stream method (Acceptance Criteria 2, 7)."""

    @pytest.mark.asyncio
    async def test_process_stream_yields_text_chunks(self):
        """Test process_stream yields text chunks for UI (Acceptance Criteria 7)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        # Create mock chunks with text deltas
        chunks = [
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": "Hello"}),
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": " world"}),
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": "!"}),
            MockStreamChunk("message_stop"),
        ]

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        # Collect yielded text chunks
        text_chunks = []
        async for text in processor.process_stream(mock_stream()):
            text_chunks.append(text)

        assert len(text_chunks) == 3
        assert text_chunks[0] == "Hello"
        assert text_chunks[1] == " world"
        assert text_chunks[2] == "!"

    @pytest.mark.asyncio
    async def test_process_stream_accumulates_full_text(self):
        """Test process_stream accumulates full text."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        chunks = [
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": "Hello"}),
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": " world"}),
            MockStreamChunk("message_stop"),
        ]

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        # Consume the stream
        async for _ in processor.process_stream(mock_stream()):
            pass

        result = processor.get_result()
        assert result.full_text == "Hello world"

    @pytest.mark.asyncio
    async def test_process_stream_stores_raw_chunks(self):
        """Test process_stream stores raw chunks (Acceptance Criteria 3)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        chunks = [
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": "Hi"}),
            MockStreamChunk("message_stop"),
        ]

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        async for _ in processor.process_stream(mock_stream()):
            pass

        result = processor.get_result()
        assert len(result.raw_chunks) == 2
        assert result.raw_chunks[0].type == "content_block_delta"
        assert result.raw_chunks[1].type == "message_stop"

    @pytest.mark.asyncio
    async def test_process_stream_returns_empty_tool_calls_by_default(self):
        """Test process_stream returns empty tool_calls list by default (Acceptance Criteria 3)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        chunks = [
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": "No tools here"}),
            MockStreamChunk("message_stop"),
        ]

        async def mock_stream():
            for chunk in chunks:
                yield chunk

        async for _ in processor.process_stream(mock_stream()):
            pass

        result = processor.get_result()
        assert result.tool_calls == []


class TestExtractToolCalls:
    """Tests for extract_tool_calls method (Acceptance Criteria 4, 5, 6)."""

    def test_extract_tool_calls_parses_single_tool_use(self):
        """Test extract_tool_calls parses single tool use (Acceptance Criteria 4)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        chunks = [
            MockStreamChunk(
                "content_block_start",
                index=0,
                content_block={"type": "tool_use", "id": "call_123", "name": "search"}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=0,
                delta={"type": "input_json_delta", "partial_json": "{\"query\":"}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=0,
                delta={"type": "input_json_delta", "partial_json": "\"test\""}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=0,
                delta={"type": "input_json_delta", "partial_json": "}"}
            ),
            MockStreamChunk("content_block_stop", index=0),
        ]

        tool_calls = processor.extract_tool_calls(chunks)

        assert len(tool_calls) == 1
        assert tool_calls[0].id == "call_123"
        assert tool_calls[0].name == "search"
        assert tool_calls[0].arguments == {"query": "test"}

    def test_extract_tool_calls_handles_partial_json_accumulation(self):
        """Test extract_tool_calls handles partial_json accumulation (Acceptance Criteria 5)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        # JSON is split across multiple chunks
        chunks = [
            MockStreamChunk(
                "content_block_start",
                index=0,
                content_block={"type": "tool_use", "id": "call_456", "name": "complex_tool"}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=0,
                delta={"type": "input_json_delta", "partial_json": "{\"param1\":"}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=0,
                delta={"type": "input_json_delta", "partial_json": " \"value1\","}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=0,
                delta={"type": "input_json_delta", "partial_json": "\"param2\": 42}"}
            ),
            MockStreamChunk("content_block_stop", index=0),
        ]

        tool_calls = processor.extract_tool_calls(chunks)

        assert len(tool_calls) == 1
        assert tool_calls[0].arguments == {"param1": "value1", "param2": 42}

    def test_extract_tool_calls_handles_multiple_tool_calls(self):
        """Test extract_tool_calls handles multiple tool calls (Acceptance Criteria 6)."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        # Two tool calls in one response
        chunks = [
            # First tool call
            MockStreamChunk(
                "content_block_start",
                index=0,
                content_block={"type": "tool_use", "id": "call_1", "name": "search"}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=0,
                delta={"type": "input_json_delta", "partial_json": "{\"q\":\"a\"}"}
            ),
            MockStreamChunk("content_block_stop", index=0),
            # Second tool call
            MockStreamChunk(
                "content_block_start",
                index=1,
                content_block={"type": "tool_use", "id": "call_2", "name": "read"}
            ),
            MockStreamChunk(
                "content_block_delta",
                index=1,
                delta={"type": "input_json_delta", "partial_json": "{\"url\":\"x\"}"}
            ),
            MockStreamChunk("content_block_stop", index=1),
        ]

        tool_calls = processor.extract_tool_calls(chunks)

        assert len(tool_calls) == 2
        assert tool_calls[0].id == "call_1"
        assert tool_calls[0].name == "search"
        assert tool_calls[0].arguments == {"q": "a"}
        assert tool_calls[1].id == "call_2"
        assert tool_calls[1].name == "read"
        assert tool_calls[1].arguments == {"url": "x"}

    def test_extract_tool_calls_with_empty_arguments(self):
        """Test extract_tool_calls with tool that has no arguments."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        chunks = [
            MockStreamChunk(
                "content_block_start",
                index=0,
                content_block={"type": "tool_use", "id": "call_789", "name": "no_args_tool"}
            ),
            MockStreamChunk("content_block_stop", index=0),
        ]

        tool_calls = processor.extract_tool_calls(chunks)

        assert len(tool_calls) == 1
        assert tool_calls[0].id == "call_789"
        assert tool_calls[0].name == "no_args_tool"
        assert tool_calls[0].arguments == {}

    def test_extract_tool_calls_returns_empty_list_for_no_tools(self):
        """Test extract_tool_calls returns empty list when no tools present."""
        mock_config = MagicMock()
        processor = StreamProcessor(config=mock_config)

        chunks = [
            MockStreamChunk("content_block_delta", delta={"type": "text_delta", "text": "Just text"}),
            MockStreamChunk("message_stop"),
        ]

        tool_calls = processor.extract_tool_calls(chunks)

        assert tool_calls == []
