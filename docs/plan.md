# goz - Development Plan

Python Textual TUI rewrite of zai-cli.

## Overview

goz is a terminal user interface (TUI) application that provides Z.AI capabilities:
- Vision analysis (images, diagrams, charts, videos)
- Web search with filtering
- Web reader (URL → markdown)
- GitHub repo exploration
- MCP tool discovery and calling

## Development Process

**See `docs/PROCESS.md` for the complete agent-driven development workflow.**

Quick summary:
- Orchestrator manages agents (PM, SWE, QA) — never writes code
- Issues live in `docs/tracker/` with status in filename
- Task panel tracks pipeline progress
- One agent per issue — always keep work flowing

## Technology Stack

- **Python**: 3.10+
- **TUI**: Textual
- **HTTP**: httpx (async)
- **Validation**: pydantic
- **Testing**: pytest + pytest-asyncio
- **Linting**: ruff

## Project Structure

```
goz/
├── goz/
│   ├── __init__.py
│   ├── __main__.py       # Entry point
│   ├── tui/              # Textual UI
│   ├── api/              # API clients
│   ├── config/           # Configuration
│   └── cli/              # CLI mode
├── tests/
│   ├── test_config.py
│   ├── test_api_*.py
│   └── test_e2e_*.py     # End-to-end integration tests
├── docs/
│   ├── PROCESS.md        # Development process (READ THIS)
│   ├── spec.md           # API and TUI specs
│   └── tracker/          # Issues
└── .claude/agents/       # PM, SWE, QA
```

## Current Issues

| Issue | Status | Description |
|-------|--------|-------------|
| 00 | .done | Code analysis and detailed specification |
| 01 | .todo | Project setup and dependencies |
| 02 | .todo | Config management |
| 03 | .todo | API client foundation |
| 04 | .todo | Vision API |
| 05 | .todo | Search API |
| 06 | .todo | Reader API |
| 07 | .todo | Textual TUI foundation |
| 08 | .todo | Vision command in TUI |
| 09 | .todo | Search/read commands |
| 10 | .todo | CLI mode |
