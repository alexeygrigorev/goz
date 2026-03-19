# Issue 09: Search and Read Commands in TUI

## Status
.groomed

## Description
Add interactive search and read command screens to the goz TUI. These screens will provide user-friendly interfaces for web search and web page reading functionality, building on the already-implemented SearchClient and ReaderClient APIs.

## Dependencies
- Issue 05 (Search API) - COMPLETED
- Issue 06 (Reader API) - COMPLETED
- Issue 07 (TUI foundation + main menu) - IN PROGRESS

## User Scenarios

### Scenario 1: Basic Web Search
**User**: Developer researching a technology
**Goal**: Find recent information about Textual TUI framework

**Steps**:
1. User launches `goz` and sees main menu
2. User presses F2 or selects "Search" from menu
3. Search screen appears with query input field
4. User types "Textual TUI Python tutorial" and presses Enter
5. Screen shows loading indicator
6. Results display in a scrollable list:
   - Each result shows: rank, title, URL, summary
   - User can scroll through results with arrow keys or page up/down
7. User presses Esc to return to main menu

### Scenario 2: Search with Filters
**User**: Developer looking for recent documentation from specific domain
**Goal**: Find latest Python documentation from python.org

**Steps**:
1. User navigates to Search screen (F2)
2. User types query: "async await"
3. User optionally sets domain filter: "python.org"
4. User optionally sets recency filter: "oneMonth"
5. User optionally sets count limit: "10"
6. User presses Enter to search
7. Results display showing only python.org results from last month
8. User can select a result to see full details

### Scenario 3: Read Web Page
**User**: Developer wants to read documentation in terminal
**Goal**: Fetch and display a documentation page as markdown

**Steps**:
1. User launches `goz` and presses F3 or selects "Read" from menu
2. Read screen appears with URL input field
3. User pastes: "https://docs.python.org/3/library/asyncio.html"
4. User presses Enter
5. Screen shows loading indicator with timeout countdown
6. Page content displays in scrollable markdown viewer with:
   - Syntax highlighting for code blocks
   - Proper markdown formatting (headers, lists, etc.)
   - Images shown as markdown image syntax
7. User scrolls through content with arrow keys/page up/down
8. User presses Esc to return to main menu

### Scenario 4: Read with Options
**User**: Developer wants plain text output without images
**Goal**: Fetch page content as plain text

**Steps**:
1. User navigates to Read screen (F3)
2. User types URL
3. User toggles format option: "text" instead of "markdown"
4. User toggles "no images" option
5. User presses Enter
6. Content displays as plain text without image references

### Scenario 5: Error Handling - Invalid URL
**User**: Developer mistypes URL
**Goal**: See helpful error message

**Steps**:
1. User navigates to Read screen
2. User types: "example.com" (missing https://)
3. User presses Enter
4. Screen shows error: "URL must start with http:// or https://"
5. User can correct input and try again

### Scenario 6: Error Handling - Search No Results
**User**: Developer searches for very specific term
**Goal**: Handle empty results gracefully

**Steps**:
1. User searches for obscure term with no matches
2. Screen shows message: "No results found. Try a different search term."
3. User can modify query and try again

## Acceptance Criteria

### Search Screen (AC1-AC10)

#### AC1: Search Screen Layout
- Screen has clear title: "Web Search"
- Query input field at top (focus on entry)
- Optional filter section (collapsible or below query):
  - Domain filter input (optional)
  - Recency filter dropdown/select (optional)
  - Count limit input (optional)
- Search button or Enter key to submit
- Results area below input section
- Help hint at bottom showing key bindings

#### AC2: Query Input
- Text input field accepts arbitrary text
- Supports special characters and unicode
- Empty/whitespace-only query shows validation error
- Maximum length reasonable (e.g., 500 characters)

#### AC3: Filter Inputs
- Domain filter: optional text input (e.g., "github.com")
- Recency filter: dropdown with options:
  - No limit (default)
  - One day
  - One week
  - One month
  - One year
- Count: optional number input, defaults to API default

#### AC4: Search Results Display
- Results shown as scrollable list
- Each result displays:
  - Rank number (1-indexed)
  - Title (truncated if too long)
  - URL (truncated if too long, with ellipsis)
  - Summary/snippet (2-3 lines max, truncated with ellipsis)
  - Optional: source domain, publish date
- List uses arrow keys for navigation
- Page up/down for faster scrolling
- Highlight selected result

#### AC5: Loading State
- Show loading indicator during search
- Display "Searching..." text with spinner
- Non-blocking UI (can cancel with Esc)

#### AC6: Empty Results
- When no results found, show friendly message
- Message: "No results found. Try different search terms or filters."
- Option to modify query and retry

#### AC7: Error Display
- Network errors: Show error message with retry option
- Auth errors: Show "Authentication failed. Check API key."
- Validation errors: Show specific error (e.g., "Query cannot be empty")
- All errors allow retry or return to main menu

#### AC8: Result Selection
- User can select a result to view details
- Detail view shows full title, URL, and summary
- Option to copy URL to clipboard (if terminal supports)
- Press Enter to open result in Read screen

#### AC9: Navigation
- Esc: Return to main menu
- Enter: Submit search (when in query field)
- Arrow keys: Navigate results
- Page up/down: Scroll results
- Ctrl+C: Quit application

#### AC10: Search History (Optional/Nice-to-have)
- Remember recent searches in session
- Up/down arrows in query field cycle through history
- Persist history across sessions (optional)

### Read Screen (AC11-AC20)

#### AC11: Read Screen Layout
- Screen has clear title: "Read Web Page"
- URL input field at top (focus on entry)
- Optional options section (collapsible or below URL):
  - Format dropdown: markdown (default) / text
  - No images toggle
  - With links summary toggle
  - Timeout input (default: 20 seconds)
- Read button or Enter key to submit
- Content viewer below input section
- Help hint at bottom showing key bindings

#### AC12: URL Input
- Text input field accepts URLs
- Validates URL starts with http:// or https://
- Shows validation error for invalid URLs
- Supports paste from clipboard

#### AC13: Markdown Rendering
- Markdown content displayed with proper formatting:
  - Headers (# ## ###) shown with different sizes/styles
  - Bold (**text**) and italic (*text*)
  - Code blocks with syntax highlighting (if available)
  - Inline code with distinct style
  - Lists (ordered and unordered)
  - Blockquotes
  - Links as underlined text
  - Images as markdown syntax or alt text

#### AC14: Text Format Display
- When format="text", display plain content
- No markdown rendering applied
- Monospace font for consistency

#### AC15: Loading State
- Show loading indicator during fetch
- Display "Fetching..." text with spinner
- Show timeout countdown if timeout > 5 seconds
- Non-blocking UI (can cancel with Esc)

#### AC16: Error Display
- Network errors: Show error message with retry option
- Timeout errors: Show "Request timed out after X seconds"
- Auth errors: Show "Authentication failed. Check API key."
- Validation errors: Show specific error (e.g., "Invalid URL format")
- 404 errors: Show "Page not found"
- All errors allow retry or return to main menu

#### AC17: Content Navigation
- Arrow keys: Scroll content
- Page up/down: Scroll by page
- Home/End: Jump to top/bottom
- Esc: Return to input/main menu
- Ctrl+C: Quit application

#### AC18: Content Metadata
- Show page title at top of content area
- Show original URL below title
- Optionally show description if available
- Metadata section distinct from content

#### AC19: Large Content Handling
- Handle large pages gracefully (e.g., >100KB)
- Show scroll position indicator (e.g., "Line 45 of 512")
- Jump to line feature (optional): Ctrl+G

#### AC20: Read History (Optional/Nice-to-have)
- Remember recent URLs in session
- Up/down arrows in URL field cycle through history
- Persist history across sessions (optional)

## Technical Implementation Notes

### File Structure
```
goz/
├── goz/
│   ├── tui/
│   │   ├── screens/
│   │   │   ├── __init__.py
│   │   │   ├── search.py      # SearchScreen
│   │   │   └── read.py        # ReadScreen
│   │   └── widgets/
│   │       ├── __init__.py
│   │       └── common.py      # Reusable widgets
```

### Key Components

#### SearchScreen
- Inherits from `textual.screen.Screen`
- Uses `goz.api.SearchClient` for API calls
- Uses `Input` widget for query
- Uses `DataTable` or `ListView` for results
- Async worker for search operation
- Error handling with `MessageBox` or similar

#### ReadScreen
- Inherits from `textual.screen.Screen`
- Uses `goz.api.ReaderClient` for API calls
- Uses `Input` widget for URL
- Uses `Markdown` viewer or `Rich` content display
- Async worker for read operation
- Error handling with `MessageBox` or similar

#### Shared Widgets
- LoadingSpinner: Show during async operations
- ErrorDisplay: Show error messages with retry option
- FilterPanel: Collapsible filter section

### Dependencies to Import
```python
from goz.api import SearchClient, SearchResult, ReaderClient, ReaderResult
from goz.api.errors import AuthError, ApiError, NetworkError, TimeoutError, ValidationError
```

## E2E Test Requirements

### Search Screen E2E Tests
1. **test_search_screen_displays_correctly**
   - Navigate to Search screen
   - Verify all widgets are present

2. **test_basic_search_returns_results**
   - Input query, submit
   - Verify results display correctly

3. **test_search_with_filters**
   - Input query with domain filter
   - Verify filtered results

4. **test_empty_query_validation**
   - Submit empty query
   - Verify error message

5. **test_network_error_handling**
   - Mock network failure
   - Verify error display

6. **test_no_results_message**
   - Mock empty response
   - Verify "no results" message

7. **test_navigation_keys**
   - Test arrow keys, page up/down
   - Verify navigation works

8. **test_esc_returns_to_main**
   - Press Esc on results screen
   - Verify returns to main menu

### Read Screen E2E Tests
1. **test_read_screen_displays_correctly**
   - Navigate to Read screen
   - Verify all widgets are present

2. **test_basic_read_displays_content**
   - Input URL, submit
   - Verify markdown content displays

3. **test_invalid_url_validation**
   - Input invalid URL (missing http://)
   - Verify error message

4. **test_format_option_works**
   - Set format to text
   - Verify plain text output

5. **test_timeout_error_handling**
   - Mock timeout
   - Verify timeout error message

6. **test_large_content_scrollable**
   - Mock large response
   - Verify scrolling works

7. **test_content_navigation**
   - Test arrow keys, page up/down, home/end
   - Verify navigation works

8. **test_esc_returns_to_main**
   - Press Esc on content screen
   - Verify returns to main menu

### Integration E2E Tests
1. **test_search_to_read_workflow**
   - Search, select result
   - Verify Read screen opens with result URL

2. **test_multiple_searches_in_session**
   - Perform multiple searches
   - Verify each works correctly

3. **test_multiple_reads_in_session**
   - Read multiple URLs
   - Verify each works correctly

## Success Metrics
- User can perform web search from TUI within 3 keypresses
- Search results display within 2 seconds of API response
- User can read web page as markdown within 3 keypresses
- Page content displays within 2 seconds of API response
- All error paths show helpful messages with retry option
- Navigation is intuitive with standard keybindings

## Open Questions
1. Should result URLs be clickable/openable in browser? (Terminal dependent)
2. Should search/read history persist across sessions?
3. Should we add syntax highlighting for code in read results?
4. Maximum content size for read results before truncation warning?

## References
- `C:\Users\alexe\git\z\zai-cli\packages\zai-cli\src\commands\search.ts` - TypeScript reference
- `C:\Users\alexe\git\z\zai-cli\packages\zai-cli\src\commands\read.ts` - TypeScript reference
- `C:\Users\alexe\git\z\goz\goz\api\search.py` - Python Search API
- `C:\Users\alexe\git\z\goz\goz\api\reader.py` - Python Reader API
- `C:\Users\alexe\git\z\docs\spec.md` - TUI specification
