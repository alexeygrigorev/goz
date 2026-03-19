# goz - Development Plan

Python Textual TUI rewrite of zai-cli.

## Overview

goz is a terminal user interface (TUI) application that provides Z.AI capabilities:
- Vision analysis (images, diagrams, charts, videos)
- Web search with filtering
- Web reader (URL → markdown)
- GitHub repo exploration
- MCP tool discovery and calling

## Development Process (STRICT)

Following the rustkyll agent-driven process with strict QA:

```
.todo.md (PM) → .groomed.md (PM) → .in-progress.md (SWE) → (QA) → .done.md (PM)
                ↓                ↓                ↓
          User Stories      TDD + E2E       Verify tests
          Acceptance        Integration      Check all
          Criteria          Tests            criteria
```

### Phase 1: PM Grooms Issue

PM writes **detailed, multi-step user scenarios** and **specific acceptance criteria**.

**User Story Format** (detailed):
```
1. First-time user with no config runs `goz`
   - User has just cloned the repo and run `uv sync`
   - User runs `goz` with no arguments
   - Application detects no config at `~/.config/goz/config.json`
   - User sees prompt: "Enter your Z.AI auth token:"
   - User enters their token
   - User sees: "Config saved to ~/.config/goz/config.json"
   - User sees main TUI menu with 4 options
   - User presses F1 and sees Vision screen
```

**NOT** this (too vague):
```
1. User runs goz and sees TUI
```

### Phase 2: SWE Implements (TDD + Integration Tests)

**MANDATORY**: For EACH acceptance criterion AND user scenario:
1. Write test FIRST
2. Verify test FAILS
3. Implement code
4. Verify test PASSES

**Integration Tests Required**:
- Every user scenario MUST have an E2E test
- Tests must be in `tests/test_e2e_*.py`
- Test must cover the complete flow

### Phase 3: QA Verifies

**QA checks**:
- [ ] Every acceptance criterion implemented
- [ ] Every user scenario has integration test
- [ ] All tests pass
- [ ] Linting passes
- [ ] TDD log exists and is complete

**If ANY fail → REJECT with specific feedback**

### Phase 4: PM Accepts

**PM checks**:
- [ ] Runs integration tests - they pass
- [ ] Every acceptance criterion verified
- [ ] Manual test if applicable
- [ ] No todos/fixmes

**If ANY fail → REJECT with specific feedback**

## TDD Log Template

SWE must use this format for every criterion/scenario:

```markdown
### [SWE] 2026-03-19

#### Criterion 1: Config file created at exact path
- Wrote: `test_config_file_created_at_exact_path` in tests/test_config.py
- Ran test: FAILS — AssertionError: config file not created
- Implemented: `Config.create()` in goz/config.py
- Ran test: PASSES
- Files modified: goz/config.py, tests/test_config.py

#### Scenario 1: First-time user flow (E2E integration test)
- Wrote: `test_first_run_prompts_and_creates_config` in tests/test_e2e_config.py
- Ran test: FAILS — no prompt shown
- Implemented: `first_run_prompt()` in goz/config.py
- Ran test: PASSES
- Files modified: goz/config.py, tests/test_e2e_config.py

#### Summary
- Tests: 12 passed, 0 failed
- Files: goz/config.py, tests/test_config.py, tests/test_e2e_config.py
```

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
├── docs/tracker/         # Issues
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
