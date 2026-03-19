# goz - Development Process

Python Textual TUI rewrite of zai-cli.

## Overview

goz is a terminal user interface (TUI) application that provides Z.AI capabilities:
- Vision analysis (images, diagrams, charts, videos)
- Web search with filtering
- Web reader (URL → markdown)
- GitHub repo exploration
- MCP tool discovery and calling

## Orchestrator Role

The orchestrator (top-level Claude Code session) is a **MANAGER**, not an implementer. It:

- Launches agents (PM, SWE, QA) and routes work between them
- Routes rejection feedback: QA fail → SWE fixes, PM reject → SWE fixes
- Commits code **ONLY after PM accepts**
- Picks next issues from the backlog
- Creates task panel items to track pipeline progress

**The orchestrator NEVER writes or modifies code** (goz/, tests/). It only touches:
- `docs/tracker/` files (creating issues, status transitions)
- Task panel items
- Git commits (after PM accepts)

**NEVER wait. NEVER idle.** The pipeline must always be running:
- After committing, immediately pick the next issues
- If user input needed, note "USER ACTION REQUIRED" and move on
- Keep agents busy at ALL times

## Issue Lifecycle

```
PM grooms (.todo)  ->  Engineer builds (.in-progress)  ->  Tester verifies  ->  PM accepts (.done)
```

### File-Based Status

| Status | Filename Pattern | Meaning |
|--------|-----------------|---------|
| Todo | `01-name.todo.md` | Not started, needs PM grooming |
| Groomed | `01-name.groomed.md` | PM groomed, ready for engineer |
| In Progress | `01-name.in-progress.md` | Engineer working on it |
| Done | `01-name.done.md` | PM accepted, complete |

### Status Transitions

```
.todo.md  -->  PM grooms  -->  .groomed.md  -->  Engineer picks up  -->  .in-progress.md
                                                      |
                                              Engineer + QA + PM pass
                                                      |
                                                      v
                                                 .done.md
```

## Agent Workflow

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

**Acceptance Criteria** (specific, testable):
```
1. Config file created at exact path `~/.config/goz/config.json`
2. Config file contains valid JSON with 3 fields
3. Token is never printed to stdout/stderr
4. On second run, no prompt appears
5. Invalid JSON in config file shows clear error
```

**QA Requirements** (integration tests that must exist):
```
- [ ] E2E: First run creates config with entered token
- [ ] E2E: Second run skips prompt
- [ ] E2E: Invalid token shows error
- [ ] E2E: `goz config` shows masked token
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

## Full Pipeline

1. **PM Grooms**: Pick `.todo.md`, add acceptance criteria/test scenarios, rename to `.groomed.md`
2. **Pick 2 issues**: Select lowest-numbered `.groomed.md` issues with deps met
3. **SWE implements**: Follow TDD, rename to `.in-progress.md`
4. **QA reviews**: Run tests, verify acceptance criteria, report PASS/FAIL
5. **QA FAIL?** → Launch SWE with feedback → QA re-verifies → repeat until PASS
6. **QA PASS?** → Launch PM for acceptance
7. **PM REJECT?** → Launch SWE with feedback → QA re-verifies → PM re-reviews → repeat
8. **PM ACCEPT?** → Orchestrator renames to `.done.md` and commits
9. **Pick next 2** and repeat

### Done Means DONE

An issue moves to `.done.md` **ONLY** when ALL acceptance criteria are fully satisfied and verified.

- "Publish to PyPI" is done when wheels are on PyPI and `pip install` works — not when the build is written
- "TUI renders" is done when the TUI actually displays correctly — not when the code compiles

If deliverable requires external verification, issue stays `.in-progress.md` until verified.

## TDD (Mandatory)

SWE agents MUST follow strict TDD for EVERY fix:

1. **Write test FIRST** — before any implementation
2. **Run test and verify it FAILS** — log the failure
3. **Implement fix** — minimum code to pass
4. **Run test and verify it PASSES** — log the success
5. **Repeat** for each distinct fix

SWE MUST log each step in the issue file's `## Log` section:

```markdown
### [SWE] 2026-03-19
- Wrote: `test_config_creation` (tests/test_config.py)
- Ran test: FAILS — AssertionError: file not created
- Implemented: `Config.create()` (goz/config.py)
- Ran test: PASSES
- Files: goz/config.py, tests/test_config.py
```

**One agent per issue.** Never combine multiple issues.

### Integration Tests Required

Every user scenario MUST have an E2E test in `tests/test_e2e_*.py` covering the complete flow.

## Rejection Loop

```
QA FAIL  -->  SWE fixes (with QA feedback)  -->  QA re-verifies  -->  repeat until PASS
PM REJECT --> SWE fixes (with PM feedback)  -->  QA re-verifies  -->  PM re-reviews --> repeat until ACCEPT
```

The orchestrator launches a new SWE agent with rejection details — does NOT fix code itself.

## Issue Log (Communication)

Every agent MUST append to the issue file's `## Log` section:

```markdown
## Log

### [SWE] 2026-03-19 12:30
- Started implementation
- Root cause: X
- Fixed: Y
- Tests: 12 passed, 0 failed
- Files: goz/config.py, tests/test_config.py

### [QA] 2026-03-19 13:15
- All tests pass
- Criteria 1-4: PASS
- Criterion 5: FAIL — Z
- VERDICT: FAIL

### [SWE] 2026-03-19 13:45
- Fixed issue Z
- Tests: 15 passed, 0 failed

### [QA] 2026-03-19 14:00
- All criteria pass
- VERDICT: PASS

### [PM] 2026-03-19 14:30
- Reviewed, verified
- VERDICT: ACCEPT
```

## No Silent Descoping

PM must NEVER silently drop acceptance criteria:
1. Explicitly note what is being descoped and why
2. Create new `.todo.md` issue(s) for descoped work
3. Make descoped items traceable to original issue

Orchestrator verifies PM acceptance doesn't silently drop criteria.

## Task Panel (Pipeline Tracking)

The orchestrator MUST use the Task panel to track every pipeline step.

### Task Panel Items

| Task Subject | Meaning |
|---|---|
| `[PM groom] issue #01` | PM grooming issue 01 |
| `[SWE] implement issue #01` | Engineering issue 01 |
| `[QA] verify issue #01` | Testing issue 01 |
| `[PM accept] issue #01 -> commit` | Acceptance + commit |
| `[Pull next] pick 2 issues` | Get more work |

### Setting Up a Batch (2 issues in parallel)

```
[PM groom #01] ──> [SWE #01] ──> [QA #01] ──> [PM accept #01] ──┐
                                                           │
                                                           +──> [Pull next]
                                                           │
[PM groom #02] ──> [SWE #02] ──> [QA #02] ──> [PM accept #02] ──┘
```

Set blockedBy dependencies: SWE blocked by PM groom, QA by SWE, PM accept by QA.

Launch parallel agents: 2 SWE agents simultaneously, then 2 QA agents, etc.

## How to Pick Issues

1. List `.groomed.md` files in `docs/tracker/`
2. Pick lowest-numbered issues first (more foundational)
3. Check dependencies — don't start until deps are `.done.md`
4. Pick 2 independent issues at a time

## Technology Stack

- **Python**: 3.10+
- **TUI**: Textual
- **HTTP**: httpx (async)
- **Validation**: pydantic
- **Testing**: pytest + pytest-asyncio
- **Linting**: ruff

## Development Commands

```bash
make test           # Run all tests
make coverage       # With coverage report
make lint           # Run ruff
make format         # Format code
make shell          # Enter dev environment
```

## Conventions

- Every issue must include tests
- Lint with `make lint` before committing
- Commit message: "Implement issue 01: project setup"
- Only commit after PM accepts
- Issues are NEVER deleted — move through status transitions

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
