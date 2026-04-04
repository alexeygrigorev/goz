# Issue 15: Agent Core + Chat History

## Status
.todo

## Description
Implement the foundational AgentCore class and ChatHistory management for the interactive coding agent.

## User Scenarios

### Scenario 1: Initialize Agent
- Developer creates new `AgentCore` instance
- Passes in valid config object
- Agent initializes with empty chat history
- Agent initializes tool registry
- Agent initializes stream processor

### Scenario 2: Add Messages to History
- User sends first message: "Hello"
- System creates `ChatMessage` with role="user"
- Message is added to chat history
- History now contains 1 message

### Scenario 3: Retrieve History for API
- System needs to make API call
- Calls `chat_history.to_api_format()`
- Returns list of dicts in Anthropic format
- Compatible with existing chat API client

### Scenario 4: History Compression
- Chat history reaches 40 messages (80% of 50 max)
- System calls `chat_history.compress()`
- Old messages are summarized
- Summary is inserted as system message
- History is reduced to ~25 messages

## Acceptance Criteria

1. `AgentCore` class exists in `goz/agent/core.py`
2. AgentCore initializes with config, history, tool_registry, stream_processor
3. `ChatMessage` dataclass has: role, content, tool_calls, tool_result_id, timestamp
4. `ChatHistory` class has: messages list, max_messages, add(), to_api_format(), compress()
5. Role types include: "user", "assistant", "tool", "tool_call", "agent_activity"
6. to_api_format() returns valid Anthropic message format
7. compress() summarizes old messages when approaching max
8. All classes have type hints

## Technical Details

### File Structure
```
goz/agent/
├── __init__.py
├── core.py           # AgentCore
└── history.py        # ChatMessage, ChatHistory
```

### ChatMessage Schema
```python
@dataclass
class ChatMessage:
    role: Literal["user", "assistant", "tool", "tool_call", "agent_activity"]
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
```

### ChatHistory API
```python
class ChatHistory:
    def __init__(self, max_messages: int = 50) -> None
    def add(self, message: ChatMessage) -> None
    def to_api_format(self) -> list[dict]
    def compress(self) -> None
    def clear(self) -> None
    @property
    def message_count(self) -> int
```

### AgentCore API (Stub)
```python
class AgentCore:
    def __init__(self, config: Config) -> None
    # Full implementation in Issue 17
```

## Dependencies
- None (foundation issue)

## Related Issues
- Issue 16: Stream Processor + State Machine
- Issue 17: Chat API Client

## Log
