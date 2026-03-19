"""Vision screen for analyzing images and videos."""
from __future__ import annotations

import time

from textual.screen import Screen
from textual.widgets import Input, Label, Select, Button, Static, TextArea
from textual.containers import Vertical, Horizontal

from goz.api.vision import VisionClient
from goz.api.image import (
    validate_image_source,
    validate_video_source,
)
from goz.api.errors import (
    ValidationError,
    AuthError,
    ApiError,
    NetworkError,
    TimeoutError as ZaiTimeoutError,
)


# Vision mode options - all 8 presets
VISION_MODES = [
    ("analyze", "General image description"),
    ("ui-to-code", "Convert UI to code"),
    ("extract-text", "Extract text from image"),
    ("diagnose-error", "Analyze error screenshot"),
    ("diagram", "Explain technical diagram"),
    ("chart", "Analyze data visualization"),
    ("diff", "Compare two UI screenshots"),
    ("video", "Analyze video content"),
]

# Default prompts for each mode
MODE_PROMPTS = {
    "analyze": "Describe this image in detail.",
    "ui-to-code": "Convert this UI to production-ready code.",
    "extract-text": "Extract all text from this image.",
    "diagnose-error": "Diagnose this error and suggest fixes.",
    "diagram": "Explain this technical diagram.",
    "chart": "Analyze this data visualization.",
    "diff": "Compare these two UI screenshots and identify differences.",
    "video": "Analyze this video content.",
}

# Output types for ui-to-code
OUTPUT_TYPES = [
    ("code", "Code output"),
    ("prompt", "Enhanced prompt"),
    ("spec", "Specification"),
    ("description", "Description only"),
]

# Diagram types
DIAGRAM_TYPES = [
    ("", "Auto-detect"),
    ("flowchart", "Flowchart"),
    ("sequence", "Sequence diagram"),
    ("architecture", "Architecture diagram"),
    ("entity-relationship", "ER diagram"),
    ("class", "Class diagram"),
    ("network", "Network diagram"),
    ("state", "State machine"),
]

# Chart focus options
CHART_FOCUS_OPTIONS = [
    ("", "General analysis"),
    ("trends", "Trends and patterns"),
    ("anomalies", "Anomalies and outliers"),
    ("comparisons", "Data comparisons"),
    ("insights", "Key insights"),
]


class VisionScreen(Screen[None]):
    """Screen for vision/image/video analysis input with all presets."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("enter", "submit", "Analyze"),
        ("f1", "toggle_help", "Help"),
    ]

    CSS = """
    VisionScreen {
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

    .subtitle {
        text-style: dim;
        content-align: center middle;
        height: 1;
    }

    .main {
        height: 1fr;
        align: center middle;
    }

    .form {
        width: 90;
        height: 1fr;
        border: thick $primary;
        padding: 2;
        scroll: true;
    }

    .form-row {
        height: auto;
    }

    Label {
        text-style: bold;
        margin: 1 0 0 0;
    }

    Input, Select {
        width: 1fr;
        margin: 0 0 1 0;
    }

    TextArea {
        width: 1fr;
        height: 4;
        margin: 0 0 1 0;
        border: solid $primary;
    }

    .button-container {
        height: 3;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    .error {
        text-style: bold red;
        margin: 1 0;
    }

    .hint {
        text-style: dim italic;
        margin: 0 0 1 0;
    }

    .options-panel {
        margin: 1 0;
        padding: 1;
        border: solid $accent;
    }

    .status-bar {
        height: 3;
        dock: bottom;
    }

    .status-text {
        content-align: center middle;
        text-style: dim;
    }

    .hidden {
        display: none;
    }

    .help-text {
        text-style: dim italic;
        margin: 2 0 0 0;
    }
    """

    def __init__(self) -> None:
        """Initialize VisionScreen."""
        super().__init__()
        self.mode = "analyze"
        self.loading = False
        self._help_visible = False

    def compose(self) -> None:
        """Compose the vision input UI."""
        yield Static("Vision Analysis", classes="title")

        with Vertical(classes="main"):
            with Vertical(classes="form"):
                # Mode selection
                yield Label("Preset:")
                yield Select(
                    [(label, value) for value, label in VISION_MODES],
                    value="analyze",
                    id="mode-select",
                )
                yield Static("", id="mode-description", classes="hint")

                # File input - changes based on mode
                yield Label("Source:")
                with Vertical(classes="form-row"):
                    yield Input(
                        placeholder="/path/to/image.png or https://...",
                        id="source1-input",
                    )
                    yield Static("Local file path or URL", id="source1-hint", classes="hint")

                # Second source for diff mode (hidden by default)
                with Vertical(classes="form-row hidden", id="source2-row"):
                    yield Label("Actual Image (for diff):")
                    yield Input(
                        placeholder="/path/to/actual.png",
                        id="source2-input",
                    )
                    yield Static("Path to the actual/current screenshot", classes="hint")

                # Prompt textarea
                yield Label("Prompt:")
                yield TextArea(
                    MODE_PROMPTS["analyze"],
                    id="prompt-input",
                )
                yield Static("Leave empty to use default prompt for selected preset", classes="hint")

                # Options panel - shows/hides based on mode
                with Vertical(classes="options-panel", id="options-panel"):
                    # ui-to-code output type (hidden by default)
                    with Vertical(classes="form-row hidden", id="output-type-row"):
                        yield Label("Output Type:")
                        yield Select(
                            [(label, value) for value, label in OUTPUT_TYPES],
                            value="code",
                            id="output-type-select",
                        )

                    # extract-text language hint (hidden by default)
                    with Vertical(classes="form-row hidden", id="language-row"):
                        yield Label("Programming Language (optional):")
                        yield Input(
                            placeholder="e.g., python, javascript, rust",
                            id="language-input",
                        )

                    # diagnose-error context (hidden by default)
                    with Vertical(classes="form-row hidden", id="context-row"):
                        yield Label("Error Context (optional):")
                        yield Input(
                            placeholder='e.g., "during npm install" or "while running tests"',
                            id="context-input",
                        )

                    # diagram type (hidden by default)
                    with Vertical(classes="form-row hidden", id="diagram-type-row"):
                        yield Label("Diagram Type:")
                        yield Select(
                            [(label, value) for value, label in DIAGRAM_TYPES],
                            value="",
                            id="diagram-type-select",
                        )

                    # chart focus (hidden by default)
                    with Vertical(classes="form-row hidden", id="chart-focus-row"):
                        yield Label("Analysis Focus:")
                        yield Select(
                            [(label, value) for value, label in CHART_FOCUS_OPTIONS],
                            value="",
                            id="chart-focus-select",
                        )

                # Buttons
                with Horizontal(classes="button-container"):
                    yield Button("Analyze [Enter]", variant="primary", id="submit-btn")
                    yield Button("Cancel [Esc]", variant="default", id="cancel-btn")

        # Status bar
        with Horizontal(classes="status-bar"):
            yield Static("F1: Help | Enter: Submit | Esc: Back", classes="status-text", id="status-bar")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle preset selection change."""
        if event.select.id == "mode-select":
            self._on_mode_changed(event.value)

    def _on_mode_changed(self, mode: str) -> None:
        """Update UI based on selected mode.

        Args:
            mode: The selected vision mode
        """
        self.mode = mode or "analyze"

        # Update prompt with default for mode
        prompt_area = self.query_one("#prompt-input", TextArea)
        prompt_area.text = MODE_PROMPTS.get(self.mode, "")

        # Update mode description
        mode_desc = self.query_one("#mode-description", Static)
        mode_descriptions = {
            "analyze": "Describe any image in detail",
            "ui-to-code": "Convert a UI design into code",
            "extract-text": "OCR for code, terminals, and documents",
            "diagnose-error": "Get explanations and fixes for errors",
            "diagram": "Understand technical diagrams",
            "chart": "Analyze data visualizations",
            "diff": "Compare two screenshots",
            "video": "Analyze video content",
        }
        mode_desc.update(mode_descriptions.get(self.mode, ""))

        # Update source label and hint
        source1_label = self.query_one("Label", Static)
        source1_label.update("Source:" if self.mode == "video" else "Image Path:")
        source1_hint = self.query_one("#source1-hint", Static)
        if self.mode == "video":
            source1_hint.update("Local video file or URL (MP4/MOV/M4V)")
        elif self.mode == "diff":
            source1_hint.update("Path to expected/baseline image")
        else:
            source1_hint.update("Local file path or URL to image")

        # Show/hide second source for diff mode
        source2_row = self.query_one("#source2-row", Vertical)
        if self.mode == "diff":
            source2_row.remove_class("hidden")
        else:
            source2_row.add_class("hidden")

        # Show/hide options based on mode
        output_type_row = self.query_one("#output-type-row", Vertical)
        language_row = self.query_one("#language-row", Vertical)
        context_row = self.query_one("#context-row", Vertical)
        diagram_type_row = self.query_one("#diagram-type-row", Vertical)
        chart_focus_row = self.query_one("#chart-focus-row", Vertical)

        # Hide all first
        output_type_row.add_class("hidden")
        language_row.add_class("hidden")
        context_row.add_class("hidden")
        diagram_type_row.add_class("hidden")
        chart_focus_row.add_class("hidden")

        # Show relevant options
        if self.mode == "ui-to-code":
            output_type_row.remove_class("hidden")
        elif self.mode == "extract-text":
            language_row.remove_class("hidden")
        elif self.mode == "diagnose-error":
            context_row.remove_class("hidden")
        elif self.mode == "diagram":
            diagram_type_row.remove_class("hidden")
        elif self.mode == "chart":
            chart_focus_row.remove_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "submit-btn":
            self.action_submit()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()

    def action_toggle_help(self) -> None:
        """Toggle help overlay."""
        self._help_visible = not self._help_visible
        if self._help_visible:
            self._show_help_overlay()
        else:
            self._remove_help_overlay()

    def _show_help_overlay(self) -> None:
        """Show help overlay with keyboard shortcuts."""
        help_text = """
Vision Analysis Help

Presets:
  analyze      - General image description
  ui-to-code   - Convert UI screenshot to code
  extract-text - OCR for code, terminals, documents
  diagnose-error - Analyze errors and suggest fixes
  diagram      - Explain technical diagrams
  chart        - Analyze data visualizations
  diff         - Compare two screenshots
  video        - Analyze video content

Keyboard Shortcuts:
  Enter  - Submit request
  Esc    - Cancel/go back
  F1     - Toggle this help

Constraints:
  Images: 5MB max (JPG, PNG, JPEG)
  Videos: 8MB max (MP4, MOV, M4V)
  URLs supported for video sources

Press F1 or Esc to close
        """
        self.app.push_screen(
            Static(help_text, id="help-overlay"),
            callback=self._remove_help_overlay,
        )

    def _remove_help_overlay(self) -> None:
        """Remove help overlay."""
        self._help_visible = False

    async def action_submit(self) -> None:
        """Submit the vision analysis request."""
        if self.loading:
            return

        # Get input values
        source1_input = self.query_one("#source1-input", Input)
        prompt_area = self.query_one("#prompt-input", TextArea)

        source1 = source1_input.value.strip()
        prompt = prompt_area.text.strip()

        # Validate source
        if not source1:
            self.show_error("Please enter a source path or URL")
            return

        # For diff mode, need second source
        source2 = ""
        if self.mode == "diff":
            source2_input = self.query_one("#source2-input", Input)
            source2 = source2_input.value.strip()
            if not source2:
                self.show_error("Please enter the actual image path for diff")
                return

        # Get mode-specific options
        output_type = "code"
        language = ""
        context = ""
        diagram_type = ""
        chart_focus = ""

        if self.mode == "ui-to-code":
            output_type_select = self.query_one("#output-type-select", Select)
            output_type = output_type_select.value or "code"
        elif self.mode == "extract-text":
            language_input = self.query_one("#language-input", Input)
            language = language_input.value.strip()
        elif self.mode == "diagnose-error":
            context_input = self.query_one("#context-input", Input)
            context = context_input.value.strip()
        elif self.mode == "diagram":
            diagram_type_select = self.query_one("#diagram-type-select", Select)
            diagram_type = diagram_type_select.value or ""
        elif self.mode == "chart":
            chart_focus_select = self.query_one("#chart-focus-select", Select)
            chart_focus = chart_focus_select.value or ""

        # Use default prompt if empty
        effective_prompt = prompt or MODE_PROMPTS.get(self.mode, "")

        # Show loading state
        self.loading = True
        submit_btn = self.query_one("#submit-btn", Button)
        status_bar = self.query_one("#status-bar", Static)

        submit_btn.disabled = True
        original_label = submit_btn.label
        submit_btn.label = "Processing..."

        original_status = status_bar.renderable
        status_bar.update("Processing... (Esc to cancel)")

        start_time = time.time()

        try:
            client = VisionClient()
            result = ""

            # Route to appropriate API method based on mode
            if self.mode == "analyze":
                validate_image_source(source1)
                result = await client.analyze(source1, effective_prompt)

            elif self.mode == "ui-to-code":
                validate_image_source(source1)
                # Enhance prompt with output type
                enhanced_prompt = effective_prompt
                if output_type == "prompt":
                    enhanced_prompt = (
                        f"{effective_prompt}\n\n"
                        f"Provide a detailed prompt that would generate this UI, "
                        f"including layout, components, styling, and functionality."
                    )
                elif output_type == "spec":
                    enhanced_prompt = (
                        f"{effective_prompt}\n\n"
                        f"Provide a technical specification including components, "
                        f"props, state management, and styling approach."
                    )
                elif output_type == "description":
                    enhanced_prompt = (
                        f"{effective_prompt}\n\n"
                        f"Provide a detailed description of the UI layout, "
                        f"components, colors, and interactions without generating code."
                    )
                result = await client.analyze(source1, enhanced_prompt)

            elif self.mode == "extract-text":
                validate_image_source(source1)
                enhanced_prompt = effective_prompt
                if language:
                    enhanced_prompt = (
                        f"{effective_prompt}\n\n"
                        f"The content is in {language}. Preserve code syntax and formatting."
                    )
                result = await client.analyze(source1, enhanced_prompt)

            elif self.mode == "diagnose-error":
                validate_image_source(source1)
                enhanced_prompt = effective_prompt
                if context:
                    enhanced_prompt = (
                        f"{effective_prompt}\n\n"
                        f"Context: {context}\n\n"
                        f"Consider this context when diagnosing the error."
                    )
                result = await client.analyze(source1, enhanced_prompt)

            elif self.mode == "diagram":
                validate_image_source(source1)
                enhanced_prompt = effective_prompt
                if diagram_type:
                    enhanced_prompt = (
                        f"{effective_prompt}\n\n"
                        f"This is a {diagram_type} diagram. Use appropriate terminology."
                    )
                result = await client.analyze(source1, enhanced_prompt)

            elif self.mode == "chart":
                validate_image_source(source1)
                enhanced_prompt = effective_prompt
                if chart_focus:
                    focus_prompts = {
                        "trends": "Focus on identifying trends and patterns over time.",
                        "anomalies": "Focus on identifying anomalies, outliers, and unusual data points.",
                        "comparisons": "Focus on comparing different data series and values.",
                        "insights": "Focus on extracting key insights and actionable conclusions.",
                    }
                    enhanced_prompt = f"{effective_prompt}\n\n{focus_prompts.get(chart_focus, '')}"
                result = await client.analyze(source1, enhanced_prompt)

            elif self.mode == "diff":
                validate_image_source(source1)
                validate_image_source(source2)
                # For diff, we need to compare two images
                # Build a prompt that asks for comparison
                # First analyze expected
                result1 = await client.analyze(source1, "Describe this image in detail.")
                # Then analyze actual
                result2 = await client.analyze(source2, "Describe this image in detail.")
                # Combine with comparison prompt
                result = (
                    f"Expected Image:\n{result1}\n\n"
                    f"Actual Image:\n{result2}\n\n"
                    f"Note: Use the vision diff command for precise visual comparison."
                )

            elif self.mode == "video":
                validate_video_source(source1)
                result = await client.analyze(source1, effective_prompt)

            # Calculate processing time
            time.time() - start_time

            # Show results
            from goz.tui.screens.result import ResultScreen
            self.app.push_screen(ResultScreen(
                title=f"Vision Results - {self.mode}",
                content=result,
            ))

        except ValidationError as e:
            self.show_error(f"Invalid input: {e}")
        except AuthError as e:
            self.show_error(f"Authentication Error: {e.message}\n{e.help}")
        except ApiError as e:
            self.show_error(f"API Error: {e.message}")
        except NetworkError as e:
            self.show_error(f"Network Error: {e.message}\n{e.help}")
        except ZaiTimeoutError as e:
            self.show_error(f"Request timed out. {e.help}")
        except FileNotFoundError as e:
            self.show_error(f"File not found: {e}")
        except ValueError as e:
            self.show_error(str(e))
        except Exception as e:
            self.show_error(f"Error: {e}")
        finally:
            self.loading = False
            submit_btn.disabled = False
            submit_btn.label = original_label
            status_bar.update(original_status)

    def show_error(self, message: str) -> None:
        """Show an error message.

        Args:
            message: Error message to display
        """
        # Remove existing error if present
        existing = self.query(".error")
        if existing:
            existing.remove()

        # Add new error message
        form = self.query_one(".form")
        error = Static(message, classes="error")
        form.mount(error)
