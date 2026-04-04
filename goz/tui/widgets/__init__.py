"""Shared widgets for goz TUI screens.

This module provides reusable UI components used across multiple screens.
"""
from __future__ import annotations

from goz.tui.widgets.loading import LoadingSpinner
from goz.tui.widgets.errors import ErrorDisplay
from goz.tui.widgets.thinking import ThinkingIndicator

__all__ = [
    "LoadingSpinner",
    "ErrorDisplay",
    "ThinkingIndicator",
]
