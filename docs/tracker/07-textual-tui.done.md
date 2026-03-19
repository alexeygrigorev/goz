# Issue 07: Textual TUI Foundation - Groomed Specification

## Status
.done

## Overview
Implement a minimal but functional Textual TUI application for goz that allows users to interactively select between vision, search, and read commands, provide input parameters, and view results.

## Dependencies
- Issue 01 (project setup) - Done
- Issue 02 (config management) - Done
- Issue 03 (API client) - Done

**BLOCKER**: Config field mismatch - VisionClient expects `anthropic_auth_token` but Config uses `zai_token`. Must be resolved before TUI implementation.

---

## Detailed User Scenarios

### Scenario 1: First Launch and Main Menu

**User Goal**: Start the TUI and see available commands

**Steps**:
1. User runs `goz` (no arguments)
2. TUI launches in terminal
3. User sees main menu with command options:
   - Vision (analyze images/screenshots)
   - Search (web search)
   - Read (fetch web pages)
   - Doctor (check connection)
4. User can navigate with F-keys or arrow keys
5. User sees hints: "Press F1-F4 to select, q to quit, Ctrl+C to exit"

**Acceptance**:
- Main menu displays with all 4 commands
- Each command has a brief description
- F1-F4 keys work for selection
- q and Ctrl+C exit the application
- No errors on startup if config exists

---

### Scenario 2: Vision Command - Image Analysis

**User Goal**: Analyze an image file

**Steps**:
1. User selects Vision from main menu (F1)
2. Vision screen opens with input fields:
   - Image path (required)
   - Prompt (optional, defaults to "Analyze this image")
   - Mode selector: analyze, ui-to-code, extract-text, diagnose-error
3. User enters image path: `./screenshot.png`
4. User selects mode: "analyze"
5. User presses Enter to submit
6. Loading indicator shows while API call is in progress
7. Results display in scrollable text area
8. User presses Esc to return to main menu

**Acceptance**:
- All input fields are visible and labeled
- Image path validation occurs before API call
- Loading state is visible during API call
- Results display in scrollable view
- Errors (file not found, API error) display in modal, not crash
- Esc returns to main menu

**Edge Cases**:
- Image file doesn't exist -> Show error modal
- Image file too large (>5MB) -> Show error modal
- Invalid image format -> Show error modal
- API timeout -> Show timeout error with retry option
- Network error -> Show error with "check connection" message
- Empty prompt -> Use default prompt
- Prompt contains special chars -> Handle correctly

---

### Scenario 3: Search Command - Web Search

**User Goal**: Search the web and view results

**Steps**:
1. User selects Search from main menu (F2)
2. Search screen opens with input fields:
   - Query (required)
   - Domain filter (optional)
   - Recency filter (optional, dropdown)
   - Count limit (optional, number input)
3. User enters query: "Python Textual tutorial"
4. User optionally sets recency to "oneWeek"
5. User presses Enter to submit
6. Loading indicator shows
7. Results display as list:
   - Each result shows: rank, title, URL, summary
   - Results are selectable for detail view
8. User can scroll through results
9. User presses Esc to return to main menu

**Acceptance**:
- All input fields are visible and labeled
- Query validation (not empty) before API call
- Recency dropdown shows valid options: oneDay, oneWeek, oneMonth, oneYear, noLimit
- Results display in formatted list
- URLs are visible and selectable
- Empty results show "No results found" message
- Esc returns to main menu

**Edge Cases**:
- Empty query -> Show validation error
- Invalid domain format -> Show validation error
- No results -> Show "No results found" message
- API error -> Show error modal with details
- Network error -> Show error with retry option
- Very long URLs -> Truncate with ellipsis for display

---

### Scenario 4: Read Command - Fetch Web Page

**User Goal**: Fetch and read a web page

**Steps**:
1. User selects Read from main menu (F3)
2. Read screen opens with input fields:
   - URL (required)
   - Format (optional, dropdown: markdown, text)
   - Timeout (optional, number, default 20)
3. User enters URL: `https://example.com/docs`
4. User leaves format as default (markdown)
5. User presses Enter to submit
6. Loading indicator shows
7. Page content displays in scrollable markdown view
8. User can scroll through long content
9. User presses Esc to return to main menu

**Acceptance**:
- All input fields are visible and labeled
- URL validation (http:// or https://) before API call
- Format dropdown shows valid options
- Markdown content renders with basic formatting
- Long content is scrollable
- Esc returns to main menu

**Edge Cases**:
- Invalid URL format -> Show validation error
- Empty URL -> Show validation error
- Page not found (404) -> Show error from API
- Timeout -> Show timeout error with retry option
- Very large content -> Handle gracefully with scroll
- Malformed HTML/API error -> Show error modal

---

### Scenario 5: Doctor Command - Connection Check

**User Goal**: Verify API connection and configuration

**Steps**:
1. User selects Doctor from main menu (F4)
2. Doctor screen runs checks:
   - Config file exists
   - API token is present
   - Base URL is reachable
3. Results display with status indicators:
   - Green checkmark for passing checks
   - Red X for failing checks
   - Error messages for failures
4. User can press Esc to return to main menu

**Acceptance**:
- All checks run automatically
- Results display with clear pass/fail indicators
- Errors include helpful messages
- Esc returns to main menu

**Edge Cases**:
- Config missing -> Show "Config not found" with setup instruction
- Token missing -> Show "No API token" with setup instruction
- Network unreachable -> Show "Cannot reach API" with network check hint
- Invalid token -> Show auth error with token refresh hint

---

### Scenario 6: Error Handling Throughout

**User Goal**: Application gracefully handles errors

**Steps**:
1. Any error occurs during operation
2. Error modal/overlay displays:
   - Error type (AuthError, ApiError, NetworkError, etc.)
   - Error message
   - Suggested action
3. User presses any key or Enter to dismiss
4. User can retry or return to main menu

**Acceptance**:
- No traceback visible to user
- Error messages are human-readable
- Auth errors suggest checking token
- Network errors suggest checking connection
- Validation errors show the specific field with issue

---

## E2E Test Requirements

### Test 1: Basic Navigation Flow
```bash
# Test that app starts and exits cleanly
goz
# Expect: Main menu appears
# Press q
# Expect: Clean exit, no errors
```

### Test 2: Vision Flow with Valid Input
```bash
goz
# Navigate to Vision (F1)
# Enter: ./test_image.png
# Select mode: analyze
# Press Enter
# Expect: Loading, then results display
# Press Esc
# Expect: Back to main menu
```

### Test 3: Vision Flow with Invalid File
```bash
goz
# Navigate to Vision (F1)
# Enter: ./nonexistent.png
# Press Enter
# Expect: Error modal "File not found"
# Dismiss error
# Expect: Back to Vision screen
```

### Test 4: Search Flow
```bash
goz
# Navigate to Search (F2)
# Enter query: "test query"
# Press Enter
# Expect: Loading, then results list
# Press Esc
# Expect: Back to main menu
```

### Test 5: Search with Empty Query
```bash
goz
# Navigate to Search (F2)
# Leave query empty
# Press Enter
# Expect: Validation error "Query cannot be empty"
```

### Test 6: Read Flow
```bash
goz
# Navigate to Read (F3)
# Enter URL: https://example.com
# Press Enter
# Expect: Loading, then markdown content
# Press Esc
# Expect: Back to main menu
```

### Test 7: Doctor Check
```bash
goz
# Navigate to Doctor (F4)
# Expect: Status checks run
# Expect: Pass/fail indicators
# Press Esc
# Expect: Back to main menu
```

### Test 8: Config Missing Scenario
```bash
# Remove config file
rm ~/.config/goz/config.json
goz
# Expect: Prompt for API token
# Enter token
# Expect: Main menu appears
```

---

## Screen Specifications

### Main Screen (MainMenu)
```
┌─────────────────────────────────────────────────────────┐
│ goz - Z.AI Tools                         v0.1.0         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   [F1] Vision    Analyze images and screenshots         │
│   [F2] Search    Search the web                        │
│   [F3] Read      Fetch and read web pages              │
│   [F4] Doctor    Check API connection                  │
│                                                         │
│   [q] Quit    [Ctrl+C] Force Exit                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Vision Screen (VisionScreen)
```
┌─────────────────────────────────────────────────────────┐
│ Vision Analysis                         [Esc] Back      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Image Path: [_________________________]                 │
│                                                         │
│ Mode: [analyze ▼]                                      │
│   o analyze      General image description             │
│   o ui-to-code   Convert UI to code                    │
│   o extract-text Extract text from image               │
│   o diagnose-error Analyze error screenshot            │
│                                                         │
│ Prompt (optional):                                     │
│ [_________________________________________]             │
│ [_________________________________________]             │
│                                                         │
│ [Enter] Analyze    [Esc] Cancel                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Vision Results (VisionResultScreen)
```
┌─────────────────────────────────────────────────────────┐
│ Vision Results                           [Esc] Back      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ This image shows a modern web interface with...         │
│                                                         │
│ [scrollable content area]                               │
│                                                         │
│                                                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Search Screen (SearchScreen)
```
┌─────────────────────────────────────────────────────────┐
│ Web Search                                [Esc] Back      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Query: [___________________________________]            │
│                                                         │
│ Domain (optional): [___________________]                │
│                                                         │
│ Recency: [no limit ▼]                                  │
│   o noLimit     All time                               │
│   o oneDay      Past 24 hours                          │
│   o oneWeek     Past week                              │
│   o oneMonth    Past month                             │
│   o oneYear     Past year                              │
│                                                         │
│ Count (optional): [__]                                 │
│                                                         │
│ [Enter] Search    [Esc] Cancel                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Search Results (SearchResultScreen)
```
┌─────────────────────────────────────────────────────────┐
│ Search Results (5)                        [Esc] Back     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1. Python Textual Documentation                         │
│    https://textual.textual.io...                        │
│    Textual is a TUI framework for Python...             │
│                                                         │
│ 2. Building Terminal UIs with Textual                   │
│    https://example.com/textual-tut...                   │
│    Learn to create beautiful terminal...                │
│                                                         │
│ 3. Textual vs Rich vs PromptToolkit                     │
│    https://example.com/comparison...                    │
│    Comparison of Python TUI libraries...                │
│                                                         │
│ [scroll for more results]                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Read Screen (ReadScreen)
```
┌─────────────────────────────────────────────────────────┐
│ Web Reader                                [Esc] Back      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ URL: [_____________________________________]            │
│                                                         │
│ Format: [markdown ▼]                                   │
│   o markdown                                           │
│   o text                                               │
│                                                         │
│ Timeout (sec): [20]                                    │
│                                                         │
│ [Enter] Fetch    [Esc] Cancel                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Doctor Screen (DoctorScreen)
```
┌─────────────────────────────────────────────────────────┐
│ Doctor - Connection Check                 [Esc] Back      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ [PASS] Config file found                               │
│ [PASS] API token present                               │
│ [PASS] Base URL reachable                              │
│                                                         │
│ All checks passed! goz is ready to use.                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Technical Implementation Notes

### File Structure
```
goz/tui/
├── __init__.py
├── app.py              # GozApp main class
├── screens/
│   ├── __init__.py
│   ├── main.py         # MainMenu screen
│   ├── vision.py       # VisionScreen + VisionResultScreen
│   ├── search.py       # SearchScreen + SearchResultScreen
│   ├── read.py         # ReadScreen + ReadResultScreen
│   └── doctor.py       # DoctorScreen
└── widgets/
    ├── __init__.py
    └── common.py       # Reusable widgets (Input, Select, etc.)
```

### Textual Components to Use
- `App`: Main application class
- `Screen`: Individual screens
- `Button`: Command selection
- `Input`: Text input fields
- `Select`: Dropdown selectors
- `TextArea`: Scrollable result display
- `Label`: Static text
- `Static`: Container for layout
- `Header`/`Footer`: Screen chrome

### Key Features
- Async operation for API calls (use `work()` method)
- Loading overlays during API calls
- Error modals for exception handling
- Keyboard navigation (F-keys, Esc, Enter)
- Screen stack for navigation

### API Integration Points
- `VisionClient.analyze(source, prompt)` -> VisionScreen
- `SearchClient.search(query, ...)` -> SearchScreen
- `ReaderClient.read(url, ...)` -> ReadScreen
- `ConfigManager` for setup verification -> DoctorScreen

---

## Open Questions / Decisions Needed

1. **Config Field Mismatch**: VisionClient expects `anthropic_auth_token` but Config uses `zai_token`
   - Resolution needed before TUI implementation starts
   - Options: Update Config fields or update VisionClient

2. **TUI Testing Strategy**: How to E2E test TUI without human interaction?
   - Option A: Use Textual's pilot testing (internal testing API)
   - Option B: Mock interactions with pytest
   - Recommendation: Use pytest + textual.pilot for automated tests

3. **Markdown Rendering**: How to render markdown in Read results?
   - Option A: Use `rich` library with `Markdown` widget
   - Option B: Plain text with basic formatting
   - Recommendation: Start with plain text, add rich rendering later

4. **Image Input**: How to input images in TUI?
   - MVP: File path input only
   - Future: Clipboard paste, drag-drop (if Textual supports)
   - Recommendation: File path input for MVP

---

## Definition of Done

- [x] All 4 command screens implemented (Vision, Search, Read, Doctor)
- [x] Main menu with F-key navigation
- [x] Input validation before API calls
- [x] Loading states during API calls
- [x] Error handling with user-friendly messages
- [x] Results display in scrollable views
- [x] Esc navigation back to main menu
- [x] Clean exit on q or Ctrl+C
- [x] Unit tests for screen navigation
- [x] Integration tests with mocked API clients
- [x] Manual E2E test pass
- [x] Documentation updated with TUI usage examples

## Log

### [PM] 2026-03-19
- Reviewed groomed specification
- All 270 tests pass
- Linting passes (ruff check goz/)
- Issue accepted and moved to .done.md
