"""Markdown viewer widget for agent TUI.

This module provides a widget for rendering markdown content
with syntax highlighting for code blocks.

Acceptance Criteria:
- MarkdownViewer widget exists
- Renders GitHub-flavored markdown
- Supports headers (h1-h6), code blocks, inline code
- Supports bold, italic, strikethrough, lists, links
- Detects language from ``` fences
- Syntax highlighting for Python, JS, JSON, Bash, Markdown, YAML
"""
from __future__ import annotations

import re
from typing import Any

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from textual.widgets import Static


# Pattern to detect code blocks with language: ```lang
CODE_BLOCK_PATTERN = re.compile(r"```(\w+)?\n(.*?)\n```", re.DOTALL)


class MarkdownViewer(Static):
    """Widget for rendering markdown content with syntax highlighting.

    This widget displays markdown-formatted text using Rich's Markdown renderer,
    with enhanced syntax highlighting for code blocks.
    """

    DEFAULT_CSS = """
    MarkdownViewer {
        padding: 0 1;
    }
    """

    def __init__(self, markdown_text: str = "", **kwargs: Any) -> None:
        """Initialize MarkdownViewer.

        Args:
            markdown_text: The markdown content to render
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self._markdown_text = markdown_text

    @property
    def markdown_text(self) -> str:
        """Get the current markdown text."""
        return self._markdown_text

    @markdown_text.setter
    def markdown_text(self, value: str) -> None:
        """Set the markdown text and refresh the display."""
        self._markdown_text = value
        self.refresh()

    def update_content(self, content: str) -> None:
        """Update the markdown content.

        Args:
            content: New markdown content to display
        """
        self._markdown_text = content
        self.refresh()

    def render(self) -> RenderableType:
        """Render markdown to Rich renderable.

        Returns:
            Rich renderable (Markdown object or Text)
        """
        if not self._markdown_text:
            return Text()

        # Use Rich's built-in Markdown which handles:
        # - Headers (h1-h6)
        # - Bold, italic, strikethrough
        # - Lists (ordered, unordered)
        # - Links
        # - Blockquotes
        # - Tables
        # - Code blocks (basic)
        return Markdown(self._markdown_text)


def render_code_block(language: str | None, code: str) -> Syntax:
    """Render a code block with syntax highlighting.

    Args:
        language: Programming language (python, javascript, etc.)
        code: The code content to highlight

    Returns:
        Rich Syntax object with highlighted code

    Acceptance Criteria:
    - Python syntax highlighting
    - JavaScript/TypeScript syntax highlighting
    - JSON syntax highlighting
    - Bash syntax highlighting
    - Markdown syntax highlighting
    - YAML syntax highlighting
    - Falls back to plain text for unknown languages
    """
    # Normalize language name
    lang_map = {
        "js": "javascript",
        "ts": "typescript",
        "yml": "yaml",
        "md": "markdown",
        "sh": "bash",
        "shell": "bash",
    }
    lang = lang_map.get(language or "", language or "text")

    # Try to create syntax with detected language
    try:
        return Syntax(
            code,
            lang,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
            background_color="default",
        )
    except Exception:
        # Fallback to plain text if language not supported
        return Syntax(
            code,
            "text",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
            background_color="default",
        )


def detect_language_from_fence(fence: str) -> str | None:
    """Detect programming language from markdown fence.

    Args:
        fence: The content after ``` (e.g., "python", "js", "")

    Returns:
        Normalized language name or None

    Acceptance Criteria:
    - Detects python, py
    - Detects javascript, js, ts, typescript
    - Detects json
    - Detects bash, sh, shell
    - Detects yaml, yml
    - Detects markdown, md
    - Returns None for empty/no language
    """
    if not fence:
        return None

    fence = fence.strip().lower()
    lang_map = {
        "python": "python",
        "py": "python",
        "javascript": "javascript",
        "js": "javascript",
        "typescript": "typescript",
        "ts": "typescript",
        "json": "json",
        "bash": "bash",
        "sh": "bash",
        "shell": "bash",
        "yaml": "yaml",
        "yml": "yaml",
        "markdown": "markdown",
        "md": "markdown",
    }
    return lang_map.get(fence, fence)
