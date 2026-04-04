# goz Interactive Coding Agent Specification

**Goal**: Transform goz from a menu-based TUI into an interactive AI coding agent.

## Executive Summary

When `goz` is run with no arguments, it launches an interactive coding agent that:
1. Accepts natural language requests
2. Reads/writes files using built-in tools
3. Executes shell commands
4. Maintains conversation context
5. Supports session persistence

**Reference Implementation**: `zai-glm-cli` (TypeScript/Node.js) → Port to Python/Textual

---

## Part 1: User Experience

### 1.1 First Launch

```
$ goz
```

The user sees:

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - Interactive Coding Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Welcome to goz! I'm your AI coding assistant.                       │
│                                                                      │
│  I can help you:                                                    │
│  • Read and analyze code                                            │
│  • Create and modify files                                          │
│  • Run terminal commands                                            │
│  • Search the web for information                                   │
│  • Debug and fix issues                                             │
│                                                                      │
│  Type your request below and press Enter.                           │
│                                                                      │
│                                                                      │
│ > │                                                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Conversation Flow

**User types**: `Read the main.py file and explain what it does`

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - Interactive Coding Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  You: Read the main.py file and explain what it does                │
│                                                                      │
│  Agent: [Thinking...]                                               │
│                                                                      │
│  [Tool: view_file]                                                  │
│  Reading: main.py                                                   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ def main():                                                │    │
│  │     app = GozApp()                                         │    │
│  │     app.run()                                              │    │
│  │                                                            │    │
│  │ if __name__ == "__main__":                                 │    │
│  │     main()                                                 │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  This is the entry point for the goz TUI application. It            │
│  creates a GozApp instance and runs it.                             │
│                                                                      │
│ >                                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 File Operations

**User types**: `Create a new file called utils.py with a function to calculate fibonacci`

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - Interactive Coding Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  You: Create a new file called utils.py...                          │
│                                                                      │
│  Agent: [Thinking...]                                               │
│                                                                      │
│  [Tool: create_file]                                                │
│  Creating: utils.py                                                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ def fibonacci(n: int) -> int:                              │    │
│  │     """Calculate the nth Fibonacci number."""               │    │
│  │     if n <= 1:                                              │    │
│  │         return n                                            │    │
│  │     return fibonacci(n - 1) + fibonacci(n - 2)              │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Created utils.py with fibonacci function.                          │
│                                                                      │
│ >                                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 Edit Operations

**User types**: `Replace the fibonacci function with an iterative version`

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - Interactive Coding Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  You: Replace the fibonacci function...                              │
│                                                                      │
│  Agent: [Thinking...]                                               │
│                                                                      │
│  [Tool: str_replace_editor]                                         │
│  Editing: utils.py                                                   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ - def fibonacci(n: int) -> int:                            │    │
│  │ -     """Calculate the nth Fibonacci number."""             │    │
│  │ -     if n <= 1:                                            │    │
│  │ -         return n                                          │    │
│  │ -     return fibonacci(n - 1) + fibonacci(n - 2)            │    │
│  │ + def fibonacci(n: int) -> int:                            │    │
│  │ +     """Calculate the nth Fibonacci number iteratively.""" │    │
│  │ +     if n <= 1:                                            │    │
│  │ +         return n                                          │    │
│  │ +     a, b = 0, 1                                           │    │
│  │ +     for _ in range(2, n + 1):                            │    │
│  │ +         a, b = b, a + b                                   │    │
│  │ +     return b                                              │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  Replaced fibonacci with iterative version.                         │
│                                                                      │
│ >                                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.5 Command Execution

**User types**: `Run the tests and show me the results`

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - Interactive Coding Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  You: Run the tests and show me the results                          │
│                                                                      │
│  Agent: [Thinking...]                                               │
│                                                                      │
│  [Tool: bash]                                                        │
│  Running: uv run pytest tests/ -v                                   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ $ uv run pytest tests/ -v                                  │    │
│  │ tests/test_utils.py::test_fibonacci PASSED               [10%]│    │
│  │ tests/test_utils.py::test_fibonacci_zero PASSED          [20%]│    │
│  │ tests/test_utils.py::test_fibonacci_negative PASSED       [30%]│    │
│  │                                                              │    │
│  │ 3 passed in 0.5s                                            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  All 3 tests passed!                                                │
│                                                                      │
│ >                                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.6 Special Agents

**User types**: `/review`

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - [Code Reviewer] Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Switched to Code Reviewer agent.                                   │
│  I'll review your code for quality, style, and best practices.      │
│                                                                      │
│  You: review utils.py                                                │
│                                                                      │
│  Agent: Let me review utils.py...                                   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Code Review: utils.py                                      │    │
│  │                                                            │    │
│  │ ✅ Type hints are present                                  │    │
│  │ ✅ Docstring included                                      │    │
│  │ ✅ Handles edge cases (n <= 1)                             │    │
│  │ ⚠️  Consider adding input validation for negative numbers  │    │
│  │ ⚠️  Consider caching for repeated calls                    │    │
│  │                                                            │    │
│  │ Overall: Good implementation!                             │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│ >                                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.7 Session Persistence

**User types**: `/save my-session`

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - Interactive Coding Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Session saved to: ~/.goz/sessions/my-session.json                  │
│  Working directory: /Users/alexe/git/z                               │
│  Messages: 12                                                        │
│  Model: glm-5-turbo                                                  │
│                                                                      │
│ >                                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**User runs**: `goz --load my-session`

```
┌─────────────────────────────────────────────────────────────────────┐
│ goz - Interactive Coding Agent                         [?] Help [q] Quit │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Session loaded: my-session                                         │
│  Restored 12 messages from /Users/alexe/git/z                       │
│                                                                      │
│  Last request was: "Run the tests and show me the results"          │
│  Last response was: "All 3 tests passed!"                           │
│                                                                      │
│ >                                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Technical Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          goz Architecture                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐    │
│  │   Textual   │◄───│ Chat Screen  │◄───│  Stream Processor   │    │
│  │     TUI     │    │              │    │                     │    │
│  └─────────────┘    └──────────────┘    └──────────┬──────────┘    │
│         ▲                    ▲                       │              │
│         │                    │                       ▼              │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌───────────────────┐     │
│  │ User Input   │    │ Chat History │    │   Agent Core       │     │
│  │ Handler      │    │ Manager      │    │                   │     │
│  └──────────────┘    └──────────────┘    └─────────┬─────────┘     │
│                                               │                     │
│                                               ▼                     │
│         ┌─────────────────────────────────────────────────┐        │
│         │              Tool Registry                      │        │
│         ├────────────┬────────────┬──────────┬──────────┤        │
│         │ view_file  │create_file│   bash   │  search  │        │
│         │str_replace │   read     │   repo   │  ...     │        │
│         └────────────┴────────────┴──────────┴──────────┘        │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    API Clients                              │   │
│  │  Anthropic (Chat) │ Search │ Read │ Repo │ Vision          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### 2.2.1 Agent Core (`goz/agent/core.py`)

```python
class AgentCore:
    """Main agent orchestrator."""

    def __init__(self, config: Config):
        self.config = config
        self.chat_history: list[ChatMessage] = []
        self.tool_registry = ToolRegistry()
        self.stream_processor = StreamProcessor(config)
        self.state_machine = ChatStateMachine()

    async def process_turn(self, user_input: str) -> AsyncIterator[str]:
        """Process a user turn and yield streaming response."""
        # 1. Add user message to history
        # 2. Call API with streaming
        # 3. Process tool calls
        # 4. Yield response chunks

    async def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool and return result."""
```

#### 2.2.2 Stream Processor (`goz/agent/stream_processor.py`)

```python
class StreamProcessor:
    """Processes streaming API responses."""

    async def process_stream(
        self,
        stream: AsyncIterator[Chunk],
    ) -> ProcessedStream:
        """Process entire stream before yielding to UI.

        This implements the "sequential streaming" pattern from zai-cli:
        - Collect all delta chunks
        - Extract tool calls
        - Return structured result
        """

    def extract_tool_calls(
        self,
        chunks: list[Chunk],
    ) -> list[ToolCall]:
        """Parse tool calls from accumulated chunks."""
```

#### 2.2.3 Chat State Machine (`goz/agent/state_machine.py`)

```python
class ChatStateMachine:
    """Manages chat conversation states."""

    class State(Enum):
        IDLE = "idle"
        THINKING = "thinking"
        PLANNING_TOOLS = "planning_tools"
        EXECUTING_TOOLS = "executing_tools"
        RESPONDING = "responding"

    def transition(self, from_state: State, to_state: State) -> bool:
        """Validate and execute state transition."""
```

#### 2.2.4 Tool System (`goz/agent/tools/`)

```python
# Base tool interface
class Tool(Protocol):
    name: str
    description: str
    input_schema: dict

    async def execute(self, **kwargs) -> str:
        """Execute the tool and return result."""

# Built-in tools
class ViewFileTool(Tool):
    name = "view_file"
    description = "View a file's contents with line numbers"

class CreateFileTool(Tool):
    name = "create_file"
    description = "Create a new file with content"

class StrReplaceEditorTool(Tool):
    name = "str_replace_editor"
    description = "Replace text in a file (string replacement with fuzzy matching)"

class BashTool(Tool):
    name = "bash"
    description = "Execute shell commands"

class SearchTool(Tool):
    name = "search"
    description = "Search the web for information"
```

#### 2.2.5 Tool Registry (`goz/agent/tools/registry.py`)

```python
class ToolRegistry:
    """Registry for available tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._register_builtin_tools()

    def register(self, tool: Tool) -> None:
        """Register a new tool."""

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""

    def list_all(self) -> list[Tool]:
        """List all registered tools."""

    def to_openai_schema(self) -> list[dict]:
        """Convert to OpenAI function-calling format."""
```

#### 2.2.6 Chat History (`goz/agent/history.py`)

```python
@dataclass
class ChatMessage:
    role: Literal["user", "assistant", "tool", "tool_call", "agent_activity"]
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

class ChatHistory:
    """Manages conversation history."""

    def __init__(self, max_messages: int = 50):
        self.messages: list[ChatMessage] = []
        self.max_messages = max_messages

    def add(self, message: ChatMessage) -> None:
        """Add a message to history."""

    def to_api_format(self) -> list[dict]:
        """Convert to API request format."""

    def compress(self) -> None:
        """Compress history when approaching token limit."""
```

#### 2.2.7 Session Manager (`goz/agent/sessions.py`)

```python
@dataclass
class Session:
    id: str
    created_at: datetime
    working_directory: str
    messages: list[ChatMessage]
    model: str

class SessionManager:
    """Manages session persistence."""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir

    async def save(self, session: Session) -> Path:
        """Save session to file."""

    async def load(self, session_id: str) -> Session:
        """Load session from file."""

    def list_sessions(self) -> list[SessionInfo]:
        """List all saved sessions."""
```

#### 2.2.8 Specialized Agents (`goz/agent/specialized.py`)

```python
class AgentType(Enum):
    GENERAL_PURPOSE = "general"
    CODE_REVIEWER = "reviewer"
    TEST_WRITER = "test_writer"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    SECURITY_AUDIT = "security"
    PERFORMANCE = "performance"
    EXPLORE = "explore"
    PLAN = "plan"

@dataclass
class AgentConfig:
    type: AgentType
    name: str
    system_prompt: str
    temperature: float = 0.7

# Agent type configurations
AGENT_CONFIGS: dict[AgentType, AgentConfig] = {
    AgentType.CODE_REVIEWER: AgentConfig(
        type=AgentType.CODE_REVIEWER,
        name="Code Reviewer",
        system_prompt="You are a code reviewer. Analyze code for quality...",
    ),
    # ... other agents
}
```

### 2.3 API Integration

#### 2.3.1 Chat API Client (`goz/agent/chat_client.py`)

```python
class ChatClient:
    """Client for chat completions with tool calling."""

    def __init__(self, config: Config):
        self.config = config
        # Use Anthropic SDK (same as Vision)
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(
            api_key=config.zai_token,
            base_url=config.zai_base_url,
        )

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: Literal["auto", "any"] = "auto",
        stream: bool = True,
    ) -> AsyncIterator[Chunk]:
        """Stream chat completion with tool calling support."""
```

#### 2.3.2 Request Format

```python
# API request structure
request = {
    "model": "glm-5-turbo",  # or config.chat_model
    "messages": [
        {"role": "user", "content": "Read main.py and explain it"},
    ],
    "tools": [
        {
            "name": "view_file",
            "description": "View a file's contents",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "line_range": {"type": "array"},
                },
                "required": ["file_path"],
            },
        },
        # ... other tools
    ],
    "tool_choice": "auto",
    "temperature": 0.7,
    "max_tokens": 32768,
}
```

#### 2.3.3 Response Format (Streaming)

```python
# SSE streaming response chunks
# Each chunk is a Server-Sent Event

# Text delta chunk
event: content_block_delta
data: {"delta": {"type": "text", "text": "This is the file..."}}

# Tool use start
event: content_block_start
data: {"content_block": {"type": "tool_use", "id": "call_123", "name": "view_file"}}

# Tool use input delta
event: content_block_delta
data: {"delta": {"type": "input_json_delta", "partial_json": '{"file_path": "main.py"'}}

# Tool use stop
event: content_block_stop
data: {}

# Message stop
event: message_stop
data: {}
```

### 2.4 Textual TUI Components

#### 2.4.1 Chat Screen (`goz/agent/tui/screens/chat.py`)

```python
class ChatScreen(Screen):
    """Main chat interface."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield ChatHistoryViewer(id="history")
        yield ChatInput(placeholder="Type your request...", id="input")
        yield Footer()

    async def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value
        # Send to agent, stream response
        async for chunk in self.agent.process_turn(user_input):
            self.update_display(chunk)

class ChatHistoryViewer(Widget):
    """Widget for displaying chat history."""

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the display."""

    def add_tool_call(self, tool_name: str, args: dict) -> None:
        """Show tool invocation."""

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Show tool result."""
```

#### 2.4.2 Markdown Renderer (`goz/agent/tui/widgets/markdown.py`)

```python
class MarkdownViewer(Widget):
    """Render markdown content with syntax highlighting."""

    def render_markdown(self, content: str) -> RichRenderable:
        """Convert markdown to Rich renderable."""
        # Use rich.markdown.Markdown
        # Add syntax highlighting for code blocks
```

#### 2.4.3 Diff Viewer (`goz/agent/tui/widgets/diff.py`)

```python
class DiffViewer(Widget):
    """Display file changes as a diff."""

    def show_diff(self, old: str, new: str) -> None:
        """Show unified diff between two strings."""
        # Use difflib.unified_diff
        # Colorize additions (green) and deletions (red)
```

### 2.5 File Structure

```
goz/
├── goz/
│   ├── __init__.py
│   ├── __main__.py           # Entry: detect agent mode vs CLI
│   ├── config/               # Existing
│   ├── api/                  # Existing (Vision, Search, Read, Repo)
│   ├── cli/                  # Existing CLI commands
│   ├── tui/                  # Existing menu-based TUI
│   ├── agent/                # NEW: Interactive agent module
│   │   ├── __init__.py
│   │   ├── core.py           # AgentCore orchestrator
│   │   ├── stream_processor.py
│   │   ├── state_machine.py
│   │   ├── history.py        # ChatMessage, ChatHistory
│   │   ├── sessions.py       # Session persistence
│   │   ├── specialized.py    # Agent types and configs
│   │   ├── chat_client.py    # Chat API client
│   │   ├── tools/            # Tool implementations
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # Tool protocol
│   │   │   ├── registry.py   # ToolRegistry
│   │   │   ├── file_tools.py # view_file, create_file, str_replace
│   │   │   ├── bash_tool.py  # bash command execution
│   │   │   ├── search_tool.py # web search
│   │   │   ├── read_tool.py  # web reader
│   │   │   ├── repo_tool.py  # repo operations
│   │   │   └── todo_tool.py  # todo list management
│   │   └── tui/              # Agent-specific TUI components
│   │       ├── __init__.py
│   │       ├── app.py        # AgentApp (main)
│   │       └── screens/
│   │       │   ├── __init__.py
│   │       │   ├── chat.py   # Main chat interface
│   │       │   ├── session.py # Session management
│   │       │   └── agents.py # Agent selection
│   └── agent/
│       └── widgets/
│           ├── __init__.py
│           ├── markdown.py   # Markdown rendering
│           ├── diff.py       # Diff viewer
│           └── thinking.py   # Thinking indicator
├── tests/
│   ├── test_agent_*.py       # Agent tests
│   ├── test_tools_*.py       # Tool tests
│   └── test_e2e_agent*.py    # E2E agent tests
└── docs/
    ├── agent-spec.md         # This file
    └── tracker/
        └── 15-*.md           # Agent implementation issues
```

---

## Part 3: Implementation Phases

### Phase 1: Foundation (Issues 15-17)

| Issue | Description | Deliverables |
|-------|-------------|--------------|
| 15 | Agent Core + Chat History | `agent/core.py`, `agent/history.py` |
| 16 | Stream Processor + State Machine | `agent/stream_processor.py`, `agent/state_machine.py` |
| 17 | Chat API Client | `agent/chat_client.py` |

**Acceptance Criteria**:
- Can create AgentCore instance
- Can add/retrieve messages from history
- Can convert history to API format
- Can process streaming API response
- Can extract tool calls from stream
- State transitions work correctly

### Phase 2: Tool System (Issues 18-22)

| Issue | Description | Deliverables |
|-------|-------------|--------------|
| 18 | Tool Base + Registry | `agent/tools/base.py`, `agent/tools/registry.py` |
| 19 | File Tools | `agent/tools/file_tools.py` (view, create, str_replace) |
| 20 | Bash Tool | `agent/tools/bash_tool.py` |
| 21 | Search/Read/Repo Tools | `agent/tools/search_tool.py`, etc. |
| 22 | Tool Integration | Tools integrated with AgentCore |

**Acceptance Criteria**:
- Tool interface defined
- Registry can register/list/get tools
- Registry exports OpenAI function schema
- All file tools work correctly
- Bash tool executes commands safely
- API tools integrate with existing clients
- Agent can execute tools and get results

### Phase 3: TUI Integration (Issues 23-26)

| Issue | Description | Deliverables |
|-------|-------------|--------------|
| 23 | Agent App + Chat Screen | `agent/tui/app.py`, `agent/tui/screens/chat.py` |
| 24 | Markdown + Diff Widgets | `agent/tui/widgets/markdown.py`, `agent/tui/widgets/diff.py` |
| 25 | Thinking Indicator | `agent/tui/widgets/thinking.py` |
| 26 | TUI-Agent Integration | Full chat flow working |

**Acceptance Criteria**:
- Can launch agent mode with `goz`
- Chat input works
- History displays correctly
- Streaming response renders word-by-word
- Tool calls are shown visually
- Markdown renders with syntax highlighting
- Diffs show additions/deletions
- Thinking state displays

### Phase 4: Session Management (Issues 27-28)

| Issue | Description | Deliverables |
|-------|-------------|--------------|
| 27 | Session Save/Load | `agent/sessions.py` |
| 28 | Session Commands | `/save`, `/load`, `/list`, `/delete` commands |

**Acceptance Criteria**:
- Can save session to file
- Can load session from file
- Can list all sessions
- Can delete session
- Session includes all messages
- Session includes working directory
- Session includes model used

### Phase 5: Specialized Agents (Issues 29-30)

| Issue | Description | Deliverables |
|-------|-------------|--------------|
| 29 | Agent Type System | `agent/specialized.py` |
| 30 | Agent Switching | `/review`, `/test`, etc. commands |

**Acceptance Criteria**:
- All 10 agent types defined
- Each has unique system prompt
- Can switch between agents
- Agent type shows in header
- Session tracks current agent

### Phase 6: Polish & CLI Integration (Issues 31-32)

| Issue | Description | Deliverables |
|-------|-------------|--------------|
| 31 | CLI Flags for Agent Mode | `--load`, `--agent`, `--session` flags |
| 32 | Error Handling + Edge Cases | Comprehensive error handling |

**Acceptance Criteria**:
- `goz --load session` works
- `goz --agent reviewer` works
- Network errors handled gracefully
- Tool errors shown to user
- Can recover from failures
- Help text updated

---

## Part 4: Tool Specifications

### 4.1 view_file

```python
{
    "name": "view_file",
    "description": "View a file's contents. Use this to read existing files. "
                   "Supports optional line range for large files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to view"
            },
            "line_range": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Optional [start, end] line range (1-indexed, inclusive)"
            }
        },
        "required": ["file_path"]
    }
}
```

### 4.2 create_file

```python
{
    "name": "create_file",
    "description": "Create a new file with content. "
                   "If the file exists, this will fail - use str_replace_editor instead.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path for the new file"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["file_path", "content"]
    }
}
```

### 4.3 str_replace_editor

```python
{
    "name": "str_replace_editor",
    "description": "Replace text in an existing file using fuzzy matching. "
                   "Best for making targeted edits to existing code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit"
            },
            "old_text": {
                "type": "string",
                "description": "Text to replace (must be unique in file)"
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text"
            }
        },
        "required": ["file_path", "old_text", "new_text"]
    }
}
```

### 4.4 bash

```python
{
    "name": "bash",
    "description": "Execute shell commands. Use for running tests, building, "
                   "git operations, and other terminal tasks.",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory (default: current directory)"
            }
        },
        "required": ["command"]
    }
}
```

### 4.5 search (Web Search)

```python
{
    "name": "search",
    "description": "Search the web for current information. "
                   "Use for finding docs, examples, troubleshooting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "count": {
                "type": "integer",
                "description": "Number of results (default: 10)"
            },
            "domain": {
                "type": "string",
                "description": "Filter to specific domain (optional)"
            }
        },
        "required": ["query"]
    }
}
```

### 4.6 read (Web Reader)

```python
{
    "name": "read",
    "description": "Fetch and convert a web page to readable markdown. "
                   "Use for reading documentation, articles, blog posts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch and parse"
            }
        },
        "required": ["url"]
    }
}
```

---

## Part 5: API Protocol Details

### 5.1 Sequential Streaming Pattern

From zai-cli, the key insight is **sequential streaming**:

1. **Process entire stream first** - Collect all chunks
2. **Extract tool calls** - Parse complete tool_call objects
3. **Execute tools** - Run tools sequentially
4. **Make follow-up call** - Send tool results back
5. **Repeat** - Until no more tool calls

This prevents "deconstructed" responses where content streams while tools execute.

```python
# Pseudocode
async def process_turn(user_input):
    messages = history.to_api_format() + [{"role": "user", "content": user_input}]

    while True:
        # 1. Stream API response
        chunks = []
        tool_calls = []
        async for chunk in api.chat_completion(messages, tools=tools):
            chunks.append(chunk)
            # Yield text delta to UI for real-time display
            if chunk.type == "content_block_delta":
                yield chunk.delta.text

        # 2. Extract tool calls from accumulated chunks
        tool_calls = extract_tool_calls(chunks)

        # 3. If no tool calls, we're done
        if not tool_calls:
            break

        # 4. Execute tools
        for tool_call in tool_calls:
            result = await execute_tool(tool_call)
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [tool_call],
            })
            messages.append({
                "role": "user",
                "tool_result_id": tool_call.id,
                "content": result,
            })

        # 5. Loop - make another API call with tool results
```

### 5.2 SSE Event Types

| Event | Description |
|-------|-------------|
| `message_start` | Start of message |
| `content_block_start` | Start of content block (text or tool_use) |
| `content_block_delta` | Delta for content block |
| `content_block_stop` | End of content block |
| `message_stop` | End of message |

### 5.3 Tool Call Accumulation

Tool calls span multiple delta chunks:

```
content_block_start: {"type": "tool_use", "id": "call_123", "name": "view_file"}
content_block_delta: {"partial_json": '{"file_path": "main.py"'}
content_block_delta: {"partial_json": ',"line_range": [1, 10]'}
content_block_delta: {"partial_json": '}'}
content_block_stop
```

Need to accumulate `partial_json` chunks and parse the final JSON.

---

## Part 6: Configuration Updates

### 6.1 New Config Fields

```python
class Config(BaseModel):
    # Existing fields...
    zai_token: str
    zai_base_url: str
    coding_base_url: str
    timeout: int
    vision_model: str
    chat_model: str

    # NEW: Agent-specific config
    agent_temperature: float = 0.7
    agent_max_tokens: int = 32768
    agent_max_history: int = 50  # Max messages before compression
    session_dir: Path = Field(default_factory=lambda: Path.home() / ".goz" / "sessions")
    default_agent: AgentType = AgentType.GENERAL_PURPOSE
```

### 6.2 Session Directory

```
~/.goz/
├── config.json           # Main config (existing)
└── sessions/
    ├── default.json      # Default auto-saved session
    ├── my-session.json   # User-saved sessions
    └── ...
```

---

## Part 7: Commands Reference

### 7.1 Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/quit`, `/q` | Quit agent |
| `/clear` | Clear conversation history |
| `/save [name]` | Save session |
| `/load <name>` | Load session |
| `/sessions`, `/ls` | List sessions |
| `/delete <name>` | Delete session |
| `/agent <type>` | Switch agent type |
| `/temperature <n>` | Set temperature |
| `/model <name>` | Set model |

### 7.2 Agent Type Commands

| Command | Agent Type |
|---------|------------|
| `/review` | Code Reviewer |
| `/test` | Test Writer |
| `/docs` | Documentation |
| `/refactor` | Refactoring |
| `/debug` | Debugging |
| `/security` | Security Audit |
| `/perf` | Performance Optimizer |
| `/explore` | Explore |
| `/plan` | Plan |
| `/general` | General Purpose |

---

## Part 8: Testing Strategy

### 8.1 Unit Tests

- `test_agent_core.py` - AgentCore logic
- `test_stream_processor.py` - Stream parsing
- `test_state_machine.py` - State transitions
- `test_chat_history.py` - History management
- `test_tool_registry.py` - Tool registration
- `test_file_tools.py` - File tool operations
- `test_bash_tool.py` - Command execution

### 8.2 Integration Tests

- `test_agent_api_integration.py` - Real API calls
- `test_tool_execution.py` - End-to-end tool flows
- `test_session_persistence.py` - Save/load sessions

### 8.3 E2E Tests

- `test_e2e_agent_chat.py` - Full conversation flow
- `test_e2e_file_operations.py` - File creation/editing
- `test_e2e_bash_execution.py` - Command running
- `test_e2e_session_lifecycle.py` - Session save/load

---

## Part 9: Open Questions

1. **MCP Tool Integration**: Should we integrate with MCP servers for external tools?
   - **Recommendation**: Phase 2 - after core tools work

2. **Code Execution Safety**: How to sandbox bash execution?
   - **Recommendation**: Warning for destructive commands, confirmation option

3. **History Compression**: When to compress/summarize history?
   - **Recommendation**: When approaching 80% of max_messages

4. **Multi-file Operations**: Support batch editing?
   - **Recommendation**: Future enhancement (Morph-style)

5. **Streaming vs Non-streaming**: Support non-streaming mode?
   - **Recommendation**: Yes, for testing and simpler use cases
