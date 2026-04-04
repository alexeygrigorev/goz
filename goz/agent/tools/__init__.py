"""Tools package for goz interactive coding agent.

This package provides the tool system for the agent including:
- Tool: Protocol defining the tool interface
- BaseTool: Base class for tool implementations
- ToolRegistry: Registry for managing available tools
- Tool exceptions: ToolInputError, ToolNotFoundError, ToolExecutionError
- File tools: ViewFileTool, CreateFileTool, StrReplaceEditorTool
- API tools: SearchTool, ReadTool, RepoSearchTool, RepoTreeTool, RepoReadTool
"""
from goz.agent.tools.base import (
    Tool,
    BaseTool,
    ToolError,
    ToolInputError,
    ToolNotFoundError,
    ToolExecutionError,
)

from goz.agent.tools.registry import ToolRegistry

from goz.agent.tools.file_tools import (
    ViewFileTool,
    CreateFileTool,
    StrReplaceEditorTool,
)

from goz.agent.tools.api_tools import (
    SearchTool,
    ReadTool,
    RepoSearchTool,
    RepoTreeTool,
    RepoReadTool,
)

from goz.agent.tools.bash_tool import BashTool, BashResult

__all__ = [
    # Base
    "Tool",
    "BaseTool",
    # Registry
    "ToolRegistry",
    # Exceptions
    "ToolError",
    "ToolInputError",
    "ToolNotFoundError",
    "ToolExecutionError",
    # File Tools
    "ViewFileTool",
    "CreateFileTool",
    "StrReplaceEditorTool",
    # API Tools
    "SearchTool",
    "ReadTool",
    "RepoSearchTool",
    "RepoTreeTool",
    "RepoReadTool",
    # Bash Tool
    "BashTool",
    "BashResult",
]
