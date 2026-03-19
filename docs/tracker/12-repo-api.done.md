# Issue 12: Repo/ZRead API

## Status
.done

## Description
Add GitHub repository exploration using ZRead API with MCP protocol calls.

## Tasks
1. [x] Create RepoClient with MCP HTTP calls
2. [x] Implement searchDoc - Search docs and code in repository
3. [x] Implement getRepoStructure - Get directory tree
4. [x] Implement readFile - Read file contents
5. [x] Add CLI commands: `goz repo search|tree|read`
6. [ ] Add TUI screen for repo commands (deferred)

## Dependencies
Issue 03 (API Client Foundation)

## Reference
zai-cli/packages/zai-cli/src/commands/repo.ts
Endpoint: https://api.z.ai/api/mcp/zread/mcp

## MCP Tool Names Used
- zai.zread.search_doc - Search documentation and code
- zai.zread.get_repo_structure - Get directory tree
- zai.zread.read_file - Read file contents

## Acceptance Criteria
1. [x] `goz repo search facebook/react "server components"`
2. [x] `goz repo tree vercel/next.js`
3. [x] `goz repo tree vercel/next.js --path packages --depth 2`
4. [x] `goz repo read anthropics/anthropic-sdk-python README.md`
5. [x] Validate repo format (owner/repo)
6. [x] Handle errors gracefully
7. [x] Support --language option (en/zh)
8. [x] All tests passing (270)
