"""Chat screen for the agent TUI.

This module provides the main chat interface screen:
- Header with app title and agent type
- ChatHistoryViewer for messages
- ThinkingIndicator for agent state
- ChatInput for user input
- Footer with key bindings
- HelpScreen for command reference
"""
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input

from goz.agent.tui.widgets import (
    ChatHistoryViewer,
    ThinkingIndicator,
)

# Keep Vertical import for HelpContent class
_ = Vertical  # Mark as used


class ChatScreen(Screen):
    """Main chat interface screen.

    Acceptance Criteria:
    - AC 7: ChatScreen class exists
    - AC 8: Has ChatHistoryViewer widget for messages
    - AC 9: Has ChatInput widget for user input
    - AC 10: Has Header showing app title and agent type
    - AC 11: Has Footer with key bindings
    - AC 12: Captures Enter key to submit input
    - AC 13: Sends input to AgentCore
    - AC 14: Streams response to display
    """

    def __init__(self, **kwargs):
        """Initialize ChatScreen."""
        super().__init__(**kwargs)
        self._welcome_widget = None

    def compose(self):
        """Compose the screen layout.

        Yields:
            Widgets for the screen layout
        """
        yield Header()
        yield ThinkingIndicator(id="thinking")
        yield ChatHistoryViewer(id="history")
        yield Input(id="input", placeholder="Type your request... (Enter to send)")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen and show welcome message."""
        self.show_welcome()
        # Focus input after a short delay to ensure widget is ready
        self.set_timer(0.1, self._focus_input)

    def _focus_input(self) -> None:
        """Focus the input widget."""
        try:
            input_widget = self.query_one("#input", Input)
            input_widget.focus()
        except:
            pass

    def on_screen_resume(self) -> None:
        """Called when screen is resumed - focus input."""
        self._focus_input()

    def show_welcome(self) -> None:
        """Show welcome message."""
        history = self.query_one(ChatHistoryViewer)
        self._welcome_widget = history.add_system_message("""Welcome to goz!

I'm your AI coding assistant. I can help you:
- Read and analyze code
- Create and modify files
- Run terminal commands
- Search the web
- Debug and fix issues

Type your request below or press / for commands.""")

    def clear_welcome(self) -> None:
        """Clear the welcome message if it exists."""
        if self._welcome_widget is not None:
            try:
                self._welcome_widget.remove()
                self._welcome_widget = None
            except Exception:
                pass  # Widget already removed or doesn't exist

    async def on_input_submitted(self, event) -> None:
        """Handle user input submission.

        Args:
            event: Input.Submitted event with the user's input
        """
        user_input = event.value

        if not user_input.strip():
            return

        # Clear welcome message on first input
        self.clear_welcome()

        # Clear the input
        event.input.value = ""

        # Check for slash commands
        if user_input.startswith("/"):
            await self.handle_slash_command(user_input)
            return

        # Add user message to display
        history = self.query_one(ChatHistoryViewer)
        history.add_user_message(user_input)
        if hasattr(self.app, "mark_dirty"):
            self.app.mark_dirty()

        # Yield to allow UI to update before API call
        import asyncio
        await asyncio.sleep(0)

        # Process with agent and stream response
        await self.process_agent_turn(user_input)

    async def on_chat_input_submitted(self, event) -> None:
        """Backward-compatible alias for older tests/widgets."""
        await self.on_input_submitted(event)

    async def process_agent_turn(self, user_input: str) -> None:
        """Process turn with agent and display streaming response.

        Args:
            user_input: The user's input message
        """
        from goz.agent.core import COMPLETION_MARKER

        history = self.query_one(ChatHistoryViewer)
        thinking = self.query_one("#thinking", ThinkingIndicator)
        agent = getattr(self.app, "agent", None)

        if agent is None:
            history.add_user_message("Agent not initialized")
            return

        # Show thinking indicator
        thinking.set_state("thinking")

        # Start assistant message
        history.start_assistant_message()

        # Stream response
        first_chunk = True
        try:
            async for chunk in agent.process_turn(user_input):
                if chunk == COMPLETION_MARKER:
                    break
                # Clear thinking once we get first content (with small delay to show it briefly)
                if first_chunk:
                    import asyncio
                    await asyncio.sleep(0.05)  # Show "Thinking..." for at least 50ms
                    thinking.set_state("idle")
                    first_chunk = False
                history.append_assistant_content(chunk)
        except Exception as e:
            # Handle errors gracefully
            thinking.set_state("idle")
            history.append_assistant_content(f"\n[Error: {e}]")

        # Clear thinking and finalize
        thinking.set_state("idle")
        history.end_assistant_message()

        # Refocus input for follow-up message
        self._focus_input()

    async def handle_slash_command(self, command: str) -> None:
        """Handle slash commands like /quit, /help, etc.

        Args:
            command: The slash command string (e.g., "/quit", "/help")
        """
        parts = command.split()
        cmd = parts[0] if parts else ""
        args = parts[1:]

        if cmd in ("/quit", "/q"):
            # Exit the application
            self.app.action_quit()
        elif cmd in ("/help", "/?"):
            # Show help screen
            self.app.push_screen(HelpScreen())
        elif cmd == "/clear":
            # Clear history
            history = self.query_one(ChatHistoryViewer)
            agent = getattr(self.app, "agent", None)
            if agent:
                agent.history.clear()
            if hasattr(self.app, "mark_dirty"):
                self.app.mark_dirty()
            history.clear()
        elif cmd == "/save":
            # Save session
            await self.cmd_save(args)
        elif cmd == "/load":
            # Load session
            await self.cmd_load(args)
        elif cmd in ("/sessions", "/ls"):
            # Show session list
            await self.cmd_sessions()
        elif cmd == "/delete":
            # Delete session
            await self.cmd_delete(args)
        elif cmd == "/session":
            # Show current session info
            await self.cmd_session()
        elif cmd == "/agent":
            # Set agent type (stub for Issue 29)
            agent_type = args[0] if args else "general"
            app = getattr(self.app, "agent", None)
            if hasattr(self.app, "set_agent_type"):
                self.app.set_agent_type(agent_type)
            history = self.query_one(ChatHistoryViewer)
            history.add_system_message(f"Agent type set to '{agent_type}' (stub)")
        else:
            history = self.query_one(ChatHistoryViewer)
            history.add_error_message(f"Unknown command: {cmd}")

    async def cmd_save(self, args: list[str]) -> None:
        """Handle /save command.

        Args:
            args: Command arguments (session name or empty for "default")
        """
        session_id = args[0] if args else "default"
        history = self.query_one(ChatHistoryViewer)

        try:
            await self.app.save_session(session_id)
            history.add_system_message(f"Session saved: {session_id}")
        except Exception as e:
            history.add_error_message(f"Failed to save session: {e}")

    async def cmd_load(self, args: list[str]) -> None:
        """Handle /load command.

        Args:
            args: Command arguments (session name or empty for list)
        """
        if not args:
            # Show session list
            from goz.agent.tui.screens.session import SessionListScreen
            from goz.agent.sessions import SessionManager

            if not hasattr(self.app, "session_manager") or self.app.session_manager is None:
                from goz.agent.tui.app import AgentApp
                if isinstance(self.app, AgentApp):
                    self.app.session_manager = SessionManager(
                        session_dir=self.app._get_session_dir()
                    )

            self.app.push_screen(SessionListScreen(
                session_manager=self.app.session_manager,
                on_load=self._load_and_refresh,
            ))
            return

        # Load specific session
        session_id = args[0]
        history = self.query_one(ChatHistoryViewer)

        try:
            await self.app.load_session(session_id)
            history.clear()
            history.add_system_message(f"Session loaded: {session_id}")
            # Restore messages in display
            for msg in self.app.agent.history.messages:
                if msg.role == "user":
                    history.add_user_message(msg.content)
                elif msg.role == "assistant":
                    history.start_assistant_message()
                    history.append_assistant_content(msg.content)
                    history.end_assistant_message()
        except FileNotFoundError:
            history.add_error_message(f"Session not found: {session_id}")
        except Exception as e:
            history.add_error_message(f"Failed to load session: {e}")

    async def cmd_sessions(self) -> None:
        """Handle /sessions command - show session list."""
        from goz.agent.tui.screens.session import SessionListScreen
        from goz.agent.sessions import SessionManager

        if not hasattr(self.app, "session_manager") or self.app.session_manager is None:
            from goz.agent.tui.app import AgentApp
            if isinstance(self.app, AgentApp):
                self.app.session_manager = SessionManager(
                    session_dir=self.app._get_session_dir()
                )

        self.app.push_screen(SessionListScreen(
            session_manager=self.app.session_manager,
            on_load=self._load_and_refresh,
        ))

    async def cmd_delete(self, args: list[str]) -> None:
        """Handle /delete command.

        Args:
            args: Command arguments (session name required)
        """
        if not args:
            history = self.query_one(ChatHistoryViewer)
            history.add_error_message("Usage: /delete <session-name>")
            return

        session_id = args[0]
        from goz.agent.tui.screens.session import ConfirmScreen

        self.app.push_screen(ConfirmScreen(
            message=f"Delete session '{session_id}'?",
            on_confirm=lambda: self._do_delete(session_id),
        ))

    async def cmd_session(self) -> None:
        """Handle /session command - show current session info."""
        import os
        from goz.agent.tui.screens.session import SessionInfoScreen

        info = {
            "name": getattr(self.app, "session_id", None) or "unsaved",
            "messages": len(self.app.agent.history.messages),
            "agent": getattr(self.app, "current_agent_type", "unknown"),
            "directory": os.getcwd(),
            "model": getattr(self.app, "config", None) and getattr(self.app.config, "chat_model", "unknown"),
        }

        self.app.push_screen(SessionInfoScreen(info=info))

    async def _load_and_refresh(self, session_id: str) -> None:
        """Load a session and refresh the display.

        Args:
            session_id: The session to load
        """
        history = self.query_one(ChatHistoryViewer)

        try:
            await self.app.load_session(session_id)
            history.clear()
            history.add_system_message(f"Session loaded: {session_id}")
            # Restore messages in display
            for msg in self.app.agent.history.messages:
                if msg.role == "user":
                    history.add_user_message(msg.content)
                elif msg.role == "assistant":
                    history.start_assistant_message()
                    history.append_assistant_content(msg.content)
                    history.end_assistant_message()
        except Exception as e:
            history.add_error_message(f"Failed to load session: {e}")

    def _do_delete(self, session_id: str) -> None:
        """Actually delete a session (called from ConfirmScreen).

        Args:
            session_id: The session to delete
        """
        import asyncio
        from goz.agent.sessions import SessionManager

        async def _delete():
            if not hasattr(self.app, "session_manager") or self.app.session_manager is None:
                from goz.agent.tui.app import AgentApp
                if isinstance(self.app, AgentApp):
                    self.app.session_manager = SessionManager(
                        session_dir=self.app._get_session_dir()
                    )

            deleted = await self.app.session_manager.delete(session_id)
            history = self.query_one(ChatHistoryViewer)

            if deleted:
                history.add_system_message(f"Session deleted: {session_id}")
            else:
                history.add_error_message(f"Session not found: {session_id}")

        # Run the async delete
        asyncio.create_task(_delete())


class HelpScreen(Screen):
    """Help screen with command reference."""

    BINDINGS = [
        ("escape", "pop_screen", "Close"),
    ]

    def compose(self):
        """Compose the help screen."""
        yield Header()
        yield HelpContent()
        yield Footer()


class HelpContent(Vertical):
    """Help content widget."""

    def render(self):
        """Render the help content."""
        from rich.panel import Panel
        from rich.text import Text

        text = Text()
        text.append("goz Commands\n", style="bold")
        text.append("/help, /?      Show this help\n", style="cyan")
        text.append("/quit, /q      Quit the session\n", style="cyan")
        text.append("/clear         Clear chat history\n", style="cyan")
        text.append("/save <name>   Save current session\n", style="cyan")
        text.append("/load <name>   Load a session (or list if no name)\n", style="cyan")
        text.append("/sessions      List all sessions\n", style="cyan")
        text.append("/delete <name> Delete a session\n", style="cyan")
        text.append("/session       Show current session info\n", style="cyan")
        text.append("/agent <type>  Switch agent type (stub)\n", style="cyan")
        text.append("\n", style="default")
        text.append("Press Esc to close", style="dim")

        return Panel(text, title="Help", border_style="blue")
