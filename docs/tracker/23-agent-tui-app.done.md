# Issue 23: Agent App + Chat Screen

## Status
.todo

## Description
Implement the AgentApp and ChatScreen for the interactive agent TUI using Textual.

## User Scenarios

### Scenario 1: Launch Agent Mode
- User runs: `goz`
- No subcommand provided
- System detects agent mode should launch
- AgentApp starts with ChatScreen
- User sees welcome message and input prompt

### Scenario 2: User Input
- User types: "Hello, what can you do?"
- User presses Enter
- Input is captured
- Message is sent to AgentCore
- Response streams to display
- Input field clears for next message

### Scenario 3: Display Streaming Response
- Agent sends response chunks
- Chat screen displays each chunk as it arrives
- Text appears word-by-word (real-time)
- Cursor shows typing in progress

### Scenario 4: Display Tool Call
- Agent calls view_file tool
- Chat screen shows: "[Tool: view_file]"
- Chat screen shows: "Reading: main.py"
- File content is displayed in a code block
- Then agent's explanation appears

### Scenario 5: Navigate History
- User scrolls up in chat history
- Previous messages are visible
- User can see full conversation
- User scrolls back down to input

### Scenario 6: Special Commands
- User types: `/help`
- System recognizes slash command
- Help dialog appears
- User presses Esc to close

### Scenario 7: Quit
- User presses `q` or types `/quit`
- Confirmation dialog: "Quit session?"
- User confirms
- App exits cleanly

## Acceptance Criteria

### AgentApp
1. `AgentApp` class exists in `goz/agent/tui/app.py`
2. Inherits from `textual.app.App`
3. Registers ChatScreen and other screens
4. Initializes AgentCore with config
5. Handles keyboard shortcuts (q=quit, /=slash commands)
6. Shows agent type in header

### ChatScreen
7. `ChatScreen` class exists in `goz/agent/tui/screens/chat.py`
8. Has ChatHistoryViewer widget for messages
9. Has ChatInput widget for user input
10. Has Header showing app title and agent type
11. Has Footer with key bindings
12. Captures Enter key to submit input
13. Sends input to AgentCore
14. Streams response to display

### ChatHistoryViewer
15. `ChatHistoryViewer` widget exists
16. Displays messages with role indicators
17. User messages aligned left (or distinct)
18. Assistant messages aligned left
19. Tool calls shown with special formatting
20. Tool results shown in blocks
21. Supports scrolling
22. Auto-scrolls to new messages
23. Syntax highlighting for code blocks

### ChatInput
24. `ChatInput` widget exists
25. Multi-line input support
26. Enter to submit, Shift+Enter for newline
27. Clears after submit
28. Shows prompt character
29. Handles slash commands

### Integration
30. AgentApp.launch() starts the TUI
31. `goz` with no args launches agent mode
32. Config is loaded and passed to AgentCore
33. Errors are shown to user, not crash
34. App exits cleanly on quit

## Technical Details

### File Structure
```
goz/agent/tui/
├── __init__.py
├── app.py           # AgentApp
└── screens/
    ├── __init__.py
    └── chat.py       # ChatScreen
```

### AgentApp
```python
from textual.app import App
from goz.agent.core import AgentCore
from goz.config import load_config

class AgentApp(App[None]):
    """Main agent TUI application."""

    TITLE = "goz - Interactive Coding Agent"
    CSS = """
    Screen {
        background: $background;
    }
    ChatHistoryViewer {
        height: 1fr;
    }
    ChatInput {
        height: 3;
    }
    """

    SCREENS = {
        "chat": ChatScreen,
    }

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.agent = AgentCore(self.config)
        self.current_agent_type = AgentType.GENERAL_PURPOSE

    def on_mount(self) -> None:
        """Mount chat screen on startup."""
        self.push_screen("chat")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
```

### ChatScreen
```python
from textual.screen import Screen
from textual.widgets import Header, Footer
from goz.agent.tui.widgets import ChatHistoryViewer, ChatInput

class ChatScreen(Screen):
    """Main chat interface."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield ChatHistoryViewer(id="history")
        yield ChatInput(placeholder="Type your request...", id="input")
        yield Footer()

    async def on_chat_input_submitted(
        self,
        event: ChatInput.Submitted,
    ) -> None:
        """Handle user input submission."""
        user_input = event.value

        if not user_input.strip():
            return

        # Check for slash commands
        if user_input.startswith("/"):
            await self.handle_slash_command(user_input)
            return

        # Add user message to display
        history = self.query_one(ChatHistoryViewer)
        history.add_user_message(user_input)

        # Process with agent and stream response
        await self.process_agent_turn(user_input)

    async def process_agent_turn(self, user_input: str) -> None:
        """Process turn with agent and display streaming response."""
        history = self.query_one(ChatHistoryViewer)

        # Start assistant message
        history.start_assistant_message()

        # Stream response
        async for chunk in self.agent.process_turn(user_input):
            if chunk == "\x00":  # Completion marker
                break
            history.append_assistant_content(chunk)

        history.end_assistant_message()

    async def handle_slash_command(self, command: str) -> None:
        """Handle slash commands like /quit, /help, etc."""
        parts = command.split()
        cmd = parts[0]

        if cmd in ("/quit", "/q"):
            self.app.exit()
        elif cmd == "/help":
            self.show_help()
        # ... other commands
```

### ChatHistoryViewer
```python
from textual.widgets import Static
from textual.containers import VerticalScroll

class ChatHistoryViewer(VerticalScroll):
    """Widget for displaying chat history."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages_container = VerticalScroll()
        self.current_message: list[str] = []

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        msg_box = MessageBox(
            content=content,
            role="user",
        )
        self.mount(msg_box)
        self.scroll_end()

    def start_assistant_message(self) -> None:
        """Start a new assistant message for streaming."""
        self.current_message = []
        self.current_box = MessageBox(role="assistant")
        self.mount(self.current_box)

    def append_assistant_content(self, chunk: str) -> None:
        """Append content to current assistant message."""
        self.current_message.append(chunk)
        self.current_box.update("".join(self.current_message))

    def end_assistant_message(self) -> None:
        """Finalize the current assistant message."""
        self.scroll_end()

    def add_tool_call(self, tool_name: str, args: dict) -> None:
        """Show a tool invocation."""
        tool_box = ToolCallBox(tool_name, args)
        self.mount(tool_box)
        self.scroll_end()

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Show a tool result."""
        result_box = ToolResultBox(tool_name, result)
        self.mount(result_box)
        self.scroll_end()
```

### ChatInput
```python
from textual.widgets import Input
from textual.message import Message

class ChatInput(Input):
    """Input widget for chat messages."""

    class Submitted(Message):
        """Emitted when user submits input."""

    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Type your request...",
            id="chat-input",
        )

    def _on_key(self, event) -> None:
        """Handle keyboard input."""
        if event.key == "enter":
            if event.shift:  # Shift+Enter = newline
                event.prevent_default()
                self.insert_text("\n")
            else:  # Enter = submit
                event.prevent_default()
                self.post_message(ChatInput.Submitted(self.value))
                self.value = ""  # Clear input
```

### MessageBox Component
```python
from rich.console import RenderableType
from rich.text import Text

class MessageBox(Static):
    """A single chat message."""

    def __init__(self, content: str, role: str, **kwargs):
        super().__init__(**kwargs)
        self.content = content
        self.role = role

    def render(self) -> RenderableType:
        if self.role == "user":
            prefix = "[bold blue]You:[/bold blue] "
        else:
            prefix = "[bold green]Agent:[/bold green] "

        text = Text()
        text.append(prefix)
        text.append(self.content)
        return text
```

### Entry Point Changes
```python
# goz/__main__.py

def main() -> None:
    """Run the goz CLI."""
    # ... existing arg parsing ...

    if args.command is None:
        # No command = launch AGENT MODE (not old TUI)
        from goz.agent.tui import run_agent_app
        run_agent_app()
        return

    # ... existing command dispatch ...
```

### CSS Styling
```css
ChatHistoryViewer {
    padding: 1;
    background: $background;
}

MessageBox {
    padding: 1;
    margin: 1 0;
    background: $surface;
}

MessageBox.user {
    background: $primary 10%;
}

MessageBox.assistant {
    background: $success 10%;
}

ToolCallBox {
    border: solid $primary;
    padding: 1;
    margin: 1 0;
}

ToolResultBox {
    border: solid $accent;
    padding: 1;
    margin: 1 0;
    background: $panel;
}

ChatInput {
    dock: bottom;
    padding: 1;
    background: $surface;
}
```

## Dependencies
- Issue 15: Agent Core
- Issue 16: Stream Processor
- Issue 17: Chat API Client
- Issue 22: Tool Integration

## Related Issues
- Issue 24: Markdown + Diff Widgets
- Issue 25: Thinking Indicator

## Log
