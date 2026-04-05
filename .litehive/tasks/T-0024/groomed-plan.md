# T-0024: Streaming Bash Output for Long-Running Commands

## Groomed Plan

### Problem Statement
BashTool.execute() blocks until the subprocess completes, then returns all output at once. For long-running commands (pytest, builds, installs), the agent gets no feedback for minutes. The agent loop in `run.py` calls `_execute_tool_call` which awaits `tool.execute()` and emits a single `tool_use` JSONL event only after completion.

### Current Architecture
1. **`BashTool.execute()`** — creates subprocess, calls `proc.communicate()`, returns `BashResult` dataclass
2. **`BashTool.execute_stream()`** — already exists! Yields lines via `AsyncIterator[str]`, merges stderr into stdout (`stderr=STDOUT`)
3. **`_execute_tool_call()`** in `run.py` — calls `tool.execute(**input)`, wraps in `asyncio.wait_for(300s)`, returns `str(result)`
4. **`run_prompt_jsonl()`** — calls `_execute_tool_call` for each tool call, emits single `tool_use` event with full output

### Key Insight
`execute_stream()` already exists but:
- It merges stderr into stdout (loses separate stderr capture)
- It has no timeout parameter
- It yields raw lines, not structured results
- The agent loop (`_execute_tool_call`) doesn't use it at all

### Implementation Plan

#### Step 1: Modify `BashTool.execute()` to stream internally
Change `execute()` to read stdout and stderr concurrently line-by-line, accumulating them into the `BashResult`. This preserves the existing API contract while enabling intermediate output.

The key change: instead of `proc.communicate()`, use line-by-line reading from both stdout and stderr pipes concurrently, with a streaming callback or internal accumulation.

**Files changed:** `goz/agent/tools/bash_tool.py`

#### Step 2: Add a `stream_callback` parameter to `execute()`
Add an optional `stream_callback: Callable[[str, str], None] | None = None` parameter. When provided, each output line is passed to the callback immediately as it arrives (with a source indicator like "stdout" or "stderr"). This lets the agent loop emit partial JSONL events.

**Files changed:** `goz/agent/tools/bash_tool.py`

#### Step 3: Update `_execute_tool_call` in `run.py` to emit streaming events
When the tool is `bash`, pass a stream callback that emits `tool_stream` JSONL events as output arrives. For short commands (< 5s), the behavior is effectively unchanged since all output arrives quickly. For long commands, the orchestrator sees incremental output.

**Files changed:** `goz/cli/run.py`

#### Step 4: Add unit tests for streaming behavior
Test the streaming callback mechanism with mock subprocesses:
- Verify callback receives lines as produced
- Verify short commands still return complete BashResult
- Verify stderr is captured alongside stdout
- Verify exit code is still correct
- Verify timeout still works
- Verify cancellation still works

**Files changed:** `tests/test_bash_tool.py`

### Acceptance Criteria (Refined)

1. **AC1: BashTool.execute() streams stdout lines via callback** — When a `stream_callback` is provided, each stdout line is passed to the callback as it's produced by the subprocess, before the command completes.

2. **AC2: Short commands unchanged** — For commands completing under 5 seconds without a callback, `execute()` returns the same `BashResult` with full stdout, stderr, exit_code, and duration. All existing tests pass.

3. **AC3: Partial output available before completion** — For long-running commands with a callback, output lines are delivered incrementally. The final `BashResult` still contains the complete output.

4. **AC4: Exit code captured correctly** — The exit code in `BashResult` matches the subprocess exit code regardless of streaming.

5. **AC5: stderr captured alongside stdout** — stderr lines are also streamed via callback (with source indicator) and included in the final `BashResult.stderr`.

6. **AC6: Timeout still works** — The 300s default timeout still terminates commands and raises `ToolExecutionError`. Streaming does not interfere with timeout handling.

7. **AC7: Unit tests for streaming** — New tests verify callback invocation, concurrent stdout/stderr streaming, timeout with streaming, and cancellation with streaming.

### PM Sizing
- **PM_COMPLEXITY:** moderate
- **PLANNED_EFFORT:** s

### Design Decisions
1. **Callback over AsyncIterator return** — Keeps the `execute()` → `BashResult` contract intact. The agent loop opts in to streaming by providing a callback. No breaking changes.
2. **Separate stdout/stderr pipes** — Unlike `execute_stream()` which merges them, the new approach reads both concurrently to preserve the distinction.
3. **`tool_stream` JSONL event** — New event type for incremental output. The existing `tool_use` event still fires at the end with the full result. Downstream consumers can ignore `tool_stream` events if they don't support them.

### Follow-Up Tasks
1. **T-0025: Agent loop uses streaming for TUI** — Wire the TUI chat screen to display streaming bash output in real-time (currently only the JSONL runner would benefit).
2. **T-0026: `execute_stream()` cleanup** — The existing `execute_stream()` method could be deprecated in favor of `execute(stream_callback=...)`, or refactored to share implementation.
