# Issue 24: Markdown + Diff Widgets

## Status
.todo

## Description
Implement widgets for rendering markdown content and displaying file diffs.

## User Scenarios

### Scenario 1: Display Markdown Response
- Agent responds with markdown-formatted text
- Response contains headers, code blocks, lists
- MarkdownViewer renders formatted output
- Headers are bold/larger
- Code blocks have syntax highlighting
- Lists are properly indented

### Scenario 2: Display Code Block
- Tool returns Python code
- MarkdownViewer detects language from ```python fence
- Code is syntax-highlighted
- Line numbers shown (optional)
- Monospace font for code

### Scenario 3: Display File Diff
- Agent edits a file with str_replace_editor
- DiffViewer shows changes
- Removed lines in red with strikethrough
- Added lines in green
- Context lines in normal color
- File path shown at top

### Scenario 4: Display Tool Result
- Bash tool returns command output
- Output shown in code block
- Exit code shown if non-zero
- Duration shown

### Scenario 5: Display Search Results
- Search tool returns results
- Each result formatted as list item
- Title bold, URL clickable
- Summary in smaller text
- Rank number shown

## Acceptance Criteria

### MarkdownViewer
1. `MarkdownViewer` widget exists in `goz/agent/tui/widgets/markdown.py`
2. Renders GitHub-flavored markdown
3. Supports headers (h1-h6)
4. Supports code blocks with syntax highlighting
5. Supports inline code
6. Supports bold, italic, strikethrough
7. Supports lists (ordered, unordered)
8. Supports links
9. Handles tables (optional enhancement)
10. Handles blockquotes
11. Detects language from ``` fences

### DiffViewer
12. `DiffViewer` widget exists in `goz/agent/tui/widgets/diff.py`
13. Shows unified diff format
14. Removed lines red (with - prefix)
15. Added lines green (with + prefix)
16. Context lines normal
17. File path shown in header
18. Line numbers shown
19. Handles multiple hunks
20. Supports inline changes (word-level diff)

### Syntax Highlighting
21. Python syntax highlighting
22. JavaScript/TypeScript syntax highlighting
23. JSON syntax highlighting
24. Bash syntax highlighting
25. Markdown syntax highlighting
26. YAML syntax highlighting

### Integration
27. ChatHistoryViewer uses MarkdownViewer for assistant messages
28. ChatHistoryViewer uses DiffViewer for edit results
29. Code blocks in tool results are syntax-highlighted
30. Performance acceptable for large outputs (1000+ lines)

## Technical Details

### File Structure
```
goz/agent/tui/widgets/
├── __init__.py
├── markdown.py   # MarkdownViewer
└── diff.py       # DiffViewer
```

### MarkdownViewer
```python
from textual.widgets import Static
from rich.console import RenderableType
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text

class MarkdownViewer(Static):
    """Widget for rendering markdown content."""

    def __init__(self, markdown_text: str, **kwargs):
        super().__init__(**kwargs)
        self.markdown_text = markdown_text

    def render(self) -> RenderableType:
        """Render markdown to Rich renderable."""
        # Use Rich's built-in Markdown
        # Extend for custom code block handling
        return self._render_with_syntax(self.markdown_text)

    def _render_with_syntax(self, text: str) -> Text:
        """Render markdown with syntax-highlighted code blocks."""
        # Parse markdown
        # Replace code blocks with Syntax objects
        # Return combined renderable
```

### Code Block Detection
```python
import re

CODE_BLOCK_RE = re.compile(
    r"```(\w+)?\n(.*?)```",
    re.DOTALL,
)

def render_code_block(language: str, code: str) -> Syntax:
    """Render a code block with syntax highlighting."""
    try:
        return Syntax(
            code,
            language or "text",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
    except Exception:
        # Fallback if syntax not supported
        return Syntax(
            code,
            "text",
            theme="monokai",
            line_numbers=True,
        )
```

### DiffViewer
```python
from textual.widgets import Static
from rich.console import RenderableType
from difflib import unified_diff

class DiffViewer(Static):
    """Widget for displaying file diffs."""

    def __init__(
        self,
        old: str,
        new: str,
        file_path: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.old = old
        self.new = new
        self.file_path = file_path

    def render(self) -> RenderableType:
        """Render diff to Rich renderable."""
        # Generate unified diff
        diff_lines = list(unified_diff(
            self.old.splitlines(keepends=True),
            self.new.splitlines(keepends=True),
            fromfile=self.file_path or "original",
            tofile=self.file_path or "modified",
            lineterm="",
        ))

        if not diff_lines:
            return Text("[dim]No changes[/dim]")

        # Colorize diff
        text = Text()
        for line in diff_lines:
            if line.startswith("-"):
                text.append(line, style="red")
            elif line.startswith("+"):
                text.append(line, style="green")
            elif line.startswith("@"):
                text.append(line, style="cyan")
            else:
                text.append(line)

        return text
```

### Inline Diff
```python
def render_inline_diff(old: str, new: str) -> Text:
    """Render word-level inline diff."""
    import difflib

    text = Text()
    matcher = difflib.SequenceMatcher(None, old, new)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            text.append(old[i1:i2])
        elif tag == "delete":
            text.append(old[i1:i2], style="red strikethrough")
        elif tag == "insert":
            text.append(new[j1:j2], style="green bold")
        elif tag == "replace":
            text.append(old[i1:i2], style="red strikethrough")
            text.append(new[j1:j2], style="green bold")

    return text
```

### ToolResultBox
```python
class ToolResultBox(Static):
    """Display tool execution results."""

    def __init__(
        self,
        tool_name: str,
        result: str,
        exit_code: int = 0,
        duration: float = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.result = result
        self.exit_code = exit_code
        self.duration = duration

    def render(self) -> RenderableType:
        """Render tool result."""
        text = Text()
        # Header with tool name
        text.append(f"[{self.tool_name}] ", style="bold cyan")
        if self.duration > 0:
            text.append(f"({self.duration:.1f}s)", style="dim")
        text.append("\n\n")

        # Result content (as code block)
        text.append(self.result, style="dim")

        # Exit code if non-zero
        if self.exit_code != 0:
            text.append(f"\n[Exit: {self.exit_code}]", style="red")

        return text
```

### FileViewBox
```python
class FileViewBox(Static):
    """Display file contents with line numbers."""

    def __init__(
        self,
        file_path: str,
        content: str,
        line_range: tuple[int, int] | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.content = content
        self.line_range = line_range

    def render(self) -> RenderableType:
        """Render file view."""
        text = Text()
        # File path header
        text.append(f"File: {self.file_path}", style="bold cyan")
        if self.line_range:
            text.append(f" (lines {self.line_range[0]}-{self.line_range[1]})", style="dim")
        text.append("\n\n")

        # Content with line numbers
        lines = self.content.splitlines()
        for i, line in enumerate(lines, 1):
            # Skip lines outside range
            if self.line_range:
                if i < self.line_range[0] or i > self.line_range[1]:
                    continue

            # Line number
            text.append(f"{i:4d}→ ", style="dim")
            # Content
            text.append(line + "\n")

        return text
```

### SearchResultsBox
```python
class SearchResultsBox(Static):
    """Display web search results."""

    def __init__(self, query: str, results: list[SearchResult], **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.results = results

    def render(self) -> RenderableType:
        """Render search results."""
        text = Text()
        text.append(f"Search results for: {self.query}\n", style="bold")
        text.append("━" * 60, style="dim")
        text.append("\n\n")

        for r in self.results:
            # Rank and title
            text.append(f"{r.rank}. ", style="bold cyan")
            text.append(r.title, style="bold")
            text.append("\n")

            # URL
            text.append(r.url, style="blue underline")
            text.append("\n")

            # Summary
            if r.summary:
                text.append(r.summary[:200] + "...", style="dim")
            text.append("\n\n")

        return text
```

### Rich Integration
```python
# Textual has built-in Rich integration
# Just need to return Rich renderables from render()

from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.console import Group
from rich.panel import Panel

# Complex layouts
def render_complex_output(self) -> RenderableType:
    return Panel(
        Group(
            Text("Header", style="bold"),
            Markdown("# Content"),
            Syntax("code", "python"),
        ),
        title="Output",
        border_style="blue",
    )
```

## Dependencies
- Issue 23: Agent App + Chat Screen

## Related Issues
- Issue 25: Thinking Indicator

## Log
- 2025-03-19: Implemented MarkdownViewer and DiffViewer widgets following TDD
  - Created 77 unit tests in tests/test_markdown_widgets.py
  - Implemented goz/agent/tui/widgets/markdown.py with MarkdownViewer
  - Implemented goz/agent/tui/widgets/diff.py with DiffViewer, CodeDiffViewer, and render_inline_diff
  - All tests pass
  - Uses Rich's built-in Markdown and Syntax for rendering
  - Uses difflib.unified_diff for diff generation

## Log
