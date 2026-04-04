"""Core agent class for interactive coding.

This module provides the AgentCore class which is the main entry point
for the interactive coding agent with full tool integration.

Acceptance Criteria (Issue 22):
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
import logging
from typing import Any, AsyncIterator

from goz.agent.chat_client import ChatClient, Chunk
from goz.agent.history import ChatHistory, ChatMessage, ToolCall
from goz.agent.tools.base import ToolError, ToolInputError
from goz.agent.tools import ToolRegistry
from goz.api.errors import ApiError, AuthError, NetworkError, TimeoutError, ZaiError
from goz.config import Config


logger = logging.getLogger(__name__)

# Completion marker for signaling turn completion to UI
COMPLETION_MARKER = "\x00"


class AgentCore:
    """Core agent class for interactive coding.

    This class implements the full agent loop with tool integration:
    - User input -> API stream -> tool calls -> tool execution -> results -> API -> response
    - Handles multiple iterations (tool -> API -> tool -> API -> response)
    - Yields text chunks for real-time UI updates
    - Manages chat history with all messages

    Attributes:
        config: Configuration for the agent
        history: Chat history manager
        tool_registry: Registry of available tools
        chat_client: Client for Z.AI Chat API
        max_iterations: Maximum tool-API iterations to prevent infinite loops
    """

    def __init__(
        self,
        config: Config,
        history: ChatHistory | None = None,
        tool_registry: ToolRegistry | None = None,
        stream_processor: Any = None,
        max_iterations: int = 10,
    ) -> None:
        """Initialize AgentCore.

        Args:
            config: Configuration object
            history: Optional ChatHistory (creates new if None)
            tool_registry: Optional ToolRegistry (creates new if None)
            stream_processor: Optional stream processor (not used in current implementation)
            max_iterations: Maximum tool-API iterations per turn (default: 10)
        """
        self.config = config
        self.history = history if history is not None else ChatHistory()
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
        self.stream_processor = stream_processor
        self.max_iterations = max_iterations

        # Initialize chat client
        self.chat_client = ChatClient(config=config)

    async def process_turn(
        self,
        user_input: str,
    ) -> AsyncIterator[str]:
        """Process a user turn and yield streaming response.

        This is the main agent loop. It:
        1. Adds user message to history
        2. Loops (up to max_iterations):
           a. Calls API with current history
           b. Streams response to UI (yields text chunks)
           c. Checks for tool calls
           d. If no tool calls, breaks
           e. Executes tools sequentially
           f. Adds tool calls and results to history
        3. Adds assistant message to history
        4. Yields completion marker

        Args:
            user_input: User's input message

        Yields:
            Text chunks for real-time UI display, followed by COMPLETION_MARKER

        Acceptance Criteria:
        - AC 1: Implements full turn processing
        - AC 2: user input -> API -> tools -> results -> API -> response
        - AC 3: Sequential tool execution
        - AC 4: Multiple tool calls in one response work
        - AC 5: Tool results formatted for API
        - AC 6: Tool errors caught and formatted
        - AC 7: Tool timeouts handled
        - AC 8: Yields text chunks for UI
        - AC 9: Completes when API stops
        - AC 10: History updated with all messages
        """
        # Step 1: Add user message to history
        self.history.add(ChatMessage(role="user", content=user_input))

        # Step 2: Main loop for tool-API iterations
        for iteration in range(self.max_iterations):
            # Step 2a: Call API with current history
            messages = self.history.to_api_format()
            tools_schema = self.tool_registry.to_openai_schema()

            # Step 2b: Process stream and yield text for UI
            accumulated_chunks: list[Chunk] = []
            accumulated_text: list[str] = []

            try:
                stream = self.chat_client.chat_completion(
                    messages=messages,
                    tools=tools_schema if tools_schema else None,
                    tool_choice="auto",
                )

                async for chunk in stream:
                    accumulated_chunks.append(chunk)

                    # Yield text for UI (AC 8)
                    # ContentBlockDelta has type="text_delta" or type="input_json_delta"
                    if hasattr(chunk, 'type') and chunk.type == "text_delta":
                        if hasattr(chunk, 'text') and chunk.text:
                            accumulated_text.append(chunk.text)
                            yield chunk.text

                # Step 2c: Extract tool calls from stream
                tool_calls = await self._extract_tool_calls_from_chunks(accumulated_chunks)

                # Step 2d: Check for completion (no more tool calls)
                if not tool_calls:
                    # No tools, turn is complete - add assistant message to history
                    assistant_text = "".join(accumulated_text)
                    self.history.add(ChatMessage(role="assistant", content=assistant_text))
                    # Yield completion marker (AC 9)
                    yield COMPLETION_MARKER
                    break

                # Step 2e: Execute tools sequentially (AC 3, AC 4)
                for tool_call_dict in tool_calls:
                    # Create tool call message (AC 10)
                    tool_call_msg = ChatMessage(
                        role="tool_call",
                        content=f"Called {tool_call_dict['name']}",
                        tool_calls=[ToolCall(
                            id=tool_call_dict['id'],
                            name=tool_call_dict['name'],
                            input=tool_call_dict['input'],
                        )],
                    )
                    self.history.add(tool_call_msg)

                    # Execute tool (AC 5, AC 6, AC 7)
                    tool_result = await self._execute_tool_call(tool_call_dict)

                    # Add tool result to history (AC 10)
                    result_msg = ChatMessage(
                        role="tool",
                        content=tool_result,
                        tool_result_id=tool_call_dict['id'],
                    )
                    self.history.add(result_msg)

                # Step 2f: Loop continues with tool results in history

            except Exception as e:
                logger.error(f"Error during turn processing: {e}")
                error_message = self._format_agent_error(e)
                self.history.add(ChatMessage(role="assistant", content=error_message))
                yield error_message
                yield COMPLETION_MARKER
                break

    async def _extract_tool_calls_from_chunks(self, chunks: list[Chunk]) -> list[dict]:
        """Extract tool calls from accumulated stream chunks.

        Args:
            chunks: List of chunks from the API stream

        Returns:
            List of tool_call dicts with id, name, and input keys
        """
        # Use the chat_client's method if available
        if hasattr(self.chat_client, 'extract_tool_calls'):
            return await self.chat_client.extract_tool_calls(chunks)

        # Fallback: implement extraction here
        import json

        tool_calls: list[dict] = []
        current_tool: dict[str, Any] | None = None
        accumulated_json: list[str] = []

        for chunk in chunks:
            # Check for ContentBlockStart with tool_use
            if hasattr(chunk, 'type') and chunk.type == "tool_use":
                current_tool = {
                    "id": getattr(chunk, 'id', ''),
                    "name": getattr(chunk, 'name', ''),
                    "input": {},
                }
                accumulated_json = []

            # Check for ContentBlockDelta with partial JSON
            elif hasattr(chunk, 'type') and chunk.type == "input_json_delta":
                if hasattr(chunk, 'partial_json') and chunk.partial_json:
                    accumulated_json.append(chunk.partial_json)

            # Check for ContentBlockStop
            elif hasattr(chunk, 'type') and chunk.type == "content_block_stop":
                if current_tool is not None and accumulated_json:
                    try:
                        json_str = "".join(accumulated_json)
                        current_tool["input"] = json.loads(json_str)
                    except json.JSONDecodeError:
                        current_tool["input"] = {"raw": "".join(accumulated_json)}
                    tool_calls.append(current_tool)
                    current_tool = None
                    accumulated_json = []

        # Alternative extraction path using ContentBlockStart type
        for chunk in chunks:
            if hasattr(chunk, 'type') and hasattr(chunk, 'index'):
                if chunk.type == "tool_use" and not any(
                    tc.get('id') == getattr(chunk, 'id', '') for tc in tool_calls
                ):
                    new_tool = {
                        "id": getattr(chunk, 'id', ''),
                        "name": getattr(chunk, 'name', ''),
                        "input": {},
                    }
                    # Find corresponding input_json_delta chunks
                    for c in chunks:
                        if (hasattr(c, 'index') and c.index == chunk.index and
                            hasattr(c, 'type') and c.type == "input_json_delta"):
                            if hasattr(c, 'partial_json') and c.partial_json:
                                try:
                                    current = new_tool["input"].get("_partial", "")
                                    current += c.partial_json
                                    new_tool["input"] = json.loads(current)
                                except json.JSONDecodeError:
                                    new_tool["input"] = {"_partial": current + c.partial_json}
                    if new_tool not in tool_calls:
                        tool_calls.append(new_tool)

        return tool_calls

    async def _execute_tool_call(self, tool_call: dict) -> str:
        """Execute a single tool call and return result.

        This handles:
        - Finding the tool by name
        - Executing with timeout
        - Catching and formatting errors

        Args:
            tool_call: Tool call dict with id, name, and input

        Returns:
            String result to send back to API

        Acceptance Criteria:
        - AC 5: Tool results formatted for API
        - AC 6: Tool errors caught and formatted
        - AC 7: Tool timeouts handled
        """
        tool_name = tool_call.get('name', '')
        tool = self.tool_registry.get(tool_name)

        if tool is None:
            available = ", ".join(sorted(self.tool_registry.tool_names)) or "none"
            return f"Tool '{tool_name}' not found. Available tools: {available}."

        try:
            # Execute with timeout (AC 7)
            result = await asyncio.wait_for(
                tool.execute(**tool_call.get('input', {})),
                timeout=300,  # 5 minutes
            )
            return str(result)

        except asyncio.TimeoutError:
            return (
                f"Tool '{tool_name}' timed out after 300 seconds. "
                "Try a smaller input or break the task into smaller steps."
            )
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return self._format_tool_error(tool_name, e)

    def __repr__(self) -> str:
        """Return string representation of AgentCore."""
        return f"AgentCore(config={self.config!r}, messages={self.history.message_count})"

    def _format_tool_error(self, tool_name: str, error: Exception) -> str:
        """Return a user-facing tool error message."""
        if isinstance(error, ToolInputError):
            return f"Tool '{tool_name}' received invalid input: {error}. Check the required fields and try again."
        if isinstance(error, PermissionError):
            return f"Tool '{tool_name}' failed due to permission denied: {error}. Check file permissions and retry."
        if isinstance(error, FileNotFoundError):
            return f"Tool '{tool_name}' could not find the requested file: {error}. Verify the path and retry."
        if isinstance(error, ToolError):
            return f"Tool '{tool_name}' failed: {error}"
        return f"Tool '{tool_name}' failed: {error}"

    def _format_agent_error(self, error: Exception) -> str:
        """Return a user-facing assistant error message."""
        if isinstance(error, AuthError):
            return f"Authentication error: {error.message} {error.help or ''}".strip()
        if isinstance(error, TimeoutError):
            return f"Request timed out. {error.help or 'Try again.'}".strip()
        if isinstance(error, NetworkError):
            return f"Network error: {error.message} {error.help or ''}".strip()
        if isinstance(error, ApiError):
            help_text = f" {error.help}" if error.help else ""
            return f"API error ({error.statusCode}): {error.message}.{help_text}".strip()
        if isinstance(error, ZaiError):
            help_text = f" {error.help}" if error.help else ""
            return f"{error.message}.{help_text}".strip()
        return f"Unexpected error: {error}"
