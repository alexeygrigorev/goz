# Issue 03: API Client Foundation

## Status
.done

## Description
Implement the base Z.AI API client with retry logic, error types, and logging support, matching the TypeScript version's functionality in `zai-cli/packages/zai-cli/src/lib/api-client.ts`.

## Dependencies
Issue 02 (config) - .done

## Reference
zai-cli/packages/zai-cli/src/lib/api-client.ts

## User Scenarios

### Scenario 1: Developer imports and instantiates ZaiApiClient
1. Developer has a valid config at `~/.config/goz/config.json` with `anthropic_auth_token` set
2. Developer writes `from goz.api import ZaiApiClient` in their Python code
3. Developer creates a client instance: `client = ZaiApiClient()`
4. Client automatically loads config from default location
5. Client is ready to make API requests with configured base URL, timeout, and auth token

### Scenario 2: API client makes successful request with retry
1. Developer creates `ZaiApiClient()` with valid config
2. Developer calls `client.request('/chat/completions', payload_dict)`
3. Client sends POST request to `{base_url}/chat/completions` with `Authorization: Bearer {token}` header
4. Request succeeds on first attempt with 200 OK
5. Client returns parsed JSON response as dict
6. No retry attempts were needed

### Scenario 3: API client retries on transient network failure
1. Developer creates `ZaiApiClient()` and calls `client.request('/chat/completions', payload_dict)`
2. First request attempt fails with `httpx.ConnectError` (network unreachable)
3. Client waits 1 second (base delay)
4. Client retries second attempt - fails again with timeout
5. Client waits 2 seconds (exponential backoff: 1000ms * 2^1)
6. Client retries third attempt - succeeds with 200 OK
7. Client returns parsed JSON response
8. Total attempts: 3, total elapsed wait time: 3 seconds

### Scenario 4: API client fails fast on authentication error (401)
1. Developer creates `ZaiApiClient()` with invalid/expired token
2. Developer calls `client.request('/chat/completions', payload_dict)`
3. API returns 401 Unauthorized with error message
4. Client immediately raises `AuthError` without retrying
5. Error message contains API's error text
6. No retry attempts were made (auth errors don't retry)

### Scenario 5: API client handles timeout error
1. Developer creates `ZaiApiClient()` with timeout=10 (seconds)
2. Developer calls `client.request('/reader', {url: 'https://slow.example.com'})`
3. Request takes longer than 10 seconds
4. httpx raises `TimeoutException`
5. Client catches and raises `TimeoutError` with message including timeout value
6. If retry attempts remain, client retries with same timeout

### Scenario 6: API client logs requests when logging enabled
1. Developer creates `ZaiApiClient()` with `enable_logging=True` (or environment variable)
2. Developer calls `client.request('/chat/completions', payload_dict)`
3. Before request, client logs: `POST /chat/completions` with payload size
4. After response, client logs: `Response 200 OK` with response size
5. On error, client logs: `Error: {error_type} - {error_message}`
6. Logs go to stderr (not stdout) to not interfere with output parsing

### Scenario 7: API client handles malformed API error response
1. Developer creates `ZaiApiClient()` and calls endpoint that returns 400
2. API returns `{"error": "Invalid request: missing required field 'model'"}`
3. Client parses nested error structure and extracts message
4. Client raises `ApiError` with extracted message: `"Invalid request: missing required field 'model'"`
5. If error parsing fails, falls back to raw response text

### Scenario 8: API client handles non-JSON error response
1. Developer creates `ZaiApiClient()` and calls endpoint
2. API returns 500 with plain text `"Internal Server Error"`
3. Client attempts to parse as JSON, fails
4. Client falls back to using raw text as error message
5. Client raises `ApiError("Internal Server Error", 500)`

## Acceptance Criteria

### Error Types (AC-ERRORS)
1. `ZaiError` base class exists with attributes: `message`, `code`, `statusCode` (optional), `help` (optional)
2. `AuthError` extends `ZaiError` with `code='AUTH_ERROR'`, `statusCode=401`, and help text about checking API key
3. `ApiError` extends `ZaiError` with `code='API_ERROR'` and accepts `statusCode` parameter
4. `NetworkError` extends `ZaiError` with `code='NETWORK_ERROR'` and help text about checking internet connection
5. `TimeoutError` extends `ZaiError` with `code='TIMEOUT_ERROR'` and help text about increasing timeout
6. All error types can be caught via `except ZaiError:`
7. All errors have string representation showing error code and message

### Base Client (AC-BASE)
1. `ZaiApiClient` class exists in `goz/api/client.py` (or `goz/api/__init__.py`)
2. Constructor accepts optional `Config` object; if not provided, loads from default location
3. Client stores `config` attribute with base URL, timeout, and auth token
4. Client has `request(endpoint: str, body: dict) -> dict` private method for making HTTP requests
5. `request()` method uses `httpx.AsyncClient` for async HTTP operations
6. `request()` sets headers: `Authorization: Bearer {token}`, `Content-Type: application/json`, `Accept-Language: en-US,en`
7. `request()` constructs full URL as `{base_url}{endpoint}`

### Request Handling (AC-REQUEST)
1. Successful requests (200 OK) return parsed JSON as Python dict
2. Non-OK responses (4xx, 5xx) raise appropriate error types
3. 401/403 responses raise `AuthError`
4. Other 4xx/5xx responses raise `ApiError` with status code
5. Request timeout raises `TimeoutError` with timeout value in message
6. Network errors (connection refused, DNS failure) raise `NetworkError`
7. `AbortError` (from httpx timeout) is caught and converted to `TimeoutError`

### Retry Logic (AC-RETRY)
1. Retry decorator/function wraps request execution with max 2 retries (3 total attempts)
2. Base delay is 1000ms (1 second)
3. Exponential backoff: delay = base_delay * 2^attempt (1s, 2s, 4s...)
4. `AuthError` is NOT retried (fails immediately)
5. Other errors trigger retry with backoff delay
6. After max retries exhausted, last error is re-raised
7. Retry logic is async-compatible (uses `asyncio.sleep` not `time.sleep`)

### Error Parsing (AC-PARSING)
1. Error responses with JSON are parsed to extract error message
2. Client handles nested error structures: `error.message`, `message`, `error`
3. If error message is object, it's stringified to JSON
4. If JSON parsing fails, raw response text is used as error message
5. Error message is passed to appropriate error type constructor

### Logging (AC-LOGGING)
1. Optional logging controlled by `enable_logging` parameter or environment variable `GOZ_API_LOG`
2. When enabled, requests log: `-> POST {endpoint}` with body size
3. When enabled, responses log: `<- {status} {size} bytes` with duration
4. When enabled, errors log: `! {error_type}: {message}`
5. Logs go to stderr via `logging` module, not stdout
6. When disabled (default), no log output occurs

### Module Structure (AC-MODULE)
1. `goz/api/__init__.py` exports: `ZaiApiClient`, `ZaiError`, `AuthError`, `ApiError`, `NetworkError`, `TimeoutError`
2. All types are importable as `from goz.api import ZaiApiClient, AuthError`
3. Module has `__all__` list defining public exports

## QA Requirements (E2E Integration Tests)

### Error Type Tests
- [x] E2E: `ZaiError` base class has all required attributes (message, code, statusCode, help)
- [x] E2E: `AuthError` has correct code and statusCode
- [x] E2E: `ApiError` accepts and stores statusCode
- [x] E2E: `NetworkError` has correct code and help text
- [x] E2E: `TimeoutError` includes timeout value in message
- [x] E2E: All error types are catchable via base `ZaiError`

### Client Instantiation Tests
- [x] E2E: `ZaiApiClient()` with no arguments loads default config
- [x] E2E: `ZaiApiClient(config=custom_config)` uses provided config
- [x] E2E: Client stores config attribute accessible after initialization

### Request Success Tests
- [x] E2E: Successful request to mock API returns parsed JSON dict
- [x] E2E: Request includes correct Authorization header with Bearer token
- [x] E2E: Request includes Content-Type and Accept-Language headers
- [x] E2E: Full URL is `{base_url}{endpoint}`

### Error Handling Tests
- [x] E2E: 401 response raises `AuthError` without retry
- [x] E2E: 403 response raises `AuthError` without retry
- [x] E2E: 400 response raises `ApiError` with statusCode=400
- [x] E2E: 500 response raises `ApiError` with statusCode=500
- [x] E2E: Timeout raises `TimeoutError` with timeout value in message
- [x] E2E: Connection error raises `NetworkError`

### Retry Logic Tests
- [x] E2E: Successful request on first attempt returns immediately (no delay)
- [x] E2E: Failed request retries 2 times (3 total attempts)
- [x] E2E: Retry delay follows exponential backoff (1s, 2s, 4s)
- [x] E2E: `AuthError` is not retried (fails immediately on 401)
- [x] E2E: After max retries, last error is re-raised
- [x] E2E: Retry succeeds on second attempt after transient failure

### Error Parsing Tests
- [x] E2E: Error response with nested `error.message` extracts message correctly
- [x] E2E: Error response with top-level `message` extracts message correctly
- [x] E2E: Error response with plain text (non-JSON) uses text as message
- [x] E2E: Error response with object message stringifies to JSON

### Logging Tests
- [x] E2E: With logging enabled, request logs to stderr
- [x] E2E: With logging disabled, no log output occurs
- [x] E2E: Error logs include error type and message
- [x] E2E: Logs go to stderr, not stdout

## Tasks
1. [x] Implement error types (ZaiError, AuthError, ApiError, NetworkError, TimeoutError)
2. [x] Implement base ZaiApiClient class with httpx.AsyncClient
3. [x] Implement request() method with headers, timeout, and error handling
4. [x] Implement retry logic with exponential backoff
5. [x] Implement error response parsing for JSON and plain text
6. [x] Implement optional request/response logging
7. [x] Add E2E integration tests for all acceptance criteria

## Log

### [PM] 2026-03-19
- Groomed issue from .todo to .groomed
- Added 8 detailed user scenarios covering all major use cases
- Added 7 acceptance criteria groups with specific, testable requirements
- Added E2E integration test requirements covering all scenarios
- Verified Issue 02 (config) dependency is .done
- Reference: zai-cli/packages/zai-cli/src/lib/api-client.ts, errors.ts

### [Dev] 2026-03-19
- TDD Implementation of Issue 03: API Client Foundation

#### Step 1: Test First - Error Type Tests (AC-ERRORS)
- Wrote tests for error types (test_zai_error_base_class_has_all_attributes, test_auth_error_attributes, etc.)
- Ran tests - PASS (error types already implemented in goz/api/errors.py)

#### Step 2: Test First - Client Instantiation Tests (AC-BASE, AC-MODULE)
- Wrote tests for client instantiation (test_zai_api_client_importable, test_all_exports_defined, etc.)
- Ran tests - FAIL (implementation needed)
- Implemented ZaiApiClient class with __init__ accepting optional Config
- Updated tests to use zai_token/zai_base_url (config field names changed from Issue 02)
- Ran tests - PASS

#### Step 3: Test First - Request Success Tests (AC-REQUEST)
- Wrote tests for successful requests (test_successful_request_returns_parsed_json, etc.)
- Ran tests - FAIL (request method not implemented with proper mocking)
- Fixed issue with httpx.AsyncClient mocking - __aexit__ was suppressing exceptions
- Created proper async aexit function that returns None to propagate exceptions
- Ran tests - PASS

#### Step 4: Test First - Error Handling Tests (AC-REQUEST)
- Wrote tests for error handling (test_401_response_raises_auth_error, test_timeout_raises_timeout_error, etc.)
- Ran tests - FAIL (errors not being raised due to __aexit__ issue)
- Fixed all mock __aexit__ setups to use proper async function
- Added is_success attribute to mock responses
- Ran tests - PASS

#### Step 5: Test First - Retry Logic Tests (AC-RETRY)
- Wrote tests for retry logic (test_failed_request_retries_two_times, test_auth_error_not_retried, etc.)
- Ran tests - FAIL (retry decorator not catching exceptions properly)
- Fixed with_retry decorator to properly handle AuthError (don't retry)
- Ran tests - PASS

#### Step 6: Test First - Error Parsing Tests (AC-PARSING)
- Wrote tests for error parsing (test_error_response_nested_error_message, etc.)
- Ran tests - FAIL (mock responses missing is_success attribute)
- Added is_success=False to error response mocks
- Ran tests - PASS

#### Step 7: Test First - Logging Tests (AC-LOGGING)
- Wrote tests for logging (test_logging_enabled_logs_request_to_stderr, etc.)
- Ran tests - FAIL (caplog not capturing DEBUG level logs)
- Added caplog.set_level(logging.DEBUG) to test
- Added logging import to test file
- Added content attribute to mock responses for logging
- Ran tests - PASS

#### Final Results
- All 34 tests PASS
- All 7 acceptance criteria groups verified with passing tests
- All QA requirements met (checked off in lists above)
- Implementation complete for Issue 03

#### Key Issues Resolved
1. httpx.AsyncClient mock __aexit__ was suppressing exceptions - fixed with proper async aexit function
2. Config field names changed from anthropic_auth_token to zai_token - updated all tests
3. Mock responses needed is_success attribute to trigger error handling
4. caplog needed set_level(logging.DEBUG) to capture DEBUG logs

### [PM] 2026-03-19
- Reviewed Issue 03: API Client Foundation
- Verified all 34 E2E tests pass
- Verified all acceptance criteria met:
  - AC-ERRORS: All error types implemented with correct attributes
  - AC-BASE: ZaiApiClient class in goz/api/client.py with proper initialization
  - AC-REQUEST: Request handling with proper headers and error responses
  - AC-RETRY: Exponential backoff retry logic with max 2 retries
  - AC-PARSING: Error message parsing for nested structures
  - AC-LOGGING: Optional logging controlled by parameter or env var
  - AC-MODULE: All types properly exported from goz/api/__init__.py
- Moved issue from .in-progress.md to .done.md
- Issue ACCEPTED
