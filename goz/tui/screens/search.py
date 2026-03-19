"""Search screen for web search.

This module provides an interactive search screen with filter options,
results display, and error handling.
"""
from __future__ import annotations

import asyncio
from typing import Any

from textual.screen import Screen
from textual.widgets import (
    Input, Label, Select, Button, Static, DataTable, Header, Footer
)
from textual.containers import Vertical, Horizontal, Container
from textual import on

from goz.api.search import SearchClient, SearchResult
from goz.api.errors import (
    ZaiError, ValidationError, AuthError, ApiError,
    NetworkError, TimeoutError
)
from goz.tui.widgets.loading import LoadingSpinner
from goz.tui.widgets.errors import ErrorDisplay


# Recency filter options matching API specification
RECENCY_OPTIONS = [
    ("noLimit", "All time"),
    ("oneDay", "Past 24 hours"),
    ("oneWeek", "Past week"),
    ("oneMonth", "Past month"),
    ("oneYear", "Past year"),
]

# Maximum query length
MAX_QUERY_LENGTH = 500


class SearchScreen(Screen[None]):
    """Screen for web search with filters and results display.

    Features:
    - Query input with validation
    - Domain, recency, and count filters
    - Scrollable results table
    - Loading indicator with spinner
    - Error handling with retry option
    - Keyboard navigation
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("enter", "submit_search", "Search"),
        ("ctrl+r", "retry_search", "Retry"),
        ("down", "cursor_down", "Down"),
        ("up", "cursor_up", "Up"),
        ("page_down", "page_down", "Page Down"),
        ("page_up", "page_up", "Page Up"),
    ]

    CSS = """
    SearchScreen {
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

    .search-form {
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

    .results-container {
        height: 1fr;
        margin: 1 0 0 0;
        display: none;
    }

    .results-container.-visible {
        display: block;
    }

    .results-header {
        text-style: bold;
        margin: 0 0 1 0;
    }

    DataTable {
        height: 1fr;
        border: thick $panel;
    }

    .no-results {
        text-style: dim italic;
        content-align: center middle;
        padding: 2;
    }

    Label {
        text-style: bold;
        margin: 1 0 0 0;
    }

    Input, Select {
        width: 1fr;
        margin: 0 0 1 0;
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
    """

    def __init__(self) -> None:
        """Initialize SearchScreen."""
        super().__init__()
        self.query = ""
        self.domain_filter: str | None = None
        self.recency_filter = "noLimit"
        self.count: int | None = None
        self.results: list[SearchResult] = []
        self.is_searching = False

    def compose(self) -> None:
        """Compose the search screen UI."""
        yield Header()

        with Container(classes="main-container"):
            yield Static("Web Search", classes="title")

            with Vertical(classes="search-form"):
                yield Label("Query:")
                query_input = Input(
                    placeholder="Enter search query",
                    id="query-input",
                    max_length=MAX_QUERY_LENGTH
                )
                query_input.focus()
                yield query_input

                yield Label("Domain Filter (optional):")
                yield Input(placeholder="example.com", id="domain-input")
                yield Static("Filter results to specific domain", classes="hint")

                yield Label("Recency:")
                yield Select(
                    [(label, value) for value, label in RECENCY_OPTIONS],
                    value="noLimit",
                    id="recency-select",
                )

                yield Label("Count Limit (optional):")
                yield Input(placeholder="Leave empty for default", id="count-input", type="integer")

                with Horizontal(classes="button-container"):
                    yield Button("Search", variant="primary", id="submit-btn")
                    yield Button("Cancel", variant="default", id="cancel-btn")

            # Loading indicator (hidden initially)
            yield LoadingSpinner("Searching...", id="loading-spinner", classes="loading-container")

            # Results section (hidden initially)
            with Vertical(id="results-section", classes="results-container"):
                yield Static(id="results-header", classes="results-header")
                yield DataTable(id="results-table")
                yield Static("[Esc] Back  [Enter] View Details  [Arrow Keys] Navigate", classes="footer-hint")

            # Error display (hidden initially)
            with Vertical(id="error-section", classes="error-section"):
                pass

        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        # Hide results section initially
        results_section = self.query_one("#results-section", Vertical)
        results_section.display = False

        # Hide loading initially
        loading = self.query_one("#loading-spinner", LoadingSpinner)
        loading.display = False

        # Configure data table
        table = self.query_one("#results-table", DataTable)
        table.zebra_stripes = True
        table.cursor_type = "row"
        table.add_columns("Rank", "Title", "Source", "URL")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "submit-btn":
            self.action_submit_search()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in results table."""
        if not self.results:
            return

        table = event.data_table
        row_key = event.row_key

        # Get the row index from the key
        row_index = table.get_row_index(row_key)

        if row_index is not None and 0 <= row_index < len(self.results):
            result = self.results[row_index]

            # Show detail view for selected result
            from goz.tui.screens.result import ResultScreen

            # Format the result detail
            content = f"""# {result.title}

**URL:** {result.url}
"""
            if result.source:
                content += f"\n**Source:** {result.source}\n"
            if result.date:
                content += f"\n**Date:** {result.date}\n"

            content += f"\n## Summary\n\n{result.summary}\n"

            self.app.push_screen(ResultScreen(
                title=f"Result {result.rank}",
                content=content,
            ))

    async def action_submit_search(self) -> None:
        """Submit the search request."""
        if self.is_searching:
            return

        # Get input values
        query_input = self.query_one("#query-input", Input)
        domain_input = self.query_one("#domain-input", Input)
        recency_select = self.query_one("#recency-select", Select)
        count_input = self.query_one("#count-input", Input)

        self.query = query_input.value.strip()
        self.domain_filter = domain_input.value.strip() or None
        self.recency_filter = recency_select.value or "noLimit"
        count_str = count_input.value.strip()
        self.count = int(count_str) if count_str else None

        # Validate query
        if not self.query:
            self.show_error("Please enter a search query")
            return

        # Clear previous errors
        self.clear_error()

        # Start searching
        self.is_searching = True
        self._show_loading(True)
        self._hide_results()

        try:
            # Make API call
            client = SearchClient()
            self.results = await client.search(
                query=self.query,
                count=self.count,
                domain_filter=self.domain_filter,
                recency_filter=self.recency_filter,
            )

            # Display results
            self._display_results(self.results)

        except ValidationError as e:
            self.show_error(f"Invalid input: {e}")
        except AuthError as e:
            self.show_error(f"Authentication failed. Check your API key.\n\n{e.message}")
        except NetworkError as e:
            self.show_error(f"Network error: {e.message}", retry=True)
        except TimeoutError as e:
            self.show_error(f"Request timed out. Please try again.", retry=True)
        except ApiError as e:
            self.show_error(f"API Error: {e.message}", retry=True)
        except Exception as e:
            self.show_error(f"Unexpected error: {e}", retry=True)
        finally:
            self.is_searching = False
            self._show_loading(False)

    def action_retry_search(self) -> None:
        """Retry the last search."""
        if self.query:
            self.action_submit_search()

    def _display_results(self, results: list[SearchResult]) -> None:
        """Display search results in the table.

        Args:
            results: List of search results
        """
        results_section = self.query_one("#results-section", Vertical)
        results_header = self.query_one("#results-header", Static)
        table = self.query_one("#results-table", DataTable)

        # Clear previous results
        table.clear()

        if not results:
            results_header.update("No results found. Try different search terms or filters.")
            # Show empty state
            table.add_column("", width=100)
            table.add_row("No results found. Try different search terms or filters.")
        else:
            results_header.update(f"Found {len(results)} result{'' if len(results) == 1 else 's'}:")
            # Populate table
            for result in results:
                # Truncate title if too long
                title = result.title[:60] + "..." if len(result.title) > 60 else result.title
                # Truncate URL if too long
                url = result.url[:50] + "..." if len(result.url) > 50 else result.url
                # Get source or domain
                source = result.source or self._extract_domain(result.url)

                table.add_row(
                    str(result.rank),
                    title,
                    source or "N/A",
                    url,
                )
            # Focus the table
            table.focus()

        # Show results section
        results_section.display = True

    def _show_loading(self, show: bool) -> None:
        """Show or hide the loading indicator.

        Args:
            show: Whether to show the loading indicator
        """
        loading = self.query_one("#loading-spinner", LoadingSpinner)
        loading.display = show
        if show:
            loading.start("Searching...")
        else:
            loading.stop()

    def _hide_results(self) -> None:
        """Hide the results section."""
        results_section = self.query_one("#results-section", Vertical)
        results_section.display = False

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
            self.action_submit_search()

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

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url: The URL to extract domain from

        Returns:
            The domain name
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or ""
        except Exception:
            return ""
