"""Agent module for goz interactive coding agent.

This package provides the core agent functionality including:
- StreamProcessor: Handle streaming API responses
- ChatStateMachine: Manage conversation states
- ChatClient: API client for chat completions with tool calling
- AgentCore: Main agent orchestrator (Issue 15)
- Tool: Protocol and registry for agent tools (Issue 18)
- File Tools: ViewFileTool, CreateFileTool, StrReplaceEditorTool (Issue 19)
- Vision Tool: DescribeImageTool (Issue 20)
"""
from goz.agent.stream_processor import (
    StreamProcessor,
    ToolCall,
    ProcessedStream,
)

from goz.agent.state_machine import (
    ChatStateMachine,
    State,
    StateTransitionError,
)

from goz.agent.chat_client import (
    ChatClient,
    ContentBlockStart,
    ContentBlockDelta,
    ContentBlockStop,
    MessageStart,
    MessageStop,
    Chunk,
)

from goz.agent.tools import (
    Tool,
    BaseTool,
    ToolRegistry,
    ToolError,
    ToolInputError,
    ToolNotFoundError,
    ToolExecutionError,
    ViewFileTool,
    CreateFileTool,
    StrReplaceEditorTool,
    DescribeImageTool,
)

__all__ = [
    # Stream processor
    "StreamProcessor",
    "ToolCall",
    "ProcessedStream",
    # State machine
    "ChatStateMachine",
    "State",
    "StateTransitionError",
    # Chat client
    "ChatClient",
    "ContentBlockStart",
    "ContentBlockDelta",
    "ContentBlockStop",
    "MessageStart",
    "MessageStop",
    "Chunk",
    # Tools
    "Tool",
    "BaseTool",
    "ToolRegistry",
    "ToolError",
    "ToolInputError",
    "ToolNotFoundError",
    "ToolExecutionError",
    # File Tools
    "ViewFileTool",
    "CreateFileTool",
    "StrReplaceEditorTool",
    # Vision Tools
    "DescribeImageTool",
]
