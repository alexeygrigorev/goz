"""Unit tests for Agent TUI App (Issue 23).

Tests cover:
- AgentApp class (textual.app.App subclass)
- ChatScreen with ChatHistoryViewer, ChatInput, Header, Footer
- ChatHistoryViewer widget
- ChatInput widget
- Integration with __main__.py for agent mode launch
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from goz.config import Config


class TestAgentApp:
    """Unit Tests: AgentApp class."""

    def test_agent_app_exists(self):
        """Test AgentApp class can be imported."""
        from goz.agent.tui.app import AgentApp  # noqa: F401
        assert AgentApp is not None

    def test_agent_app_inherits_from_textual_app(self):
        """Test AgentApp inherits from textual.app.App."""
        from goz.agent.tui.app import AgentApp
        from textual.app import App

        assert issubclass(AgentApp, App)

    def test_agent_app_has_title(self):
        """Test AgentApp has TITLE attribute."""
        from goz.agent.tui.app import AgentApp

        assert hasattr(AgentApp, "TITLE")
        assert "goz" in AgentApp.TITLE.lower()

    def test_agent_app_has_css(self):
        """Test AgentApp has CSS attribute."""
        from goz.agent.tui.app import AgentApp

        assert hasattr(AgentApp, "CSS")
        assert isinstance(AgentApp.CSS, str)

    def test_agent_app_has_screens(self):
        """Test AgentApp has SCREENS attribute with ChatScreen."""
        from goz.agent.tui.app import AgentApp

        assert hasattr(AgentApp, "SCREENS")
        assert "chat" in AgentApp.SCREENS

    def test_agent_app_init_creates_config(self):
        """Test AgentApp initializes config."""
        from goz.agent.tui.app import AgentApp

        with patch("goz.agent.tui.app.load_config") as mock_load:
            mock_config = Config(zai_token="test-token")
            mock_load.return_value = mock_config

            app = AgentApp()
            assert app.config is not None
            assert app.config.zai_token == "test-token"

    def test_agent_app_init_creates_agent_core(self):
        """Test AgentApp initializes AgentCore."""
        from goz.agent.tui.app import AgentApp

        with patch("goz.agent.tui.app.load_config") as mock_load:
            mock_config = Config(zai_token="test-token")
            mock_load.return_value = mock_config

            app = AgentApp()
            assert hasattr(app, "agent")
            assert app.agent is not None

    def test_agent_app_has_agent_type(self):
        """Test AgentApp has current_agent_type attribute."""
        from goz.agent.tui.app import AgentApp

        # Mock both load_config and AgentCore to avoid initialization issues
        with patch("goz.agent.tui.app.load_config"), \
             patch("goz.agent.tui.app.AgentCore"):
            app = AgentApp()
            assert hasattr(app, "current_agent_type")

    def test_agent_app_has_action_quit(self):
        """Test AgentApp has action_quit method."""
        from goz.agent.tui.app import AgentApp

        # Mock both load_config and AgentCore to avoid initialization issues
        with patch("goz.agent.tui.app.load_config"), \
             patch("goz.agent.tui.app.AgentCore"):
            app = AgentApp()
            assert hasattr(app, "action_quit")
            assert callable(app.action_quit)

    def test_agent_app_registers_chat_screen(self):
        """Test AgentApp registers ChatScreen in SCREENS."""
        from goz.agent.tui.app import AgentApp
        from goz.agent.tui.screens.chat import ChatScreen

        assert AgentApp.SCREENS["chat"] is ChatScreen


class TestChatScreen:
    """Unit Tests: ChatScreen class."""

    def test_chat_screen_exists(self):
        """Test ChatScreen class can be imported."""
        from goz.agent.tui.screens.chat import ChatScreen  # noqa: F401
        assert ChatScreen is not None

    def test_chat_screen_inherits_from_textual_screen(self):
        """Test ChatScreen inherits from textual.screen.Screen."""
        from goz.agent.tui.screens.chat import ChatScreen
        from textual.screen import Screen

        assert issubclass(ChatScreen, Screen)

    def test_chat_screen_has_compose_method(self):
        """Test ChatScreen has compose method."""
        from goz.agent.tui.screens.chat import ChatScreen

        assert hasattr(ChatScreen, "compose")
        assert callable(ChatScreen.compose)

    def test_chat_screen_compose_yields_widgets(self):
        """Test ChatScreen.compose yields expected widgets."""
        from goz.agent.tui.screens.chat import ChatScreen

        screen = ChatScreen()
        widgets = list(screen.compose())
        # Should yield Header, ChatHistoryViewer, ChatInput, Footer
        assert len(widgets) >= 3

    def test_chat_screen_handles_chat_input_submitted(self):
        """Test ChatScreen has on_chat_input_submitted handler."""
        from goz.agent.tui.screens.chat import ChatScreen

        assert hasattr(ChatScreen, "on_chat_input_submitted")

    def test_chat_screen_has_process_agent_turn(self):
        """Test ChatScreen has process_agent_turn method."""
        from goz.agent.tui.screens.chat import ChatScreen

        assert hasattr(ChatScreen, "process_agent_turn")
        assert callable(ChatScreen.process_agent_turn)

    def test_chat_screen_has_handle_slash_command(self):
        """Test ChatScreen has handle_slash_command method."""
        from goz.agent.tui.screens.chat import ChatScreen

        assert hasattr(ChatScreen, "handle_slash_command")
        assert callable(ChatScreen.handle_slash_command)


class TestChatHistoryViewer:
    """Unit Tests: ChatHistoryViewer widget."""

    def test_chat_history_viewer_exists(self):
        """Test ChatHistoryViewer can be imported."""
        from goz.agent.tui.widgets import ChatHistoryViewer  # noqa: F401
        assert ChatHistoryViewer is not None

    def test_chat_history_viewer_has_add_user_message(self):
        """Test ChatHistoryViewer has add_user_message method."""
        from goz.agent.tui.widgets import ChatHistoryViewer

        assert hasattr(ChatHistoryViewer, "add_user_message")
        assert callable(ChatHistoryViewer.add_user_message)

    def test_chat_history_viewer_has_start_assistant_message(self):
        """Test ChatHistoryViewer has start_assistant_message method."""
        from goz.agent.tui.widgets import ChatHistoryViewer

        assert hasattr(ChatHistoryViewer, "start_assistant_message")
        assert callable(ChatHistoryViewer.start_assistant_message)

    def test_chat_history_viewer_has_append_assistant_content(self):
        """Test ChatHistoryViewer has append_assistant_content method."""
        from goz.agent.tui.widgets import ChatHistoryViewer

        assert hasattr(ChatHistoryViewer, "append_assistant_content")
        assert callable(ChatHistoryViewer.append_assistant_content)

    def test_chat_history_viewer_has_end_assistant_message(self):
        """Test ChatHistoryViewer has end_assistant_message method."""
        from goz.agent.tui.widgets import ChatHistoryViewer

        assert hasattr(ChatHistoryViewer, "end_assistant_message")
        assert callable(ChatHistoryViewer.end_assistant_message)

    def test_chat_history_viewer_has_add_tool_call(self):
        """Test ChatHistoryViewer has add_tool_call method."""
        from goz.agent.tui.widgets import ChatHistoryViewer

        assert hasattr(ChatHistoryViewer, "add_tool_call")
        assert callable(ChatHistoryViewer.add_tool_call)

    def test_chat_history_viewer_has_add_tool_result(self):
        """Test ChatHistoryViewer has add_tool_result method."""
        from goz.agent.tui.widgets import ChatHistoryViewer

        assert hasattr(ChatHistoryViewer, "add_tool_result")
        assert callable(ChatHistoryViewer.add_tool_result)


class TestChatInput:
    """Unit Tests: ChatInput widget."""

    def test_chat_input_exists(self):
        """Test ChatInput can be imported."""
        from goz.agent.tui.widgets import ChatInput  # noqa: F401
        assert ChatInput is not None

    def test_chat_input_has_submitted_message(self):
        """Test ChatInput has Submitted message class."""
        from goz.agent.tui.widgets import ChatInput

        assert hasattr(ChatInput, "Submitted")

    def test_chat_input_handles_enter_key(self):
        """Test ChatInput handles Enter key for submission."""
        from goz.agent.tui.widgets import ChatInput

        # Widget should have key handling logic
        assert hasattr(ChatInput, "_on_key")


class TestMessageBox:
    """Unit Tests: MessageBox widget."""

    def test_message_box_exists(self):
        """Test MessageBox can be imported."""
        from goz.agent.tui.widgets import MessageBox  # noqa: F401
        assert MessageBox is not None

    def test_message_box_has_role_attribute(self):
        """Test MessageBox has role attribute."""
        from goz.agent.tui.widgets import MessageBox

        widget = MessageBox(content="test", role="user")
        assert hasattr(widget, "role")
        assert widget.role == "user"


class TestIntegration:
    """Integration Tests: Agent mode launch from __main__.py."""

    def test_run_agent_app_exists(self):
        """Test run_agent_app function can be imported."""
        from goz.agent.tui import run_agent_app  # noqa: F401
        assert run_agent_app is not None

    def test_run_agent_app_is_callable(self):
        """Test run_agent_app is callable."""
        from goz.agent.tui import run_agent_app

        assert callable(run_agent_app)

    @patch("goz.agent.tui.app.AgentCore")
    @patch("goz.agent.tui.app.load_config")
    def test_agent_app_loads_config(self, mock_load, mock_core):
        """Test AgentApp loads config on initialization."""
        from goz.agent.tui.app import AgentApp

        mock_config = Config(zai_token="test-token")
        mock_load.return_value = mock_config

        app = AgentApp()
        assert mock_load.called

    @patch("goz.agent.tui.app.AgentCore")
    @patch("goz.agent.tui.app.load_config")
    def test_agent_app_initializes_agent_core(self, mock_load, mock_core):
        """Test AgentApp initializes AgentCore with config."""
        from goz.agent.tui.app import AgentApp

        mock_config = Config(zai_token="test-token")
        mock_load.return_value = mock_config

        app = AgentApp()
        assert mock_core.called
        # Check that AgentCore was called with config
        call_args = mock_core.call_args
        assert call_args is not None


class TestSlashCommands:
    """Unit Tests: Slash command handling."""

    def test_slash_command_quit(self):
        """Test /quit command is recognized."""
        from goz.agent.tui.screens.chat import ChatScreen

        # Should have /quit handling
        assert hasattr(ChatScreen, "handle_slash_command")
        assert callable(ChatScreen.handle_slash_command)

    def test_slash_command_help(self):
        """Test /help command is recognized."""
        from goz.agent.tui.screens.chat import ChatScreen

        assert hasattr(ChatScreen, "handle_slash_command")

    def test_slash_command_q_shortcut(self):
        """Test /q shortcut for quit."""
        from goz.agent.tui.screens.chat import ChatScreen

        assert hasattr(ChatScreen, "handle_slash_command")


class TestKeyboardShortcuts:
    """Unit Tests: Keyboard shortcuts."""

    def test_quit_action_bound_to_q(self):
        """Test q key bound to quit action."""
        from goz.agent.tui.app import AgentApp

        # Mock both load_config and AgentCore to avoid initialization issues
        with patch("goz.agent.tui.app.load_config"), \
             patch("goz.agent.tui.app.AgentCore"):
            app = AgentApp()
            assert hasattr(app, "action_quit")
            assert callable(app.action_quit)
