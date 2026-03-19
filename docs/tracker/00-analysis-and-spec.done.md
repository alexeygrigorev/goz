# Issue 00: Code Analysis and Detailed Specification

## Status
.done

## Summary

Completed full analysis of zai-cli TypeScript codebase and created Python TUI specification.

## Key Findings

### Original Architecture (zai-cli)
- **MCP Protocol**: Uses UTCP SDK for MCP (Model Context Protocol)
- **Commands**: vision, search, read, repo, tools, tool, call, doctor, code
- **Config**: Environment-based (Z_AI_API_KEY, Z_AI_MODE, etc.)
- **Error Handling**: Custom types (AuthError, ValidationError, ApiError, NetworkError, TimeoutError)
- **Output Modes**: data (raw), json (wrapped), pretty (formatted)

### Python Implementation Strategy
- **Simplicity**: Direct HTTP API calls instead of full MCP
- **Core Features**: vision, search, read (MVP)
- **Dual Mode**: CLI + TUI
- **Tech Stack**: Textual, httpx, pydantic

## Deliverables

1. ✅ API Module Spec - HTTP client, types, error handling
2. ✅ Config Module Spec - File format, loading, validation
3. ✅ TUI Architecture Spec - Screens, widgets, navigation
4. ✅ Command Specs - Each command's workflow
5. ✅ Issue List - Complete implementation plan

## Files Created

- `docs/spec.md` - Full specification
- Updated `docs/plan.md` with issue list

## Acceptance Criteria

1. ✅ All command files analyzed with feature extraction
2. ✅ API types documented in Python equivalents
3. ✅ Config spec written (env vars, loading)
4. ✅ TUI architecture spec written (screens, widgets, state)
5. ✅ Updated issue list with dependencies

---

## QA Verification

**Date**: 2026-03-19
**Tests**: N/A (specification only)
**Lint**: N/A
**Acceptance Criteria**: All met
**Verdict**: PASS

---

## PM Decision

ACCEPT - Specification complete. Ready to begin implementation.
