# goz

A Python coding agent for Z.AI.

`goz run` is a general-purpose prompt executor that can be used directly or as a Litehive engine. In JSON mode it emits a stable JSONL event stream that external orchestrators can consume without depending on Litehive-specific verdict text.

## Install

```bash
cd ~/git/goz
python3 -m venv .venv
.venv/bin/pip install -e .
```

Create a launcher in `~/bin/goz` that calls the module directly from the
project virtualenv:

```bash
#!/usr/bin/env bash
set -euo pipefail

exec "$HOME/git/goz/.venv/bin/python" -m goz "$@"
```

Make it executable and ensure `~/bin` is on your `PATH`:

```bash
chmod +x ~/bin/goz
goz --help
```

## Usage

### One-shot agent run

```bash
goz run --format json "Implement a hello world function and add tests"
goz run --format json --dir /path/to/repo "Fix the failing test in test_main.py"
goz run --model glm-5.1 --format json "Refactor the config module"
goz run --max-turns 30 --format json "Add input validation"
goz run --resume-session <id> "Continue from where you left off"
```

### `goz run` JSONL contract

`goz run --format json` emits newline-delimited JSON events. External callers should treat these event types as the stable contract:

- `text`: assistant text output. This is plain streamed text and may contain any content; callers should not require `STAGE_RESULT` or any other verdict-shaped payload unless they explicitly own that prompt contract.
- `tool_use`: a completed tool invocation with the tool name, parsed input, output, and error status.
- `step_finish`: the terminal event for the run. It includes token and cost accounting, the session ID, and a continuation payload for resumable orchestration.

The `step_finish.part.continuation` payload is stable and shaped like:

```json
{
  "resume_session_id": "<session-id>"
}
```

That payload can be passed back to `goz run --resume-session <session-id>` by Litehive or any other orchestrator.

### CLI commands

```bash
goz vision analyze screenshot.png     # Analyze an image
goz search "python async patterns"    # Web search
goz read https://example.com/article  # Fetch and parse a web page
goz repo tree owner/repo              # Browse GitHub repo structure
goz repo search owner/repo "query"    # Search code in a GitHub repo
goz usage                             # Show Z.AI quota and token usage
goz usage --json                      # Usage stats as JSON
goz models                            # List available Z.AI models with pricing
goz doctor                            # Check API connectivity
goz config get zai_token              # View config
```

### Interactive TUI

```bash
goz        # Launch the interactive terminal UI
goz tui    # Same thing
```

## litehive engine

goz is registered as a litehive engine. To use it in a litehive workspace:

```yaml
# .litehive/config.yaml
default_engine: goz
engine_fallbacks:
  goz:
    - opencode
    - codex
```

Or per-task:

```bash
litehive add "Some task" --engine goz
litehive run
```

## Tools

These tools are available to the agent during `goz run`:

- `bash` - Execute shell commands with output capture
- `view_file` - Read files with line numbers and optional line range
- `write_file` - Create or overwrite files
- `str_replace_editor` - Targeted text replacement in existing files
- `glob` - Find files by pattern (e.g. `**/*.py`)
- `grep` - Search file contents with regex
- `search` - Z.AI web search
- `read` - Fetch web pages as markdown
- `repo_search`, `repo_tree`, `repo_read` - GitHub repo exploration

## Quota and usage

Check your Z.AI quota and token usage:

```
$ goz usage
Plan: max

API calls (5h window):
  Limit:     4.0k
  Used:      10 (1%)
  Remaining: 4.0k

Token quota (3h window):
  Used: 3% (resets 2026-04-05 15:49)
```

## Configuration

Config lives at `~/.config/goz/config.json`:

```json
{
  "zai_token": "your-z-ai-api-key",
  "chat_model": "glm-5-turbo",
  "vision_model": "glm-4.6v"
}
```

Set your token on first run, or:

```bash
goz config set zai_token <your-key>
```

## Development

```bash
uv run pytest -q                      # Run tests
uv run pytest tests_integration/      # Integration tests (requires API key)
```
