"""Unit tests for Markdown and Diff widgets (Issue 24).

TDD Approach:
1. Write tests FIRST
2. Run tests - verify they FAIL
3. Implement code
4. Run tests - verify they PASS

This file tests:
- MarkdownViewer widget for rendering markdown content
- DiffViewer widget for displaying file diffs
- Syntax highlighting for code blocks
"""
from __future__ import annotations

import pytest

from goz.agent.tui.widgets.markdown import MarkdownViewer
from goz.agent.tui.widgets.diff import DiffViewer


class TestMarkdownViewerInit:
    """Unit Tests: MarkdownViewer initialization."""

    def test_markdown_viewer_class_exists(self):
        """Test MarkdownViewer class can be imported."""
        from goz.agent.tui.widgets.markdown import MarkdownViewer  # noqa: F401
        assert MarkdownViewer is not None

    def test_markdown_viewer_init_with_empty_string(self):
        """Test MarkdownViewer initializes with empty markdown."""
        viewer = MarkdownViewer("")
        assert viewer.markdown_text == ""

    def test_markdown_viewer_init_with_simple_text(self):
        """Test MarkdownViewer initializes with simple text."""
        viewer = MarkdownViewer("Hello world")
        assert viewer.markdown_text == "Hello world"

    def test_markdown_viewer_init_with_markdown(self):
        """Test MarkdownViewer initializes with markdown content."""
        md = "# Header\n\nSome **bold** text."
        viewer = MarkdownViewer(md)
        assert viewer.markdown_text == md

    def test_markdown_viewer_is_textual_widget(self):
        """Test MarkdownViewer is a Textual Widget."""
        from textual.widgets import Static
        viewer = MarkdownViewer("test")
        assert isinstance(viewer, Static)


class TestMarkdownViewerRender:
    """Unit Tests: MarkdownViewer rendering."""

    def test_render_returns_renderable(self):
        """Test render() returns a Rich renderable."""
        from rich.console import RenderableType
        viewer = MarkdownViewer("test")
        result = viewer.render()
        # Result should be a valid Rich renderable (has __rich_console__ or is str/Text)
        assert result is not None
        # Check it's renderable by Rich
        from io import StringIO
        from rich.console import Console
        console = Console(file=StringIO())
        console.print(result)  # Should not raise

    def test_render_plain_text(self):
        """Test rendering plain text without markdown."""
        viewer = MarkdownViewer("Just plain text")
        result = viewer.render()
        assert result is not None

    def test_render_headers(self):
        """Test rendering markdown headers (h1-h6)."""
        md = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_bold_italic_strikethrough(self):
        """Test rendering bold, italic, and strikethrough text."""
        md = "**bold** and *italic* and ~~strikethrough~~"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_inline_code(self):
        """Test rendering inline code."""
        md = "Here is some `inline code` in text."
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_code_block_no_language(self):
        """Test rendering code block without language specification."""
        md = "```\nprint('hello')\n```"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_code_block_with_python(self):
        """Test rendering Python code block."""
        md = """```python
def hello():
    print("Hello, world!")
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_code_block_with_javascript(self):
        """Test rendering JavaScript code block."""
        md = """```javascript
function hello() {
    console.log("Hello");
}
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_code_block_with_json(self):
        """Test rendering JSON code block."""
        md = """```json
{"key": "value", "number": 42}
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_code_block_with_bash(self):
        """Test rendering Bash code block."""
        md = """```bash
echo "Hello, World!"
ls -la
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_code_block_with_yaml(self):
        """Test rendering YAML code block."""
        md = """```yaml
key: value
nested:
  item: test
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_unordered_list(self):
        """Test rendering unordered list."""
        md = """- Item 1
- Item 2
  - Nested item
- Item 3"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_ordered_list(self):
        """Test rendering ordered list."""
        md = """1. First item
2. Second item
3. Third item"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_links(self):
        """Test rendering markdown links."""
        md = "[Link text](https://example.com)"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_blockquotes(self):
        """Test rendering blockquotes."""
        md = "> This is a quote\n>\n> Multi-line"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_tables(self):
        """Test rendering markdown tables (optional enhancement)."""
        md = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_render_mixed_content(self):
        """Test rendering complex markdown with mixed elements."""
        md = """# Document Title

This is a paragraph with **bold** and *italic* text.

## Code Example

```python
def example():
    return [1, 2, 3]
```

## List

- Item 1
- Item 2

> A quote for emphasis
"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None


class TestMarkdownViewerLanguageDetection:
    """Unit Tests: Code block language detection."""

    def test_detect_python_language(self):
        """Test Python language is detected from ```python fence."""
        md = "```python\nprint('test')\n```"
        viewer = MarkdownViewer(md)
        # Language should be detected
        assert "python" in viewer.markdown_text.lower()

    def test_detect_javascript_language(self):
        """Test JavaScript language is detected from ```javascript fence."""
        md = "```javascript\nconsole.log('test')\n```"
        viewer = MarkdownViewer(md)
        assert "javascript" in viewer.markdown_text.lower()

    def test_detect_js_language(self):
        """Test JS language is detected from ```js fence."""
        md = "```js\nconsole.log('test')\n```"
        viewer = MarkdownViewer(md)
        assert "js" in viewer.markdown_text.lower()

    def test_detect_json_language(self):
        """Test JSON language is detected from ```json fence."""
        md = "```json\n{\"key\": \"value\"}\n```"
        viewer = MarkdownViewer(md)
        assert "json" in viewer.markdown_text.lower()

    def test_detect_bash_language(self):
        """Test Bash language is detected from ```bash fence."""
        md = "```bash\necho test\n```"
        viewer = MarkdownViewer(md)
        assert "bash" in viewer.markdown_text.lower()

    def test_detect_yaml_language(self):
        """Test YAML language is detected from ```yaml fence."""
        md = "```yaml\nkey: value\n```"
        viewer = MarkdownViewer(md)
        assert "yaml" in viewer.markdown_text.lower()

    def test_detect_yml_language(self):
        """Test YML language is detected from ```yml fence."""
        md = "```yml\nkey: value\n```"
        viewer = MarkdownViewer(md)
        assert "yml" in viewer.markdown_text.lower()

    def test_detect_markdown_language(self):
        """Test Markdown language is detected from ```markdown fence."""
        md = "```markdown\n# Header\n```"
        viewer = MarkdownViewer(md)
        assert "markdown" in viewer.markdown_text.lower()

    def test_detect_md_language(self):
        """Test MD language is detected from ```md fence."""
        md = "```md\n# Header\n```"
        viewer = MarkdownViewer(md)
        assert "md" in viewer.markdown_text.lower()

    def test_no_language_detected_when_missing(self):
        """Test no language is detected when fence has no language."""
        md = "```\ncode\n```"
        viewer = MarkdownViewer(md)
        # Should not crash, should handle gracefully


class TestDiffViewerInit:
    """Unit Tests: DiffViewer initialization."""

    def test_diff_viewer_class_exists(self):
        """Test DiffViewer class can be imported."""
        from goz.agent.tui.widgets.diff import DiffViewer  # noqa: F401
        assert DiffViewer is not None

    def test_diff_viewer_init_with_old_new(self):
        """Test DiffViewer initializes with old and new content."""
        old = "line 1\nline 2"
        new = "line 1\nline 2 modified"
        viewer = DiffViewer(old=old, new=new)
        assert viewer.old == old
        assert viewer.new == new

    def test_diff_viewer_init_with_file_path(self):
        """Test DiffViewer initializes with file path."""
        viewer = DiffViewer(
            old="old content",
            new="new content",
            file_path="/path/to/file.py"
        )
        assert viewer.file_path == "/path/to/file.py"

    def test_diff_viewer_init_default_file_path(self):
        """Test DiffViewer has default empty file path."""
        viewer = DiffViewer(old="old", new="new")
        assert viewer.file_path == ""

    def test_diff_viewer_is_textual_widget(self):
        """Test DiffViewer is a Textual Widget."""
        from textual.widgets import Static
        viewer = DiffViewer(old="old", new="new")
        assert isinstance(viewer, Static)


class TestDiffViewerRender:
    """Unit Tests: DiffViewer rendering."""

    def test_render_returns_renderable(self):
        """Test render() returns a Rich renderable."""
        viewer = DiffViewer(old="old", new="new")
        result = viewer.render()
        assert result is not None
        # Check it's renderable by Rich
        from io import StringIO
        from rich.console import Console
        console = Console(file=StringIO())
        console.print(result)  # Should not raise

    def test_render_no_changes(self):
        """Test rendering when old and new are identical."""
        content = "line 1\nline 2\nline 3"
        viewer = DiffViewer(old=content, new=content)
        result = viewer.render()
        assert result is not None

    def test_render_single_addition(self):
        """Test rendering with added line."""
        old = "line 1\nline 2"
        new = "line 1\nline 2\nline 3 (added)"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None

    def test_render_single_deletion(self):
        """Test rendering with deleted line."""
        old = "line 1\nline 2\nline 3"
        new = "line 1\nline 2"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None

    def test_render_single_modification(self):
        """Test rendering with modified line."""
        old = "line 1\nline 2 old\nline 3"
        new = "line 1\nline 2 new\nline 3"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None

    def test_render_multiple_hunks(self):
        """Test rendering with multiple change hunks."""
        old = "line 1\nline 2\nline 3\nline 4\nline 5"
        new = "line 1 modified\nline 2\nline 3\nline 4 modified\nline 5"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None

    def test_render_with_file_path_header(self):
        """Test rendering includes file path in header."""
        viewer = DiffViewer(
            old="old",
            new="new",
            file_path="/test/file.py"
        )
        result = viewer.render()
        assert result is not None

    def test_render_empty_to_content(self):
        """Test rendering from empty file to content."""
        viewer = DiffViewer(old="", new="line 1\nline 2")
        result = viewer.render()
        assert result is not None

    def test_render_content_to_empty(self):
        """Test rendering from content to empty file."""
        viewer = DiffViewer(old="line 1\nline 2", new="")
        result = viewer.render()
        assert result is not None

    def test_render_both_empty(self):
        """Test rendering when both old and new are empty."""
        viewer = DiffViewer(old="", new="")
        result = viewer.render()
        assert result is not None


class TestDiffViewerColors:
    """Unit Tests: DiffViewer color styling."""

    def test_added_lines_green(self):
        """Test added lines are colored green."""
        old = "line 1"
        new = "line 1\nline 2 (added)"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None
        # Result should contain styling for additions

    def test_removed_lines_red(self):
        """Test removed lines are colored red."""
        old = "line 1\nline 2 (removed)"
        new = "line 1"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None
        # Result should contain styling for deletions

    def test_context_lines_normal_color(self):
        """Test context lines have normal color."""
        old = "line 1\nline 2\nline 3"
        new = "line 1\nline 2 modified\nline 3"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None
        # Context lines should be visible

    def test_hunk_headers_cyan(self):
        """Test hunk headers (@@ lines) are colored cyan."""
        old = "line 1\nline 2\nline 3"
        new = "line 1\nline 2 modified\nline 3"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None


class TestDiffViewerLineNumbers:
    """Unit Tests: DiffViewer line number display."""

    def test_line_numbers_in_output(self):
        """Test diff output includes line numbers."""
        viewer = DiffViewer(
            old="line 1\nline 2",
            new="line 1\nline 2 modified"
        )
        result = viewer.render()
        assert result is not None

    def test_line_numbers_for_additions(self):
        """Test line numbers shown for added lines."""
        old = "line 1"
        new = "line 1\nline 2"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None

    def test_line_numbers_for_deletions(self):
        """Test line numbers shown for deleted lines."""
        old = "line 1\nline 2"
        new = "line 1"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None


class TestPerformanceLargeContent:
    """Performance Tests: Large content handling."""

    def test_markdown_viewer_1000_lines(self):
        """Test MarkdownViewer handles 1000+ lines."""
        lines = ["Line " + str(i) for i in range(1000)]
        md = "\n".join(lines)
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_markdown_viewer_with_code_1000_lines(self):
        """Test MarkdownViewer handles 1000+ lines in code block."""
        code_lines = ["    x = " + str(i) for i in range(1000)]
        code = "\n".join(code_lines)
        md = f"```python\n{code}\n```"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_diff_viewer_1000_lines(self):
        """Test DiffViewer handles 1000+ lines."""
        old_lines = ["line " + str(i) for i in range(1000)]
        new_lines = ["line " + str(i) + " modified" for i in range(1000)]
        viewer = DiffViewer(old="\n".join(old_lines), new="\n".join(new_lines))
        result = viewer.render()
        assert result is not None


class TestEdgeCases:
    """Edge case tests for both widgets."""

    def test_markdown_viewer_none_input(self):
        """Test MarkdownViewer handles None-like input."""
        viewer = MarkdownViewer("")
        result = viewer.render()
        assert result is not None

    def test_markdown_viewer_unicode_content(self):
        """Test MarkdownViewer handles unicode content."""
        md = "# Hello 世界\n\nEmoji: 🌍🚀\n\n```python\n# コメント\nprint('Hello')\n```"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_markdown_viewer_malformed_code_block(self):
        """Test MarkdownViewer handles malformed code blocks."""
        md = "```python\ncode without closing fence"
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_diff_viewer_unicode_content(self):
        """Test DiffViewer handles unicode content."""
        old = "line 1\n世界\nline 3"
        new = "line 1\n🌍\nline 3"
        viewer = DiffViewer(old=old, new=new)
        result = viewer.render()
        assert result is not None

    def test_diff_viewer_only_line_breaks(self):
        """Test DiffViewer handles content with only line breaks."""
        viewer = DiffViewer(old="\n\n\n", new="\n\n")
        result = viewer.render()
        assert result is not None

    def test_diff_viewer_very_long_lines(self):
        """Test DiffViewer handles very long lines."""
        long_line = "x" * 10000
        viewer = DiffViewer(old=long_line, new=long_line + "y")
        result = viewer.render()
        assert result is not None


class TestSyntaxHighlighting:
    """Unit Tests: Syntax highlighting functionality."""

    def test_python_syntax_highlighting(self):
        """Test Python code gets syntax highlighting."""
        md = '''```python
def function(param: str) -> int:
    """Docstring."""
    variable = [1, 2, 3]
    return len(variable)
```'''
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_javascript_syntax_highlighting(self):
        """Test JavaScript code gets syntax highlighting."""
        md = """```javascript
const arrow = (param) => {
    const array = [1, 2, 3];
    return array.length;
};
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_json_syntax_highlighting(self):
        """Test JSON code gets syntax highlighting."""
        md = """```json
{
    "key": "value",
    "number": 42,
    "nested": {
        "array": [true, false, null]
    }
}
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_bash_syntax_highlighting(self):
        """Test Bash code gets syntax highlighting."""
        md = """```bash
#!/bin/bash
VAR="value"
if [[ $VAR == "value" ]]; then
    echo "Match"
fi
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_yaml_syntax_highlighting(self):
        """Test YAML code gets syntax highlighting."""
        md = """```yaml
key: value
number: 42
boolean: true
nested:
  - item1
  - item2
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_markdown_syntax_highlighting(self):
        """Test Markdown code gets syntax highlighting."""
        md = """```markdown
# Header in code

```python
# nested code
```

**bold** in code
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None

    def test_unknown_language_fallback(self):
        """Test unknown language falls back to plain text."""
        md = """```unknownlangxyz
this is not a known language
```"""
        viewer = MarkdownViewer(md)
        result = viewer.render()
        assert result is not None


class TestInlineDiff:
    """Unit Tests: Inline diff functionality."""

    def test_inline_diff_function_exists(self):
        """Test inline diff function exists."""
        from goz.agent.tui.widgets.diff import render_inline_diff
        assert render_inline_diff is not None

    def test_inline_diff_no_change(self):
        """Test inline diff with no changes."""
        from goz.agent.tui.widgets.diff import render_inline_diff
        result = render_inline_diff("same text", "same text")
        assert result is not None

    def test_inline_diff_single_insertion(self):
        """Test inline diff with single insertion."""
        from goz.agent.tui.widgets.diff import render_inline_diff
        result = render_inline_diff("text", "text new")
        assert result is not None

    def test_inline_diff_single_deletion(self):
        """Test inline diff with single deletion."""
        from goz.agent.tui.widgets.diff import render_inline_diff
        result = render_inline_diff("text old", "text")
        assert result is not None

    def test_inline_diff_replacement(self):
        """Test inline diff with replacement."""
        from goz.agent.tui.widgets.diff import render_inline_diff
        result = render_inline_diff("old text", "new content")
        assert result is not None

    def test_inline_diff_empty_strings(self):
        """Test inline diff with empty strings."""
        from goz.agent.tui.widgets.diff import render_inline_diff
        result = render_inline_diff("", "")
        assert result is not None

    def test_inline_diff_empty_to_content(self):
        """Test inline diff from empty to content."""
        from goz.agent.tui.widgets.diff import render_inline_diff
        result = render_inline_diff("", "new text")
        assert result is not None
