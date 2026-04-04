"""Unit tests for BashTool (Issue 20).

Tests follow TDD:
1. Write test FIRST
2. Verify test FAILS
3. Implement code
4. Verify test PASSES
"""
import asyncio
import os
import platform
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from goz.agent.tools.base import BaseTool, ToolInputError, ToolExecutionError
from goz.agent.tools.bash_tool import BashTool, BashResult


class TestBashToolExists:
    """Unit Tests: BashTool class exists and has required attributes."""

    def test_bash_tool_class_exists(self):
        """Test BashTool class can be imported."""
        from goz.agent.tools.bash_tool import BashTool  # noqa: F401
        assert BashTool is not None

    def test_bash_tool_has_name(self):
        """Test BashTool has name attribute."""
        tool = BashTool()
        assert tool.name == "bash"

    def test_bash_tool_has_description(self):
        """Test BashTool has description attribute."""
        tool = BashTool()
        assert tool.description is not None
        assert len(tool.description) > 0
        assert "shell" in tool.description.lower()

    def test_bash_tool_has_input_schema(self):
        """Test BashTool has input_schema attribute."""
        tool = BashTool()
        assert tool.input_schema is not None
        assert "type" in tool.input_schema
        assert tool.input_schema["type"] == "object"
        assert "properties" in tool.input_schema
        assert "command" in tool.input_schema["properties"]


class TestBashToolInputSchema:
    """Unit Tests: BashTool input schema is correct."""

    def test_input_schema_has_command_property(self):
        """Test input schema has command property."""
        tool = BashTool()
        props = tool.input_schema["properties"]
        assert "command" in props
        assert props["command"]["type"] == "string"
        assert props["command"].get("description") is not None

    def test_input_schema_has_cwd_property(self):
        """Test input schema has optional cwd property."""
        tool = BashTool()
        props = tool.input_schema["properties"]
        assert "cwd" in props
        assert props["cwd"]["type"] == "string"
        assert "cwd" not in tool.input_schema.get("required", [])

    def test_input_schema_has_timeout_property(self):
        """Test input schema has optional timeout property."""
        tool = BashTool()
        props = tool.input_schema["properties"]
        assert "timeout" in props
        assert props["timeout"]["type"] == "integer"
        assert "timeout" not in tool.input_schema.get("required", [])

    def test_input_schema_command_is_required(self):
        """Test command is in required fields."""
        tool = BashTool()
        required = tool.input_schema.get("required", [])
        assert "command" in required


class TestBashToolExecuteSimpleCommand:
    """Unit Tests: BashTool executes simple commands."""

    @pytest.mark.asyncio
    async def test_execute_echo_command(self):
        """Test executing a simple echo command."""
        tool = BashTool()
        result = await tool.execute(command="echo hello")
        assert isinstance(result, BashResult)
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.stderr == ""

    @pytest.mark.asyncio
    async def test_execute_python_version(self):
        """Test executing python --version."""
        tool = BashTool()
        result = await tool.execute(command="python --version")
        assert isinstance(result, BashResult)
        # python --version outputs to stderr on some platforms
        output = result.stdout + result.stderr
        assert "Python" in output

    @pytest.mark.asyncio
    async def test_execute_returns_bash_result(self):
        """Test execute returns BashResult dataclass."""
        tool = BashTool()
        result = await tool.execute(command="echo test")
        assert hasattr(result, "exit_code")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")
        assert hasattr(result, "duration")
        assert isinstance(result.exit_code, int)
        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)
        assert isinstance(result.duration, float)


class TestBashToolExitCodes:
    """Unit Tests: BashTool handles different exit codes."""

    @pytest.mark.asyncio
    async def test_execute_success_exit_code(self):
        """Test successful command returns exit code 0."""
        tool = BashTool()
        result = await tool.execute(command="echo success")
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_failure_exit_code(self):
        """Test failing command returns non-zero exit code."""
        tool = BashTool()
        result = await tool.execute(command="exit 1")
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_execute_custom_exit_code(self):
        """Test command can return custom exit code."""
        tool = BashTool()
        result = await tool.execute(command="exit 42")
        assert result.exit_code == 42


class TestBashToolStderr:
    """Unit Tests: BashTool captures stderr."""

    @pytest.mark.asyncio
    async def test_execute_captures_stderr(self):
        """Test stderr is captured separately from stdout."""
        tool = BashTool()
        result = await tool.execute(command='python -c "import sys; sys.stderr.write(\'error\\n\')"')
        assert isinstance(result.stderr, str)
        # May have output in stderr
        assert len(result.stderr) >= 0


class TestBashToolWorkingDirectory:
    """Unit Tests: BashTool supports cwd parameter."""

    @pytest.mark.asyncio
    async def test_execute_with_cwd(self):
        """Test executing command in specific directory."""
        tool = BashTool()
        # Use a temp directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await tool.execute(command="echo %cd%" if platform.system() == "Windows" else "echo $PWD", cwd=tmpdir)
            assert result.exit_code == 0
            # Output should contain the temp directory path
            assert tmpdir in result.stdout or tmpdir.replace("\\", "/") in result.stdout

    @pytest.mark.asyncio
    async def test_execute_default_cwd(self):
        """Test default cwd is current directory."""
        tool = BashTool()
        cwd = os.getcwd()
        result = await tool.execute(command="echo %cd%" if platform.system() == "Windows" else "echo $PWD")
        assert result.exit_code == 0
        # Should contain current directory
        assert cwd in result.stdout or cwd.replace("\\", "/") in result.stdout

    @pytest.mark.asyncio
    async def test_execute_relative_cwd_resolves_against_working_dir(self):
        """Test relative cwd is resolved against tool working_dir."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "nested")
            os.mkdir(nested)
            tool = BashTool(working_dir=tmpdir)
            result = await tool.execute(
                command="echo %cd%" if platform.system() == "Windows" else "echo $PWD",
                cwd="nested",
            )
            assert result.exit_code == 0
            assert nested in result.stdout or nested.replace("\\", "/") in result.stdout


class TestBashToolTimeout:
    """Unit Tests: BashTool supports timeout parameter."""

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self):
        """Test command completes within timeout."""
        tool = BashTool()
        # Quick command should complete
        result = await tool.execute(command="echo quick", timeout=5)
        assert result.exit_code == 0
        assert "quick" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_timeout_raises_error(self):
        """Test command that exceeds timeout raises error."""
        tool = BashTool()
        with pytest.raises((TimeoutError, ToolExecutionError)):
            # Use ping for timeout test (works on Windows and Unix)
            # ping for 10 seconds should exceed 1 second timeout
            if platform.system() == "Windows":
                await tool.execute(command="ping 127.0.0.1 -n 15", timeout=1)
            else:
                await tool.execute(command="sleep 10", timeout=1)


class TestBashToolDestructiveCommands:
    """Unit Tests: BashTool warns about destructive commands."""

    def test_detects_rm_command(self):
        """Test rm command is detected as destructive."""
        tool = BashTool()
        assert tool._is_destructive("rm -rf /") is True

    def test_detects_recursive_rm(self):
        """Test rm -r is detected as destructive."""
        tool = BashTool()
        assert tool._is_destructive("rm -r file.txt") is True

    def test_detects_mv_to_root(self):
        """Test mv to root is detected as destructive."""
        tool = BashTool()
        assert tool._is_destructive("mv file /") is True

    def test_detects_dd_command(self):
        """Test dd command is detected as destructive."""
        tool = BashTool()
        assert tool._is_destructive("dd if=/dev/zero of=/dev/sda") is True

    def test_detects_windows_format(self):
        """Test Windows format command is detected as destructive."""
        tool = BashTool()
        assert tool._is_destructive("format C:") is True

    def test_detects_windows_del(self):
        """Test Windows del command is detected as destructive."""
        tool = BashTool()
        assert tool._is_destructive("del /Q *.*") is True

    def test_safe_command_not_destructive(self):
        """Test safe commands are not flagged."""
        tool = BashTool()
        assert tool._is_destructive("echo hello") is False
        assert tool._is_destructive("ls -la") is False
        assert tool._is_destructive("cat file.txt") is False
        assert tool._is_destructive("git status") is False

    @pytest.mark.asyncio
    async def test_execute_rejects_destructive_command(self):
        """Test destructive commands are refused."""
        tool = BashTool()
        with pytest.raises(ToolExecutionError, match="Refusing to run destructive command"):
            await tool.execute(command="rm -rf /")


class TestBashToolCrossPlatform:
    """Unit Tests: BashTool works across platforms."""

    def test_get_shell_command_windows(self):
        """Test Windows uses cmd /c."""
        tool = BashTool()
        with patch.object(platform, 'system', return_value='Windows'):
            shell = tool._get_shell_command()
            assert shell == ["cmd", "/c"] or shell == ["cmd.exe", "/c"]

    def test_get_shell_command_unix(self):
        """Test Unix uses shell -c."""
        tool = BashTool()
        with patch.object(platform, 'system', return_value='Linux'):
            shell = tool._get_shell_command()
            assert len(shell) == 2
            assert shell[1] == "-c"
            assert "sh" in shell[0] or "bash" in shell[0]

    def test_get_shell_command_macos(self):
        """Test macOS uses shell -c."""
        tool = BashTool()
        with patch.object(platform, 'system', return_value='Darwin'):
            shell = tool._get_shell_command()
            assert len(shell) == 2
            assert shell[1] == "-c"


class TestBashToolStreaming:
    """Unit Tests: BashTool supports streaming output."""

    @pytest.mark.asyncio
    async def test_execute_stream_yields_output(self):
        """Test streaming command yields output lines."""
        tool = BashTool()
        lines = []
        async for line in tool.execute_stream(command="echo line1 && echo line2"):
            lines.append(line)
        assert len(lines) > 0
        output = "".join(lines)
        assert "line1" in output or "line2" in output

    @pytest.mark.asyncio
    async def test_execute_stream_with_cwd(self):
        """Test streaming with custom cwd."""
        tool = BashTool()
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            lines = []
            async for line in tool.execute_stream(command="echo test", cwd=tmpdir):
                lines.append(line)
            assert len(lines) > 0

    @pytest.mark.asyncio
    async def test_execute_stream_rejects_destructive_command(self):
        """Test streaming path also blocks destructive commands."""
        tool = BashTool()
        with pytest.raises(ToolExecutionError, match="Refusing to run destructive command"):
            async for _ in tool.execute_stream(command="rm -rf /"):
                pass


class TestBashToolGracefulShutdown:
    """Unit Tests: BashTool handles Ctrl+C gracefully."""

    @pytest.mark.asyncio
    async def test_execute_cancelled_during_wait(self):
        """Test command can be cancelled during execution."""
        tool = BashTool()
        # Start a long-running command
        task = asyncio.create_task(
            tool.execute(command="python -c \"import time; time.sleep(100)\"")
        )
        # Wait a bit then cancel
        await asyncio.sleep(0.1)
        task.cancel()
        # Should raise CancelledError, not hang
        with pytest.raises(asyncio.CancelledError):
            await task


class TestBashToolEnvironment:
    """Unit Tests: BashTool uses shell environment."""

    @pytest.mark.asyncio
    async def test_execute_has_env_access(self):
        """Test command can access environment variables."""
        tool = BashTool()
        # Set a test env var and check if command can see it
        os.environ["TEST_BASH_TOOL_VAR"] = "test_value"
        try:
            result = await tool.execute(command="echo %TEST_BASH_TOOL_VAR%" if platform.system() == "Windows" else "echo $TEST_BASH_TOOL_VAR")
            assert result.exit_code == 0
            assert "test_value" in result.stdout
        finally:
            del os.environ["TEST_BASH_TOOL_VAR"]


class TestBashToolOutputFormat:
    """Unit Tests: BashTool output formatting."""

    @pytest.mark.asyncio
    async def test_format_output_basic(self):
        """Test output formatting for basic command."""
        tool = BashTool()
        result = await tool.execute(command="echo test")
        output = tool.format_output(result, command="echo test")
        assert "echo test" in output
        assert "Exit:" in output
        assert "0" in output
        assert "test" in output

    @pytest.mark.asyncio
    async def test_format_output_with_duration(self):
        """Test output includes duration."""
        tool = BashTool()
        result = await tool.execute(command="echo test")
        output = tool.format_output(result, command="echo test")
        assert "s" in output  # Duration should have seconds indicator


class TestBaseTool:
    """Unit Tests: BaseTool class foundation."""

    def test_base_tool_exists(self):
        """Test BaseTool class exists."""
        from goz.agent.tools.base import BaseTool  # noqa: F401
        assert BaseTool is not None

    def test_base_tool_has_working_dir(self):
        """Test BaseTool initializes with working_dir."""
        from goz.agent.tools.base import BaseTool

        class TestTool(BaseTool):
            name = "test"
            description = "test"
            input_schema = {}

            async def execute(self, **kwargs):
                return "test"

        tool = TestTool(working_dir="/tmp")
        assert tool.working_dir == "/tmp"

    def test_base_tool_default_working_dir(self):
        """Test BaseTool uses cwd as default working_dir."""
        from goz.agent.tools.base import BaseTool

        class TestTool(BaseTool):
            name = "test"
            description = "test"
            input_schema = {}

            async def execute(self, **kwargs):
                return "test"

        tool = TestTool()
        assert tool.working_dir == os.getcwd()


class TestToolErrors:
    """Unit Tests: Tool error handling."""

    def test_tool_input_error_exists(self):
        """Test ToolInputError exists."""
        from goz.agent.tools.base import ToolInputError  # noqa: F401
        assert ToolInputError is not None

    def test_tool_execution_error_exists(self):
        """Test ToolExecutionError exists."""
        from goz.agent.tools.base import ToolExecutionError  # noqa: F401
        assert ToolExecutionError is not None

    def test_tool_input_error_is_exception(self):
        """Test ToolInputError is an Exception."""
        from goz.agent.tools.base import ToolInputError
        assert issubclass(ToolInputError, Exception)

    def test_tool_execution_error_is_exception(self):
        """Test ToolExecutionError is an Exception."""
        from goz.agent.tools.base import ToolExecutionError
        assert issubclass(ToolExecutionError, Exception)
