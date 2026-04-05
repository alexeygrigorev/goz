# goz

A Python coding agent for Z.AI, built as a litehive engine.

goz runs as a CLI tool that accepts prompts, uses tools (file read/write, bash, glob, grep), and outputs JSONL events compatible with the litehive orchestrator.

## Install

```bash
pip install -e .
# or
uv pip install -e .
```

## Usage

### One-shot agent run (litehive engine mode)

```bash
goz run --format json "Implement a hello world function and add tests"
goz run --format json --dir /path/to/repo "Fix the failing test in test_main.py"
goz run --model glm-5.1 --format json "Refactor the config module"
goz run --max-turns 30 --format json "Add input validation"
goz run --resume-session <id> "Continue from where you left off"
```

### CLI commands

```bash
goz vision analyze screenshot.png     # Analyze an image
goz search "python async patterns"    # Web search
goz read https://example.com/article  # Fetch and parse a web page
goz repo tree owner/repo              # Browse GitHub repo structure
goz repo search owner/repo "query"    # Search code in a GitHub repo
goz usage                             # Show Z.AI token usage and quota
goz usage --json                      # Usage stats as JSON
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

## Tools available during `goz run`

- `bash` - Execute shell commands with output capture
- `view_file` - Read files with line numbers
- `create_file` - Create new files
- `str_replace_editor` - Edit files with string replacement
- `glob` - Find files by pattern
- `grep` - Search file contents with regex
- `search` - Z.AI web search
- `read` - Fetch web pages as markdown
- `repo_search`, `repo_tree`, `repo_read` - GitHub repo exploration

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
uv run pytest -q           # Run tests
uv run pytest tests_integration/  # Integration tests (requires API key)
```
