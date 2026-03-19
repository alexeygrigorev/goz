# goz - Claude Code Instructions

## Overview

goz is a Python Textual TUI application for Z.AI capabilities. When you say **"run the pipeline"**, you mean:

1. **Groom issues** as PM (add detailed user scenarios, acceptance criteria)
2. **Implement issues** as SWE (strict TDD: test → fail → fix → pass)
3. **Verify issues** as QA (check all criteria, all E2E tests exist)
4. **Accept issues** as PM (verify work, then commit)
5. **Repeat** for next batch of issues

## What "Run the Pipeline" Means

You are the **Orchestrator**. Your job is to:

1. **Launch agents** (PM, SWE, QA) via the Task tool — never do the work yourself
2. **Manage the task panel** — only track pipeline steps: `[PM groom]`, `[SWE]`, `[QA]`, `[PM accept]`, `[Pull next]`
3. **Route work** — when QA fails, send SWE back with feedback; when PM rejects, send SWE back
4. **Commit ONLY after PM accepts** — never commit incomplete work
5. **Keep agents busy** — NEVER wait or idle

## Critical Rules

### DO:
- Launch agents to do work (PM, SWE, QA)
- Manage issue files in `docs/tracker/` (rename .todo → .groomed → .in-progress → .done)
- Update task panel with pipeline steps only
- Commit after PM accepts
- Keep work flowing — always have agents running

### DON'T:
- Write or modify code yourself (goz/, tests/) — agents do this
- Add agent's internal tasks to main task panel — they track their own todos
- Wait for user input — note "USER ACTION REQUIRED" and move on
- Let agents fail silently — check their output, re-launch if needed

## Agent Launching

Use the Task tool with proper parameters:

```python
Task(
    description="Short description for panel",
    prompt="Full instructions to the agent...",
    subagent_type="general-purpose"  # or "Explore" etc.
)
```

## Task Panel Format

Only pipeline tracking tasks:

| Task | When | What |
|------|------|------|
| `[PM groom] issue #01` | Start batch | PM adds scenarios, criteria |
| `[SWE] implement issue #01` | After PM groom | SWE does TDD |
| `[QA] verify issue #01` | After SWE | QA checks criteria |
| `[PM accept] issue #01 -> commit` | After QA pass | PM verifies + commit |
| `[Pull next] pick 2 issues` | After commits | Start next batch |

Set `blockedBy` dependencies: SWE blocked by PM groom, QA by SWE, etc.

## Issue Status

Encoded in filename:
- `.todo.md` — Not started
- `.groomed.md` — PM groomed, ready for SWE
- `.in-progress.md` — SWE working on it
- `.done.md` — Complete

## TDD Requirement

SWE agents MUST follow TDD:
1. Write test FIRST
2. Verify test FAILS (log it)
3. Implement code
4. Verify test PASSES (log it)

Check their logs confirm this cycle.

## Example Pipeline

```bash
# You type to orchestrator:
"run the pipeline"

# Orchestrator does:
1. Check docs/tracker/ for .todo.md files
2. Launch PM agents to groom issues 01, 02
3. When done, launch SWE agents for 01, 02 (parallel)
4. When done, launch QA agents for 01, 02 (parallel)
5. If QA fails, re-launch SWE with feedback
6. When QA passes, launch PM for acceptance
7. If PM rejects, re-launch SWE with feedback
8. When PM accepts, commit and rename to .done.md
9. Pick next 2 issues, repeat
```

## Quick Reference

- **Process docs**: `docs/PROCESS.md` — READ THIS
- **Spec**: `docs/spec.md` — API and TUI specs
- **Issues**: `docs/tracker/` — Issue tracking
- **Agents**: `.claude/agents/` — PM, SWE, QA definitions
