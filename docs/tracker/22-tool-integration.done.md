# Issue 22: Tool Integration

## Status
.done

## Description
Integrate all tools with AgentCore, implementing the tool execution loop.

## User Scenarios

### Scenario 1: Single Tool Call
- User asks: "Read main.py"
- Agent processes turn
- API returns single tool_use: view_file
- Agent executes view_file tool
- Tool returns file content
- Agent sends result to API
- API streams final response
- User sees explanation

### Scenario 2: Multiple Tool Calls
- User asks: "Read both main.py and utils.py"
- Agent processes turn
- API returns two tool_use blocks
- Agent executes view_file(main.py)
- Agent executes view_file(utils.py)
- Agent sends both results to API
- API streams comparison
- User sees analysis

### Scenario 3: Tool Call Loop
- User asks: "Find all functions and add type hints"
- Agent processes turn
- API calls: view_file
- Result sent to API
- API calls: str_replace_editor (first function)
- Result sent to API
- API calls: str_replace_editor (second function)
- Result sent to API
- API streams completion
- User sees summary

### Scenario 4: Tool Error Handling
- User asks: "Read nonexistent.py"
- Agent processes turn
- API calls: view_file("nonexistent.py")
- Tool raises FileNotFoundError
- Agent formats error for API
- API explains to user

### Scenario 5: Tool Timeout
- User asks: "Run this long test"
- API calls: bash with long-running command
- Tool times out
- Agent reports timeout to API
- API suggests alternatives

## Acceptance Criteria

1. `AgentCore.process_turn()` implements full turn processing
2. Process turn: user input → API stream → tool calls → results → API → response
3. Tool execution is sequential (not parallel)
4. Multiple tool calls in one response work correctly
5. Tool results are formatted for API consumption
6. Tool errors are caught and formatted
7. Tool timeouts are handled
8. Streaming response yields text chunks for UI
9. Turn completes when API stops (no more tool calls)
10. Chat history is updated with all messages

## Technical Details

### File Structure
```
goz/agent/
└── core.py  # Enhance AgentCore with full process_turn implementation
```

### AgentCore.process_turn()
```python
class AgentCore:
    async def process_turn(
        self,
        user_input: str,
    ) -> AsyncIterator[str]:
        """Process a user turn and yield streaming response.

        Flow:
        1. Add user message to history
        2. Loop:
           a. Call API with current history
           b. Stream response to UI (yield text chunks)
           c. Check for tool calls
           d. If no tool calls, break
           e. Execute tools sequentially
           f. Add tool calls and results to history
        3. Add assistant message to history
        4. Yield completion marker

        Yields:
            Text chunks for real-time UI display
        """
```

### Turn Processing Algorithm
```python
async def process_turn(self, user_input: str) -> AsyncIterator[str]:
    # 1. Add user message
    self.history.add(ChatMessage(role="user", content=user_input))

    # 2. Main loop
    max_iterations = 10  # Prevent infinite loops
    for iteration in range(max_iterations):
        # 2a. Call API
        messages = self.history.to_api_format()
        tools_schema = self.tools.to_openai_schema()

        stream = self.chat_client.chat_completion(
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
        )

        # 2b. Process stream
        accumulated_chunks = []
        async for chunk in stream:
            accumulated_chunks.append(chunk)
            # Yield text for UI
            if chunk.type == "content_block_delta" and chunk.delta_type == "text":
                yield chunk.text

        # 2c. Extract tool calls
        tool_calls = self.stream_processor.extract_tool_calls(accumulated_chunks)

        # 2d. Check for completion
        if not tool_calls:
            # No tools, turn is complete
            # Add assistant message to history
            assistant_text = extract_text_from_chunks(accumulated_chunks)
            self.history.add(ChatMessage(role="assistant", content=assistant_text))
            yield "\x00"  # Completion marker
            break

        # 2e. Execute tools
        for tool_call in tool_calls:
            # Add tool call to history
            self.history.add(ChatMessage(
                role="tool_call",
                content=f"Called {tool_call.name}",
                tool_calls=[tool_call],
            ))

            try:
                # Execute tool
                tool = self.tools.get(tool_call.name)
                if tool is None:
                    result = f"Tool not found: {tool_call.name}"
                else:
                    result = await tool.execute(**tool_call.arguments)

                # Add tool result to history
                self.history.add(ChatMessage(
                    role="tool",
                    content=result,
                    tool_result_id=tool_call.id,
                ))

            except Exception as e:
                # Handle tool errors
                error_msg = f"Tool {tool_call.name} failed: {e}"
                self.history.add(ChatMessage(
                    role="tool",
                    content=error_msg,
                    tool_result_id=tool_call.id,
                ))

        # 2f. Loop continues with tool results in history
```

### Message Flow Example
```python
# Initial state
history = [
    ChatMessage(role="user", content="Read main.py"),
]

# After API call (with tool request)
history = [
    ChatMessage(role="user", content="Read main.py"),
    ChatMessage(
        role="tool_call",
        content="Called view_file",
        tool_calls=[ToolCall(id="call_1", name="view_file", arguments={...})],
    ),
]

# After tool execution
history = [
    ChatMessage(role="user", content="Read main.py"),
    ChatMessage(
        role="tool_call",
        content="Called view_file",
        tool_calls=[ToolCall(id="call_1", name="view_file", arguments={...})],
    ),
    ChatMessage(
        role="tool",
        content="<file content>",
        tool_result_id="call_1",
    ),
]

# After final API call
history = [
    ChatMessage(role="user", content="Read main.py"),
    ChatMessage(
        role="tool_call",
        content="Called view_file",
        tool_calls=[ToolCall(id="call_1", name="view_file", arguments={...})],
    ),
    ChatMessage(
        role="tool",
        content="<file content>",
        tool_result_id="call_1",
    ),
    ChatMessage(
        role="assistant",
        content="This file contains...",
    ),
]
```

### Tool Call Execution
```python
async def execute_tool_call(self, tool_call: ToolCall) -> str:
    """Execute a single tool call and return result."""
    tool = self.tools.get(tool_call.name)

    if tool is None:
        raise ToolNotFoundError(f"Unknown tool: {tool_call.name}")

    # Update state machine
    self.state_machine.transition(State.EXECUTING_TOOLS)

    try:
        # Execute with timeout
        result = await asyncio.wait_for(
            tool.execute(**tool_call.arguments),
            timeout=300,  # 5 minutes
        )
        return result

    except asyncio.TimeoutError:
        raise ToolExecutionError(f"Tool {tool_call.name} timed out")

    except ToolError:
        # Re-raise tool errors
        raise

    except Exception as e:
        # Wrap unexpected errors
        raise ToolExecutionError(f"Tool {tool_call.name} failed: {e}")
```

### Completion Marker
```python
# Special character to signal completion to UI
COMPLETION_MARKER = "\x00"

# UI checks for this
async def display_stream(agent: AgentCore, user_input: str):
    buffer = []
    async for chunk in agent.process_turn(user_input):
        if chunk == COMPLETION_MARKER:
            break
        buffer.append(chunk)
        update_ui(chunk)

    # Turn complete
    show_ready_state()
```

## Dependencies
- Issue 17: Chat API Client
- Issue 18: Tool Base + Registry
- Issue 19: File Tools
- Issue 20: Bash Tool
- Issue 21: API Tools

## Related Issues
- Issue 23: Agent App + Chat Screen

## Log

### 2025-03-19: Implementation Complete (TDD)

**Tests Written FIRST:**
- Created `tests/test_agent_integration.py` with 14 comprehensive tests
- All tests initially failed (expected per TDD)

**Implementation:**
- Enhanced `AgentCore.process_turn()` with full turn processing
- Implemented tool-API loop with max_iterations guard
- Added sequential tool execution
- Implemented tool error catching and formatting
- Added tool timeout handling (300s default)
- Text chunks yielded for real-time UI
- Completion marker (`\x00`) signals turn end
- Chat history updated with all messages

**Tests PASS:**
- All 14 integration tests pass
- All 15 existing agent_core tests pass
- Total: 91 agent-related tests pass

**Files Modified:**
- `goz/agent/core.py` - Enhanced AgentCore with process_turn implementation
- `tests/test_agent_integration.py` - New comprehensive integration tests

**Acceptance Criteria Met:**
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
