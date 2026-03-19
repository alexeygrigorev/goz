"""Main menu screen for goz TUI."""
from __future__ import annotations

from textual.screen import Screen
from textual.widgets import Button, Static
from textual.containers import Vertical, Center, Horizontal
from textual import on
from textual.app import App


class MenuButton(Button):
    """A button for menu items."""

    def __init__(self, label: str, description: str, key_hint: str, **kwargs: Any) -> None:
        """Initialize a menu button.

        Args:
            label: Button label
            description: Description text
            key_hint: Keyboard shortcut hint
            **kwargs: Additional arguments for Button
        """
        super().__init__(label, **kwargs)
        self.description = description
        self.key_hint = key_hint


class MainMenuScreen(Screen[None]):
    """Main menu screen with command options."""

    BINDINGS = [
        ("q", "app.quit", "Quit"),
        ("c", "app.quit", "Quit"),
        ("f1", "show_vision", "Vision"),
        ("f2", "show_search", "Search"),
        ("f3", "show_read", "Read"),
        ("f4", "show_doctor", "Doctor"),
        ("escape", "app.quit", "Quit"),
    ]

    CSS = """
    MainMenuScreen {
        align: center middle;
    }

    .title {
        text-align: center;
        text-style: bold;
        margin: 1 0;
    }

    .subtitle {
        text-align: center;
        text-style: dim;
        margin: 0 0 3 0;
    }

    MenuButton {
        width: 60;
        margin: 1 1;
    }

    MenuButton:hover {
        background: $primary;
    }

    .key-hint {
        text-style: bold;
        color: $accent;
    }

    .description {
        text-style: dim;
        margin: 0 2;
    }

    .help-text {
        text-align: center;
        text-style: dim italic;
        margin: 3 0 0 0;
    }

    .container {
        height: 100%;
    }
    """

    def compose(self) -> None:
        """Compose the main menu UI."""
        with Vertical(classes="container"):
            yield Static("goz - Z.AI Tools", classes="title")
            yield Static("Interactive Terminal UI", classes="subtitle")
            yield Static("")

            yield MenuButton("Vision", "Analyze images and screenshots", "[F1]")
            yield MenuButton("Search", "Search the web", "[F2]")
            yield MenuButton("Read", "Fetch and read web pages", "[F3]")
            yield MenuButton("Doctor", "Check API connection", "[F4]")

            yield Static("")
            yield Static("[F1-F4] Select Command  [q] Quit", classes="help-text")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        button = event.button
        if isinstance(button, MenuButton):
            label = button.label.lower()
            if "vision" in label:
                self.action_show_vision()
            elif "search" in label:
                self.action_show_search()
            elif "read" in label:
                self.action_show_read()
            elif "doctor" in label:
                self.action_show_doctor()

    def action_show_vision(self) -> None:
        """Navigate to Vision screen."""
        self.app.push_screen("vision")

    def action_show_search(self) -> None:
        """Navigate to Search screen."""
        self.app.push_screen("search")

    def action_show_read(self) -> None:
        """Navigate to Read screen."""
        self.app.push_screen("read")

    def action_show_doctor(self) -> None:
        """Navigate to Doctor screen."""
        self.app.push_screen("doctor")
