# Issue 17: Chat API Client

## Status
.todo

## Description
Implement the ChatClient for Anthropic-style chat completions with tool calling support, using the existing Anthropic SDK.

## User Scenarios

### Scenario 1: Simple Chat Request
- User sends: "Hello, what can you do?"
- ChatClient sends to API with no tools
- API streams response
- Client yields text chunks
- Response: "I can help you read, write, and analyze code..."

### Scenario 2: Chat with Tools
- User sends: "Read main.py and explain it"
- ChatClient includes view_file tool in request
- API requests tool call: view_file(main.py)
- Client receives tool_use block
- Tool execution happens separately
- Client sends tool result back
- API streams final response

### Scenario 3: Streaming Response
- User sends: "Tell me a story"
- API streams word-by-word
- Client yields each chunk immediately
- UI updates in real-time
- User sees text appear progressively

### Scenario 4: Multiple Tool Calls
- User sends: "Check both main.py and utils.py"
- API returns two tool_use blocks
- Client extracts both tool calls
- Tools execute sequentially
- Both results sent back to API
- Final response compares both files

## Acceptance Criteria

1. `ChatClient` class exists in `goz/agent/chat_client.py`
2. Uses existing Anthropic SDK (same as Vision API)
3. Uses config.zai_token and config.zai_base_url
4. `chat_completion()` method sends messages and returns async iterator
5. Supports `tools` parameter for function calling
6. Supports `tool_choice` parameter ("auto", "any", or specific tool)
7. Supports `stream` parameter (True/False)
8. Response chunks yield text deltas
9. Tool calls are properly formatted in stream
10. Errors are raised as appropriate exceptions (AuthError, ApiError, etc.)
11. Timeout is configurable via config

## Technical Details

### File Structure
```
goz/agent/
└── chat_client.py
```

### ChatClient API
```python
class ChatClient:
    def __init__(self, config: Config) -> None:
        """Initialize with existing Anthropic SDK client."""

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "any"] = "auto",
        stream: bool = True,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Chunk]:
        """Stream chat completion.

        Args:
            messages: Chat history in Anthropic format
            tools: Tool definitions in OpenAI format
            tool_choice: How to select tools
            stream: Whether to stream response
            temperature: Generation temperature
            max_tokens: Max tokens in response

        Yields:
            Chunk objects from API response

        Raises:
            AuthError: For 401/403 responses
            ApiError: For other API errors
            NetworkError: For connection failures
        """
```

### Request Format
```python
# Anthropic/OpenAI compatible format
request = {
    "model": "glm-5-turbo",  # or config.chat_model
    "messages": [
        {"role": "user", "content": "Read main.py"},
    ],
    "tools": [
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
    ],
    "tool_choice": "auto",
    "temperature": 0.7,
    "max_tokens": 32768,
    "stream": True,
}
```

### Chunk Types We Handle
```python
@dataclass
class ContentBlockStart:
    type: Literal["text", "tool_use"]
    index: int
    id: str | None = None  # For tool_use
    name: str | None = None  # For tool_use

@dataclass
class ContentBlockDelta:
    type: Literal["text_delta", "input_json_delta"]
    index: int
    text: str | None = None  # For text_delta
    partial_json: str | None = None  # For input_json_delta

@dataclass
class ContentBlockStop:
    index: int

@dataclass
class MessageStart:
    id: str
    model: str

@dataclass
class MessageStop:
    stop_reason: Literal["end_turn", "max_tokens", "tool_use"]
```

### Reuse Existing Infrastructure
```python
# Use existing error classes from goz/api/errors.py
from goz.api.errors import AuthError, ApiError, NetworkError, TimeoutError

# Use existing config from goz/config
from goz.config import Config

# Use Anthropic SDK (already a dependency)
from anthropic import AsyncAnthropic
```

## Dependencies
- Issue 15: Agent Core (for data structures)
- Issue 16: Stream Processor (consumer of this client)

## Related Issues
- Existing Vision API (similar pattern to follow)

## Log

### 2025-03-19 - Implementation Complete
- Implemented ChatClient class in goz/agent/chat_client.py
- Uses AsyncAnthropic from existing SDK (same as Vision API)
- Supports tools, tool_choice, stream, temperature, and max_tokens parameters
- Converts Anthropic SSE events to our Chunk data classes
- Error handling for AuthError, ApiError, NetworkError, TimeoutError
- All 16 tests passing
- TDD process followed:
  1. Wrote tests first (tests/test_chat_client.py)
  2. Verified tests FAIL
  3. Implemented code (goz/agent/chat_client.py)
  4. Verified tests PASS (16/16 passing)
