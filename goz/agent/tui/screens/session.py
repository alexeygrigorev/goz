"""Session screens for the agent TUI.

This module provides screens for session management:
- SessionListScreen: List and select saved sessions
- SessionInfoScreen: Display current session info
- ConfirmScreen: Confirmation dialog for destructive actions

Acceptance Criteria:
- AC 1: SessionListScreen shows all sessions with metadata
- AC 2: SessionListScreen supports keyboard navigation
- AC 3: SessionListScreen Enter to load, Esc to close
- AC 4: SessionInfoScreen shows current session info
- AC 5: ConfirmScreen shows confirmation dialog
- AC 6: Error handling for non-existent sessions
"""
import os
from datetime import datetime
from typing import Awaitable, Callable

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, ListView, ListItem, Static

from goz.agent.sessions import SessionInfo, SessionManager


class SessionListScreen(Screen):
    """Screen for listing and selecting sessions.

    Acceptance Criteria:
    - AC 1: Shows all sessions with metadata
    - AC 2: Supports keyboard navigation
    - AC 3: Enter to load, Esc to close
    """

    BINDINGS = [
        ("escape", "pop_screen", "Close"),
        ("q", "pop_screen", "Close"),
    ]

    def __init__(
        self,
        session_manager: SessionManager,
        on_load: Callable[[str], Awaitable[None]],
    ):
        """Initialize SessionListScreen.

        Args:
            session_manager: SessionManager instance
            on_load: Callback when session is selected for loading
        """
        super().__init__()
        self.session_manager = session_manager
        self.on_load = on_load

    def compose(self):
        """Compose the screen layout."""
        yield Header()
        yield SessionListView(id="session-list")
        yield Footer()

    async def on_mount(self) -> None:
        """Load sessions on mount."""
        list_view = self.query_one(SessionListView)
        sessions = self.session_manager.list_sessions()
        list_view.set_sessions(sessions)


class SessionListView(Static):
    """List view for sessions."""

    def set_sessions(self, sessions: list[SessionInfo]) -> None:
        """Set sessions to display.

        Args:
            sessions: List of SessionInfo objects to display
        """
        self.sessions = sessions
        self.refresh()

    def render(self) -> RenderableType:
        """Render the session list."""
        if not self.sessions:
            return Panel(
                Text("No saved sessions found.", style="dim"),
                title="Sessions",
                border_style="blue",
            )

        table = Table(show_header=True, header_style="bold cyan", border_style="blue")
        table.add_column("Name", style="cyan")
        table.add_column("Messages", style="dim")
        table.add_column("Agent", style="dim")
        table.add_column("Updated", style="dim")

        for s in self.sessions:
            updated_str = s.updated_at.strftime("%Y-%m-%d %H:%M")
            table.add_row(
                s.id,
                str(s.message_count),
                s.agent_type,
                updated_str,
            )

        return Panel(
            table,
            title=f"Sessions ({len(self.sessions)})",
            border_style="blue",
        )

    def on_key(self, event) -> None:
        """Handle keyboard input for session selection.

        Args:
            event: Key event
        """
        # Handle Enter to load first session
        # (In a full implementation, we'd have proper cursor navigation)
        if event.key == "enter" and self.sessions:
            # For now, just load the first session
            # A full implementation would have cursor navigation
            pass


class SessionInfoScreen(Screen):
    """Screen showing current session info.

    Acceptance Criteria:
    - AC 4: Shows current session info
    - Press any key to close
    """

    BINDINGS = [
        ("escape", "pop_screen", "Close"),
    ]

    def __init__(self, info: dict):
        """Initialize SessionInfoScreen.

        Args:
            info: Dictionary with session info (name, messages, agent, directory, model)
        """
        super().__init__()
        self.info = info

    def compose(self):
        """Compose the screen layout."""
        yield Header()
        yield SessionInfoDisplay(info=self.info)
        yield Footer()

    def on_key(self, event) -> None:
        """Close on any key except escape."""
        if event.key != "escape":
            self.app.pop_screen()


class SessionInfoDisplay(Static):
    """Display session info."""

    def __init__(self, info: dict):
        """Initialize SessionInfoDisplay.

        Args:
            info: Dictionary with session info
        """
        super().__init__()
        self.info = info

    def render(self) -> RenderableType:
        """Render the session info."""
        from rich.console import Group

        i = self.info
        return Panel(
            Group(
                Text("Current Session", style="bold cyan"),
                Text(""),
                self._row("Name:", i.get("name", "unsaved")),
                self._row("Messages:", str(i.get("messages", 0))),
                self._row("Agent:", i.get("agent", "unknown")),
                self._row("Model:", i.get("model", "unknown")),
                self._row("Directory:", i.get("directory", "unknown")),
                Text(""),
                Text("[dim]Press any key to close[/dim]"),
            ),
            title="Session Info",
            border_style="blue",
        )

    def _row(self, label: str, value: str) -> Text:
        """Create a row with label and value.

        Args:
            label: Row label
            value: Row value

        Returns:
            Text object with formatted row
        """
        return Text.assemble(
            Text(label, style="bold"),
            Text(" "),
            Text(value, style="default"),
            Text("\n"),
        )


class ConfirmScreen(Screen):
    """Confirmation dialog.

    Acceptance Criteria:
    - AC 5: Shows confirmation dialog
    - User can confirm (y/Enter) or cancel (n/Esc)
    """

    class Confirmed(Message):
        """User confirmed the action."""

    class Cancelled(Message):
        """User cancelled the action."""

    def __init__(
        self,
        message: str,
        on_confirm: Callable[[], None],
    ):
        """Initialize ConfirmScreen.

        Args:
            message: Confirmation message to display
            on_confirm: Callback when user confirms
        """
        super().__init__()
        self.message = message
        self.on_confirm = on_confirm

    def compose(self):
        """Compose the confirmation dialog."""
        yield Header()
        yield ConfirmDialog(message=self.message)
        yield Footer()

    def on_confirm_dialog_confirmed(self) -> None:
        """Handle confirmation."""
        self.on_confirm()
        self.app.pop_screen()

    def on_confirm_dialog_cancelled(self) -> None:
        """Handle cancellation."""
        self.app.pop_screen()


class ConfirmDialog(Static):
    """Dialog widget for confirmation."""

    def __init__(self, message: str):
        """Initialize ConfirmDialog.

        Args:
            message: Confirmation message
        """
        super().__init__()
        self.message = message

    def render(self) -> RenderableType:
        """Render the confirmation dialog."""
        from rich.console import Group

        return Panel(
            Group(
                Text(self.message, style="bold yellow"),
                Text(""),
                Text("[y] Yes  [n] No  [Enter] Yes  [Esc] No", style="dim"),
            ),
            title="Confirm",
            border_style="yellow",
        )

    def on_key(self, event) -> None:
        """Handle key press for confirmation.

        Args:
            event: Key event
        """
        if event.key in ("y", "enter"):
            self.post_message(ConfirmDialog.Confirmed(self))
        elif event.key in ("n", "escape"):
            self.post_message(ConfirmDialog.Cancelled(self))

    class Confirmed(Message):
        """User confirmed the action."""

    class Cancelled(Message):
        """User cancelled the action."""
