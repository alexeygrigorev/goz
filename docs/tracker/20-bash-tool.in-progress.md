# Issue 20: Bash Tool

## Status
.in-progress

## Description
Implement the bash tool for executing shell commands safely.

## User Scenarios

### Scenario 1: Run Simple Command
- User asks: "Run the tests"
- Agent calls bash(command="uv run pytest")
- Tool executes command
- Returns output + exit code
- Agent shows results to user

### Scenario 2: Run Command with Working Directory
- User asks: "Run tests in the backend directory"
- Agent calls bash(command="pytest", cwd="backend")
- Tool executes in specified directory
- Returns output from that directory
- Agent shows results

### Scenario 3: Long-Running Command
- User asks: "Watch the file for changes"
- Agent calls bash(command="tail -f log.txt")
- Tool streams output as it comes
- Agent displays output in real-time
- User can cancel

### Scenario 4: Command Fails
- Agent calls bash(command="exit 1")
- Tool returns exit code 1
- Returns stderr output
- Agent shows error to user

### Scenario 5: Destructive Command Warning
- User asks: "Delete all files"
- Agent calls bash(command="rm -rf *")
- Tool warns about destructive command
- Requires confirmation
- Executes after confirmation

## Acceptance Criteria

1. `BashTool` class exists in `goz/agent/tools/bash_tool.py`
2. `execute()` runs shell commands asynchronously
3. Returns stdout, stderr, exit_code
4. Supports optional `cwd` parameter
5. Supports optional `timeout` parameter
6. Handles long-running commands
7. Shows command output in real-time
8. Warns about destructive commands (rm, mv, etc.)
9. Handles Ctrl+C gracefully
10. Works on Windows, macOS, Linux
11. Respects working_dir from config
12. Uses shell environment variables

## Technical Details

### File Structure
```
goz/agent/tools/
└── bash_tool.py   # BashTool
```

### Tool Definition
```python
class BashTool(BaseTool):
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

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int = 300,
    ) -> str:
        """Execute shell command."""
```

### Output Format
```python
class BashResult:
    """Result of bash command execution."""
    exit_code: int
    stdout: str
    stderr: str
    duration: float  # seconds
```

### Return Format
```
Command: pytest tests/ -v
Exit: 0 (in 2.3s)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tests/test_utils.py::test_fibonacci PASSED               [ 33%]
tests/test_utils.py::test_zero PASSED                    [ 66%]
tests/test_utils.py::test_negative PASSED                [100%]

3 passed in 2.3s
```

### Destructive Command Detection
```python
DESTRUCTIVE_PATTERNS = [
    r"rm\s+(-rf?|-r)?\s+\*",  # rm *
    r"rm\s+(-rf?|-r)?\s+-r",   # rm -r
    r"mv\s+.*\s+/",           # mv to root
    r"dd\s+if=",              # dd command
    r"format\s+",             # Windows format
    r"del\s+",                # Windows delete
]

def is_destructive(command: str) -> bool:
    """Check if command looks destructive."""
```

### Cross-Platform Shell
```python
import platform
import shutil

def get_shell_command() -> list[str]:
    """Get appropriate shell command for platform."""
    if platform.system() == "Windows":
        return ["cmd", "/c"]
    else:
        # Use user's shell if available
        shell = os.environ.get("SHELL", shutil.which("bash") or "/bin/sh")
        return [shell, "-c"]
```

### Async Execution
```python
import asyncio
from asyncio.subprocess import Process

async def run_command(
    cmd: str,
    cwd: str | None = None,
    timeout: int = 300,
) -> BashResult:
    """Run command asynchronously with timeout."""
    shell_cmd = get_shell_command() + [cmd]
    proc = await asyncio.create_subprocess_exec(
        *shell_cmd,
        cwd=cwd or self.working_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError(f"Command timed out after {timeout}s")

    return BashResult(
        exit_code=proc.returncode or 0,
        stdout=stdout.decode(),
        stderr=stderr.decode(),
        duration=...,
    )
```

### Streaming Support (for TUI)
```python
async def run_command_stream(
    cmd: str,
    cwd: str | None = None,
) -> AsyncIterator[str]:
    """Run command and yield output line by line."""
    proc = await asyncio.create_subprocess_exec(
        *shell_cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # Combine
    )

    async for line in proc.stdout:
        yield line.decode()

    await proc.wait()
```

### Environment Variables
```python
def get_env() -> dict[str, str]:
    """Get environment for subprocess."""
    env = os.environ.copy()
    # Add PATH for common tools
    env["PATH"] = env.get("PATH", "")
    # Preserve user's PATH
    return env
```

### Security Considerations
- Commands run with user's permissions (same as terminal)
- No sandbox - same as zai-cli behavior
- Warning for destructive commands
- Clear error messages for permission issues

## Dependencies
- Issue 18: Tool Base + Registry

## Related Issues
- Issue 19: File Tools
- Issue 21: Search/Read/Repo Tools

## Log

### [SWE] 2026-03-19
- **TDD Cycle Complete**
- Wrote: `tests/test_bash_tool.py` with 42 tests covering all acceptance criteria
- Ran tests: FAILS - ModuleNotFoundError: No module named 'goz.agent.tools.bash_tool'
- Implemented: `goz/agent/tools/bash_tool.py` with BashTool class
  - BashTool class with async execute() method
  - BashResult dataclass for results
  - Cross-platform shell detection (Windows cmd, Unix shells)
  - Timeout handling with asyncio.wait_for
  - Destructive command pattern detection
  - execute_stream() for real-time output
  - format_output() for display formatting
- Fixed: Destructive patterns regex for rm -rf / and rm -r commands
- Fixed: Cancellation handling to properly propagate CancelledError
- Fixed: Timeout test to use platform-appropriate commands (ping on Windows, sleep on Unix)
- Ran tests: PASSES - All 42 tests pass
- Files:
  - `goz/agent/tools/bash_tool.py` (303 lines)
  - `tests/test_bash_tool.py` (407 lines)
- Note: BaseTool and ToolRegistry already existed (Issue 18 completed)
