"""Agent TUI Widgets.

This module provides widgets for the agent TUI screens.

This package includes both:
- Chat widgets (ChatHistoryViewer, ChatInput, ThinkingIndicator, etc.) - Issue 23/26
- Markdown/Diff widgets (MarkdownViewer, DiffViewer) - Issue 24
"""
from __future__ import annotations

# Import markdown and diff widgets (Issue 24)
from goz.agent.tui.widgets.markdown import MarkdownViewer
from goz.agent.tui.widgets.diff import DiffViewer, CodeDiffViewer, render_inline_diff

# Import chat widgets (Issue 23/26)
from goz.agent.tui.widgets.chat import (
    ChatHistoryViewer,
    ChatInput,
    MessageBox,
    ToolCallBox,
    ToolResultBox,
    ThinkingIndicator,
)

__all__ = [
    # Chat widgets
    "ChatHistoryViewer",
    "ChatInput",
    "MessageBox",
    "ToolCallBox",
    "ToolResultBox",
    "ThinkingIndicator",
    # Markdown/Diff widgets
    "MarkdownViewer",
    "DiffViewer",
    "CodeDiffViewer",
    "render_inline_diff",
]
