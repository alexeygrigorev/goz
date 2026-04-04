"""Tool registry for goz interactive coding agent.

This module provides the ToolRegistry class for managing available tools.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from goz.agent.tools.base import Tool, ToolNotFoundError

if TYPE_CHECKING:
    from collections.abc import Set


class ToolRegistry:
    """Registry for managing available tools.

    The ToolRegistry stores tool implementations and provides methods
    for registering, retrieving, and listing tools. It also supports
    exporting tool definitions to OpenAI function-calling format.

    Attributes:
        _tools: Internal storage for registered tools
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        name = tool.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")
        self._tools[name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool.

        Args:
            name: Name of the tool to unregister

        Note:
            Does not raise if tool is not found (idempotent operation)
        """
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """Get tool by name.

        Args:
            name: Name of the tool to retrieve

        Returns:
            Tool instance if found, None otherwise
        """
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        """List all registered tools.

        Returns:
            List of all registered Tool instances
        """
        return list(self._tools.values())

    def to_openai_schema(self) -> list[dict]:
        """Export tools to OpenAI function-calling format.

        Converts all registered tools to the format expected by OpenAI's
        function calling API. Each tool is represented as a dict with
        name, description, and parameters (input_schema).

        Returns:
            List of dicts with keys: name, description, parameters

        Example:
            >>> schema = registry.to_openai_schema()
            >>> schema[0]
            {
                "name": "read_file",
                "description": "Read contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        """
        result = []
        for tool in self.list_all():
            result.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            })
        return result

    @property
    def tool_names(self) -> Set[str]:
        """Get set of registered tool names.

        Returns:
            Set containing the names of all registered tools
        """
        return set(self._tools.keys())
