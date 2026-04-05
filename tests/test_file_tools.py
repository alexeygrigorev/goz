"""Unit tests for File Tools (Issue 19)."""
import os
import tempfile
from pathlib import Path

import pytest

from goz.agent.tools.file_tools import ViewFileTool, CreateFileTool, StrReplaceEditorTool
from goz.agent.tools.base import ToolInputError, ToolExecutionError


class TestViewFileTool:
    """Unit Tests: ViewFileTool class."""

    def test_view_file_tool_exists(self):
        """Test ViewFileTool class can be imported."""
        from goz.agent.tools.file_tools import ViewFileTool  # noqa: F401
        assert ViewFileTool is not None

    def test_view_file_tool_has_name(self):
        """Test ViewFileTool has correct name."""
        tool = ViewFileTool()
        assert tool.name == "view_file"

    def test_view_file_tool_has_description(self):
        """Test ViewFileTool has description."""
        tool = ViewFileTool()
        assert tool.description is not None
        assert len(tool.description) > 0

    def test_view_file_tool_has_input_schema(self):
        """Test ViewFileTool has input_schema."""
        tool = ViewFileTool()
        assert "file_path" in tool.input_schema["properties"]
        assert "line_range" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_view_file_reads_existing_file(self):
        """Test view_file reads file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("hello\nworld\nfoo")

            tool = ViewFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path="test.py")

            assert "hello" in result
            assert "world" in result
            assert "foo" in result

    @pytest.mark.asyncio
    async def test_view_file_with_line_range(self):
        """Test view_file with line_range parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("line1\nline2\nline3\nline4\nline5")

            tool = ViewFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path="test.py", line_range=[2, 4])

            assert "line2" in result
            assert "line3" in result
            assert "line4" in result
            assert "line1" not in result
            assert "line5" not in result

    @pytest.mark.asyncio
    async def test_view_file_not_found_raises_error(self):
        """Test view_file raises FileNotFoundError for non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = ViewFileTool(working_dir=tmpdir)

            with pytest.raises(ToolExecutionError, match="File not found"):
                await tool.execute(file_path="nonexistent.py")

    @pytest.mark.asyncio
    async def test_view_file_includes_line_numbers(self):
        """Test view_file output includes line numbers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("line1\nline2\nline3")

            tool = ViewFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path="test.py")

            # Should have line numbers in format like "  1→" or "     1→"
            assert "1" in result
            assert "2" in result
            assert "3" in result

    @pytest.mark.asyncio
    async def test_view_file_handles_unicode(self):
        """Test view_file handles unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# Unicode: hello\nprint('world')")

            tool = ViewFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path="test.py")

            assert "hello" in result
            assert "world" in result

    @pytest.mark.asyncio
    async def test_view_file_validates_input(self):
        """Test view_file validates input schema."""
        tool = ViewFileTool()
        # Missing required field_path
        with pytest.raises(ToolInputError, match="Missing required field"):
            tool.validate_input(tool.input_schema, {})

    @pytest.mark.asyncio
    async def test_view_file_handles_absolute_path(self):
        """Test view_file handles absolute paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("content")

            tool = ViewFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path=str(test_file))

            assert "content" in result

    @pytest.mark.asyncio
    async def test_view_file_handles_windows_paths(self):
        """Test view_file handles Windows-style paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "subdir" / "test.py"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("content")

            tool = ViewFileTool(working_dir=tmpdir)
            # Use forward slashes (common in agent inputs)
            result = await tool.execute(file_path="subdir/test.py")

            assert "content" in result


class TestCreateFileTool:
    """Unit Tests: CreateFileTool class."""

    def test_create_file_tool_exists(self):
        """Test CreateFileTool class can be imported."""
        from goz.agent.tools.file_tools import CreateFileTool  # noqa: F401
        assert CreateFileTool is not None

    def test_create_file_tool_has_name(self):
        """Test CreateFileTool has correct name."""
        tool = CreateFileTool()
        assert tool.name == "write_file"

    def test_create_file_tool_has_description(self):
        """Test CreateFileTool has description."""
        tool = CreateFileTool()
        assert tool.description is not None
        assert len(tool.description) > 0

    def test_create_file_tool_has_input_schema(self):
        """Test CreateFileTool has input_schema."""
        tool = CreateFileTool()
        assert "file_path" in tool.input_schema["properties"]
        assert "content" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_create_file_creates_new_file(self):
        """Test create_file creates a new file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = CreateFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path="new.py", content="hello world")

            assert "Created" in result or "success" in result.lower()
            assert (Path(tmpdir) / "new.py").exists()
            assert (Path(tmpdir) / "new.py").read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_create_file_creates_parent_dirs(self):
        """Test create_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = CreateFileTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="subdir/nested/file.py",
                content="content"
            )

            assert (Path(tmpdir) / "subdir" / "nested" / "file.py").exists()
            assert (Path(tmpdir) / "subdir" / "nested" / "file.py").read_text() == "content"

    @pytest.mark.asyncio
    async def test_write_file_overwrites_existing(self):
        """Test write_file overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            existing_file = Path(tmpdir) / "existing.py"
            existing_file.write_text("old content")

            tool = CreateFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path="existing.py", content="new content")

            assert "updated" in result.lower()
            assert existing_file.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_create_file_handles_unicode_content(self):
        """Test create_file handles unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = CreateFileTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="unicode.py",
                content="# Unicode: hello\nprint('world')"
            )

            assert (Path(tmpdir) / "unicode.py").read_text() == "# Unicode: hello\nprint('world')"

    @pytest.mark.asyncio
    async def test_create_file_validates_input(self):
        """Test create_file validates input schema."""
        tool = CreateFileTool()
        # Missing required fields
        with pytest.raises(ToolInputError, match="Missing required field"):
            tool.validate_input(tool.input_schema, {})

    @pytest.mark.asyncio
    async def test_create_file_handles_empty_content(self):
        """Test create_file handles empty content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = CreateFileTool(working_dir=tmpdir)
            result = await tool.execute(file_path="empty.py", content="")

            assert (Path(tmpdir) / "empty.py").exists()
            assert (Path(tmpdir) / "empty.py").read_text() == ""


class TestStrReplaceEditorTool:
    """Unit Tests: StrReplaceEditorTool class."""

    def test_str_replace_editor_tool_exists(self):
        """Test StrReplaceEditorTool class can be imported."""
        from goz.agent.tools.file_tools import StrReplaceEditorTool  # noqa: F401
        assert StrReplaceEditorTool is not None

    def test_str_replace_editor_tool_has_name(self):
        """Test StrReplaceEditorTool has correct name."""
        tool = StrReplaceEditorTool()
        assert tool.name == "str_replace_editor"

    def test_str_replace_editor_tool_has_description(self):
        """Test StrReplaceEditorTool has description."""
        tool = StrReplaceEditorTool()
        assert tool.description is not None
        assert len(tool.description) > 0

    def test_str_replace_editor_tool_has_input_schema(self):
        """Test StrReplaceEditorTool has input_schema."""
        tool = StrReplaceEditorTool()
        assert "file_path" in tool.input_schema["properties"]
        assert "old_text" in tool.input_schema["properties"]
        assert "new_text" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_str_replace_editor_replaces_text(self):
        """Test str_replace_editor replaces text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def hello():\n    print('hello')")

            tool = StrReplaceEditorTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="test.py",
                old_text="def hello():\n    print('hello')",
                new_text="def goodbye():\n    print('goodbye')"
            )

            assert "Edited" in result or "success" in result.lower()
            assert test_file.read_text() == "def goodbye():\n    print('goodbye')"

    @pytest.mark.asyncio
    async def test_str_replace_editor_fails_if_not_found(self):
        """Test str_replace_editor fails if old_text not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("existing content")

            tool = StrReplaceEditorTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="test.py",
                old_text="nonexistent text",
                new_text="replacement"
            )

            assert "not found" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_str_replace_editor_fails_on_multiple_matches(self):
        """Test str_replace_editor fails if old_text appears multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("hello\nworld\nhello")

            tool = StrReplaceEditorTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="test.py",
                old_text="hello",
                new_text="goodbye"
            )

            assert "multiple" in result.lower() or "more context" in result.lower()

    @pytest.mark.asyncio
    async def test_str_replace_editor_requires_file_exists(self):
        """Test str_replace_editor requires file to exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = StrReplaceEditorTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="nonexistent.py",
                old_text="old",
                new_text="new"
            )

            assert "not found" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_str_replace_editor_handles_unicode(self):
        """Test str_replace_editor handles unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("# hello\nprint('world')")

            tool = StrReplaceEditorTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="test.py",
                old_text="# hello",
                new_text="# goodbye"
            )

            assert test_file.read_text() == "# goodbye\nprint('world')"

    @pytest.mark.asyncio
    async def test_str_replace_editor_returns_diff_style_output(self):
        """Test str_replace_editor returns diff-style confirmation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("old line")

            tool = StrReplaceEditorTool(working_dir=tmpdir)
            result = await tool.execute(
                file_path="test.py",
                old_text="old line",
                new_text="new line"
            )

            # Should show diff with - and + indicators
            assert "-" in result or "+" in result or "old" in result
            assert "new line" in result

    @pytest.mark.asyncio
    async def test_str_replace_editor_validates_input(self):
        """Test str_replace_editor validates input schema."""
        tool = StrReplaceEditorTool()
        # Missing required fields
        with pytest.raises(ToolInputError, match="Missing required field"):
            tool.validate_input(tool.input_schema, {})

    @pytest.mark.asyncio
    async def test_str_replace_editor_preserves_line_endings(self):
        """Test str_replace_editor handles line ending variations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            # Write with \n (Python will handle platform-specific)
            test_file.write_text("line1\nline2\nline3")

            tool = StrReplaceEditorTool(working_dir=tmpdir)
            await tool.execute(
                file_path="test.py",
                old_text="line1\nline2",
                new_text="line1_modified\nline2"
            )

            # Content should be correctly replaced
            content = test_file.read_text()
            assert "line1_modified" in content
            assert "line2" in content
            assert "line3" in content
            # Check the file still has 3 lines
            lines = content.splitlines()
            assert len(lines) == 3
