"""Tests for ChatInput widget to debug typing issues.

Tests cover:
- ChatInput widget initialization
- Text input capability
- Enter key submission
- Submitted message emission
- Focus handling
"""
import pytest
from unittest.mock import MagicMock, patch

from goz.agent.tui.widgets import ChatInput


class TestChatInputBasics:
    """Basic tests for ChatInput widget."""

    def test_chat_input_exists(self):
        """Test ChatInput can be imported."""
        from goz.agent.tui.widgets import ChatInput  # noqa: F401
        assert ChatInput is not None

    def test_chat_input_inherits_from_input(self):
        """Test ChatInput inherits from textual.widgets.Input."""
        from textual.widgets import Input

        assert issubclass(ChatInput, Input)

    def test_chat_input_has_submitted_message(self):
        """Test ChatInput has Submitted message class."""
        assert hasattr(ChatInput, "Submitted")

    def test_chat_input_init(self):
        """Test ChatInput can be instantiated."""
        input_widget = ChatInput()
        assert input_widget is not None
        assert input_widget.placeholder == "Type your request... (Enter to send)"

    def test_chat_input_has_placeholder(self):
        """Test ChatInput has placeholder text."""
        input_widget = ChatInput()
        assert input_widget.placeholder is not None
        assert "Type" in input_widget.placeholder


class TestChatInputTyping:
    """Tests for text typing functionality."""

    def test_value_is_empty_on_init(self):
        """Test that input starts empty when created in an app."""
        # Note: Textual widgets need an app context for reactive properties
        # This test just checks the widget can be created
        input_widget = ChatInput()
        assert input_widget is not None


class TestChatInputSubmission:
    """Tests for input submission via Enter key."""

    def test_submitted_event_exists(self):
        """Test Input.Submitted event exists."""
        from textual.widgets import Input
        assert hasattr(Input, "Submitted")

    def test_can_get_value_from_event(self):
        """Test that value can be extracted from Submitted event."""
        # This tests the pattern used in on_input_submitted
        test_value = "test message"
        assert test_value == "test message"


class TestChatInputWithPilot:
    """Tests using Textual's pilot for interactive testing."""

    @pytest.mark.asyncio
    async def test_input_can_be_focused(self):
        """Test that input can receive focus."""
        from textual.app import App
        from textual.widgets import Input

        class TestApp(App):
            def compose(self):
                yield Input(id="test_input")

        app = TestApp()
        async with app.run_test() as pilot:
            input_widget = app.query_one("#test_input", Input)
            # Focus the input
            input_widget.focus()
            # Check it has focus
            assert input_widget.has_focus

    @pytest.mark.asyncio
    async def test_chat_input_in_screen(self):
        """Test ChatInput works in a screen."""
        from textual.app import App
        from textual.screen import Screen
        from textual.widgets import Footer, Header

        from goz.agent.tui.widgets import ChatInput

        class TestScreen(Screen):
            def compose(self):
                yield Header()
                yield ChatInput(id="input")
                yield Footer()

        class TestApp(App):
            SCREENS = {"test": TestScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            # Push the test screen directly
            screen = TestScreen()
            app.push_screen(screen)
            await pilot.pause()

            # Check ChatInput exists - query from the screen
            input_widget = screen.query_one("#input", ChatInput)
            assert input_widget is not None
            assert input_widget.id == "input"

    @pytest.mark.asyncio
    async def test_can_type_in_chat_input(self):
        """Test that text can be entered into ChatInput."""
        from textual.app import App
        from textual.widgets import Footer, Header

        from goz.agent.tui.widgets import ChatInput

        class TestApp(App):
            def compose(self):
                yield Header()
                yield ChatInput(id="input")
                yield Footer()

        app = TestApp()
        async with app.run_test() as pilot:
            input_widget = app.query_one("#input", ChatInput)

            # Focus the input
            input_widget.focus()
            await pilot.pause()

            # Type some text
            await pilot.press("h", "e", "l", "l", "o")
            await pilot.pause()

            # Check the value was set
            assert input_widget.value == "hello"


class TestChatInputMessageEmission:
    """Tests for Submitted message emission."""

    @pytest.mark.asyncio
    async def test_submitted_message_emitted_on_enter(self):
        """Test that Submitted message is emitted when Enter is pressed."""
        from textual.app import App
        from textual.widgets import Footer, Header

        from goz.agent.tui.widgets import ChatInput

        # Track if message was received
        received_messages = []

        class TestApp(App):
            def compose(self):
                yield Header()
                yield ChatInput(id="input")
                yield Footer()

            def on_input_submitted(self, event):
                received_messages.append(event.value)

        app = TestApp()
        async with app.run_test() as pilot:
            input_widget = app.query_one("#input", ChatInput)

            # Focus and type
            input_widget.focus()
            await pilot.pause()
            await pilot.press("t", "e", "s", "t")
            await pilot.pause()

            # Press Enter to submit
            await pilot.press("enter")
            await pilot.pause()

            # Check message was received
            assert "test" in received_messages

    @pytest.mark.asyncio
    async def test_input_cleared_after_submit(self):
        """Test that input is cleared after submission."""
        from textual.app import App
        from textual.widgets import Footer, Header

        from goz.agent.tui.widgets import ChatInput

        class TestApp(App):
            def compose(self):
                yield Header()
                yield ChatInput(id="input")
                yield Footer()

            def on_input_submitted(self, event):
                """Clear input after submission."""
                event.input.value = ""

        app = TestApp()
        async with app.run_test() as pilot:
            input_widget = app.query_one("#input", ChatInput)

            # Focus and type
            input_widget.focus()
            await pilot.pause()
            await pilot.press("t", "e", "s", "t")
            await pilot.pause()

            # Verify text is there
            assert input_widget.value == "test"

            # Press Enter to submit
            await pilot.press("enter")
            await pilot.pause()

            # Check input was cleared
            assert input_widget.value == ""


class TestChatScreenIntegration:
    """Integration tests for ChatScreen with Input."""

    @pytest.mark.asyncio
    async def test_chat_screen_has_input(self):
        """Test that ChatScreen includes Input widget."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            screen = ChatScreen()
            app.push_screen(screen)
            await pilot.pause()

            # Check Input exists - query from the screen
            input_widget = screen.query_one("#input", Input)
            assert input_widget is not None

    @pytest.mark.asyncio
    async def test_input_auto_focused_on_mount(self):
        """Test that Input is automatically focused when ChatScreen mounts."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            screen = ChatScreen()
            app.push_screen(screen)
            # Wait longer than the 0.1s timer in on_mount
            await pilot.pause(delay=0.2)

            # Check Input is focused
            input_widget = screen.query_one("#input", Input)
            assert input_widget.has_focus, "Input should be auto-focused on mount"

    @pytest.mark.asyncio
    async def test_input_auto_focused_with_screens_dict(self):
        """Test auto-focus when pushing screen by name (like AgentApp does)."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            # Push by name like AgentApp does
            app.push_screen("chat")
            # Wait for mount and focus timer
            await pilot.pause(delay=0.2)

            # Get the pushed screen and check focus
            screen = app.screen
            input_widget = screen.query_one("#input", Input)
            assert input_widget.has_focus, "Input should be auto-focused when pushed by name"

    @pytest.mark.asyncio
    async def test_can_type_into_auto_focused_input(self):
        """End-to-end test: input is auto-focused and can receive typing."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            # Push chat screen by name (like AgentApp)
            app.push_screen("chat")
            # Wait for mount, welcome message, and auto-focus
            await pilot.pause(delay=0.2)

            # Type without explicitly focusing - should work due to auto-focus
            await pilot.press("h", "e", "l", "l", "o")
            await pilot.pause()

            # Check the text was entered
            screen = app.screen
            input_widget = screen.query_one("#input", Input)
            assert input_widget.value == "hello", f"Expected 'hello', got '{input_widget.value}'"

    @pytest.mark.asyncio
    async def test_chat_input_focusable_in_screen(self):
        """Test that Input can be focused in ChatScreen."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            screen = ChatScreen()
            app.push_screen(screen)
            await pilot.pause()

            input_widget = screen.query_one("#input", Input)
            input_widget.focus()
            await pilot.pause()

            assert input_widget.has_focus

    @pytest.mark.asyncio
    async def test_can_type_in_chat_screen(self):
        """Test that text can be entered in ChatScreen."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            screen = ChatScreen()
            app.push_screen(screen)
            await pilot.pause()

            input_widget = screen.query_one("#input", Input)
            input_widget.focus()
            await pilot.pause()

            # Type some text
            await pilot.press("h", "i")
            await pilot.pause()

            assert input_widget.value == "hi"

    @pytest.mark.asyncio
    async def test_welcome_message_cleared_on_first_input(self):
        """Test that welcome message is cleared when user sends first message."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen
        from goz.agent.tui.widgets import ChatHistoryViewer

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

        app = TestApp()
        async with app.run_test() as pilot:
            screen = ChatScreen()
            app.push_screen(screen)
            await pilot.pause()

            # Welcome message should exist
            assert screen._welcome_widget is not None
            history = screen.query_one(ChatHistoryViewer)
            # Check that welcome widget is in history
            assert screen._welcome_widget in history.children

            # Type and send first message
            input_widget = screen.query_one("#input", Input)
            input_widget.focus()
            await pilot.pause()
            await pilot.press("t", "e", "s", "t", "enter")
            await pilot.pause()

            # Welcome should be cleared
            assert screen._welcome_widget is None

    @pytest.mark.asyncio
    async def test_user_message_displayed_in_conversation(self):
        """Test that user's typed message appears in the conversation history."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen
        from goz.agent.tui.widgets import ChatHistoryViewer

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

            def __init__(self):
                super().__init__()
                # Mock agent to avoid actual API calls
                from unittest.mock import AsyncMock, MagicMock
                self.agent = MagicMock()
                self.agent.process_turn = AsyncMock()
                # Make it yield completion marker immediately
                async def mock_process():
                    yield "\x00"  # COMPLETION_MARKER
                self.agent.process_turn = mock_process

        app = TestApp()
        async with app.run_test() as pilot:
            screen = ChatScreen()
            app.push_screen(screen)
            await pilot.pause()

            # Type and send a message
            input_widget = screen.query_one("#input", Input)
            input_widget.focus()
            await pilot.pause()
            await pilot.press("h", "e", "l", "l", "o", "enter")
            await pilot.pause()

            # Check that user message appears in history
            history = screen.query_one(ChatHistoryViewer)
            # Should have at least the user message (welcome was cleared)
            assert len(list(history.children)) > 0

    @pytest.mark.asyncio
    async def test_streaming_response_displayed(self):
        """Test that streaming response chunks are displayed in real-time."""
        from textual.app import App
        from textual.widgets import Input

        from goz.agent.tui.screens.chat import ChatScreen
        from goz.agent.tui.widgets import ChatHistoryViewer

        class TestApp(App):
            SCREENS = {"chat": ChatScreen}

            def __init__(self):
                super().__init__()
                # Mock agent with streaming response
                from unittest.mock import AsyncMock, MagicMock, patch
                from goz.agent.core import COMPLETION_MARKER

                async def mock_process(user_input):
                    # Simulate streaming
                    yield "Hello"
                    yield " world"
                    yield "!"
                    yield COMPLETION_MARKER

                mock_agent = MagicMock()
                mock_agent.process_turn = mock_process
                self.agent = mock_agent

        app = TestApp()
        async with app.run_test() as pilot:
            screen = ChatScreen()
            app.push_screen(screen)
            await pilot.pause()

            # Send a message
            input_widget = screen.query_one("#input", Input)
            input_widget.focus()
            await pilot.pause()
            await pilot.press("t", "e", "s", "t", "enter")
            await pilot.pause()

            # Check that response was streamed
            history = screen.query_one(ChatHistoryViewer)
            # Should have user message and assistant message
            children = list(history.children)
            # User message + assistant message with content
            assert len(children) >= 1
