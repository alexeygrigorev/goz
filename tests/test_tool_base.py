"""Unit tests for Tool Base + Registry (Issue 18)."""
import pytest
from typing import Protocol

from goz.agent.tools.base import Tool, BaseTool, ToolInputError, ToolNotFoundError, ToolExecutionError


class TestToolProtocol:
    """Unit Tests: Tool protocol definition."""

    def test_tool_protocol_exists(self):
        """Test Tool protocol can be imported."""
        from goz.agent.tools.base import Tool  # noqa: F401
        assert Tool is not None

    def test_tool_protocol_has_name(self):
        """Test Tool protocol requires name attribute."""
        class MockTool(Tool):
            name = "test_tool"
            description = "A test tool"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MockTool()
        assert hasattr(tool, 'name')
        assert tool.name == "test_tool"

    def test_tool_protocol_has_description(self):
        """Test Tool protocol requires description attribute."""
        class MockTool(Tool):
            name = "test_tool"
            description = "A test tool"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MockTool()
        assert hasattr(tool, 'description')
        assert tool.description == "A test tool"

    def test_tool_protocol_has_input_schema(self):
        """Test Tool protocol requires input_schema attribute."""
        class MockTool(Tool):
            name = "test_tool"
            description = "A test tool"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MockTool()
        assert hasattr(tool, 'input_schema')
        assert tool.input_schema == {"type": "object"}

    def test_tool_protocol_has_execute_method(self):
        """Test Tool protocol requires execute method."""
        class MockTool(Tool):
            name = "test_tool"
            description = "A test tool"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MockTool()
        assert hasattr(tool, 'execute')
        assert callable(tool.execute)


class TestBaseTool:
    """Unit Tests: BaseTool class."""

    def test_base_tool_exists(self):
        """Test BaseTool class can be imported."""
        from goz.agent.tools.base import BaseTool  # noqa: F401
        assert BaseTool is not None

    def test_base_tool_init_default_working_dir(self):
        """Test BaseTool initializes with default working_dir."""
        import os
        tool = BaseTool()
        assert tool.working_dir == os.getcwd()

    def test_base_tool_init_custom_working_dir(self):
        """Test BaseTool initializes with custom working_dir."""
        tool = BaseTool(working_dir="/custom/path")
        assert tool.working_dir == "/custom/path"

    def test_base_tool_validate_input_valid(self):
        """Test validate_input passes with valid data."""
        tool = BaseTool()
        schema = {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"}
            },
            "required": ["file_path"]
        }
        data = {"file_path": "test.py"}
        # Should not raise
        tool.validate_input(schema, data)

    def test_base_tool_validate_input_missing_required(self):
        """Test validate_input raises on missing required field."""
        tool = BaseTool()
        schema = {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"}
            },
            "required": ["file_path"]
        }
        data = {}  # Missing file_path
        with pytest.raises(ToolInputError):
            tool.validate_input(schema, data)

    def test_base_tool_validate_input_wrong_type(self):
        """Test validate_input raises on wrong type."""
        tool = BaseTool()
        schema = {
            "type": "object",
            "properties": {
                "line_range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2
                }
            }
        }
        data = {"line_range": "not-an-array"}
        with pytest.raises(ToolInputError):
            tool.validate_input(schema, data)

    def test_base_tool_validate_input_array_constraints(self):
        """Test validate_input enforces array constraints."""
        tool = BaseTool()
        schema = {
            "type": "object",
            "properties": {
                "line_range": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 2,
                    "maxItems": 2
                }
            }
        }
        # Too many items
        data = {"line_range": [1, 2, 3]}
        with pytest.raises(ToolInputError):
            tool.validate_input(schema, data)


class TestToolExceptions:
    """Unit Tests: Tool exceptions."""

    def test_tool_input_error_exists(self):
        """Test ToolInputError can be imported."""
        from goz.agent.tools.base import ToolInputError  # noqa: F401
        assert ToolInputError is not None

    def test_tool_input_error_is_exception(self):
        """Test ToolInputError is an Exception."""
        assert issubclass(ToolInputError, Exception)

    def test_tool_not_found_error_exists(self):
        """Test ToolNotFoundError can be imported."""
        from goz.agent.tools.base import ToolNotFoundError  # noqa: F401
        assert ToolNotFoundError is not None

    def test_tool_not_found_error_is_exception(self):
        """Test ToolNotFoundError is an Exception."""
        assert issubclass(ToolNotFoundError, Exception)

    def test_tool_execution_error_exists(self):
        """Test ToolExecutionError can be imported."""
        from goz.agent.tools.base import ToolExecutionError  # noqa: F401
        assert ToolExecutionError is not None

    def test_tool_execution_error_is_exception(self):
        """Test ToolExecutionError is an Exception."""
        assert issubclass(ToolExecutionError, Exception)

    def test_tool_input_error_message(self):
        """Test ToolInputError stores message."""
        error = ToolInputError("Invalid input")
        assert str(error) == "Invalid input"
        assert "Invalid input" in error.args

    def test_tool_not_found_error_message(self):
        """Test ToolNotFoundError stores message."""
        error = ToolNotFoundError("tool_not_found")
        assert "tool_not_found" in str(error)


class TestConcreteToolImplementation:
    """Unit Tests: Concrete tool implementation using BaseTool."""

    def test_concrete_tool_creation(self):
        """Test creating a concrete tool using BaseTool."""

        class SimpleTool(BaseTool):
            name = "simple"
            description = "A simple tool"
            input_schema = {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }

            async def execute(self, message: str) -> str:
                self.validate_input(self.input_schema, {"message": message})
                return f"Echo: {message}"

        tool = SimpleTool()
        assert tool.name == "simple"
        assert tool.description == "A simple tool"

    @pytest.mark.asyncio
    async def test_concrete_tool_execute(self):
        """Test executing a concrete tool."""

        class SimpleTool(BaseTool):
            name = "simple"
            description = "A simple tool"
            input_schema = {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }

            async def execute(self, message: str) -> str:
                self.validate_input(self.input_schema, {"message": message})
                return f"Echo: {message}"

        tool = SimpleTool()
        result = await tool.execute(message="hello")
        assert result == "Echo: hello"
