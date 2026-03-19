"""Loading spinner widget for async operations.

This module provides a loading indicator widget that displays
a spinner animation during async operations.
"""
from __future__ import annotations

import asyncio
from typing import Any

from textual.widget import Widget
from textual.reactive import reactive
from textual import log


class LoadingSpinner(Widget):
    """A loading spinner widget with animated text.

    Displays a spinning animation with customizable text message.
    Useful for showing loading states during async operations.

    Attributes:
        text: The text to display next to the spinner
        is_loading: Whether the spinner is currently animating
    """

    DEFAULT_CSS = """
    LoadingSpinner {
        height: 1;
        width: auto;
        content-align: center middle;
    }

    LoadingSpinner.-loading {
        text-style: bold;
    }
    """

    # Frames for spinner animation
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    text: reactive[str] = reactive("Loading...")
    is_loading: reactive[bool] = reactive(False)
    _frame_index: int = 0
    _task: asyncio.Task[None] | None = None

    def __init__(self, text: str = "Loading...", **kwargs: Any) -> None:
        """Initialize LoadingSpinner.

        Args:
            text: The text to display next to the spinner
            **kwargs: Additional arguments for Widget
        """
        super().__init__(**kwargs)
        self.text = text

    def on_mount(self) -> None:
        """Called when widget is mounted to the app."""
        self._frame_index = 0

    def start(self, text: str | None = None) -> None:
        """Start the spinner animation.

        Args:
            text: Optional new text to display
        """
        if text is not None:
            self.text = text
        self.is_loading = True
        self._frame_index = 0

        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._animate())

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.is_loading = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None

    async def _animate(self) -> None:
        """Run the spinner animation loop."""
        while self.is_loading:
            self._frame_index = (self._frame_index + 1) % len(self.SPINNER_FRAMES)
            self.refresh()
            await asyncio.sleep(0.1)

    def render(self) -> str:
        """Render the spinner widget.

        Returns:
            The rendered string with spinner frame and text
        """
        if self.is_loading:
            frame = self.SPINNER_FRAMES[self._frame_index]
            return f"[bold]{frame}[/bold] {self.text}"
        return ""

    async def __aenter__(self) -> None:
        """Async context manager entry."""
        self.start()

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        self.stop()
