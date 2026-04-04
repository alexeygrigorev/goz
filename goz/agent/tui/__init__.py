"""Agent TUI module for goz interactive coding agent.

This package provides the Textual-based TUI for the interactive agent:
- AgentApp: Main TUI application
- ChatScreen: Chat interface screen
- Widgets: ChatHistoryViewer, ChatInput, MessageBox, etc.
"""
from goz.agent.tui.app import AgentApp


def run_agent_app(
    session_id: str | None = None,
    agent_type: str | None = None,
) -> None:
    """Launch the agent TUI application.

    This is the entry point for agent mode when `goz` is run with no args.

    Args:
        session_id: Optional session ID to load (stub for Issue 27)
        agent_type: Optional agent type to start with (stub for Issue 29)
    """
    app = AgentApp()

    # Load session if specified
    if session_id:
        # Note: This is async, but we can't await here
        # The app will need to handle this in on_mount
        app._pending_session_load = session_id

    # Set agent type if specified
    if agent_type:
        app.set_agent_type(agent_type)

    app.run()


__all__ = ["AgentApp", "run_agent_app"]
