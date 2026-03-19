# Issue 14: Code Mode (TypeScript Tool Chains)

## Status
.todo

## Description
Add Code Mode for executing TypeScript tool chains.

## Tasks
1. Evaluate if Python equivalent is needed
2. Consider: Use Python-based tool chaining instead
3. Or: Keep TypeScript dependency for code mode
4. Implement `goz code run <file>` - Run TS file
5. Implement `goz code eval <code>` - Evaluate TS code
6. Implement `goz code interfaces` - Show TS interfaces
7. Implement `goz code prompt` - Show prompt template

## Dependencies
Issue 13 (MCP Tools)

## Reference
zai-cli/packages/zai-cli/src/commands/code.ts
zai-cli/packages/zai-cli/src/lib/code-mode.ts

## Decision Required
Python equivalent vs TypeScript dependency?
- Option A: Implement Python tool chaining (native)
- Option B: Keep TypeScript for code mode (requires Node.js)

## Acceptance Criteria (if implementing)
1. `goz code run ./chain.ts` - Execute tool chain file
2. `goz code eval "const r = await zai.search..."`
3. `goz code interfaces` - Show available interfaces
4. `goz code prompt` - Show Claude prompt template
