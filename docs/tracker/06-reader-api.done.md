# Issue 06: Reader API Implementation - Groomed

## Status
.done

## Description
Implement web reader API for fetching and converting web pages to markdown/text format.
The reader API should support URL fetching with configurable format options, timeout,
and cache controls.

## Dependencies
- Issue 03 (API Client) - Must be completed first

## User Scenarios

### Scenario 1: Basic URL to Markdown Conversion
**User Story**: As a developer, I want to fetch a web page and get its content as markdown
so that I can read documentation without leaving my terminal.

**Steps**:
1. User provides a valid HTTPS URL
2. System validates URL format (must start with http:// or https://)
3. System makes HTTP request to reader API endpoint
4. System returns parsed markdown content
5. Content is displayed to user

**Acceptance Criteria**:
- AC1: URL validation rejects URLs not starting with http:// or https://
- AC2: Successful request returns markdown string
- AC3: Returned content preserves basic markdown formatting (headers, lists, code blocks)
- AC4: Invalid URLs raise `ValidationError` with clear message
- AC5: Network failures raise `NetworkError` with helpful message
- AC6: Auth failures (401/403) raise `AuthError` with config help message

### Scenario 2: Format Selection (Markdown vs Text)
**User Story**: As a user, I want to choose between markdown and plain text output
so that I can get content in the format most useful for my needs.

**Steps**:
1. User provides URL
2. User specifies format preference ("markdown" or "text")
3. System includes format parameter in API request
4. System returns content in specified format

**Acceptance Criteria**:
- AC7: Default format is "markdown" when not specified
- AC8: Format parameter accepts "markdown" or "text" (case-insensitive)
- AC9: Invalid format values raise `ValidationError` with list of valid options
- AC10: Text format strips markdown syntax

### Scenario 3: Timeout Configuration
**User Story**: As a user, I want to configure request timeout so that slow-loading
pages don't hang my terminal session indefinitely.

**Steps**:
1. User provides URL
2. User optionally specifies timeout in seconds
3. System uses configured timeout for the request
4. If timeout exceeded, system raises `TimeoutError`

**Acceptance Criteria**:
- AC11: Default timeout is 20 seconds (matching reference implementation)
- AC12: Timeout parameter accepts positive integer values
- AC13: Timeout of 0 or negative raises `ValidationError`
- AC14: `TimeoutError` includes the timeout value in error message
- AC15: `TimeoutError` includes helpful hint about increasing timeout

### Scenario 4: Cache Control
**User Story**: As a user, I want to bypass cache when fetching frequently updated content
so that I always get the latest version.

**Steps**:
1. User provides URL
2. User sets no_cache=True
3. System includes no_cache flag in API request
4. Server bypasses cache and returns fresh content

**Acceptance Criteria**:
- AC16: Default behavior uses server cache (no_cache=False)
- AC17: no_cache parameter accepts boolean values
- AC18: Parameter name matches spec: `no_cache` (snake_case)

### Scenario 5: Image Retention Control
**User Story**: As a user, I want to control whether images are included in the output
so that I can get cleaner text-only output or full content with images.

**Steps**:
1. User provides URL
2. User sets retain_images preference
3. System includes retain_images in API request
4. Returned content includes or excludes images based on preference

**Acceptance Criteria**:
- AC19: Default behavior retains images (retain_images=True)
- AC20: retain_images parameter accepts boolean values
- AC21: When False, image markdown syntax is removed from output

### Scenario 6: Links Summary
**User Story**: As a researcher, I want to get a summary of all links on a page
so that I can quickly understand what resources are referenced.

**Steps**:
1. User provides URL
2. User sets with_links_summary=True
3. System includes parameter in API request
4. Response includes additional links summary section

**Acceptance Criteria**:
- AC22: Default is False (no links summary)
- AC23: with_links_summary parameter accepts boolean values
- AC24: When True, response includes structured links data

## API Specification

### Module: `goz.api.reader`

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ReaderResult:
    """Result from web reader API.

    Attributes:
        content: The main page content as markdown/text
        title: Page title
        url: Original URL
        description: Page meta description (if available)
    """
    content: str
    title: str
    url: str
    description: str | None = None

class ReaderClient:
    """Client for Z.AI Web Reader API operations."""

    async def read(
        self,
        url: str,
        format: Literal["markdown", "text"] = "markdown",
        timeout: int = 20,
        no_cache: bool = False,
        retain_images: bool = True,
        with_links_summary: bool = False,
    ) -> ReaderResult:
        """Fetch and parse web page content.

        Args:
            url: The URL to fetch (must start with http:// or https://)
            format: Output format - "markdown" or "text" (default: "markdown")
            timeout: Request timeout in seconds (default: 20)
            no_cache: Bypass server cache (default: False)
            retain_images: Include images in output (default: True)
            with_links_summary: Include links summary (default: False)

        Returns:
            ReaderResult with parsed content

        Raises:
            ValidationError: If URL format is invalid or parameters are invalid
            AuthError: For authentication failures (401/403)
            ApiError: For other API errors
            NetworkError: For network failures
            TimeoutError: For request timeouts
        """
```

### Endpoint
- **Path**: `/reader` (relative to `zai_base_url`)
- **Method**: POST
- **Headers**:
  - `Authorization: Bearer {zai_token}`
  - `Content-Type: application/json`
  - `Accept-Language: en-US,en`

### Request Body
```json
{
  "url": "https://example.com",
  "return_format": "markdown",
  "timeout": 20,
  "no_cache": false,
  "retain_images": true,
  "with_links_summary": false
}
```

### Response Body
```json
{
  "id": "req-uuid",
  "created": 1234567890,
  "reader_result": {
    "content": "# Page Title\n\nContent here...",
    "title": "Page Title",
    "url": "https://example.com",
    "description": "Page description",
    "metadata": {}
  }
}
```

## Implementation Tasks

1. **Create `goz/api/reader.py` module**
   - Define `ReaderResult` dataclass
   - Implement `ReaderClient` class
   - Add URL validation helper
   - Add response parsing helper

2. **Update `goz/api/__init__.py`**
   - Export `ReaderClient` and `ReaderResult`

3. **Update `goz/api/client.py` (if needed)**
   - Ensure request method supports reader endpoint
   - Or use existing ZaiApiClient.request method

4. **Create tests in `tests/test_reader.py`**
   - Unit tests for URL validation
   - Unit tests for parameter validation
   - Mock API response tests
   - Error handling tests

## E2E Test Requirements

### Test Case 1: Fetch Public Documentation Page
```
Input: https://docs.python.org/3/
Expected: Success, markdown content returned
Validations:
- Response has content field
- Response has title field
- Content contains markdown headers
```

### Test Case 2: Invalid URL Protocol
```
Input: ftp://example.com
Expected: ValidationError
Validations:
- Error message mentions http:// or https:// requirement
```

### Test Case 3: Timeout on Slow Page
```
Input: https://example.com with timeout=1
Expected: TimeoutError (if page is slow)
Validations:
- Error includes timeout value
```

### Test Case 4: Format Selection
```
Input: URL with format="text"
Expected: Content without markdown syntax
Validations:
- No markdown headers (# ##)
- No markdown code blocks (```)
```

### Test Case 5: Text Format with Links Summary
```
Input: URL with format="text", with_links_summary=True
Expected: Content includes structured links section
Validations:
- Links summary included in output
```

## Edge Cases to Cover

1. **URL Encoding**: URLs with special characters, query parameters, fragments
2. **Redirects**: URLs that redirect (3xx responses)
3. **Large Pages**: Pages with large content (should handle gracefully)
4. **Empty Content**: Pages with minimal content
5. **Non-ASCII**: Pages with unicode content
6. **Malformed HTML**: Poorly formatted HTML pages
7. **Authentication Required**: Pages behind auth (should return error)
8. **Not Found**: 404 pages (should return error)
9. **Server Error**: 5xx responses (should return ApiError)
10. **Network Issues**: DNS failures, connection refused (NetworkError)
11. **Invalid Timeout**: Negative or zero timeout values
12. **Invalid Format**: Values other than "markdown" or "text"
13. **Empty URL**: Empty string URL
14. **Very Long URL**: URLs exceeding typical length

## Integration Points

### Depends On
- **Issue 03 (API Client)**: Uses `ZaiApiClient.request` method
- **Issue 02 (Config)**: Uses `Config` for auth token and base URL
- **goz.api.errors**: All error types (AuthError, ApiError, NetworkError, TimeoutError)

### Used By
- **Issue 09 (TUI Read Screen)**: Will use ReaderClient for TUI read functionality
- **Issue 10 (CLI Commands)**: Will use ReaderClient for `goz read` CLI command

## Definition of Done

- [x] `ReaderClient` class implemented in `goz/api/reader.py`
- [x] `ReaderResult` dataclass defined
- [x] URL validation implemented and tested
- [x] All parameters validated (format, timeout, boolean flags)
- [x] Error handling covers all edge cases
- [x] Unit tests written with pytest
- [x] Tests cover all acceptance criteria
- [x] Module exported from `goz.api`
- [x] Code follows project patterns (async, retry, error handling)
- [x] Documentation in docstrings
- [x] E2E test passes with real API (or mocked)

## Acceptance Report

**Date Accepted**: 2026-03-19

**Tests Passed**: 34/34

### Test Results Summary

All E2E tests passed successfully:

1. **ReaderResult** (3 tests) - Dataclass properly defined with all required fields
2. **ReaderClient Import** (2 tests) - Client is importable and properly exported
3. **Basic URL to Markdown** (5 tests) - URL validation, http/https support, error handling
4. **Format Selection** (5 tests) - Markdown/text formats, case-insensitivity, validation
5. **Timeout Configuration** (5 tests) - Default timeout, custom values, validation
6. **Cache Control** (2 tests) - no_cache parameter works correctly
7. **Image Retention** (2 tests) - retain_images parameter controls image output
8. **Links Summary** (2 tests) - with_links_summary parameter works correctly
9. **Edge Cases** (8 tests) - Query parameters, fragments, unicode, HTTP errors, endpoint path

### Implementation Verified

- Module location: `C:\Users\alexe\git\z\goz\api\reader.py`
- Exports: `ReaderClient`, `ReaderResult` exported from `goz.api`
- Endpoint: `/reader` (relative to base URL)
- All 6 user scenarios implemented with full acceptance criteria coverage
- All 14 edge cases covered by tests
