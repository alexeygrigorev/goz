# Issue 02: Configuration Management

## Status
.in-progress

## Description
Implement file-based configuration at `~/.config/goz/config.json` with Z.AI credentials.

## User Stories / Use Scenarios

### Scenario 1: First-time user runs `goz` with no existing config

A user has just installed goz and is running it for the first time:

- User has just run `uv sync --dev` to install goz
- User runs `goz` with no arguments
- Application starts and checks for config at `~/.config/goz/config.json`
- Config file does not exist
- Application creates directory `~/.config/goz/` if it doesn't exist
- User sees prompt on terminal: "Enter your Z.AI auth token:"
- User types their token and presses Enter
- User sees confirmation: "Config saved to ~/.config/goz/config.json"
- User sees main TUI menu appear with 4 options (Vision, Search, Read, Doctor)

### Scenario 2: User checks current configuration

A user wants to verify their configuration is set correctly:

- User runs `goz config`
- Application reads `~/.config/goz/config.json`
- User sees output showing:
  - `anthropic_auth_token`: `********` (masked, showing only last 4 chars)
  - `anthropic_base_url`: `https://api.z.ai/api/anthropic`
  - `timeout`: `120`
- Command exits with code 0

### Scenario 3: User updates their auth token

A user's old token expired and they need to update it:

- User runs `goz config set anthropic_auth_token sk-1234567890abcdef`
- Application reads existing config file
- Application updates the `anthropic_auth_token` field
- Application writes updated config back to `~/.config/goz/config.json`
- User sees confirmation: "Config updated successfully"
- Command exits with code 0

### Scenario 4: User runs `goz` with existing valid config

A returning user runs goz after having already configured it:

- User has valid config at `~/.config/goz/config.json`
- User runs `goz` with no arguments
- Application reads config successfully
- No prompt is shown
- Main TUI menu appears immediately

## Tasks
1. Config model with pydantic (anthropic_auth_token, anthropic_base_url, timeout)
2. Load from `~/.config/goz/config.json`
3. Create config directory if missing
4. First-run prompt for token
5. `goz config` command to view/set config

## Acceptance Criteria

1. **Config Path**: Config file is read/written at `~/.config/goz/config.json`
2. **Config Schema**: Valid JSON with fields: anthropic_auth_token (string), anthropic_base_url (string, default), timeout (int, default 120)
3. **First Run Prompt**: When config doesn't exist, prompt user for token
4. **Config Creation**: After prompt, config file is created with entered token and defaults
5. **Silent Loading**: When config exists, no prompt is shown
6. **Config Command**: `goz config` displays current settings
7. **Token Masking**: Token is never printed in plain text (show only last 4 chars as `****1234`)
8. **Config Set**: `goz config set <key> <value>` updates specific field

## QA Requirements

Integration tests (must exist in `tests/test_e2e_config.py`):
- [x] E2E: First run creates `~/.config/goz/config.json` with entered token
- [x] E2E: Subsequent run with existing config skips prompt
- [x] E2E: `goz config` shows masked token (****last4) and other fields
- [x] E2E: `goz config set anthropic_auth_token <token>` updates file
- [x] E2E: Invalid JSON in config file shows clear error message
- [x] E2E: Config directory `~/.config/goz/` is created if missing
- [x] E2E: Token never appears in stdout or stderr unmasked

## Dependencies
Issue 01 (project setup)

## Reference
zai-cli/packages/zai-cli/src/lib/config.ts

## Log

### [PM] 2026-03-19
- Grooming issue 02
- Expanded user stories to 4 detailed multi-step scenarios
- Added 8 specific acceptance criteria
- Defined 7 integration tests for QA verification
- Renamed to .groomed.md

### [Dev] 2026-03-19
- TDD Implementation of Issue 02: Configuration Management

#### Step 1: Test First - Config Model Tests
- Wrote tests for Config pydantic model (test_config_model_*)
- Ran tests - FAIL (implementation didn't exist)
- Implemented Config model with pydantic
- Ran tests - PASS

#### Step 2: Test First - Config Path Tests
- Wrote tests for config path at ~/.config/goz/config.json (test_default_config_path)
- Ran tests - PASS (constants already defined correctly)

#### Step 3: Test First - First Run Tests
- Wrote tests for first run creates config directory (test_first_run_creates_config_directory)
- Ran tests - FAIL (patching issue with DEFAULT_CONFIG_DIR)
- Fixed test to patch DEFAULT_CONFIG_FILE instead
- Implemented _ensure_config_dir() called in __init__
- Ran tests - PASS

- Wrote tests for first run creates config file with token (test_first_run_creates_config_file_with_token)
- Ran tests - ERROR (fixture typo: monkeycaplog -> capsys)
- Fixed fixture typo
- Ran tests - FAIL (sys.stdin.readline() not mockable)
- Changed _prompt_and_create() to use input() instead of sys.stdin.readline()
- Ran tests - PASS

#### Step 4: Test First - Silent Loading Tests
- Wrote tests for existing config loads without prompt (test_existing_config_loads_without_prompt)
- Ran tests - PASS

#### Step 5: Test First - Config Command Tests
- Wrote tests for goz config command shows masked token (test_config_command_shows_masked_token)
- Ran tests - PASS
- Wrote tests for short token masking (test_config_command_short_token_masking)
- Ran tests - PASS

#### Step 6: Test First - Config Set Tests
- Wrote tests for goz config set updates token/base_url/timeout
- Ran tests - PASS (set_config already implemented)

#### Step 7: Test First - Invalid JSON Tests
- Wrote tests for invalid JSON shows error (test_invalid_json_shows_error)
- Ran tests - PASS (JSONDecodeError raised as expected)
- Wrote tests for empty config file (test_empty_config_file_creates_default)
- Ran tests - FAIL (empty file causes JSONDecodeError)
- Added check for empty file (st_size == 0) in load() method
- Ran tests - PASS

#### Step 8: Test First - Token Never Exposed Tests
- Wrote tests for token not in logs (test_token_not_in_logs)
- Ran tests - PASS

#### Step 9: Test First - CLI Config Command Tests
- Wrote tests for goz config CLI command (test_goz_config_shows_current_settings)
- Ran tests - FAIL (command not implemented)
- Implemented cmd_config() function and dispatched to it from main()
- Ran tests - PASS

- Wrote tests for goz config set CLI command (test_goz_config_set_updates_token)
- Ran tests - PASS

- Wrote tests for goz config set invalid key (test_goz_config_set_invalid_key_shows_error)
- Ran tests - FAIL (error printed to stderr, test checked stdout)
- Fixed test to check captured.err instead of captured.out
- Ran tests - PASS

#### Final Results
- All 21 tests PASS
- All 7 QA requirements verified with passing tests
- Implementation complete for Issue 02
