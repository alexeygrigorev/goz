"""Thinking indicator widget for agent state visualization.

This module provides a widget for displaying animated indicators
when the agent is thinking, planning, executing tools, or in error states.

Acceptance Criteria (Issue 25):
1. ThinkingIndicator widget exists in goz/tui/widgets/thinking.py
2. Shows animated "Thinking..." text
3. Spinning character animation (|, /, -, \\)
4. Displays when agent is thinking
5. Hides when response starts
6. Shows tool name when executing tools
7. Different styles for different states
8. Red indicator for errors
9. Green indicator for successful completion
"""
from __future__ import annotations

from typing import Any

from textual.widgets import Static


class ThinkingIndicator(Static):
    """Animated indicator for agent thinking and processing states.

    This widget displays different animated messages based on the agent's
    current state: idle, thinking, planning, executing, error, or success.

    States:
        idle: Widget is hidden (default)
        thinking: Shows "Thinking..." with spinner
        planning: Shows "Planning actions..." with spinner
        executing: Shows "Running: <tool_name>" with spinner
        error: Shows "Error occurred" in red
        success: Shows success message in green

    Attributes:
        state: Current state (idle, thinking, planning, executing, error, success)
        tool_name: Name of the tool being executed (when state is 'executing')
        animation_frame: Current frame index for spinner animation
        SPINNER_FRAMES: List of spinner characters [| / - \\]
    """

    DEFAULT_CSS = """
    ThinkingIndicator {
        height: 1;
        width: auto;
        padding: 0 1;
    }

    ThinkingIndicator.thinking {
        text-style: dim;
    }

    ThinkingIndicator.planning {
        text-style: bold cyan;
    }

    ThinkingIndicator.executing {
        text-style: bold yellow;
    }

    ThinkingIndicator.error {
        text-style: bold red;
    }

    ThinkingIndicator.success {
        text-style: bold green;
    }
    """

    # Spinner animation frames
    SPINNER_FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize ThinkingIndicator.

        Args:
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self.state: str = "idle"
        self.tool_name: str | None = None
        self.animation_frame: int = 0

    def on_mount(self) -> None:
        """Called when widget is mounted to the app.

        Starts the animation timer.
        """
        self.animation_frame = 0
        # Use set_interval from textual.timer.Timer
        self.set_interval(0.1, self.animate)

    def animate(self) -> None:
        """Update animation frame and refresh display.

        Called every 0.1 seconds by the timer.
        """
        self.animation_frame = (self.animation_frame + 1) % len(self.SPINNER_FRAMES)
        self.update_content()

    def set_state(
        self,
        state: str,
        tool_name: str | None = None,
    ) -> None:
        """Set the current state and update display.

        Args:
            state: New state (idle, thinking, planning, executing, error, success)
            tool_name: Optional tool name for 'executing' state
        """
        self.state = state
        self.tool_name = tool_name

        # Widget is visible only when not idle
        self.visible = (state != "idle")

        # Add/remove CSS classes based on state
        self.remove_class("thinking", "planning", "executing", "error", "success")
        if state != "idle":
            self.add_class(state)

        self.update_content()

    def update_content(self) -> None:
        """Update display based on current state and animation frame.

        Updates the widget's rendered content with appropriate
        text and styling for the current state.
        """
        if self.state == "thinking":
            frame = self.SPINNER_FRAMES[self.animation_frame]
            self.update(f"[dim]{frame} Thinking...[/dim]")

        elif self.state == "planning":
            frame = self.SPINNER_FRAMES[self.animation_frame]
            self.update(f"[cyan]{frame} Planning actions...[/cyan]")

        elif self.state == "executing":
            frame = self.SPINNER_FRAMES[self.animation_frame]
            tool = self.tool_name or "tool"
            self.update(f"[yellow]{frame} Running: {tool}[/yellow]")

        elif self.state == "error":
            self.update("[red]Error occurred[/red]")

        elif self.state == "success":
            self.update("[green]Success[/green]")

        elif self.state == "idle":
            self.update("")

    def render(self) -> str:
        """Render the current widget content.

        Returns:
            The rendered content as a string, or empty string if idle
        """
        if self.state == "idle":
            return ""

        content = self._get_content_for_state()
        return content

    def _get_content_for_state(self) -> str:
        """Get the content string for the current state.

        Returns:
            Content string with appropriate styling
        """
        frame = self.SPINNER_FRAMES[self.animation_frame]

        if self.state == "thinking":
            return f"[dim]{frame} Thinking...[/dim]"
        elif self.state == "planning":
            return f"[cyan]{frame} Planning actions...[/cyan]"
        elif self.state == "executing":
            tool = self.tool_name or "tool"
            return f"[yellow]{frame} Running: {tool}[/yellow]"
        elif self.state == "error":
            return "[red]Error occurred[/red]"
        elif self.state == "success":
            return "[green]Success[/green]"

        return ""
