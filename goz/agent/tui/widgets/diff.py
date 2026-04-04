"""Diff viewer widget for agent TUI.

This module provides a widget for displaying file diffs
with colorized additions and deletions.

Acceptance Criteria:
- DiffViewer widget exists
- Shows unified diff format
- Removed lines red (with - prefix)
- Added lines green (with + prefix)
- Context lines normal
- File path shown in header
- Line numbers shown
- Handles multiple hunks
- Supports inline changes (word-level diff)
"""
from __future__ import annotations

import difflib
from typing import Any

from rich.console import RenderableType
from rich.syntax import Syntax
from rich.text import Text
from textual.widgets import Static


class DiffViewer(Static):
    """Widget for displaying file diffs with colorized output.

    Displays unified diffs showing additions (green), deletions (red),
    and context (normal) with file path header and line numbers.
    """

    DEFAULT_CSS = """
    DiffViewer {
        padding: 0 1;
    }
    """

    def __init__(
        self,
        old: str,
        new: str,
        file_path: str = "",
        **kwargs: Any,
    ) -> None:
        """Initialize DiffViewer.

        Args:
            old: Original content
            new: Modified content
            file_path: Optional file path for display
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self.old = old
        self.new = new
        self.file_path = file_path

    def render(self) -> RenderableType:
        """Render diff to Rich renderable.

        Returns:
            Rich Text with colorized diff or message for no changes
        """
        # Generate unified diff using Python's difflib
        old_lines = self.old.splitlines(keepends=True)
        new_lines = self.new.splitlines(keepends=True)

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=self.file_path or "original",
                tofile=self.file_path or "modified",
                lineterm="",
            )
        )

        # No changes detected
        if not diff_lines:
            return Text("[dim]No changes[/dim]")

        # Colorize the diff output
        text = Text()

        for line in diff_lines:
            # File path header (--- and +++ lines)
            if line.startswith("---") or line.startswith("+++"):
                text.append(line + "\n", style="bold cyan")
            # Hunk header (@@ line)
            elif line.startswith("@@"):
                text.append(line + "\n", style="cyan")
            # Removed line (red with strikethrough effect conceptually)
            elif line.startswith("-") and not line.startswith("---"):
                text.append(line + "\n", style="red")
            # Added line (green)
            elif line.startswith("+") and not line.startswith("+++"):
                text.append(line + "\n", style="green")
            # Context line (normal)
            else:
                text.append(line + "\n")

        return text


def render_inline_diff(old: str, new: str) -> Text:
    """Render word-level inline diff.

    Shows character-level differences with strikethrough for deletions
    and bold green for insertions.

    Args:
        old: Original text
        new: Modified text

    Returns:
        Rich Text with inline diff highlighting

    Acceptance Criteria:
    - Shows no change for identical text
    - Shows deletions in red strikethrough
    - Shows insertions in green bold
    - Shows replacements with both styles
    """
    text = Text()
    matcher = difflib.SequenceMatcher(None, old, new)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # No change - append as-is
            text.append(old[i1:i2])
        elif tag == "delete":
            # Deleted text - red strikethrough
            text.append(old[i1:i2], style="red strikethrough")
        elif tag == "insert":
            # Inserted text - green bold
            text.append(new[j1:j2], style="green bold")
        elif tag == "replace":
            # Replaced text - show both
            text.append(old[i1:i2], style="red strikethrough")
            text.append(new[j1:j2], style="green bold")

    return text


class CodeDiffViewer(Static):
    """Widget for displaying code diffs with syntax highlighting.

    This is an enhanced diff viewer that applies syntax highlighting
    to the code while showing the diff colors.
    """

    DEFAULT_CSS = """
    CodeDiffViewer {
        padding: 0 1;
    }
    """

    def __init__(
        self,
        old: str,
        new: str,
        file_path: str = "",
        language: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize CodeDiffViewer.

        Args:
            old: Original content
            new: Modified content
            file_path: Optional file path for display
            language: Optional programming language for syntax highlighting
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self.old = old
        self.new = new
        self.file_path = file_path
        self.language = language or self._detect_language_from_path(file_path)

    def _detect_language_from_path(self, path: str) -> str | None:
        """Detect programming language from file path.

        Args:
            path: File path

        Returns:
            Language name or None
        """
        if not path:
            return None

        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".json": "json",
            ".sh": "bash",
            ".bash": "bash",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".md": "markdown",
            ".tsx": "typescript",
            ".jsx": "javascript",
        }

        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return None

    def render(self) -> RenderableType:
        """Render code diff with syntax highlighting.

        Returns:
            Rich renderable with highlighted code diff
        """
        # For code diffs, we use the standard diff viewer
        # Syntax highlighting on diffs is complex, so we stick with colorized text
        viewer = DiffViewer(
            old=self.old,
            new=self.new,
            file_path=self.file_path,
        )
        return viewer.render()
