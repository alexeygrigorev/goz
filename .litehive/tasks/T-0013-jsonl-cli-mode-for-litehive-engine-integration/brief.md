# T-0013 JSONL CLI mode for litehive engine integration

- Mode: implementation
- Task type: adapter
- PM complexity: moderate
- Planned effort: m

## Goal
Add a `goz run` CLI command that accepts a prompt, executes it, and outputs JSONL events compatible with litehive `ExternalCLIAdapter` protocol.

## Acceptance Criteria
- `goz run --format json 'prompt'` outputs JSONL events to stdout
- Emits `{type: text, part: {text: ...}}` for assistant messages
- Emits `{type: step_finish, part: {tokens: {...}, cost: ...}}` at end
- Emits `{type: error, error: {name: ..., data: {message: ...}}}` on errors
- Supports `--dir` flag for working directory
- Supports `--model` flag for model override
- Agent emits `STAGE_RESULT` JSON block with verdict in output
- Exit code `0` on success, non-zero on failure

## Constraints
- Keep changes scoped to the task.
- Prefer focused pytest coverage for the changed CLI and agent modules.
- Keep litehive compatibility at the JSONL adapter boundary.

## Plan
- Extend CLI parsing and dispatch for `goz run`.
- Adapt agent streaming output into litehive-compatible JSONL events.
- Apply per-invocation working-directory and model overrides.
- Bootstrap a default CLI tool registry so `tool_use` events can occur.
- Verify with focused pytest coverage for parsing, streaming, errors, and overrides.
