# Issue 11: Config Command

## Status
.done

## Description
Add `goz config` CLI command enhancements to view and set configuration.

## Tasks
1. [x] `goz config` - Show current config (already implemented)
2. [x] `goz config set <key> <value>` - Set a value (already implemented)
3. [x] `goz config get <key>` - Get a single value
4. [x] `goz config edit` - Open config in editor
5. [x] `goz config list` - List all config keys and descriptions

## Dependencies
Issue 02 (config module)

## Current State
- `goz config` - Shows current config via ConfigManager.show_config()
- `goz config set <key> <value>` - Sets values via ConfigManager.set_config()

## Acceptance Criteria
1. [x] `goz config` displays all current config values
2. [x] `goz config set <key> <value>` sets a config value
3. [x] `goz config get <key>` retrieves and displays a single value
4. [x] `goz config edit` opens config in $EDITOR
5. [x] `goz config list` lists all available keys with descriptions
6. [x] Error handling for invalid keys
