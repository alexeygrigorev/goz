# Issue 03: API Client Foundation

## Status
.todo

## Description
Implement the base Z.AI API client with retry logic, matching the TypeScript version's functionality.

## Tasks
1. Base API client class with httpx
2. Retry logic with exponential backoff
3. Error types (AuthError, ApiError, NetworkError, TimeoutError)
4. Request/response logging support

## Dependencies
Issue 02 (config)

## Reference
zai-cli/packages/zai-cli/src/lib/api-client.ts
