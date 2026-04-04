"""Chat widgets for the agent TUI.

This module provides widgets for the chat interface:
- ChatHistoryViewer: Display chat messages with scrolling
- MessageBox: Display a single chat message
- ToolCallBox: Display tool invocation
- ToolResultBox: Display tool result
- ThinkingIndicator: Show agent thinking/executing state
"""
from dataclasses import dataclass
from typing import Literal

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Input, Static

from goz.agent.tui.widgets.markdown import MarkdownViewer


# Role types for messages
MessageRole = Literal["user", "assistant", "tool", "tool_call"]


class ChatHistoryViewer(VerticalScroll):
    """Widget for displaying chat history.

    Acceptance Criteria:
    - AC 15: Displays messages with role indicators
    - AC 16: User messages aligned left (or distinct)
    - AC 17: Assistant messages aligned left
    - AC 18: Tool calls shown with special formatting
    - AC 19: Tool results shown in blocks
    - AC 20: Supports scrolling
    - AC 21: Auto-scrolls to new messages
    - AC 22: Syntax highlighting for code blocks (basic)
    """

    def __init__(self, **kwargs):
        """Initialize ChatHistoryViewer."""
        super().__init__(**kwargs)
        self.current_message_chunks: list[str] = []
        self.current_box: MessageBox | None = None

    def add_user_message(self, content: str) -> None:
        """Add a user message to the history.

        Args:
            content: The user message content
        """
        msg_box = MessageBox(content=content, role="user")
        self.mount(msg_box)
        self.scroll_end()

    def start_assistant_message(self) -> None:
        """Start a new assistant message for streaming.

        Creates a new MarkdownViewer that will be updated as content arrives.
        """
        self.current_message_chunks = []
        self.current_viewer = MarkdownViewer(markdown_text="")
        self.mount(self.current_viewer)

    def append_assistant_content(self, chunk: str) -> None:
        """Append content to the current assistant message.

        Args:
            chunk: Text chunk to append
        """
        self.current_message_chunks.append(chunk)
        if self.current_viewer:
            # Update the markdown content
            self.current_viewer.update_content("".join(self.current_message_chunks))

    def end_assistant_message(self) -> None:
        """Finalize the current assistant message.

        Scrolls to the end to show the complete message.
        """
        self.scroll_end()
        self.current_viewer = None
        self.current_message_chunks = []

    def add_tool_call(self, tool_name: str, args: dict) -> None:
        """Show a tool invocation.

        Args:
            tool_name: Name of the tool being called
            args: Tool arguments
        """
        tool_box = ToolCallBox(tool_name=tool_name, args=args)
        self.mount(tool_box)
        self.scroll_end()

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Show a tool result.

        Args:
            tool_name: Name of the tool that was called
            result: Result string from the tool
        """
        result_box = ToolResultBox(tool_name=tool_name, result=result)
        self.mount(result_box)
        self.scroll_end()

    def add_system_message(self, content: str) -> Static:
        """Add a system/welcome message to the history.

        Args:
            content: The system message content

        Returns:
            The Static widget containing the message (for removal)
        """
        text = Text()
        text.append(content, style="bold cyan")
        panel = Panel(text, border_style="cyan", padding=(0, 1))
        msg_box = Static(panel)
        self.mount(msg_box)
        self.scroll_end()
        return msg_box

    def add_error_message(self, content: str) -> None:
        """Add an error message to the history.

        Args:
            content: The error message content
        """
        text = Text()
        text.append(f"Error: {content}", style="bold red")
        panel = Panel(text, border_style="red", padding=(0, 1))
        msg_box = Static(panel)
        self.mount(msg_box)
        self.scroll_end()

    def clear(self) -> None:
        """Clear all messages from the history.

        Note: VerticalScroll manages children internally. We iterate
        over mounted children and remove them properly.
        """
        # Get all mounted children and remove them
        # We use a list() to avoid modification during iteration
        for child in list(self._nodes):
            try:
                child.remove()
            except Exception:
                # Child might already be removed or not mountable
                pass


class MessageBox(Static):
    """A single chat message display.

    Acceptance Criteria:
    - Shows role indicator (You/Agent)
    - Distinct styling for user vs assistant messages
    - Displays message content
    """

    def __init__(self, content: str, role: MessageRole, **kwargs):
        """Initialize MessageBox.

        Args:
            content: Message content
            role: Message role (user, assistant, tool, etc.)
        """
        super().__init__(**kwargs)
        self.content = content
        self.role = role

    def update_content(self, new_content: str) -> None:
        """Update the message content.

        Args:
            new_content: New content to display
        """
        self.content = new_content
        self.update(self._render_content())

    def _render_content(self) -> RenderableType:
        """Render the message with role indicator.

        Returns:
            Rich renderable for display
        """
        if self.role == "user":
            prefix = "[bold blue]You:[/bold blue] "
        elif self.role == "assistant":
            prefix = "[bold green]Agent:[/bold green] "
        elif self.role == "tool_call":
            prefix = "[bold yellow]Tool Call:[/bold yellow] "
        elif self.role == "tool":
            prefix = "[bold cyan]Tool Result:[/bold cyan] "
        else:
            prefix = "[bold]Message:[/bold] "

        text = Text()
        text.append(prefix)
        text.append(self.content)
        return text

    def render(self) -> RenderableType:
        """Render the message.

        Returns:
            Rich renderable for display
        """
        return self._render_content()


class ToolCallBox(Static):
    """Display a tool call invocation.

    Shows tool name and arguments in a formatted box.
    """

    def __init__(self, tool_name: str, args: dict, **kwargs):
        """Initialize ToolCallBox.

        Args:
            tool_name: Name of the tool being called
            args: Tool arguments
        """
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args = args

    def render(self) -> RenderableType:
        """Render the tool call.

        Returns:
            Rich renderable for display
        """
        text = Text()
        text.append(f"[Tool: {self.tool_name}]", style="bold yellow")
        if self.args:
            import json
            args_str = json.dumps(self.args, indent=2)
            text.append(f"\n{args_str}", style="dim")
        return text


class ToolResultBox(Static):
    """Display a tool result.

    Shows tool name and result in a formatted box.
    """

    def __init__(self, tool_name: str, result: str, **kwargs):
        """Initialize ToolResultBox.

        Args:
            tool_name: Name of the tool that was called
            result: Result from the tool
        """
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.result = result

    def render(self) -> RenderableType:
        """Render the tool result.

        Returns:
            Rich renderable for display
        """
        text = Text()
        text.append(f"[Result: {self.tool_name}]", style="bold cyan")
        text.append(f"\n{self.result}", style="dim")
        return text


class ThinkingIndicator(Static):
    """Widget for showing agent state (thinking, executing, etc.).

    Acceptance Criteria:
    - Shows "Thinking..." when processing
    - Shows "Running: <tool>" when executing tools
    - Shows error state on errors
    - Hides when idle
    """

    state: str = "idle"  # idle, thinking, executing, error
    tool_name: str | None = None

    DEFAULT_CSS = """
    ThinkingIndicator {
        height: 1;
        padding: 0 1;
        text_style: bold;
    }
    ThinkingIndicator.-thinking {
        color: $warning;
    }
    ThinkingIndicator.-executing {
        color: $primary;
    }
    ThinkingIndicator.-error {
        color: $error;
    }
    """

    def __init__(self, **kwargs):
        """Initialize ThinkingIndicator."""
        super().__init__(**kwargs)
        self.state = "idle"
        self.tool_name = None

    def set_state(self, state: str, data: str | None = None) -> None:
        """Set the indicator state.

        Args:
            state: One of "idle", "thinking", "executing", "error"
            data: Optional data (e.g., tool name for executing state)
        """
        self.state = state
        self.tool_name = data
        self.update_classes()
        self.refresh()

    def update_classes(self) -> None:
        """Update CSS classes based on state."""
        self.remove_class("-thinking", "-executing", "-error")
        if self.state == "thinking":
            self.add_class("-thinking")
        elif self.state == "executing":
            self.add_class("-executing")
        elif self.state == "error":
            self.add_class("-error")

    def render(self) -> RenderableType:
        """Render the indicator.

        Returns:
            Rich renderable for display
        """
        if self.state == "idle":
            return ""
        elif self.state == "thinking":
            return "[bold yellow]Thinking...[/bold yellow]"
        elif self.state == "executing":
            tool = self.tool_name or "tool"
            return f"[bold cyan]Running: {tool}[/bold cyan]"
        elif self.state == "error":
            return "[bold red]Error[/bold red]"
        return ""


class ChatInput(Input):
    """Input widget for chat messages.

    Acceptance Criteria:
    - AC 24: Multi-line input support
    - AC 25: Enter to submit, Shift+Enter for newline
    - AC 26: Clears after submit
    - AC 27: Shows prompt character
    - AC 28: Handles slash commands
    """

    def __init__(self, **kwargs):
        """Initialize ChatInput."""
        super().__init__(
            placeholder="Type your request... (Enter to send)",
            **kwargs
        )
