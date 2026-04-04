# Issue 16: Stream Processor + State Machine

## Status
.todo

## Description
Implement the StreamProcessor for handling API streaming responses and ChatStateMachine for managing conversation states.

## User Scenarios

### Scenario 1: Process Text Stream
- API starts streaming response
- StreamProcessor receives chunks
- Text chunks are accumulated
- Chunks are yielded to UI in real-time
- Final complete text is available for storage

### Scenario 2: Extract Tool Calls
- API response contains tool calls
- Tool call spans multiple chunks
- `content_block_start` chunk with tool_use type
- Multiple `content_block_delta` chunks with partial_json
- `content_block_stop` chunk
- Processor accumulates and parses complete tool call
- Returns ToolCall object with name, id, and arguments

### Scenario 3: State Transition - Thinking
- User submits message
- State transitions from IDLE to THINKING
- UI shows "Thinking..." indicator

### Scenario 4: State Transition - Planning Tools
- API returns tool_use block
- State transitions from THINKING to PLANNING_TOOLS
- UI shows "Planning actions..."

### Scenario 5: State Transition - Executing Tools
- Tool execution begins
- State transitions from PLANNING_TOOLS to EXECUTING_TOOLS
- UI shows tool being executed

### Scenario 6: State Transition - Responding
- Tool results sent to API
- API streams final response
- State transitions to RESPONDING
- UI shows response text

### Scenario 7: State Transition - Done
- Response complete, no more tools
- State transitions to IDLE
- UI shows ready for input

## Acceptance Criteria

### StreamProcessor
1. `StreamProcessor` class exists in `goz/agent/stream_processor.py`
2. `process_stream()` method takes async iterator of chunks
3. Returns `ProcessedStream` with: full_text, tool_calls, raw_chunks
4. `extract_tool_calls()` parses tool calls from chunks
5. Handles partial_json accumulation correctly
6. Handles multiple tool calls in one response
7. Yields text chunks for real-time UI updates

### ChatStateMachine
1. `ChatStateMachine` class exists in `goz/agent/state_machine.py`
2. `State` enum has: IDLE, THINKING, PLANNING_TOOLS, EXECUTING_TOOLS, RESPONDING
3. `current_state` property returns current state
4. `transition()` validates and executes state changes
5. Valid transitions match the state diagram
6. Invalid transitions raise `StateTransitionError`
7. State change events can be subscribed to

### Data Structures
8. `ToolCall` dataclass: id, name, arguments
9. `ProcessedStream` dataclass: full_text, tool_calls, raw_chunks
10. `StateTransitionError` exception class

## Technical Details

### File Structure
```
goz/agent/
├── stream_processor.py
└── state_machine.py
```

### StreamProcessor API
```python
class StreamProcessor:
    def __init__(self, config: Config) -> None

    async def process_stream(
        self,
        stream: AsyncIterator[Chunk],
    ) -> AsyncIterator[str]:  # Yields text chunks for UI
        """Process stream and yield text chunks.

        After stream completes, use get_result() to get tool calls.
        """

    def get_result(self) -> ProcessedStream:
        """Get the final processed result."""

    def extract_tool_calls(self, chunks: list[Chunk]) -> list[ToolCall]:
        """Parse tool calls from accumulated chunks."""
```

### State Machine API
```python
class ChatStateMachine:
    class State(Enum):
        IDLE = "idle"
        THINKING = "thinking"
        PLANNING_TOOLS = "planning_tools"
        EXECUTING_TOOLS = "executing_tools"
        RESPONDING = "responding"

    @property
    def current_state(self) -> State

    def transition(self, to_state: State) -> bool:
        """Transition to new state. Raises if invalid."""

    def can_transition(self, from_state: State, to_state: State) -> bool:
        """Check if transition is valid."""

    # Valid transitions:
    # IDLE → THINKING
    # THINKING → PLANNING_TOOLS
    # THINKING → RESPONDING (no tools)
    # PLANNING_TOOLS → EXECUTING_TOOLS
    # EXECUTING_TOOLS → THINKING (more API calls needed)
    # EXECUTING_TOOLS → RESPONDING (final response)
    # RESPONDING → IDLE
```

### Chunk Types (from Anthropic SDK)
```python
# These are the types we need to handle:
# - content_block_start: {"type": "text" | "tool_use"}
# - content_block_delta: {"type": "text_delta", "text": "..."}
#                         or {"type": "input_json_delta", "partial_json": "..."}
# - content_block_stop
# - message_stop
```

## Dependencies
- Issue 15: Agent Core (needs ChatMessage, ChatHistory)

## Related Issues
- Issue 17: Chat API Client (uses StreamProcessor)

## Log
