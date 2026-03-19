# Issue 02: Configuration Management

## Status
.todo

## Description
Implement file-based configuration at `~/.config/goz/config.json` with Z.AI credentials.

## User Stories / Use Scenarios

1. **First-time user runs `goz`**
   - Config file doesn't exist
   - Prompt: "Enter your Z.AI auth token:"
   - Create `~/.config/goz/config.json` with default settings
   - Launch TUI

2. **User wants to check config**
   - Runs `goz config`
   - Shows current config (token masked)

3. **User wants to change token**
   - Runs `goz config set anthropic_auth_token <token>`
   - Token updated in file

4. **User has existing config**
   - Runs `goz`
   - Config loaded automatically
   - No prompts

## Tasks
1. Config model with pydantic (anthropic_auth_token, anthropic_base_url, timeout)
2. Load from `~/.config/goz/config.json`
3. Create config directory if missing
4. First-run prompt for token
5. `goz config` command to view/set config

## Acceptance Criteria
1. Config file created at `~/.config/goz/config.json`
2. Token prompted on first run
3. Config loads silently on subsequent runs
4. `goz config` shows current settings
5. Token is masked when displayed

## QA Requirements
- [ ] End-to-end: First run creates config
- [ ] End-to-end: Subsequent runs load config
- [ ] End-to-end: `goz config set` updates file
- [ ] Token never printed in plain text

## Dependencies
Issue 01 (project setup)

## Reference
zai-cli/packages/zai-cli/src/lib/config.ts
