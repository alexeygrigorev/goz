"""Bash tool for executing shell commands (Issue 20).

This module provides the BashTool class for safely executing shell commands
with support for:
- Async execution with timeout
- Working directory specification
- Cross-platform shell handling (Windows, macOS, Linux)
- Destructive command warnings
- Output streaming
- Graceful cancellation handling
"""
from __future__ import annotations

import asyncio
import os
import platform
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from goz.agent.tools.base import BaseTool, ToolExecutionError


@dataclass
class BashResult:
    """Result of bash command execution.

    Attributes:
        exit_code: Process exit code (0 for success)
        stdout: Standard output from the command
        stderr: Standard error output from the command
        duration: Execution time in seconds
    """

    exit_code: int
    stdout: str
    stderr: str
    duration: float


class BashTool(BaseTool):
    """Tool for executing shell commands.

    Provides safe async execution of shell commands with:
    - Cross-platform support (Windows cmd, Unix shells)
    - Timeout handling
    - Working directory control
    - Destructive command warnings
    - Real-time output streaming

    Attributes:
        name: Tool identifier ("bash")
        description: Human-readable description
        input_schema: JSON Schema for tool inputs
    """

    name = "bash"
    description = (
        "Execute shell commands. Use for running tests, building, "
        "git operations, and other terminal tasks. Commands run in "
        "the current working directory unless specified."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory (default: current directory)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 300)"
            }
        },
        "required": ["command"]
    }

    # Destructive command patterns
    DESTRUCTIVE_PATTERNS = [
        r"rm\s+-rf\s+/",          # rm -rf /
        r"rm\s+-rf?\s+\*",        # rm -rf * or rm -f *
        r"rm\s+-r\s+",            # rm -r (with path)
        r"rm\s+-rf\s+",           # rm -rf (with path)
        r"mv\s+.*\s+/",           # mv to root
        r"dd\s+if=",              # dd command
        r"format\s+",             # Windows format
        r"del\s+",                # Windows delete
    ]

    def _resolve_cwd(self, cwd: str | None) -> str:
        """Resolve cwd relative to the tool working directory."""
        path = Path(cwd) if cwd is not None else Path(self.working_dir)
        if not path.is_absolute():
            path = Path(self.working_dir) / path
        return str(path.resolve())

    def _get_shell_command(self) -> list[str]:
        """Get appropriate shell command for platform.

        Returns:
            List of shell command and arguments (e.g., ["cmd", "/c"] or ["/bin/bash", "-c"])
        """
        if platform.system() == "Windows":
            return ["cmd", "/c"]
        else:
            # Use user's shell if available
            shell = os.environ.get("SHELL", shutil.which("bash") or "/bin/sh")
            return [shell, "-c"]

    def _is_destructive(self, command: str) -> bool:
        """Check if command looks destructive.

        Args:
            command: Command string to check

        Returns:
            True if command matches destructive patterns
        """
        command_lower = command.lower()
        for pattern in self.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, command_lower):
                return True
        return False

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int = 300,
    ) -> BashResult:
        """Execute shell command.

        Args:
            command: Shell command to execute
            cwd: Working directory (uses working_dir if None)
            timeout: Timeout in seconds (default: 300)

        Returns:
            BashResult with exit_code, stdout, stderr, and duration

        Raises:
            ToolExecutionError: If command times out or execution fails
        """
        self.validate_input(
            self.input_schema,
            {"command": command, **({"cwd": cwd} if cwd is not None else {}), "timeout": timeout},
        )

        if timeout <= 0:
            raise ToolExecutionError("Timeout must be greater than 0 seconds")

        if self._is_destructive(command):
            raise ToolExecutionError(
                "Refusing to run destructive command without confirmation"
            )

        work_dir = self._resolve_cwd(cwd)

        # Get platform-appropriate shell command
        shell_cmd = self._get_shell_command()
        full_cmd = shell_cmd + [command]

        # Start timing
        start_time = time.time()

        try:
            # Create subprocess
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )

            # Wait for completion with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                # Kill the process on timeout
                proc.kill()
                await proc.wait()
                duration = time.time() - start_time
                raise ToolExecutionError(
                    f"Command timed out after {timeout}s: {command}"
                )

            # Calculate duration
            duration = time.time() - start_time

            # Decode output
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # Get exit code
            exit_code = proc.returncode or 0

            return BashResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
            )

        except FileNotFoundError:
            raise ToolExecutionError(
                f"Shell not found: {shell_cmd[0]}. Please ensure your shell is installed."
            )
        except PermissionError:
            raise ToolExecutionError(
                f"Permission denied executing command in {work_dir}"
            )
        except asyncio.CancelledError:
            # Handle graceful cancellation - kill process and propagate
            proc_var = locals().get('proc')
            if proc_var is not None:
                proc_var.kill()
                await proc_var.wait()
            raise asyncio.CancelledError()
        except Exception as e:
            raise ToolExecutionError(f"Command execution failed: {e}")

    async def execute_stream(
        self,
        command: str,
        cwd: str | None = None,
    ) -> AsyncIterator[str]:
        """Execute command and yield output line by line.

        This method streams output as it's produced, useful for
        long-running commands or real-time display.

        Args:
            command: Shell command to execute
            cwd: Working directory (uses working_dir if None)

        Yields:
            Output lines as they are produced

        Raises:
            ToolExecutionError: If command execution fails
        """
        self.validate_input(
            self.input_schema,
            {"command": command, **({"cwd": cwd} if cwd is not None else {})},
        )

        if self._is_destructive(command):
            raise ToolExecutionError(
                "Refusing to run destructive command without confirmation"
            )

        work_dir = self._resolve_cwd(cwd)

        # Get platform-appropriate shell command
        shell_cmd = self._get_shell_command()
        full_cmd = shell_cmd + [command]

        try:
            # Create subprocess with combined stdout/stderr
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=os.environ.copy(),
            )

            # Read output line by line
            try:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    yield line.decode("utf-8", errors="replace")
            except asyncio.CancelledError:
                # Handle graceful cancellation
                proc.kill()
                await proc.wait()
                raise

            # Wait for process to complete
            await proc.wait()

        except FileNotFoundError:
            raise ToolExecutionError(f"Shell not found: {shell_cmd[0]}")
        except PermissionError:
            raise ToolExecutionError(f"Permission denied in {work_dir}")
        except Exception as e:
            raise ToolExecutionError(f"Stream execution failed: {e}")

    def format_output(self, result: BashResult, command: str) -> str:
        """Format command result for display.

        Args:
            result: BashResult from execute()
            command: The command that was executed

        Returns:
            Formatted string for display
        """
        lines = [
            f"Command: {command}",
            f"Exit: {result.exit_code} (in {result.duration:.1f}s)",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if result.stdout:
            lines.append("")
            lines.append(result.stdout)

        if result.stderr:
            if result.stdout:
                lines.append("")
            lines.append("STDERR:")
            lines.append(result.stderr)

        return "\n".join(lines)
