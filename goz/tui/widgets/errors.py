"""Error display widget for showing error messages.

This module provides a widget for displaying error messages
with optional retry functionality.
"""
from __future__ import annotations

from typing import Any, Callable

from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Horizontal, Vertical


class ErrorDisplay(Widget):
    """A widget for displaying error messages with optional actions.

    Shows error messages in a visually distinct way with optional
    retry/close buttons for user interaction.

    Attributes:
        message: The error message to display
        show_retry: Whether to show a retry button
        show_close: Whether to show a close button
        on_retry: Optional callback for retry button
        on_close: Optional callback for close button
    """

    DEFAULT_CSS = """
    ErrorDisplay {
        height: auto;
        width: 1fr;
        padding: 1;
    }

    .error-container {
        width: 1fr;
        border: thick red;
        padding: 1 2;
        background: $panel;
    }

    .error-title {
        text-style: bold red;
        margin: 0 0 1 0;
    }

    .error-message {
        text-style: $text;
        margin: 0 0 1 0;
        width: 1fr;
    }

    .error-help {
        text-style: dim italic;
        margin: 0 0 1 0;
    }

    .error-buttons {
        height: 3;
        align: right middle;
    }

    Button {
        margin: 0 1;
    }

    Button.-retry {
        variant: primary;
    }

    Button.-close {
        variant: default;
    }
    """

    def __init__(
        self,
        message: str = "An error occurred",
        *,
        show_retry: bool = False,
        show_close: bool = True,
        help_text: str | None = None,
        on_retry: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ErrorDisplay.

        Args:
            message: The error message to display
            show_retry: Whether to show a retry button
            show_close: Whether to show a close button
            help_text: Optional help text to display below the error
            on_retry: Optional callback for retry button
            on_close: Optional callback for close button
            **kwargs: Additional arguments for Widget
        """
        super().__init__(**kwargs)
        self.message = message
        self.show_retry = show_retry
        self.show_close = show_close
        self.help_text = help_text
        self._on_retry = on_retry
        self._on_close = on_close

    def compose(self) -> None:
        """Compose the error display UI."""
        with Vertical(classes="error-container"):
            yield Static("Error", classes="error-title")
            yield Static(self.message, classes="error-message")
            if self.help_text:
                yield Static(self.help_text, classes="error-help")

            if self.show_retry or self.show_close:
                with Horizontal(classes="error-buttons"):
                    if self.show_retry:
                        yield Button("Retry", variant="primary", classes="-retry", id="retry-btn")
                    if self.show_close:
                        yield Button("Close", variant="default", classes="-close", id="close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "retry-btn" and self._on_retry:
            self._on_retry()
        elif event.button.id == "close-btn":
            if self._on_close:
                self._on_close()
            else:
                # Default behavior: remove self
                self.remove()

    def update_message(self, message: str, help_text: str | None = None) -> None:
        """Update the error message.

        Args:
            message: New error message
            help_text: Optional new help text
        """
        self.message = message
        if help_text is not None:
            self.help_text = help_text

        # Update the UI
        message_widget = self.query_one(".error-message", Static)
        message_widget.update(message)

        if help_text and self.help_text:
            help_widget = self.query(".error-help")
            if help_widget:
                help_widget[0].update(help_text)
