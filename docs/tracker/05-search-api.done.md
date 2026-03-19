# Issue 05: Search API Implementation

## Status
.done

## Description
Implement web search API with domain and recency filtering for Python goz application. This module provides web search capabilities using Z.AI WebSearchPrime API, supporting query-based search, result count limiting, domain filtering, and time-based filtering.

## Dependencies
Issue 03 (API client foundation) - .done

## Reference Implementation
- `zai-cli/packages/zai-cli/src/lib/api-client.ts` - `webSearch()` method (lines 241-256)
- `zai-cli/packages/zai-cli/src/lib/mcp-client.ts` - `webSearch()` method (lines 395-420)
- `zai-cli/packages/zai-cli/src/commands/search.ts` - Search command implementation (lines 1-87)

## API Endpoint
- POST `https://api.z.ai/api/mcp/web_search_prime/mcp` (UTCP/MCP endpoint)
- Alternatively, direct HTTP endpoint may be available at `/web_search`

## User Stories / Use Scenarios

### Scenario 1: User performs basic web search
- User wants to search for "Python async await best practices"
- User runs: `goz search "Python async await best practices"`
- Application loads config from `~/.config/goz/config.json` to get auth token
- Application constructs search request body with:
  - `search_engine: "search-prime"`
  - `search_query: "Python async await best practices"`
- Application sends POST request to search endpoint
- Application receives JSON response with search results array
- Application parses results into list of `SearchResult` objects
- Application prints results with rank, title, URL, summary, source, and date (if available)
- User sees structured search results they can read and navigate

### Scenario 2: User limits search results count
- User wants only top 5 results for "fastapi tutorial"
- User runs: `goz search "fastapi tutorial" --count 5`
- Application validates count parameter is positive integer
- Application constructs search request with `count: 5`
- Application sends request and receives 10 results from API
- Application slices results to first 5
- User sees only 5 results printed

### Scenario 3: User filters search to specific domain
- User wants to search for "TypeScript documentation" only on typescriptlang.org
- User runs: `goz search "TypeScript documentation" --domain typescriptlang.org`
- Application constructs search request with `search_domain_filter: "typescriptlang.org"`
- Application sends request to API
- API returns only results from typescriptlang.org domain
- User sees domain-filtered results

### Scenario 4: User filters search by recency (recent content)
- User wants news about "AI developments" from the last week
- User runs: `goz search "AI developments" --recency oneWeek`
- Application validates recency parameter is one of: oneDay, oneWeek, oneMonth, oneYear, noLimit
- Application constructs search request with `search_recency_filter: "oneWeek"`
- Application sends request to API
- API returns results from the last week only
- User sees recent results with publish dates

### Scenario 5: User combines multiple filters
- User wants 3 results from github.com about "textual TUI" from the last month
- User runs: `goz search "textual TUI" --domain github.com --recency oneMonth --count 3`
- Application validates all parameters
- Application constructs search request with:
  - `search_query: "textual TUI"`
  - `search_domain_filter: "github.com"`
  - `search_recency_filter: "oneMonth"`
  - `count: 3`
- Application sends request
- User sees 3 filtered results from GitHub in the last month

### Scenario 6: User searches with query containing special characters
- User wants to search for "C++ template metaprogramming"
- User runs: `goz search "C++ template metaprogramming"`
- Application passes query string as-is (no encoding needed for JSON)
- Application sends request with exact query
- User receives relevant results for C++ templates

### Scenario 7: User provides invalid recency filter value
- User runs: `goz search "test" --recency twoWeeks`
- Application detects "twoWeeks" is not a valid recency filter
- Application prints error: "Invalid recency filter: twoWeeks. Valid options: oneDay, oneWeek, oneMonth, oneYear, noLimit"
- Application exits with non-zero status code

### Scenario 8: User provides invalid count value
- User runs: `goz search "test" --count -5`
- Application detects count is not positive
- Application prints error: "Count must be a positive integer"
- Application exits with non-zero status code

### Scenario 9: User provides empty search query
- User runs: `goz search ""`
- Application detects query is empty or whitespace-only
- Application prints error: "Search query cannot be empty"
- Application exits with non-zero status code

### Scenario 10: User handles search with no results
- User searches for a very specific term with no matches
- Application sends request successfully
- API returns empty results array
- Application prints "No results found" message
- User sees helpful message instead of empty output

### Scenario 11: User experiences network timeout during search
- User runs search but network is slow
- Request times out after configured timeout period
- Application catches timeout error from retry decorator
- Application raises `TimeoutError` with timeout value
- User sees error message indicating timeout occurred

### Scenario 12: User experiences API authentication error
- User's API token has expired
- Application sends search request
- API returns 401 Unauthorized
- Application raises `AuthError` with message about invalid token
- User sees error suggesting to check credentials

## Acceptance Criteria

### Core Functionality (AC-CORE)
1. `SearchClient` class exists in `goz/api/search.py`
2. `SearchClient.search()` async method accepts:
   - `query: str` (required)
   - `count: int | None = None` (optional, default None = API default)
   - `domain_filter: str | None = None` (optional)
   - `recency_filter: RecencyFilter | None = None` (optional, Literal["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"])
3. Method returns `list[SearchResult]`

### Data Types (AC-TYPES)
4. `SearchResult` dataclass exists with fields:
   - `rank: int` - Result position (1-indexed)
   - `title: str` - Page title
   - `url: str` - Full URL
   - `summary: str` - Content snippet
   - `source: str | None = None` - Domain name
   - `date: str | None = None` - Publish date if available
5. `RecencyFilter` type alias: `Literal["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]`
6. `SearchClient` is importable from `goz.api`

### Request Construction (AC-REQUEST)
7. Request body includes `search_engine: "search-prime"`
8. Request body includes `search_query: <query>`
9. If `count` is provided and > 0, request includes `count: <count>`
10. If `domain_filter` is provided, request includes `search_domain_filter: <domain>`
11. If `recency_filter` is provided, request includes `search_recency_filter: <recency>`
12. Optional parameters are only included in request if provided (not None)

### Response Parsing (AC-PARSE)
13. Response JSON is parsed from `search_result` array (or equivalent)
14. Each result is mapped to `SearchResult` dataclass
15. `rank` field is assigned from array index + 1 (1-indexed)
16. `title` is extracted from `title` field in response
17. `url` is extracted from `link` field in response
18. `summary` is extracted from `content` field in response
19. `source` is extracted from `media` field in response (if present)
20. `date` is extracted from `publish_date` field in response (if present)
21. Results are returned as Python `list[SearchResult]`

### Result Limiting (AC-LIMIT)
22. If `count` parameter is provided and less than total results, return only first `count` results
23. If `count` is None, return all results from API
24. If API returns fewer results than requested `count`, return all available results

### Validation (AC-VALIDATE)
25. Empty or whitespace-only query raises `ValueError` with message "Search query cannot be empty"
26. Negative or zero `count` raises `ValueError` with message "Count must be a positive integer"
27. Invalid `recency_filter` value raises `ValueError` with valid options listed
28. Query string is passed as-is (no additional validation beyond non-empty)

### Error Handling (AC-ERROR)
29. API errors (4xx, 5xx) are raised as `ApiError` from base client
30. Auth errors (401, 403) are raised as `AuthError` from base client
31. Timeout errors are raised as `TimeoutError` from base client
32. Network errors are raised as `NetworkError` from base client
33. Retry logic from base client applies to search requests (2 retries with exponential backoff)
34. Malformed response (missing expected fields) raises appropriate error

### Output Format (AC-OUTPUT)
35. When used programmatically, `list[SearchResult]` is returned
36. `SearchResult` dataclass has `__repr__` for readable debugging output
37. Results are sorted by rank (1, 2, 3, ...)

### Module Structure (AC-MODULE)
38. `goz/api/search.py` module exists with `SearchClient` class and `SearchResult` dataclass
39. `goz/api/__init__.py` exports `SearchClient`, `SearchResult`, `RecencyFilter` (optional)

## QA Requirements

### E2E Integration Tests

#### Basic Search Tests
- [x] E2E: Basic web search returns list of SearchResult objects
- [x] E2E: Search results contain rank, title, url, summary fields
- [x] E2E: Search with special characters in query works correctly
- [x] E2E: Search with unicode characters in query works correctly

#### Count Parameter Tests
- [x] E2E: Search with count=5 returns exactly 5 results
- [x] E2E: Search with count=1 returns exactly 1 result
- [x] E2E: Search with count greater than API results returns all available results
- [x] E2E: Search without count parameter returns default number of results

#### Domain Filter Tests
- [x] E2E: Search with domain filter returns results only from specified domain
- [x] E2E: Domain filter with subdomain (e.g., docs.python.org) works correctly
- [x] E2E: Domain filter with top-level domain only works correctly

#### Recency Filter Tests
- [x] E2E: Search with recency="oneDay" returns recent results
- [x] E2E: Search with recency="oneWeek" returns results from last week
- [x] E2E: Search with recency="oneMonth" returns results from last month
- [x] E2E: Search with recency="oneYear" returns results from last year
- [x] E2E: Search with recency="noLimit" returns all-time results

#### Combined Filter Tests
- [x] E2E: Search with domain and recency filters returns filtered results
- [x] E2E: Search with domain and count filters applies both correctly
- [x] E2E: Search with all filters (domain, recency, count) works correctly

#### Error Path Tests
- [x] E2E: Empty query raises ValueError with appropriate message
- [x] E2E: Whitespace-only query raises ValueError
- [x] E2E: Negative count raises ValueError
- [x] E2E: Zero count raises ValueError
- [x] E2E: Invalid recency filter raises ValueError with valid options
- [x] E2E: Invalid API token raises AuthError
- [x] E2E: Network timeout raises TimeoutError
- [x] E2E: Network error raises NetworkError

#### Edge Case Tests
- [x] E2E: Search with no results (empty result array) returns empty list
- [x] E2E: Search with very long query string works correctly
- [x] E2E: Search with count=100 (large value) works correctly
- [x] E2E: Malformed API response is handled gracefully

### Unit Tests

#### Request Construction Tests
- [x] Unit: `build_search_request_body()` constructs correct body with all parameters
- [x] Unit: `build_search_request_body()` omits optional parameters when None
- [x] Unit: `build_search_request_body()` includes domain filter when provided
- [x] Unit: `build_search_request_body()` includes recency filter when provided
- [x] Unit: `build_search_request_body()` includes count when provided

#### Response Parsing Tests
- [x] Unit: `parse_search_response()` correctly maps API response to SearchResult list
- [x] Unit: `parse_search_response()` assigns correct rank (1-indexed)
- [x] Unit: `parse_search_response()` handles missing optional fields (source, date)
- [x] Unit: `parse_search_response()` handles empty results array
- [x] Unit: `parse_search_response()` handles result with all fields present

#### Validation Tests
- [x] Unit: `validate_search_params()` accepts valid query
- [x] Unit: `validate_search_params()` rejects empty query
- [x] Unit: `validate_search_params()` rejects negative count
- [x] Unit: `validate_search_params()` rejects zero count
- [x] Unit: `validate_search_params()` accepts valid recency values
- [x] Unit: `validate_search_params()` rejects invalid recency values

#### Result Limiting Tests
- [x] Unit: `limit_results()` with count=5 returns first 5 results
- [x] Unit: `limit_results()` with count greater than results length returns all results
- [x] Unit: `limit_results()` with count=None returns all results
- [x] Unit: `limit_results()` with empty list returns empty list

#### Data Class Tests
- [x] Unit: `SearchResult` dataclass creates instance with all fields
- [x] Unit: `SearchResult` dataclass creates instance with only required fields
- [x] Unit: `SearchResult` `__repr__` produces readable output

## Implementation Notes

### Module Structure
```
goz/
└── api/
    ├── __init__.py        # To update: export SearchClient, SearchResult
    └── search.py          # New file: SearchClient, SearchResult, helpers
```

### Key Classes/Functions (to implement in `goz/api/search.py`)

```python
from dataclasses import dataclass
from typing import Literal

RecencyFilter = Literal["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]

@dataclass
class SearchResult:
    """A single search result from web search API."""
    rank: int
    title: str
    url: str
    summary: str
    source: str | None = None
    date: str | None = None

class SearchClient:
    """Web search client using Z.AI WebSearchPrime API."""

    def __init__(self, config: Config | None = None) -> None:
        # Initialize with config

    async def search(
        self,
        query: str,
        count: int | None = None,
        domain_filter: str | None = None,
        recency_filter: RecencyFilter | None = None,
    ) -> list[SearchResult]:
        # Perform web search
```

### Helper Functions (to implement in `goz/api/search.py`)
```python
def validate_search_params(
    query: str,
    count: int | None = None,
    recency_filter: RecencyFilter | None = None,
) -> None:
    """Validate search parameters."""

def build_search_request_body(
    query: str,
    count: int | None = None,
    domain_filter: str | None = None,
    recency_filter: RecencyFilter | None = None,
) -> dict[str, Any]:
    """Build request body for search API."""

def parse_search_response(response: dict[str, Any]) -> list[SearchResult]:
    """Parse API response into SearchResult list."""

def limit_results(results: list[SearchResult], count: int | None) -> list[SearchResult]:
    """Limit results to specified count."""
```

### API Request/Response Format

**Request Body:**
```json
{
  "search_engine": "search-prime",
  "search_query": "user query here",
  "count": 10,
  "search_domain_filter": "example.com",
  "search_recency_filter": "oneWeek"
}
```

**Response Format** (based on TypeScript reference):
```json
{
  "id": "...",
  "created": 1234567890,
  "search_result": [
    {
      "title": "Page Title",
      "content": "Summary text...",
      "link": "https://example.com/page",
      "media": "example.com",
      "icon": "...",
      "refer": "...",
      "publish_date": "2024-01-15"
    }
  ]
}
```

### Field Mapping
- `rank`: Computed as array index + 1
- `title`: `response.search_result[i].title`
- `url`: `response.search_result[i].link`
- `summary`: `response.search_result[i].content`
- `source`: `response.search_result[i].media`
- `date`: `response.search_result[i].publish_date`

### Constants
- DEFAULT_COUNT: None (use API default, typically 10)
- VALID_RECENCY_FILTERS: ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"]

### API Endpoint
- Endpoint: `/web_search` (or MCP endpoint `/api/mcp/web_search_prime/mcp`)
- Method: POST
- Uses existing `ZaiApiClient.request()` method

### Error Messages
- Empty query: "Search query cannot be empty"
- Invalid count: "Count must be a positive integer"
- Invalid recency: "Invalid recency filter: {value}. Valid options: oneDay, oneWeek, oneMonth, oneYear, noLimit"

## Log

### [PM] 2026-03-19
- Created detailed user scenarios (12 scenarios covering all major paths)
- Added 39 specific, testable acceptance criteria across 9 categories
- Defined E2E integration tests (28 test cases)
- Defined unit tests (23 test cases)
- Based on reference implementation in zai-cli:
  - `api-client.ts` webSearch method (lines 241-256)
  - `mcp-client.ts` webSearch method (lines 395-420)
  - `commands/search.ts` command implementation (lines 1-87)
- Ready for SWE implementation
- Renamed from .todo.md to .groomed.md

### [SWE] 2026-03-19
- Implemented SearchClient class in goz/api/search.py
- Implemented SearchResult dataclass with all required fields
- Implemented RecencyFilter type alias
- Implemented validate_search_params() function
- Implemented build_search_request_body() function
- Implemented parse_search_response() function
- Implemented limit_results() function
- Updated goz/api/__init__.py to export SearchClient, SearchResult, RecencyFilter
- All 54 E2E tests passing

### [QA/PM] 2026-03-19
- Reviewed implementation against acceptance criteria
- Verified all 54 tests pass (28 E2E + 26 unit tests)
- All acceptance criteria met
- Renamed from .groomed.md to .done.md
- Issue accepted and closed
