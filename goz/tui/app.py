"""Main TUI application for goz using Textual.

This module provides the main GozApp class that orchestrates all screens
and navigation for the goz TUI.
"""
from __future__ import annotations

from pathlib import Path

from textual.app import App

from goz.tui.screens.main import MainMenuScreen
from goz.tui.screens.vision import VisionScreen
from goz.tui.screens.search import SearchScreen
from goz.tui.screens.read import ReadScreen
from goz.tui.screens.doctor import DoctorScreen
from goz.tui.screens.result import ResultScreen
from goz.config import load_config


class GozApp(App[None]):
    """Main goz TUI application.

    This is the entry point for the Textual TUI. It manages the screen stack
    and provides navigation between different command screens.

    Screens are registered for string-based routing.
    """

    CSS = """
    Screen {
        background: $background;
    }
    """

    TITLE = "goz - Z.AI Tools"
    SUB_TITLE = "Interactive Terminal UI"

    # Register screens for string-based routing
    SCREENS = {
        "main": MainMenuScreen,
        "vision": VisionScreen,
        "search": SearchScreen,
        "read": ReadScreen,
        "doctor": DoctorScreen,
        "result": ResultScreen,
    }

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize GozApp.

        Args:
            config_path: Optional path to config file for testing
        """
        super().__init__()
        self.config_path = config_path

        # Load configuration (will prompt if needed)
        try:
            self.config = load_config()
        except Exception:
            # Will be handled by Doctor screen
            self.config = None

    def on_mount(self) -> None:
        """Mount the main screen when app starts."""
        self.push_screen("main")

    def action_show_vision(self) -> None:
        """Navigate to Vision screen."""
        self.push_screen("vision")

    def action_show_search(self) -> None:
        """Navigate to Search screen."""
        self.push_screen("search")

    def action_show_read(self) -> None:
        """Navigate to Read screen."""
        self.push_screen("read")

    def action_show_doctor(self) -> None:
        """Navigate to Doctor screen."""
        self.push_screen("doctor")

    def action_show_result(
        self,
        title: str,
        content: str,
    ) -> None:
        """Show a result screen.

        Args:
            title: Title for the result screen
            content: Content to display
        """
        self.push_screen(ResultScreen(title=title, content=content))

    def action_go_back(self) -> None:
        """Go back to the previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
        else:
            self.exit()


def run_tui() -> None:
    """Run the TUI application."""
    app = GozApp()
    app.run()
