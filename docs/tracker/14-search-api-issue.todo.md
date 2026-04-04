# Issue 14: Search API Service Availability

## Status
.todo

## Description
The Z.AI `web_search_prime` API returns empty results (error 429 "Insufficient balance").
Both goz Python implementation and Claude's built-in search tool are affected.

## Problem Details
- API endpoint: `https://api.z.ai/api/coding/paas/v4/web_search`
- MCP endpoint: `https://api.z.ai/api/mcp/web_search_prime/mcp`
- Error: Returns empty array or 429 "Insufficient balance or no resource package"
- Affects: `goz search` command

## Current Workaround
None. Users need to:
1. Check Z.AI account balance
2. Ensure the service package includes search API access
3. Contact Z.AI support if balance is sufficient

## Investigation Needed
- [x] Confirm if this is a balance issue or service availability issue
- [x] Check if different API endpoint or authentication method is required
- [x] Verify Node.js zai-cli has same issue
- [x] Check if MCP protocol implementation vs direct HTTP makes a difference

## Related Issues
- Issue 05: Search API Implementation (marked .done but service may not work)

## Technical Notes
### Direct HTTP endpoint
```
POST https://api.z.ai/api/coding/paas/v4/web_search
{
  "search_engine": "search-prime",
  "search_query": "...",
  "count": N
}
```
Returns: `{"error":{"code":"1113","message":"Insufficient balance..."}}`

### MCP endpoint
```
POST https://api.z.ai/api/mcp/web_search_prime/mcp
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "web_search_prime",
    "arguments": {"search_query": "..."}
  }
}
```
Returns: Empty array or authentication error

### What Works
- ✅ Vision API (Anthropic SDK)
- ✅ Reader API (`/api/coding/paas/v4/reader`)
- ❌ Search API (both endpoints)

## Resolution Steps
1. Verify account balance/service package
2. Test with different Z.AI account/region
3. Check Z.AI documentation for search API requirements
4. Implement fallback or alternative search if needed

## Research Update (2026-04-04)

### Question and scope
- Investigate why Z.AI search returns empty results or `429 Insufficient balance` in `goz`.
- Determine whether the failure is caused by account entitlement, an outdated endpoint/auth pattern, or both.
- Out of scope: implementing a full SSE MCP transport migration for the search service.

### Evidence
- Repository direct HTTP client used `https://api.z.ai/api/coding/paas/v4/web_search` via `config.coding_base_url`.
- Repository MCP client used `https://api.z.ai/api/mcp/web_search_prime/mcp` with JSON-RPC POST and Bearer auth header.
- Official Z.AI Web Search docs now show the direct API on `https://api.z.ai/api/paas/v4/web_search`, not the older `/api/coding/paas/v4/web_search` route.
- Current official Z.AI docs are inconsistent for MCP search: one guide shows SSE access at `https://api.z.ai/api/mcp/web_search/sse?Authorization=YOUR API Key`, while another current official page still documents `https://api.z.ai/api/mcp/web_search_prime/mcp` with Bearer auth headers and an alternate `web_search_prime/sse` URL.
- The published npm package `zai-cli@1.1.0` still points direct HTTP search at `/web_search` under base URL `https://api.z.ai/api/coding/paas/v4`, and its MCP config still points at `https://api.z.ai/api/mcp/web_search_prime/mcp`.
- `goz` direct HTTP parsing expected either a bare list or a single result object. The documented API response shape wraps results under `search_result`, which can explain empty results even when the request succeeds.
- No local `goz` config or API key was available in this workspace, so live authenticated calls could not be reproduced here.

### Observed evidence vs inference
- Observed: current docs and current published `zai-cli` disagree on the direct HTTP and MCP search endpoints.
- Observed: official docs disagree with each other on MCP transport and auth details, while repo code and `zai-cli` currently use the `web_search_prime/mcp` HTTP endpoint with Bearer auth headers.
- Observed: `goz` had a parsing bug for the documented `{"search_result": [...]}` HTTP response shape.
- Inference: `429 Insufficient balance or no resource package` is still plausibly a real account-entitlement problem when the request reaches a valid backend.
- Inference: empty-result behavior can come from client-side parsing even if service availability is fine.
- Inference: the MCP failures are more likely caused by a stale or incompatible integration than by Python-specific behavior, because the current published Node `zai-cli` still uses the same older MCP path family and the official docs do not present a single unambiguous MCP configuration.

### Recommendation
- Treat this as two separate issues:
  1. Direct HTTP search: use the current documented general API route (`/api/paas/v4/web_search`) and parse `search_result`.
  2. MCP search: do a credentialed follow-up against the currently published MCP variants (`web_search_prime/mcp`, `web_search_prime/sse`, and the guide-only `web_search/sse`) before changing transports in code.
- Workaround today: prefer direct HTTP search over MCP for investigation and user-facing commands.
- If `429` persists on the corrected direct HTTP route, escalate as an account/package entitlement issue with Z.AI support rather than continuing client-side retries.
