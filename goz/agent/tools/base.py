"""Base tool definitions for goz interactive coding agent.

This module provides:
- Tool: Protocol defining the tool interface
- BaseTool: Base class with common functionality
- Tool exception classes
"""
from __future__ import annotations

import os
from typing import Any, Protocol


class ToolError(Exception):
    """Base error for tool operations."""

    pass


class ToolInputError(ToolError):
    """Tool input validation failed.

    Raised when tool inputs do not match the expected schema.
    """

    pass


class ToolNotFoundError(ToolError):
    """Tool not found in registry.

    Raised when attempting to retrieve a tool that hasn't been registered.
    """

    def __init__(self, tool_name: str) -> None:
        """Initialize ToolNotFoundError.

        Args:
            tool_name: Name of the tool that was not found
        """
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' not found")


class ToolExecutionError(ToolError):
    """Tool execution failed.

    Raised when a tool's execute method encounters an error during execution.
    """

    pass


class Tool(Protocol):
    """Protocol for agent tools.

    A Tool is a callable unit that can be invoked by the agent to perform
    specific actions like reading files, running commands, searching code, etc.

    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description of what the tool does
        input_schema: JSON Schema describing the expected input format
    """

    name: str
    description: str
    input_schema: dict

    async def execute(self, **kwargs: Any) -> str:
        """Execute the tool with the given arguments.

        Args:
            **kwargs: Tool-specific arguments matching input_schema

        Returns:
            String result to send back to the API

        Raises:
            ToolInputError: If input validation fails
            ToolExecutionError: If execution fails
        """
        ...


class BaseTool:
    """Base class for tools with common functionality.

    Provides working directory management and input validation utilities
    for tool implementations.

    Attributes:
        working_dir: Current working directory for file operations
    """

    def __init__(self, working_dir: str | None = None) -> None:
        """Initialize BaseTool.

        Args:
            working_dir: Working directory for file operations.
                Defaults to current directory if not provided.
        """
        self.working_dir = working_dir or os.getcwd()

    def validate_input(self, schema: dict, data: dict) -> None:
        """Validate input against JSON schema.

        Performs basic validation checking for required fields and types.
        This is a simplified validator - production use should use
        jsonschema library for full JSON Schema compliance.

        Args:
            schema: JSON Schema for validation
            data: Input data to validate

        Raises:
            ToolInputError: If validation fails
        """
        if not isinstance(data, dict):
            raise ToolInputError(
                f"Invalid input: expected object, got {type(data).__name__}"
            )

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                raise ToolInputError(
                    f"Missing required field: '{field}'"
                )

        # Basic type checking for properties
        properties = schema.get("properties", {})
        for field, value in data.items():
            if field not in properties:
                continue  # Allow extra fields by default

            prop_schema = properties[field]
            expected_type = prop_schema.get("type")

            if expected_type == "string":
                if not isinstance(value, str):
                    raise ToolInputError(
                        f"Field '{field}': expected string, got {type(value).__name__}"
                    )
            elif expected_type == "number":
                if not isinstance(value, (int, float)):
                    raise ToolInputError(
                        f"Field '{field}': expected number, got {type(value).__name__}"
                    )
            elif expected_type == "integer":
                if not isinstance(value, int):
                    raise ToolInputError(
                        f"Field '{field}': expected integer, got {type(value).__name__}"
                    )
            elif expected_type == "boolean":
                if not isinstance(value, bool):
                    raise ToolInputError(
                        f"Field '{field}': expected boolean, got {type(value).__name__}"
                    )
            elif expected_type == "array":
                if not isinstance(value, list):
                    raise ToolInputError(
                        f"Field '{field}': expected array, got {type(value).__name__}"
                    )
                # Check item type if specified
                items_schema = prop_schema.get("items", {})
                item_type = items_schema.get("type")
                if item_type:
                    for i, item in enumerate(value):
                        if item_type == "string" and not isinstance(item, str):
                            raise ToolInputError(
                                f"Field '{field}[{i}]': expected string, got {type(item).__name__}"
                            )
                        elif item_type == "integer" and not isinstance(item, int):
                            raise ToolInputError(
                                f"Field '{field}[{i}]': expected integer, got {type(item).__name__}"
                            )

            # Check min/max for arrays
            if expected_type == "array" and isinstance(value, list):
                min_items = prop_schema.get("minItems")
                max_items = prop_schema.get("maxItems")
                if min_items is not None and len(value) < min_items:
                    raise ToolInputError(
                        f"Field '{field}': minimum {min_items} items required, got {len(value)}"
                    )
                if max_items is not None and len(value) > max_items:
                    raise ToolInputError(
                        f"Field '{field}': maximum {max_items} items allowed, got {len(value)}"
                    )
