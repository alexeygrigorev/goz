"""Result screen for displaying output."""
from __future__ import annotations


from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Horizontal
from textual.widgets import TextArea


class ResultScreen(Screen[None]):
    """Screen for displaying results from API calls."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("q", "app.pop_screen", "Back"),
    ]

    CSS = """
    ResultScreen {
        layout: vertical;
    }

    .header {
        height: 3;
        dock: top;
    }

    .title {
        text-style: bold;
        content-align: center middle;
    }

    .content {
        height: 1fr;
    }

    TextArea {
        width: 1fr;
        height: 1fr;
        border: none;
        background: $background;
    }

    .footer {
        height: 3;
        dock: bottom;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, title: str = "", content: str = "") -> None:
        """Initialize ResultScreen.

        Args:
            title: Title for the result screen
            content: Content to display
        """
        super().__init__()
        self.title = title or "Result"
        self.content = content or "No content to display."

    def compose(self) -> None:
        """Compose the result screen UI."""
        yield Static(self.title, classes="title")

        text_area = TextArea(self.content, id="result-content")
        text_area.read_only = True
        yield text_area

        with Horizontal(classes="footer"):
            yield Button("Back [Esc]", variant="default", id="back-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.app.pop_screen()

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        self.app.pop_screen()
