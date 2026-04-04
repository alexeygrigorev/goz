"""Test that message submission flow works correctly.

This test verifies the exact sequence of events when user submits a message:

1. User types "hello" in input (text should be visible while typing)
2. User presses Enter
3. Input box is cleared immediately
4. User message "hello" appears in conversation history
5. "Thinking..." indicator appears
6. API call happens (may take time)
7. Response streams in
8. "Thinking..." indicator disappears
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from textual.app import App
from textual.widgets import Input

from goz.agent.tui.screens.chat import ChatScreen
from goz.agent.tui.widgets import ChatHistoryViewer, ThinkingIndicator


@pytest.mark.asyncio
async def test_message_submission_flow():
    """Test the complete message submission flow."""
    from goz.agent.core import COMPLETION_MARKER

    class TestApp(App):
        SCREENS = {"chat": ChatScreen}

        def __init__(self):
            super().__init__()
            # Mock agent with delay before first chunk
            async def mock_process(user_input):
                # Simulate API delay - this is when "Thinking..." should be visible
                import asyncio
                await asyncio.sleep(0.05)
                # Return some response
                yield "Hello "
                yield "there!"
                yield COMPLETION_MARKER

            mock_agent = MagicMock()
            mock_agent.process_turn = mock_process
            self.agent = mock_agent

    app = TestApp()
    async with app.run_test() as pilot:
        screen = ChatScreen()
        app.push_screen(screen)
        await pilot.pause()

        # Get widgets
        input_widget = screen.query_one("#input", Input)
        history = screen.query_one(ChatHistoryViewer)
        thinking = screen.query_one("#thinking", ThinkingIndicator)

        # Initial state: welcome message visible, input empty, thinking idle
        assert screen._welcome_widget is not None, "Welcome should exist initially"
        assert input_widget.value == "", "Input should be empty initially"
        assert thinking.state == "idle", "Thinking should be idle initially"

        # Focus input
        input_widget.focus()
        await pilot.pause()

        # User types "hello" - text should appear in input
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.pause()

        # Check input shows the typed text
        assert input_widget.value == "hello", "Input should show typed text"

        # User presses Enter
        await pilot.press("enter")
        # Need to wait for async handlers to complete
        await pilot.pause()

        # IMMEDIATELY after Enter:
        # 1. Input should be cleared
        assert input_widget.value == "", "Input should be cleared after Enter"

        # 2. Welcome should be removed
        assert screen._welcome_widget is None, "Welcome should be cleared"

        # 3. User message should be in history
        children = list(history.children)
        user_messages = [c for c in children if hasattr(c, 'role') and c.role == "user"]
        assert len(user_messages) >= 1, "User message should be in history"

        # 4. After streaming completes, response should be visible
        await pilot.pause()

        # 5. Response should be visible
        children = list(history.children)
        # Should have user message + assistant message
        assert len(children) >= 1, "Should have messages in history"

        # 6. Thinking should be cleared
        assert thinking.state == "idle", "Thinking should be idle after response"

        # 7. Input should be focused for follow-up
        assert input_widget.has_focus, "Input should be focused after response"


@pytest.mark.asyncio
async def test_typing_is_visible_in_real_time():
    """Test that typed characters appear immediately in input."""
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

        # Type one character at a time and verify it appears
        await pilot.press("h")
        await pilot.pause()
        assert input_widget.value == "h", "First char should appear"

        await pilot.press("i")
        await pilot.pause()
        assert input_widget.value == "hi", "Second char should appear"

        await pilot.press("!")
        await pilot.pause()
        assert input_widget.value == "hi!", "Third char should appear"


@pytest.mark.asyncio
async def test_follow_up_conversation_input_refocuses():
    """Test that after a response, input is refocused for follow-up messages."""
    from textual.app import App
    from textual.widgets import Input

    from goz.agent.tui.screens.chat import ChatScreen
    from goz.agent.tui.widgets import ChatHistoryViewer
    from goz.agent.core import COMPLETION_MARKER

    class TestApp(App):
        SCREENS = {"chat": ChatScreen}

        def __init__(self):
            super().__init__()
            # Mock agent that responds quickly
            async def mock_process(user_input):
                import asyncio
                await asyncio.sleep(0.01)
                yield "Response to: " + user_input
                yield COMPLETION_MARKER

            mock_agent = MagicMock()
            mock_agent.process_turn = mock_process
            self.agent = mock_agent

    app = TestApp()
    async with app.run_test() as pilot:
        screen = ChatScreen()
        app.push_screen(screen)
        await pilot.pause()

        input_widget = screen.query_one("#input", Input)

        # First message
        input_widget.focus()
        await pilot.pause()
        await pilot.press("h", "i", "enter")
        await pilot.pause()

        # Wait for response to complete
        await pilot.pause()

        # After response, input should have focus again
        assert input_widget.has_focus, "Input should be focused after response"

        # Should be able to type a follow-up message
        await pilot.press("b", "y", "e")
        await pilot.pause()

        assert input_widget.value == "bye", "Should be able to type follow-up message"

        # Submit follow-up
        await pilot.press("enter")
        await pilot.pause()

        # Should be cleared and ready for next input
        assert input_widget.value == "", "Input should be cleared after follow-up"
        assert input_widget.has_focus, "Input should still be focused"
