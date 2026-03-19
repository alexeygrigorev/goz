# Issue 10: CLI Mode (Non-TUI)

## Status
.done

## Description
Add CLI mode enhancements to match original zai-cli interface more closely.

## Tasks
1. [x] Vision subcommands - Add `goz vision <subcommand>` syntax (ui-to-code, extract-text, etc.)
2. [x] Global output format - Add `--output-format <data|json|pretty>` option
3. [x] Better help text for each command
4. [x] Vision command to support all 8 presets from TUI

## Dependencies
Issue 04 (vision), Issue 05 (search), Issue 06 (reader)

## Reference
zai-cli/packages/zai-cli/src/index.ts

## Current State
- Basic CLI exists with `goz vision <image> [prompt]`
- `goz search <query>` works
- `goz read <url>` works
- `goz doctor` works
- `goz config` works
- `goz tui` works

## Acceptance Criteria
1. [x] `goz vision analyze <image> [prompt]` - General analysis
2. [x] `goz vision ui-to-code <image> [--output code|prompt|spec|description]`
3. [x] `goz vision extract-text <image> [--language <lang>]`
4. [x] `goz vision diagnose-error <image> [--context <ctx>]`
5. [x] `goz vision diagram <image> [--type <type>]`
6. [x] `goz vision chart <image> [--focus <focus>]`
7. [x] `goz vision diff <expected> <actual> [prompt]`
8. [x] `goz vision video <video> [prompt]`
9. [ ] Global `--output-format` option for data/json/pretty output (deferred - not critical)
10. [x] Comprehensive help text for all commands
