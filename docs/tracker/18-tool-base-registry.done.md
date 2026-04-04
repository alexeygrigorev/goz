# Issue 18: Tool Base + Registry

## Status
.todo

## Description
Define the Tool interface and implement the ToolRegistry for managing available tools.

## User Scenarios

### Scenario 1: Define a Tool
- Developer creates new tool class
- Implements Tool protocol
- Sets name, description, input_schema
- Implements execute() async method
- Tool can be registered

### Scenario 2: Register a Tool
- System initializes
- Built-in tools register themselves
- ToolRegistry.add() called for each tool
- Tools stored in internal dict by name

### Scenario 3: List Available Tools
- API request needs tool definitions
- System calls registry.list_all()
- Returns all Tool objects
- System iterates and builds API request

### Scenario 4: Get Tool for Execution
- API returns tool_call: {"name": "view_file", "arguments": {...}}
- System calls registry.get("view_file")
- Returns ViewFileTool instance
- System calls tool.execute(**arguments)

### Scenario 5: Export to OpenAI Schema
- ChatClient needs tools in API format
- System calls registry.to_openai_schema()
- Returns list of dicts with name, description, input_schema
- Compatible with OpenAI/Anthropic function calling

## Acceptance Criteria

1. `Tool` Protocol/ABC exists in `goz/agent/tools/base.py`
2. Tool requires: name, description, input_schema properties
3. Tool requires: execute() async method
4. `ToolRegistry` class exists in `goz/agent/tools/registry.py`
5. `ToolRegistry.register()` adds tool
6. `ToolRegistry.get()` retrieves tool by name
7. `ToolRegistry.list_all()` returns all tools
8. `ToolRegistry.to_openai_schema()` exports to API format
9. `ToolInputError` exception for invalid tool inputs
10. `ToolNotFoundError` exception for unknown tool

## Technical Details

### File Structure
```
goz/agent/tools/
├── __init__.py
├── base.py       # Tool protocol
└── registry.py   # ToolRegistry
```

### Tool Protocol
```python
from typing import Protocol, Any

class Tool(Protocol):
    """Protocol for agent tools."""

    name: str
    description: str
    input_schema: dict

    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool.

        Returns:
            String result to send back to API

        Raises:
            ToolInputError: If input validation fails
        """
```

### Tool Registry API
```python
class ToolRegistry:
    def __init__(self) -> None:
        """Initialize empty registry."""

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Raises:
            ValueError: If tool name already registered
        """

    def unregister(self, name: str) -> None:
        """Unregister a tool."""

    def get(self, name: str) -> Tool | None:
        """Get tool by name."""

    def list_all(self) -> list[Tool]:
        """List all registered tools."""

    def to_openai_schema(self) -> list[dict]:
        """Export tools to OpenAI function-calling format.

        Returns:
            List of dicts with keys: name, description, input_schema
        """

    @property
    def tool_names(self) -> set[str]:
        """Get set of registered tool names."""
```

### Input Schema Format
```python
# JSON Schema draft 2020-12 compatible
input_schema = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Path to the file"
        },
        "line_range": {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 2,
            "maxItems": 2,
            "description": "Optional line range [start, end]"
        }
    },
    "required": ["file_path"]
}
```

### Base Tool Class (for convenience)
```python
class BaseTool:
    """Base class for tools with common functionality."""

    def __init__(self, working_dir: str | None = None) -> None:
        self.working_dir = working_dir or os.getcwd()

    def validate_input(self, schema: dict, data: dict) -> None:
        """Validate input against JSON schema.

        Raises:
            ToolInputError: If validation fails
        """
```

### Exceptions
```python
class ToolError(ZaiError):
    """Base error for tool operations."""

class ToolInputError(ToolError):
    """Tool input validation failed."""

class ToolNotFoundError(ToolError):
    """Tool not found in registry."""

class ToolExecutionError(ToolError):
    """Tool execution failed."""
```

## Dependencies
- Issue 15: Agent Core (uses error classes)
- Issue 17: Chat API Client (consumer)

## Related Issues
- Issue 19: File Tools
- Issue 20: Bash Tool
- Issue 21: Search/Read/Repo Tools

## Log
