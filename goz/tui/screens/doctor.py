"""Doctor screen for checking API connection."""
from __future__ import annotations

from typing import Any

from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal

from goz.config import DEFAULT_CONFIG_FILE, load_config

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class DoctorScreen(Screen[None]):
    """Screen for checking API connection and configuration."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    CSS = """
    DoctorScreen {
        align: center middle;
    }

    .title {
        text-align: center;
        text-style: bold;
        margin: 1 0;
    }

    .results {
        width: 80;
        border: thick $primary;
        padding: 2;
    }

    .check-item {
        margin: 1 0;
    }

    .pass {
        text-style: bold green;
    }

    .fail {
        text-style: bold red;
    }

    .check-name {
        text-style: bold;
    }

    .check-message {
        text-style: dim;
        margin: 0 0 0 2;
    }

    .summary {
        text-align: center;
        text-style: bold;
        margin: 2 0 0 0;
    }

    .summary-pass {
        text-style: bold green;
    }

    .summary-fail {
        text-style: bold red;
    }

    .button-container {
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self) -> None:
        """Initialize DoctorScreen."""
        super().__init__()
        self.checks: list[dict[str, Any]] = []

    def compose(self) -> None:
        """Compose the doctor screen UI."""
        yield Static("Doctor - Connection Check", classes="title")

        with Vertical(classes="results"):
            yield Static("Running checks...", id="status-text")

        yield Static("", id="summary")

        with Horizontal(classes="button-container"):
            yield Button("Back", variant="default", id="back-btn")

    def on_mount(self) -> None:
        """Run checks when screen is mounted."""
        self.run_checks()

    async def run_checks(self) -> None:
        """Run all diagnostic checks."""
        self.checks = []

        # Check 1: Config file exists
        config_file = DEFAULT_CONFIG_FILE
        if config_file.exists():
            self.add_check(True, "Config file", f"Found at {config_file}")
        else:
            self.add_check(False, "Config file", f"Not found at {config_file}. Run 'goz config' to set up.")

        # Check 2: API token present
        try:
            config = load_config()
            if config.zai_token:
                # Show only last 4 chars
                masked = f"****{config.zai_token[-4:]}" if len(config.zai_token) > 4 else "****"
                self.add_check(True, "API token", f"Present ({masked})")
            else:
                self.add_check(False, "API token", "Not set. Run 'goz config set zai_token <token>'")
        except Exception as e:
            self.add_check(False, "API token", f"Error loading config: {e}")

        # Check 3: Base URL reachable
        try:
            config = load_config()
            if HTTPX_AVAILABLE:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.get(config.zai_base_url)
                    # Any response means the URL is reachable
                    self.add_check(True, "Base URL", f"Reachable ({config.zai_base_url})")
            else:
                self.add_check(None, "Base URL", "Cannot test (httpx not available)")
        except (httpx.ConnectError, httpx.NetworkError) as e:
            self.add_check(False, "Base URL", f"Cannot connect: {e}")
        except Exception as e:
            self.add_check(None, "Base URL", f"Error checking: {e}")

        # Display results
        self.display_results()

    def add_check(self, passed: bool | None, name: str, message: str) -> None:
        """Add a check result.

        Args:
            passed: True if passed, False if failed, None if skip
            name: Check name
            message: Check message
        """
        self.checks.append({"passed": passed, "name": name, "message": message})

    def display_results(self) -> None:
        """Display all check results."""
        results_container = self.query_one(".results")
        summary_text = self.query_one("#summary")

        # Clear existing results
        results_container.remove_children()

        # Add each check
        for check in self.checks:
            passed = check["passed"]
            name = check["name"]
            message = check["message"]

            if passed is True:
                status = "[PASS]"
                status_class = "pass"
            elif passed is False:
                status = "[FAIL]"
                status_class = "fail"
            else:
                status = "[SKIP]"
                status_class = "dim"

            check_widget = Static(
                f"{status} {name}: {message}",
                classes=f"check-item {status_class}"
            )
            results_container.mount(check_widget)

        # Add summary
        passed_count = sum(1 for c in self.checks if c["passed"] is True)
        failed_count = sum(1 for c in self.checks if c["passed"] is False)

        if failed_count == 0:
            summary_text.update(f"All checks passed! ({passed_count}/{passed_count})")
            summary_text.remove_class("summary-fail")
            summary_text.add_class("summary-pass")
        else:
            summary_text.update(f"Some checks failed: {failed_count} failed, {passed_count} passed")
            summary_text.remove_class("summary-pass")
            summary_text.add_class("summary-fail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.app.pop_screen()
