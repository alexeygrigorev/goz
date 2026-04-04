"""Stream Processor for handling Anthropic API streaming responses.

This module provides the StreamProcessor class for processing streaming
responses from the Anthropic-compatible Z.AI API, extracting text chunks
for real-time UI updates and parsing tool calls.

Acceptance Criteria (Issue 16):
1. StreamProcessor class exists
2. process_stream() method takes async iterator of chunks
3. Returns ProcessedStream with: full_text, tool_calls, raw_chunks
4. extract_tool_calls() parses tool calls from chunks
5. Handles partial_json accumulation
6. Handles multiple tool calls in one response
7. Yields text chunks for real-time UI updates
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from goz.config import Config


logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call extracted from a streaming response.

    Attributes:
        id: The unique identifier for this tool call
        name: The name of the tool being called
        arguments: The arguments passed to the tool (as a dict)

    Acceptance Criteria 8: ToolCall dataclass: id, name, arguments
    """
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedStream:
    """Result of processing a complete API stream.

    Attributes:
        full_text: The complete accumulated text from the stream
        tool_calls: List of tool calls extracted from the stream
        raw_chunks: All raw chunks received (for debugging/replay)

    Acceptance Criteria 9: ProcessedStream dataclass: full_text, tool_calls, raw_chunks
    """
    full_text: str
    tool_calls: list[ToolCall]
    raw_chunks: list[Any] = field(default_factory=list)


class StreamProcessor:
    """Processes streaming responses from Anthropic API.

    This class handles streaming responses from the Z.AI Anthropic-compatible API.
    It accumulates text chunks for real-time UI updates and extracts tool calls
    from content blocks.

    Acceptance Criteria 1: StreamProcessor class exists
    Acceptance Criteria 2: process_stream() method takes async iterator of chunks

    Chunk Types (from Anthropic SDK):
    - content_block_start: {"type": "text" | "tool_use"}
    - content_block_delta: {"type": "text_delta", "text": "..."}
                         or {"type": "input_json_delta", "partial_json": "..."}
    - content_block_stop
    - message_stop
    """

    def __init__(self, config: Config) -> None:
        """Initialize StreamProcessor.

        Args:
            config: Configuration object

        Acceptance Criteria 1: StreamProcessor class exists
        """
        self.config = config
        self._full_text: str = ""
        self._raw_chunks: list[Any] = []
        self._text_chunks: list[str] = []

        # Tool call tracking
        self._tool_blocks: dict[int, dict[str, Any]] = {}  # index -> {id, name, partial_json}
        self._current_block_index: int | None = None

    async def process_stream(
        self,
        stream: AsyncIterator[Any],
    ) -> AsyncIterator[str]:
        """Process stream and yield text chunks.

        This method consumes the streaming response, yielding text chunks
        for real-time UI updates. After the stream completes, use get_result()
        to retrieve the full processed result including tool calls.

        Args:
            stream: Async iterator of chunks from Anthropic SDK

        Yields:
            Text chunks as they arrive from the API

        Acceptance Criteria 2: process_stream() method takes async iterator of chunks
        Acceptance Criteria 7: Yields text chunks for real-time UI updates
        """
        # Reset state for new stream
        self._full_text = ""
        self._raw_chunks = []
        self._text_chunks = []
        self._tool_blocks = {}
        self._current_block_index = None

        async for chunk in stream:
            # Store raw chunk
            self._raw_chunks.append(chunk)

            # Process chunk based on type
            chunk_type = getattr(chunk, 'type', None)

            if chunk_type == 'content_block_delta':
                await self._handle_content_block_delta(chunk)
            elif chunk_type == 'content_block_start':
                await self._handle_content_block_start(chunk)
            elif chunk_type == 'content_block_stop':
                await self._handle_content_block_stop(chunk)
            elif chunk_type == 'message_stop':
                # Stream is complete
                pass

        # Yield all accumulated text chunks
        for text_chunk in self._text_chunks:
            yield text_chunk

    async def _handle_content_block_delta(self, chunk: Any) -> None:
        """Handle content_block_delta chunk.

        Extracts text deltas for UI updates and partial_json for tool arguments.
        """
        delta = getattr(chunk, 'delta', None)
        if not delta:
            return

        delta_type = delta.get('type', '')

        if delta_type == 'text_delta':
            # Text content - yield for UI and accumulate
            text = delta.get('text', '')
            if text:
                self._full_text += text
                self._text_chunks.append(text)

        elif delta_type == 'input_json_delta':
            # Partial JSON for tool arguments
            if self._current_block_index is not None:
                partial_json = delta.get('partial_json', '')
                if self._current_block_index not in self._tool_blocks:
                    self._tool_blocks[self._current_block_index] = {
                        'partial_json': ''
                    }
                self._tool_blocks[self._current_block_index]['partial_json'] += partial_json

    async def _handle_content_block_start(self, chunk: Any) -> None:
        """Handle content_block_start chunk.

        Identifies new tool_use blocks.
        """
        index = getattr(chunk, 'index', None)
        content_block = getattr(chunk, 'content_block', None)

        if index is not None and content_block:
            self._current_block_index = index

            if content_block.get('type') == 'tool_use':
                self._tool_blocks[index] = {
                    'id': content_block.get('id', ''),
                    'name': content_block.get('name', ''),
                    'partial_json': ''
                }
            else:
                # Text block - just track the index
                if index not in self._tool_blocks:
                    self._tool_blocks[index] = {}

    async def _handle_content_block_stop(self, chunk: Any) -> None:
        """Handle content_block_stop chunk.

        Finalizes tool argument accumulation.
        """
        index = getattr(chunk, 'index', None)
        if index is not None and index in self._tool_blocks:
            # Parse accumulated JSON for tool arguments
            partial_json = self._tool_blocks[index].get('partial_json', '')
            if partial_json:
                try:
                    self._tool_blocks[index]['arguments'] = json.loads(partial_json)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse tool arguments: {partial_json}")
                    self._tool_blocks[index]['arguments'] = {}

    def get_result(self) -> ProcessedStream:
        """Get the final processed result.

        Returns a ProcessedStream containing the full text, extracted tool calls,
        and all raw chunks received.

        Returns:
            ProcessedStream with full_text, tool_calls, and raw_chunks

        Acceptance Criteria 3: Returns ProcessedStream with: full_text, tool_calls, raw_chunks
        """
        tool_calls = self.extract_tool_calls(self._raw_chunks)

        return ProcessedStream(
            full_text=self._full_text,
            tool_calls=tool_calls,
            raw_chunks=self._raw_chunks
        )

    def extract_tool_calls(self, chunks: list[Any]) -> list[ToolCall]:
        """Parse tool calls from accumulated chunks.

        This method processes the raw chunks to extract any tool calls that
        were present in the response. It handles partial_json accumulation
        and multiple tool calls in a single response.

        Args:
            chunks: List of raw chunks from the API stream

        Returns:
            List of ToolCall objects extracted from the stream

        Acceptance Criteria 4: extract_tool_calls() parses tool calls from chunks
        Acceptance Criteria 5: Handles partial_json accumulation
        Acceptance Criteria 6: Handles multiple tool calls in one response
        """
        # Re-process chunks to extract tool calls
        tool_blocks: dict[int, dict[str, Any]] = {}

        for chunk in chunks:
            chunk_type = getattr(chunk, 'type', None)

            if chunk_type == 'content_block_start':
                index = getattr(chunk, 'index', None)
                content_block = getattr(chunk, 'content_block', None)

                if index is not None and content_block:
                    if content_block.get('type') == 'tool_use':
                        tool_blocks[index] = {
                            'id': content_block.get('id', ''),
                            'name': content_block.get('name', ''),
                            'partial_json': ''
                        }

            elif chunk_type == 'content_block_delta':
                index = getattr(chunk, 'index', None)
                delta = getattr(chunk, 'delta', None)

                if index is not None and delta and index in tool_blocks:
                    delta_type = delta.get('type', '')
                    if delta_type == 'input_json_delta':
                        partial_json = delta.get('partial_json', '')
                        tool_blocks[index]['partial_json'] += partial_json

            elif chunk_type == 'content_block_stop':
                index = getattr(chunk, 'index', None)
                if index is not None and index in tool_blocks:
                    partial_json = tool_blocks[index].get('partial_json', '')
                    # Always try to parse - even if partial_json was accumulated
                    try:
                        tool_blocks[index]['arguments'] = json.loads(partial_json) if partial_json else {}
                    except json.JSONDecodeError:
                        tool_blocks[index]['arguments'] = {}

        # Convert tool blocks to ToolCall objects
        tool_calls = []
        for block in tool_blocks.values():
            if block.get('name'):  # Only include blocks with a tool name
                tool_calls.append(ToolCall(
                    id=block.get('id', ''),
                    name=block.get('name', ''),
                    arguments=block.get('arguments', {})
                ))

        return tool_calls
