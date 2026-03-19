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
- [ ] Confirm if this is a balance issue or service availability issue
- [ ] Check if different API endpoint or authentication method is required
- [ ] Verify Node.js zai-cli has same issue
- [ ] Check if MCP protocol implementation vs direct HTTP makes a difference

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
