"""Auto-load project context files from the working directory."""

from __future__ import annotations

from pathlib import Path

CONTEXT_FILES: list[str] = [
    "CLAUDE.md",
    "README.md",
    ".cursorrules",
    ".github/copilot-instructions.md",
]

DEFAULT_MAX_CHARS: int = 16_000  # ~4000 tokens at 4 chars/token


def load_project_context(
    working_dir: str,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """Load project context files from *working_dir* and return combined text.

    Checks for files in priority order: CLAUDE.md, README.md, .cursorrules,
    .github/copilot-instructions.md.  Each file that exists is read and
    concatenated with a header.  If the total exceeds *max_chars*, it is
    truncated.  Returns an empty string when no files are found.
    """
    base = Path(working_dir)
    parts: list[str] = []

    for name in CONTEXT_FILES:
        filepath = base / name
        if filepath.is_file():
            try:
                content = filepath.read_text(errors="replace")
            except OSError:
                continue
            header = f"# {name}\n"
            parts.append(header + content)

    if not parts:
        return ""

    combined = "\n\n".join(parts)

    if len(combined) > max_chars:
        combined = combined[:max_chars]

    return combined
