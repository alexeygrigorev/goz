# Issue 21: Search/Read/Repo Tools

## Status
.todo

## Description
Implement tools that wrap existing API clients: search (web search), read (web reader), repo (GitHub exploration).

## User Scenarios

### Scenario 1: Web Search
- User asks: "Search for Python async await best practices"
- Agent calls search(query="Python async await best practices", count=10)
- Tool uses existing SearchClient
- Returns list of search results
- Agent presents results to user

### Scenario 2: Search with Domain Filter
- User asks: "Search for React documentation on react.dev"
- Agent calls search(query="React hooks", domain="react.dev")
- Tool filters results to domain
- Returns filtered results

### Scenario 3: Web Read
- User asks: "Read and summarize https://example.com/article"
- Agent calls read(url="https://example.com/article")
- Tool uses existing ReaderClient
- Returns markdown content
- Agent summarizes for user

### Scenario 4: Repo Search
- User asks: "Search vercel/next.js for app router"
- Agent calls repo_search(repo="vercel/next.js", query="app router")
- Tool uses existing RepoClient
- Returns search results from repo
- Agent presents findings

### Scenario 5: Repo Tree
- User asks: "Show the structure of facebook/react"
- Agent calls repo_tree(repo="facebook/react")
- Tool returns directory tree
- Agent displays structure

### Scenario 6: Repo Read
- User asks: "Show the README of anthropics/anthropic-sdk-python"
- Agent calls repo_read(repo="anthropics/anthropic-sdk-python", file_path="README.md")
- Tool returns file content
- Agent displays to user

## Acceptance Criteria

### search tool
1. `SearchTool` class in `goz/agent/tools/api_tools.py`
2. Wraps existing SearchClient
3. Supports query, count, domain parameters
4. Returns formatted search results
5. Handles empty results gracefully

### read tool
6. `ReadTool` class in `goz/agent/tools/api_tools.py`
7. Wraps existing ReaderClient
8. Supports url parameter
9. Returns markdown content
10. Handles fetch errors gracefully

### repo_search tool
11. `RepoSearchTool` class in `goz/agent/tools/api_tools.py`
12. Wraps existing RepoClient.search()
13. Supports repo, query, language parameters
14. Returns formatted results

### repo_tree tool
15. `RepoTreeTool` class in `goz/agent/tools/api_tools.py`
16. Wraps existing RepoClient.tree()
17. Supports repo, path, depth parameters
18. Returns formatted tree structure

### repo_read tool
19. `RepoReadTool` class in `goz/agent/tools/api_tools.py`
20. Wraps existing RepoClient.read()
21. Supports repo, file_path parameters
22. Returns file content

### General
23. All tools use existing API clients (no duplicate code)
24. All tools validate inputs against schema
25. All tools handle errors appropriately
26. All tools return formatted output

## Technical Details

### File Structure
```
goz/agent/tools/
└── api_tools.py   # SearchTool, ReadTool, RepoSearchTool, RepoTreeTool, RepoReadTool
```

### Tool Definitions

#### search
```python
class SearchTool(BaseTool):
    name = "search"
    description = (
        "Search the web for current information. "
        "Use for finding documentation, examples, news, and troubleshooting."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "count": {
                "type": "integer",
                "description": "Number of results (default: 10, max: 50)"
            },
            "domain": {
                "type": "string",
                "description": "Filter to specific domain (optional)"
            }
        },
        "required": ["query"]
    }

    def __init__(self, config: Config):
        self.client = SearchClient(config)

    async def execute(
        self,
        query: str,
        count: int = 10,
        domain: str | None = None,
    ) -> str:
        """Search the web."""
```

#### read
```python
class ReadTool(BaseTool):
    name = "read"
    description = (
        "Fetch and convert a web page to readable markdown. "
        "Use for reading documentation, articles, blog posts, and news."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch and parse"
            }
        },
        "required": ["url"]
    }

    def __init__(self, config: Config):
        self.client = ReaderClient(config)

    async def execute(self, url: str) -> str:
        """Fetch and parse web page."""
```

#### repo_search
```python
class RepoSearchTool(BaseTool):
    name = "repo_search"
    description = (
        "Search code and documentation in a GitHub repository. "
        "Use for finding specific code patterns, functions, or topics in a repo."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format (e.g., 'vercel/next.js')"
            },
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "language": {
                "type": "string",
                "enum": ["en", "zh"],
                "description": "Result language"
            }
        },
        "required": ["repo", "query"]
    }

    def __init__(self, config: Config):
        self.client = RepoClient(config)

    async def execute(
        self,
        repo: str,
        query: str,
        language: str | None = None,
    ) -> str:
        """Search repository."""
```

#### repo_tree
```python
class RepoTreeTool(BaseTool):
    name = "repo_tree"
    description = (
        "Get the directory structure of a GitHub repository. "
        "Use for understanding project layout and finding files."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format"
            },
            "path": {
                "type": "string",
                "description": "Directory path (default: repo root)"
            },
            "depth": {
                "type": "integer",
                "description": "Depth for subdirectory expansion (default: 1)"
            }
        },
        "required": ["repo"]
    }

    def __init__(self, config: Config):
        self.client = RepoClient(config)

    async def execute(
        self,
        repo: str,
        path: str | None = None,
        depth: int = 1,
    ) -> str:
        """Get repository tree."""
```

#### repo_read
```python
class RepoReadTool(BaseTool):
    name = "repo_read"
    description = (
        "Read a file from a GitHub repository. "
        "Use for viewing source code, READMEs, configs, etc."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository in 'owner/repo' format"
            },
            "file_path": {
                "type": "string",
                "description": "Path to the file (relative to repo root)"
            }
        },
        "required": ["repo", "file_path"]
    }

    def __init__(self, config: Config):
        self.client = RepoClient(config)

    async def execute(self, repo: str, file_path: str) -> str:
        """Read file from repository."""
```

### Output Formats

#### search output
```
Found 10 results for "Python async await"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Python Async/Await Best Practices
   https://realpython.com/async-io-python/
   Learn how to use async/await in Python effectively, including
   common patterns, pitfalls, and best practices...

2. Async IO in Python: A Complete Walkthrough
   https://docs.python.org/3/library/asyncio.html
   Official Python documentation for asyncio...
```

#### read output
```
Fetched: https://example.com/article
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Article Title

Content here as markdown...
```

#### repo_search output
```
Search results for "app router" in vercel/next.js
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. App Router Documentation
   The App Router is a new routing paradigm...
   URL: /docs/app-router.md

2. App Router Migration Guide
   How to migrate from pages to app directory...
```

#### repo_tree output
```
vercel/next.js
├── packages/
│   ├── next/
│   │   ├── app.js
│   │   └── server.js
│   └── react/
│       └── index.js
└── docs/
    └── guide.md
```

## Dependencies
- Issue 18: Tool Base + Registry
- Existing: SearchClient, ReaderClient, RepoClient

## Related Issues
- Issue 19: File Tools
- Issue 20: Bash Tool
- Issue 22: Tool Integration

## Log
