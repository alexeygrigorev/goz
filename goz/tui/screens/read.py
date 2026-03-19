"""Read screen for fetching and displaying web pages.

This module provides an interactive read screen with URL validation,
content display in markdown or text format, and error handling.
"""
from __future__ import annotations

import asyncio
from typing import Any, Literal

from textual.screen import Screen
from textual.widgets import (
    Input, Label, Select, Button, Static, Header, Footer, Checkbox
)
from textual.containers import Vertical, Horizontal, Container

from goz.api.reader import ReaderClient
from goz.api.errors import (
    ValidationError, AuthError, ApiError,
    NetworkError, TimeoutError
)
from goz.tui.widgets.loading import LoadingSpinner
from goz.tui.widgets.errors import ErrorDisplay


# Format options
FORMAT_OPTIONS = [
    ("markdown", "Markdown format"),
    ("text", "Plain text"),
]

# Default timeout in seconds
DEFAULT_TIMEOUT = 20

# Maximum timeout in seconds
MAX_TIMEOUT = 120


class ReadScreen(Screen[None]):
    """Screen for reading web pages with various options.

    Features:
    - URL input with validation
    - Format selection (markdown/text)
    - Optional image toggles and timeout
    - Loading indicator with countdown
    - Error handling with retry option
    - Content display with scroll
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("enter", "submit_fetch", "Fetch"),
        ("ctrl+r", "retry_fetch", "Retry"),
    ]

    CSS = """
    ReadScreen {
        layout: vertical;
    }

    .header-container {
        height: 3;
        dock: top;
    }

    .main-container {
        height: 1fr;
        padding: 1 2;
    }

    .read-form {
        width: 80;
        border: thick $primary;
        padding: 2;
        margin: 0 auto;
    }

    .title {
        text-align: center;
        text-style: bold;
        margin: 0 0 1 0;
        content-align: center middle;
    }

    .loading-container {
        height: 3;
        content-align: center middle;
    }

    .preview-container {
        height: 1fr;
        margin: 1 0 0 0;
        display: none;
    }

    .preview-container.-visible {
        display: block;
    }

    .preview-header {
        text-style: bold;
        margin: 0 0 1 0;
    }

    .preview-meta {
        text-style: dim;
        margin: 0 0 1 0;
    }

    .preview-content {
        height: 1fr;
        border: thick $panel;
        padding: 1;
        overflow-y: auto;
    }

    .options-group {
        margin: 1 0;
    }

    Label {
        text-style: bold;
        margin: 1 0 0 0;
    }

    Input, Select {
        width: 1fr;
        margin: 0 0 1 0;
    }

    .checkbox-container {
        height: 3;
        align: left middle;
        margin: 0 0 1 0;
    }

    Checkbox {
        margin: 0 2 0 0;
    }

    .button-container {
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    .hint {
        text-style: dim italic;
        margin: 0 0 1 0;
        height: 1;
    }

    .footer-hint {
        text-style: dim italic;
        content-align: center middle;
        margin: 1 0 0 0;
    }

    .error-section {
        margin: 1 0 0 0;
    }

    .timeout-value {
        text-style: bold $accent;
    }
    """

    def __init__(self, initial_url: str = "") -> None:
        """Initialize ReadScreen.

        Args:
            initial_url: Optional URL to pre-populate the input
        """
        super().__init__()
        self.url = initial_url
        self.format: Literal["markdown", "text"] = "markdown"
        self.timeout = DEFAULT_TIMEOUT
        self.retain_images = True
        self.with_links_summary = False
        self.is_fetching = False
        self._countdown_task: asyncio.Task[None] | None = None

    def compose(self) -> None:
        """Compose the read screen UI."""
        yield Header()

        with Container(classes="main-container"):
            yield Static("Read Web Page", classes="title")

            with Vertical(classes="read-form"):
                yield Label("URL:")
                url_input = Input(
                    placeholder="https://example.com",
                    id="url-input",
                    value=self.url
                )
                if not self.url:
                    url_input.focus()
                yield url_input
                yield Static("Must start with http:// or https://", classes="hint")

                yield Label("Format:")
                yield Select(
                    [(label, value) for value, label in FORMAT_OPTIONS],
                    value="markdown",
                    id="format-select",
                )

                with Horizontal(classes="checkbox-container"):
                    yield Checkbox(
                        "Retain images",
                        value=True,
                        id="retain-images-checkbox"
                    )
                    yield Checkbox(
                        "Include links summary",
                        value=False,
                        id="links-summary-checkbox"
                    )

                yield Label("Timeout (seconds):")
                yield Input(
                    placeholder=str(DEFAULT_TIMEOUT),
                    value=str(DEFAULT_TIMEOUT),
                    id="timeout-input",
                    type="integer"
                )
                yield Static(
                    f"Default: {DEFAULT_TIMEOUT}s, Max: {MAX_TIMEOUT}s",
                    classes="hint"
                )

                with Horizontal(classes="button-container"):
                    yield Button("Fetch", variant="primary", id="submit-btn")
                    yield Button("Cancel", variant="default", id="cancel-btn")

            # Loading indicator (hidden initially)
            yield LoadingSpinner("Fetching...", id="loading-spinner", classes="loading-container")

            # Preview section (hidden initially)
            with Vertical(id="preview-section", classes="preview-container"):
                yield Static(id="preview-header", classes="preview-header")
                yield Static(id="preview-meta", classes="preview-meta")
                yield Static(id="preview-content", classes="preview-content")
                yield Static("[Esc] Back  [Arrow Keys/Page Up/Down] Scroll", classes="footer-hint")

            # Error display (hidden initially)
            with Vertical(id="error-section", classes="error-section"):
                pass

        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        # Hide preview section initially
        preview_section = self.query_one("#preview-section", Vertical)
        preview_section.display = False

        # Hide loading initially
        loading = self.query_one("#loading-spinner", LoadingSpinner)
        loading.display = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "submit-btn":
            self.action_submit_fetch()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    async def action_submit_fetch(self) -> None:
        """Submit the fetch request."""
        if self.is_fetching:
            return

        # Get input values
        url_input = self.query_one("#url-input", Input)
        format_select = self.query_one("#format-select", Select)
        timeout_input = self.query_one("#timeout-input", Input)
        retain_images_cb = self.query_one("#retain-images-checkbox", Checkbox)
        links_summary_cb = self.query_one("#links-summary-checkbox", Checkbox)

        self.url = url_input.value.strip()
        self.format = format_select.value or "markdown"  # type: ignore
        timeout_str = timeout_input.value.strip()
        self.timeout = int(timeout_str) if timeout_str else DEFAULT_TIMEOUT
        self.retain_images = retain_images_cb.value
        self.with_links_summary = links_summary_cb.value

        # Validate URL
        if not self.url:
            self.show_error("Please enter a URL")
            return

        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            self.show_error(
                "URL must start with http:// or https://",
                help_text="Example: https://example.com"
            )
            return

        # Validate timeout
        if self.timeout <= 0 or self.timeout > MAX_TIMEOUT:
            self.show_error(
                f"Timeout must be between 1 and {MAX_TIMEOUT} seconds",
                help_text=f"Current value: {self.timeout}"
            )
            return

        # Clear previous errors
        self.clear_error()

        # Start fetching
        self.is_fetching = True
        self._show_loading(True)
        self._hide_preview()

        try:
            # Make API call
            client = ReaderClient()
            result = await client.read(
                url=self.url,
                format=self.format,
                timeout=self.timeout,
                retain_images=self.retain_images,
                with_links_summary=self.with_links_summary,
            )

            # Display content
            self._display_content(result)

        except ValidationError as e:
            self.show_error(f"Invalid input: {e}")
        except AuthError as e:
            self.show_error(
                "Authentication failed. Check your API key.",
                help_text=e.message
            )
        except NetworkError as e:
            self.show_error(f"Network error: {e.message}", retry=True)
        except TimeoutError:
            self.show_error(
                f"Request timed out after {self.timeout} seconds",
                help_text="Try increasing the timeout or check your connection",
                retry=True
            )
        except ApiError as e:
            self.show_error(f"API Error: {e.message}", retry=True)
        except Exception as e:
            self.show_error(f"Unexpected error: {e}", retry=True)
        finally:
            self.is_fetching = False
            self._stop_countdown()
            self._show_loading(False)

    def action_retry_fetch(self) -> None:
        """Retry the last fetch."""
        if self.url:
            self.action_submit_fetch()

    def _display_content(self, result: Any) -> None:
        """Display the fetched content.

        Args:
            result: ReaderResult from the API
        """
        preview_section = self.query_one("#preview-section", Vertical)
        preview_header = self.query_one("#preview-header", Static)
        preview_meta = self.query_one("#preview-meta", Static)
        preview_content = self.query_one("#preview-content", Static)

        # Set header
        preview_header.update(f"Reading: {result.title}")

        # Set metadata
        meta_lines = [f"URL: {result.url}"]
        if result.description:
            meta_lines.append(f"Description: {result.description}")
        meta_lines.append(f"Format: {self.format}")
        preview_meta.update("\n".join(meta_lines))

        # Set content
        # Add title at the top of content
        content = f"# {result.title}\n\n{result.content}"
        preview_content.update(content)

        # Show preview section
        preview_section.display = True

    def _show_loading(self, show: bool) -> None:
        """Show or hide the loading indicator.

        Args:
            show: Whether to show the loading indicator
        """
        loading = self.query_one("#loading-spinner", LoadingSpinner)
        loading.display = show
        if show:
            loading.start(f"Fetching... (timeout: {self.timeout}s)")
            self._start_countdown()
        else:
            loading.stop()

    def _start_countdown(self) -> None:
        """Start countdown timer for timeout."""
        async def countdown() -> None:
            for remaining in range(self.timeout, 0, -1):
                if not self.is_fetching:
                    break
                loading = self.query_one("#loading-spinner", LoadingSpinner)
                loading.text = f"Fetching... ({remaining}s remaining)"
                await asyncio.sleep(1)

        self._countdown_task = asyncio.create_task(countdown())

    def _stop_countdown(self) -> None:
        """Stop the countdown timer."""
        if self._countdown_task and not self._countdown_task.done():
            self._countdown_task.cancel()
            self._countdown_task = None

    def _hide_preview(self) -> None:
        """Hide the preview section."""
        preview_section = self.query_one("#preview-section", Vertical)
        preview_section.display = False

    def show_error(
        self,
        message: str,
        help_text: str | None = None,
        retry: bool = False
    ) -> None:
        """Show an error message.

        Args:
            message: Error message to display
            help_text: Optional help text
            retry: Whether to show a retry button
        """
        # Clear previous error
        self.clear_error()

        # Add new error display
        error_section = self.query_one("#error-section", Vertical)

        def on_retry() -> None:
            self.clear_error()
            self.action_submit_fetch()

        def on_close() -> None:
            self.clear_error()

        error_display = ErrorDisplay(
            message=message,
            help_text=help_text,
            show_retry=retry,
            show_close=True,
            on_retry=on_retry if retry else None,
            on_close=on_close,
        )
        error_section.mount(error_display)

    def clear_error(self) -> None:
        """Clear any displayed error messages."""
        error_section = self.query_one("#error-section", Vertical)
        for child in error_section.children:
            child.remove()
