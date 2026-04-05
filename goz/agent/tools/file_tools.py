"""File operation tools for goz interactive coding agent.

This module provides tools for file operations including:
- ViewFileTool: View file contents with line numbers
- CreateFileTool: Create new files with content
- StrReplaceEditorTool: Replace text in existing files
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from goz.agent.tools.base import BaseTool, ToolExecutionError


class ViewFileTool(BaseTool):
    """Tool for viewing file contents with line numbers.

    Attributes:
        name: Tool identifier
        description: Human-readable description
        input_schema: JSON Schema for input validation
    """

    name = "view_file"
    description = (
        "View a file's contents with line numbers. "
        "Use this to read existing files and understand code structure. "
        "For large files, use line_range to focus on specific sections."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to view"
            },
            "line_range": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 2,
                "maxItems": 2,
                "description": "Optional [start, end] line range (1-indexed, inclusive)"
            }
        },
        "required": ["file_path"]
    }

    async def execute(
        self,
        file_path: str,
        line_range: list[int] | None = None,
    ) -> str:
        """View file contents.

        Args:
            file_path: Path to the file to view
            line_range: Optional [start, end] line range (1-indexed, inclusive)

        Returns:
            Formatted file contents with line numbers

        Raises:
            ToolExecutionError: If file not found or cannot be read
        """
        # Resolve path
        full_path = self._resolve_path(file_path)

        # Check if file exists
        if not full_path.exists():
            raise ToolExecutionError(f"File not found: {file_path}")

        # Check if it's a file (not directory)
        if not full_path.is_file():
            raise ToolExecutionError(f"Not a file: {file_path}")

        try:
            # Read file content
            content = full_path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            # Get total line count
            total_lines = len(lines)

            # Apply line range if specified
            if line_range is not None:
                start, end = line_range
                # Convert from 1-indexed to 0-indexed
                start_idx = max(0, start - 1)
                end_idx = min(total_lines, end)
                lines = lines[start_idx:end_idx]
                display_range = f" (lines {start}-{end_idx})"
            else:
                display_range = ""

            # Format output with line numbers
            result = self._format_output(full_path, lines, total_lines, display_range)
            return result

        except UnicodeDecodeError:
            raise ToolExecutionError(f"Binary file or encoding error: {file_path}")

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to working directory.

        Args:
            file_path: File path (relative or absolute)

        Returns:
            Resolved absolute Path
        """
        path = Path(file_path)

        # If relative, resolve against working_dir
        if not path.is_absolute():
            path = Path(self.working_dir) / path

        return path.resolve()

    def _format_output(
        self,
        file_path: Path,
        lines: list[str],
        total_lines: int,
        display_range: str = ""
    ) -> str:
        """Format file output with line numbers.

        Args:
            file_path: Path to the file
            lines: List of file lines
            total_lines: Total number of lines in file
            display_range: Optional range suffix for display

        Returns:
            Formatted output string
        """
        # Calculate line number width
        start_line = 1 if not display_range else int(display_range.split("-")[0].split()[1].rstrip(")"))
        width = len(str(total_lines))

        output = []
        output.append(f"File: {file_path}{display_range} ({total_lines} lines)")
        output.append("" + "=" * 60)
        output.append("")

        for i, line in enumerate(lines, start=start_line):
            line_num = f"{i:>{width}}→"
            # Strip trailing newline for display
            display_line = line.rstrip("\n\r")
            output.append(f"{line_num} {display_line}")

        return "\n".join(output)


class CreateFileTool(BaseTool):
    """Tool for creating or overwriting files with content.

    Attributes:
        name: Tool identifier
        description: Human-readable description
        input_schema: JSON Schema for input validation
    """

    name = "write_file"
    description = (
        "Write content to a file, creating it if it doesn't exist or overwriting if it does. "
        "Use this for creating new files or completely replacing file contents. "
        "For targeted edits to existing files, prefer str_replace_editor instead."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to write to (created if missing, overwritten if exists)"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["file_path", "content"]
    }

    async def execute(self, file_path: str, content: str) -> str:
        """Write content to a file.

        Args:
            file_path: Path to write to
            content: Content to write

        Returns:
            Success message with file path and whether it was created or updated

        Raises:
            ToolExecutionError: If write fails
        """
        full_path = self._resolve_path(file_path)
        existed = full_path.exists()

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            action = "Updated" if existed else "Created"
            return f"{action}: {file_path}"

        except PermissionError:
            raise ToolExecutionError(f"Permission denied: {file_path}")
        except OSError as e:
            raise ToolExecutionError(f"Failed to write file: {e}")

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to working directory.

        Args:
            file_path: File path (relative or absolute)

        Returns:
            Resolved absolute Path
        """
        path = Path(file_path)

        # If relative, resolve against working_dir
        if not path.is_absolute():
            path = Path(self.working_dir) / path

        return path.resolve()


class StrReplaceEditorTool(BaseTool):
    """Tool for replacing text in existing files.

    Attributes:
        name: Tool identifier
        description: Human-readable description
        input_schema: JSON Schema for input validation
    """

    name = "str_replace_editor"
    description = (
        "Replace text in an existing file. "
        "Best for making targeted edits to existing code. "
        "The old_text must be unique in the file - use more context if needed."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit"
            },
            "old_text": {
                "type": "string",
                "description": "Text to replace (must be unique in file)"
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text"
            }
        },
        "required": ["file_path", "old_text", "new_text"]
    }

    async def execute(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
    ) -> str:
        """Replace text in file.

        Args:
            file_path: Path to the file to edit
            old_text: Text to replace (must be unique in file)
            new_text: Replacement text

        Returns:
            Diff-style confirmation of changes

        Raises:
            ToolExecutionError: If file not found or replacement fails
        """
        # Resolve path
        full_path = self._resolve_path(file_path)

        # Check if file exists
        if not full_path.exists():
            return f"Error: File not found: {file_path}"

        try:
            # Read file content
            content = full_path.read_text(encoding="utf-8")

            # Check if old_text exists
            if old_text not in content:
                return "Error: Could not find the specified text to replace. It may have changed."

            # Check for multiple matches
            count = content.count(old_text)
            if count > 1:
                return "Error: Found multiple matches for the specified text. Include more context."

            # Perform replacement
            new_content = content.replace(old_text, new_text, 1)

            # Write back
            full_path.write_text(new_content, encoding="utf-8")

            # Generate diff-style output
            return self._format_diff(file_path, old_text, new_text)

        except PermissionError:
            raise ToolExecutionError(f"Permission denied: {file_path}")
        except OSError as e:
            raise ToolExecutionError(f"Failed to edit file: {e}")

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to working directory.

        Args:
            file_path: File path (relative or absolute)

        Returns:
            Resolved absolute Path
        """
        path = Path(file_path)

        # If relative, resolve against working_dir
        if not path.is_absolute():
            path = Path(self.working_dir) / path

        return path.resolve()

    def _format_diff(self, file_path: str, old_text: str, new_text: str) -> str:
        """Format diff-style output for replacement.

        Args:
            file_path: Path to the file
            old_text: Original text
            new_text: Replacement text

        Returns:
            Diff-style output string
        """
        output = []
        output.append(f"Edited: {file_path}")
        output.append("" + "=" * 60)
        output.append("")

        # Split into lines for diff display
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        # Show old text with - prefix
        for line in old_lines:
            stripped = line.rstrip("\n\r")
            output.append(f"- {stripped}")

        # Show new text with + prefix
        for line in new_lines:
            stripped = line.rstrip("\n\r")
            output.append(f"+ {stripped}")

        return "\n".join(output)
