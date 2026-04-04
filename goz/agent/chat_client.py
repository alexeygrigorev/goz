"""Chat API Client for Z.AI (Issue 17).

This module provides the ChatClient class for interacting with the Z.AI
chat API using the Anthropic SDK with tool calling support.

Acceptance Criteria:
1. ChatClient class exists in goz/agent/chat_client.py
2. Uses existing Anthropic SDK (same as Vision API)
3. Uses config.zai_token and config.zai_base_url
4. chat_completion() method sends messages and returns async iterator
5. Supports tools parameter for function calling
6. Supports tool_choice parameter ("auto", "any")
7. Supports stream parameter (True/False)
8. Response chunks yield text deltas
9. Tool calls are properly formatted in stream
10. Errors raised as appropriate exceptions (AuthError, ApiError, etc.)
11. Timeout configurable via config
"""
import asyncio
import json
from dataclasses import dataclass
from typing import AsyncIterator, Literal

import anthropic
from anthropic import AsyncAnthropic

from goz.api.errors import AuthError, ApiError, NetworkError, TimeoutError, ZaiError
from goz.config import Config


# Chunk types for streaming responses (from spec)
@dataclass
class ContentBlockStart:
    """Start of a content block in the stream.

    Attributes:
        type: The type of content block ("text" or "tool_use")
        index: The index of this content block
        id: Tool call ID (only for tool_use type)
        name: Tool name (only for tool_use type)
    """
    type: Literal["text", "tool_use"]
    index: int
    id: str | None = None
    name: str | None = None


@dataclass
class ContentBlockDelta:
    """Delta for a content block in the stream.

    Attributes:
        type: The type of delta ("text_delta" or "input_json_delta")
        index: The index of this content block
        text: Text content (only for text_delta type)
        partial_json: Partial JSON string (only for input_json_delta type)
    """
    type: Literal["text_delta", "input_json_delta"]
    index: int
    text: str | None = None
    partial_json: str | None = None


@dataclass
class ContentBlockStop:
    """End of a content block in the stream.

    Attributes:
        index: The index of this content block
    """
    index: int


@dataclass
class MessageStart:
    """Start of the message.

    Attributes:
        id: Message ID
        model: Model name
    """
    id: str
    model: str


@dataclass
class MessageStop:
    """End of the message.

    Attributes:
        stop_reason: Reason for stopping ("end_turn", "max_tokens", "tool_use")
    """
    stop_reason: Literal["end_turn", "max_tokens", "tool_use"]


# Union type for all chunk types
Chunk = ContentBlockStart | ContentBlockDelta | ContentBlockStop | MessageStart | MessageStop


class ChatClient:
    """Client for Z.AI Chat API with tool calling support.

    This client uses the Anthropic SDK to interact with the Z.AI chat API,
    supporting streaming responses, tool calling, and various generation
    parameters.

    Attributes:
        config: Configuration object containing API credentials and settings
        _client: Internal AsyncAnthropic client instance
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialize ChatClient.

        Args:
            config: Optional config object. If not provided, loads from default location.

        Acceptance Criteria:
        - Uses config.zai_token and config.zai_base_url (AC 3)
        - Uses AsyncAnthropic from existing SDK (AC 2)
        - Timeout is configurable via config (AC 11)
        """
        if config is None:
            from goz.config import load_config
            config = load_config()

        self.config = config

        # Initialize async Anthropic client (same pattern as VisionClient)
        self._client = AsyncAnthropic(
            api_key=self.config.zai_token,
            base_url=self.config.zai_base_url,
            timeout=self.config.timeout,
        )

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "any", "none"] | dict = "auto",
        stream: bool = True,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Chunk]:
        """Stream chat completion with tool calling support.

        Args:
            messages: Chat history in Anthropic format
            tools: Tool definitions in Anthropic format (optional)
            tool_choice: How to select tools ("auto", "any", "none", or specific tool dict)
            stream: Whether to stream response (True) or wait for complete response (False)
            temperature: Generation temperature (uses config default if None)
            max_tokens: Max tokens in response (uses config default if None)

        Yields:
            Chunk objects from the API response

        Raises:
            AuthError: For 401/403 authentication failures
            ApiError: For other API errors (4xx, 5xx)
            NetworkError: For connection failures
            TimeoutError: For request timeouts

        Acceptance Criteria:
        - Returns async iterator (AC 4)
        - Supports tools parameter (AC 5)
        - Supports tool_choice parameter (AC 6)
        - Supports stream parameter (AC 7)
        - Response chunks yield text deltas (AC 8)
        - Tool calls properly formatted in stream (AC 9)
        - Errors raised as appropriate exceptions (AC 10)
        """
        # Build request parameters
        params: dict = {
            "model": self.config.chat_model,
            "messages": messages,
        }

        # Add optional parameters
        if tools is not None:
            params["tools"] = tools

        if tool_choice != "auto":
            params["tool_choice"] = tool_choice

        if temperature is not None:
            params["temperature"] = temperature
        else:
            params["temperature"] = self.config.temperature

        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        else:
            params["max_tokens"] = self.config.max_tokens

        try:
            if stream:
                # Streaming mode
                async with self._client.messages.stream(**params) as stream:
                    async for event in stream:
                        chunk = self._convert_sse_event_to_chunk(event)
                        if chunk is not None:
                            yield chunk
            else:
                # Non-streaming mode - convert response to chunks
                response = await self._client.messages.create(**params)
                async for chunk in self._response_to_chunks(response):
                    yield chunk

        except anthropic.AuthenticationError as e:
            raise AuthError(str(e))
        except anthropic.APITimeoutError as e:
            raise TimeoutError(timeoutMs=int(self.config.timeout * 1000))
        except anthropic.APIConnectionError as e:
            raise NetworkError(str(e))
        except anthropic.APIStatusError as e:
            raise ApiError(str(e), statusCode=e.status_code)
        except Exception as e:
            raise ZaiError(f"Unexpected error: {e}")

    def _convert_sse_event_to_chunk(self, event: anthropic.types.RawMessageStreamEvent) -> Chunk | None:
        """Convert Anthropic SSE event to our Chunk type.

        Args:
            event: Raw SSE event from Anthropic SDK

        Returns:
            Chunk object or None if event type not handled
        """
        event_type = event.type

        if event_type == "message_start":
            return MessageStart(
                id=event.message.id,
                model=event.message.model,
            )

        elif event_type == "content_block_start":
            content_block = event.content_block
            if content_block.type == "text":
                return ContentBlockStart(
                    type="text",
                    index=event.index,
                )
            elif content_block.type == "tool_use":
                return ContentBlockStart(
                    type="tool_use",
                    index=event.index,
                    id=content_block.id,
                    name=content_block.name,
                )

        elif event_type == "content_block_delta":
            delta = event.delta
            if delta.type == "text_delta":
                return ContentBlockDelta(
                    type="text_delta",
                    index=event.index,
                    text=delta.text,
                )
            elif delta.type == "input_json_delta":
                return ContentBlockDelta(
                    type="input_json_delta",
                    index=event.index,
                    partial_json=delta.partial_json,
                )

        elif event_type == "content_block_stop":
            return ContentBlockStop(index=event.index)

        elif event_type == "message_stop":
            return MessageStop(stop_reason=event.message.stop_reason)

        # Return None for unhandled event types
        return None

    async def _response_to_chunks(self, response: anthropic.types.Message) -> AsyncIterator[Chunk]:
        """Convert non-streaming response to chunk stream.

        Args:
            response: Complete response from messages.create()

        Yields:
            Chunk objects representing the response
        """
        # Yield message start
        yield MessageStart(id=response.id, model=response.model)

        # Yield content blocks
        for index, block in enumerate(response.content):
            if block.type == "text":
                yield ContentBlockStart(type="text", index=index)
                yield ContentBlockDelta(type="text_delta", index=index, text=block.text)
                yield ContentBlockStop(index=index)

            elif block.type == "tool_use":
                yield ContentBlockStart(
                    type="tool_use",
                    index=index,
                    id=block.id,
                    name=block.name,
                )
                # Yield the input JSON as a single delta
                input_json = json.dumps(block.input)
                yield ContentBlockDelta(
                    type="input_json_delta",
                    index=index,
                    partial_json=input_json,
                )
                yield ContentBlockStop(index=index)

        # Yield message stop
        yield MessageStop(stop_reason=response.stop_reason)

    async def extract_tool_calls(
        self,
        chunks: list[Chunk],
    ) -> list[dict]:
        """Extract tool calls from accumulated stream chunks.

        This method processes a list of chunks and extracts complete
        tool_call objects by accumulating partial_json deltas.

        Args:
            chunks: List of chunks from a stream

        Returns:
            List of tool_call dicts with id, name, and input keys

        Example:
            >>> chunks = []
            >>> async for chunk in client.chat_completion(messages, tools=tools):
            ...     chunks.append(chunk)
            >>> tool_calls = await client.extract_tool_calls(chunks)
        """
        tool_calls: list[dict] = []
        current_tool: dict[str, Any] | None = None
        accumulated_json: list[str] = []

        for chunk in chunks:
            if isinstance(chunk, ContentBlockStart) and chunk.type == "tool_use":
                # Start of a new tool call
                current_tool = {
                    "id": chunk.id,
                    "name": chunk.name,
                    "input": {},
                }
                accumulated_json = []

            elif isinstance(chunk, ContentBlockDelta) and chunk.type == "input_json_delta":
                # Accumulate partial JSON
                if chunk.partial_json:
                    accumulated_json.append(chunk.partial_json)

            elif isinstance(chunk, ContentBlockStop) and current_tool is not None:
                # End of current tool call - parse accumulated JSON
                if accumulated_json:
                    try:
                        json_str = "".join(accumulated_json)
                        current_tool["input"] = json.loads(json_str)
                    except json.JSONDecodeError:
                        # If JSON is incomplete, keep as string
                        current_tool["input"] = {"raw": "".join(accumulated_json)}

                tool_calls.append(current_tool)
                current_tool = None
                accumulated_json = []

        return tool_calls

    async def simple_chat(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        """Simple chat without streaming or tool calling.

        This is a convenience method for basic chat interactions.

        Args:
            message: User message
            system_prompt: Optional system prompt

        Returns:
            Complete response text
        """
        messages: list[dict] = [{"role": "user", "content": message}]

        params: dict = {
            "model": self.config.chat_model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
        }

        if system_prompt:
            params["system"] = system_prompt

        try:
            response = await self._client.messages.create(**params)
            return response.content[0].text
        except anthropic.AuthenticationError as e:
            raise AuthError(str(e))
        except anthropic.APITimeoutError as e:
            raise TimeoutError(timeoutMs=int(self.config.timeout * 1000))
        except anthropic.APIConnectionError as e:
            raise NetworkError(str(e))
        except anthropic.APIStatusError as e:
            raise ApiError(str(e), statusCode=e.status_code)
        except Exception as e:
            raise ZaiError(f"Unexpected error: {e}")
