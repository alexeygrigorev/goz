# Issue 13: MCP Tools Discovery

## Status
.todo

## Description
Add MCP tool discovery and direct tool calling capabilities.

## Tasks
1. Create MCP client for listing tools
2. Implement `goz tools` - List available MCP tools
3. Implement `goz tool <name>` - Show tool schema
4. Implement `goz call <tool>` - Call tool with JSON args
5. Add options: --filter, --full, --json, --file, --stdin, --dry-run

## Dependencies
Issue 03 (API Client Foundation)

## Reference
zai-cli/packages/zai-cli/src/commands/tools.ts
zai-cli/packages/zai-cli/src/lib/mcp-client.ts

## Acceptance Criteria
1. `goz tools` - List all tool names
2. `goz tools --filter vision` - Filter tools by name
3. `goz tools --full` - Show full tool schemas
4. `goz tool zai.vision.analyze_image` - Show specific tool schema
5. `goz call zai.search.webSearchPrime --json '{"search_query":"test"}'`
6. Support @file prefix for loading JSON from file
7. Support --stdin for reading JSON from stdin
8. --dry-run option to preview without calling
