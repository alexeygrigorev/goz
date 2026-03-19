# Issue 01: Project Setup and Dependencies

## Status
.todo

## Description
Set up the goz Python package structure with Textual TUI framework and all required dependencies.

## User Stories / Use Scenarios

1. **Developer clones repo**
   - Runs `uv sync --dev`
   - All dependencies installed
   - Can run `goz --help`

2. **Developer runs tests**
   - Runs `make test`
   - All tests pass

3. **Developer runs linter**
   - Runs `make lint`
   - Code is clean

## Tasks
1. Update pyproject.toml with Textual and other dependencies
2. Create package structure (tui/, api/, config/, cli/)
3. Set up test structure
4. Update Makefile with dev commands

## Acceptance Criteria
1. `uv sync --dev` installs all dependencies
2. `goz --help` shows usage
3. Package structure matches spec
4. Tests can run with `make test`

## QA Requirements
- [ ] End-to-end: Fresh install works
- [ ] End-to-end: `goz --help` displays help
- [ ] End-to-end: `make test` passes (even if empty)
- [ ] End-to-end: `make lint` passes

## Dependencies
None

## Reference
See zai-cli/packages/zai-cli/src/ for original structure
