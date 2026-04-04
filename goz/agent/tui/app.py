"""AgentApp - Main TUI application for goz interactive coding agent.

This module provides the AgentApp class which is the main entry point
for the interactive agent TUI.

Acceptance Criteria:
- AC 1: AgentApp class exists
- AC 2: Inherits from textual.app.App
- AC 3: Registers ChatScreen and other screens
- AC 4: Initializes AgentCore with config
- AC 5: Handles keyboard shortcuts (q=quit, /=slash commands)
- AC 6: Shows agent type in header
"""
import os
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult

from goz.agent.core import AgentCore
from goz.agent.history import ChatHistory
from goz.agent.sessions import Session, SessionManager
from goz.agent.tui.screens.chat import ChatScreen
from goz.agent.tui.screens.session import ConfirmScreen
from goz.config import Config, load_config


class AgentApp(App[None]):
    """Main agent TUI application.

    Acceptance Criteria:
    - AC 1: AgentApp class exists in goz/agent/tui/app.py
    - AC 2: Inherits from textual.app.App
    - AC 3: Registers ChatScreen and other screens
    - AC 4: Initializes AgentCore with config
    - AC 5: Handles keyboard shortcuts (q=quit, /=slash commands)
    - AC 6: Shows agent type in header
    """

    TITLE = "goz - Interactive Coding Agent"
    MOUSE_SUPPORT = False  # Allow terminal text selection

    CSS = """
    Screen {
        background: $background;
        layout: vertical;
    }
    ChatHistoryViewer {
        height: 1fr;
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
        height: 3;
        padding: 1;
        background: $surface;
    }
    ThinkingIndicator {
        height: 1;
    }
    """

    SCREENS = {
        "chat": ChatScreen,
    }

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, config: Config | None = None):
        """Initialize AgentApp."""
        super().__init__()
        self.config = config or load_config()
        self.agent = AgentCore(self.config)
        self.current_agent_type = "general_purpose"
        self.session_id: str | None = None
        self.session_manager: SessionManager | None = None
        self._session_dir: Path | None = None
        self.has_unsaved_changes = False

    def _get_session_dir(self) -> Path:
        """Get the session directory for saving/loading sessions.

        Returns:
            Path to the session directory
        """
        if self._session_dir is None:
            self._session_dir = Path.home() / ".goz" / "sessions"
            self._session_dir.mkdir(parents=True, exist_ok=True)
        return self._session_dir

    def on_mount(self) -> None:
        """Mount chat screen on startup."""
        self.push_screen("chat")

    def action_quit(self) -> None:
        """Quit the application.

        Acceptance Criteria:
        - AC 5: Handles keyboard shortcuts (q=quit)
        """
        if self.has_unsaved_changes and self.agent.history.messages:
            self.push_screen(
                ConfirmScreen(
                    message="You have unsaved changes. Quit without saving?",
                    on_confirm=self.exit,
                )
            )
            return
        self.exit()

    async def load_session(self, session_id: str) -> None:
        """Load a saved session.

        Args:
            session_id: The session identifier to load

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        # Initialize session manager if needed
        if self.session_manager is None:
            self.session_manager = SessionManager(session_dir=self._get_session_dir())

        # Load session from file
        session = await self.session_manager.load(session_id)

        # Restore chat history
        self.agent.history = ChatHistory(messages=session.messages)

        # Restore session metadata
        self.session_id = session.id
        self.current_agent_type = session.agent_type
        self.has_unsaved_changes = False

        # Note: working_directory could be restored with os.chdir(session.working_directory)
        # but we'll skip that to avoid surprising the user

    async def save_session(self, session_id: str) -> None:
        """Save the current session.

        Args:
            session_id: The session identifier to save
        """
        # Initialize session manager if needed
        if self.session_manager is None:
            self.session_manager = SessionManager(session_dir=self._get_session_dir())

        # Create session object
        now = datetime.now()
        session = Session(
            id=session_id,
            created_at=now,
            updated_at=now,
            working_directory=os.getcwd(),
            messages=self.agent.history.messages,
            model=self.config.chat_model,
            agent_type=self.current_agent_type,
            config_snapshot=self.config.model_dump() if hasattr(self.config, "model_dump") else {},
        )

        # Save session
        await self.session_manager.save(session)

        # Update session_id
        self.session_id = session_id
        self.has_unsaved_changes = False

    def set_agent_type(self, agent_type: str) -> None:
        """Set the agent type (stub for Issue 29).

        Args:
            agent_type: The agent type to use (e.g., "general", "reviewer")
        """
        # Stub implementation for Issue 29
        # In the future, this will switch between different agent configurations
        self.current_agent_type = agent_type
        self.has_unsaved_changes = True

    def mark_dirty(self) -> None:
        """Mark the current session state as modified."""
        self.has_unsaved_changes = True
