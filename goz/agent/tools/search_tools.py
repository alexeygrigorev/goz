"""Code search tools for goz coding agent.

Provides:
- GlobTool: Find files by glob pattern
- GrepTool: Search file contents with regex
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from goz.agent.tools.base import BaseTool, ToolExecutionError


class GlobTool(BaseTool):
    """Find files matching a glob pattern."""

    name = "glob"
    description = (
        "Find files by glob pattern (e.g. '**/*.py', 'src/**/*.ts'). "
        "Returns matching file paths relative to the working directory, "
        "sorted by modification time (newest first). "
        "Use this to discover files before reading them."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match (e.g. '**/*.py', 'src/**/*.ts')",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in (default: working directory)",
            },
        },
        "required": ["pattern"],
    }

    async def execute(self, pattern: str, path: str | None = None, **kwargs: Any) -> str:
        search_dir = Path(path) if path else Path(self.working_dir)
        if not search_dir.is_absolute():
            search_dir = Path(self.working_dir) / search_dir

        if not search_dir.exists():
            raise ToolExecutionError(f"Directory not found: {search_dir}")
        if not search_dir.is_dir():
            raise ToolExecutionError(f"Not a directory: {search_dir}")

        matches: list[tuple[float, str]] = []
        try:
            for match in search_dir.glob(pattern):
                if match.is_file():
                    try:
                        mtime = match.stat().st_mtime
                    except OSError:
                        mtime = 0
                    rel = str(match.relative_to(Path(self.working_dir)))
                    matches.append((mtime, rel))
        except Exception as exc:
            raise ToolExecutionError(f"Glob failed: {exc}") from exc

        # Sort newest first
        matches.sort(key=lambda x: x[0], reverse=True)

        if not matches:
            return f"No files found matching '{pattern}'"

        # Limit to 250 results
        paths = [m[1] for m in matches[:250]]
        truncated = f"\n... ({len(matches) - 250} more)" if len(matches) > 250 else ""
        return "\n".join(paths) + truncated


class GrepTool(BaseTool):
    """Search file contents with regex."""

    name = "grep"
    description = (
        "Search file contents using a regular expression pattern. "
        "Returns matching lines with file paths and line numbers. "
        "Use this to find specific code, function definitions, imports, etc."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regular expression pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in (default: working directory)",
            },
            "glob": {
                "type": "string",
                "description": "Filter files by glob pattern (e.g. '*.py', '*.ts')",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "Case insensitive search (default: false)",
            },
        },
        "required": ["pattern"],
    }

    # Skip binary and large files
    _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache"}
    _MAX_FILE_SIZE = 1_000_000  # 1MB
    _MAX_RESULTS = 250

    async def execute(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        case_insensitive: bool = False,
        **kwargs: Any,
    ) -> str:
        search_path = Path(path) if path else Path(self.working_dir)
        if not search_path.is_absolute():
            search_path = Path(self.working_dir) / search_path

        if not search_path.exists():
            raise ToolExecutionError(f"Path not found: {search_path}")

        flags = re.IGNORECASE if case_insensitive else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as exc:
            raise ToolExecutionError(f"Invalid regex: {exc}") from exc

        results: list[str] = []

        if search_path.is_file():
            files = [search_path]
        else:
            files = list(self._iter_files(search_path, glob))

        for file_path in files:
            if len(results) >= self._MAX_RESULTS:
                break
            self._search_file(file_path, regex, results)

        if not results:
            return f"No matches found for '{pattern}'"

        truncated = f"\n... ({self._MAX_RESULTS}+ matches, showing first {self._MAX_RESULTS})" if len(results) >= self._MAX_RESULTS else ""
        return "\n".join(results[:self._MAX_RESULTS]) + truncated

    def _iter_files(self, directory: Path, glob_pattern: str | None) -> list[Path]:
        files: list[Path] = []
        for root, dirs, filenames in os.walk(directory):
            # Skip hidden and known large dirs
            dirs[:] = [d for d in dirs if d not in self._SKIP_DIRS and not d.startswith(".")]

            for name in filenames:
                if glob_pattern and not fnmatch.fnmatch(name, glob_pattern):
                    continue
                fp = Path(root) / name
                try:
                    if fp.stat().st_size > self._MAX_FILE_SIZE:
                        continue
                except OSError:
                    continue
                files.append(fp)
        return files

    def _search_file(self, file_path: Path, regex: re.Pattern, results: list[str]) -> None:
        try:
            text = file_path.read_text(errors="replace")
        except (OSError, UnicodeDecodeError):
            return

        rel = str(file_path.relative_to(Path(self.working_dir))) if file_path.is_relative_to(Path(self.working_dir)) else str(file_path)

        for i, line in enumerate(text.splitlines(), 1):
            if len(results) >= self._MAX_RESULTS:
                return
            if regex.search(line):
                results.append(f"{rel}:{i}: {line.rstrip()}")
