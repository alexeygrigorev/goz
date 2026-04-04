"""Unit tests for Tool Base and Registry (Issue 18)."""
import pytest

from goz.agent.tools.base import Tool, BaseTool, ToolInputError, ToolNotFoundError
from goz.agent.tools.registry import ToolRegistry


# ========== Test Tool Protocol ==========


class TestToolProtocol:
    """Unit Tests: Tool Protocol definition."""

    def test_tool_protocol_exists(self):
        """Test Tool protocol can be imported."""
        from goz.agent.tools.base import Tool  # noqa: F401
        assert Tool is not None

    def test_tool_has_name_attribute(self):
        """Test Tool protocol requires name attribute."""
        # Create a minimal tool implementation
        class MinimalTool:
            name: str = "test_tool"
            description: str = "A test tool"
            input_schema: dict = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MinimalTool()
        assert hasattr(tool, "name")
        assert tool.name == "test_tool"

    def test_tool_has_description_attribute(self):
        """Test Tool protocol requires description attribute."""
        class MinimalTool:
            name: str = "test_tool"
            description: str = "A test tool"
            input_schema: dict = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MinimalTool()
        assert hasattr(tool, "description")
        assert tool.description == "A test tool"

    def test_tool_has_input_schema_attribute(self):
        """Test Tool protocol requires input_schema attribute."""
        class MinimalTool:
            name: str = "test_tool"
            description: str = "A test tool"
            input_schema: dict = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MinimalTool()
        assert hasattr(tool, "input_schema")
        assert tool.input_schema == {"type": "object"}

    def test_tool_has_execute_method(self):
        """Test Tool protocol requires execute async method."""
        class MinimalTool:
            name: str = "test_tool"
            description: str = "A test tool"
            input_schema: dict = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = MinimalTool()
        assert hasattr(tool, "execute")
        import inspect
        assert inspect.iscoroutinefunction(tool.execute)


# ========== Test Tool Exceptions ==========


class TestToolInputError:
    """Unit Tests: ToolInputError exception."""

    def test_tool_input_error_exists(self):
        """Test ToolInputError can be imported."""
        from goz.agent.tools.base import ToolInputError  # noqa: F401
        assert ToolInputError is not None

    def test_tool_input_error_is_exception(self):
        """Test ToolInputError is an Exception subclass."""
        assert issubclass(ToolInputError, Exception)

    def test_tool_input_error_can_be_raised(self):
        """Test ToolInputError can be raised with message."""
        with pytest.raises(ToolInputError, match="Invalid input"):
            raise ToolInputError("Invalid input")

    def test_tool_input_error_message(self):
        """Test ToolInputError stores message."""
        error = ToolInputError("Test validation error")
        assert str(error) == "Test validation error"
        assert "Test validation error" in error.args


class TestToolNotFoundError:
    """Unit Tests: ToolNotFoundError exception."""

    def test_tool_not_found_error_exists(self):
        """Test ToolNotFoundError can be imported."""
        from goz.agent.tools.base import ToolNotFoundError  # noqa: F401
        assert ToolNotFoundError is not None

    def test_tool_not_found_error_is_exception(self):
        """Test ToolNotFoundError is an Exception subclass."""
        assert issubclass(ToolNotFoundError, Exception)

    def test_tool_not_found_error_can_be_raised(self):
        """Test ToolNotFoundError can be raised with tool name."""
        with pytest.raises(ToolNotFoundError, match="Tool.*not found"):
            raise ToolNotFoundError("unknown_tool")

    def test_tool_not_found_error_message(self):
        """Test ToolNotFoundError stores message."""
        error = ToolNotFoundError("my_tool")
        assert "my_tool" in str(error)


# ========== Test BaseTool Class ==========


class TestBaseTool:
    """Unit Tests: BaseTool class."""

    def test_base_tool_exists(self):
        """Test BaseTool class can be imported."""
        from goz.agent.tools.base import BaseTool  # noqa: F401
        assert BaseTool is not None

    def test_base_tool_can_be_subclassed(self):
        """Test BaseTool can be subclassed."""

        class ConcreteTool(BaseTool):
            name = "concrete_tool"
            description = "A concrete tool"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "concrete result"

        tool = ConcreteTool()
        assert tool.name == "concrete_tool"
        assert tool.description == "A concrete tool"

    def test_base_tool_has_working_dir(self):
        """Test BaseTool has working_dir attribute."""

        class ConcreteTool(BaseTool):
            name = "test_tool"
            description = "Test"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return str(self.working_dir)

        tool = ConcreteTool()
        assert hasattr(tool, "working_dir")
        assert tool.working_dir is not None

    def test_base_tool_working_dir_can_be_set(self):
        """Test BaseTool working_dir can be customized."""

        class ConcreteTool(BaseTool):
            name = "test_tool"
            description = "Test"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return str(self.working_dir)

        tool = ConcreteTool(working_dir="/custom/path")
        assert tool.working_dir == "/custom/path"

    def test_base_tool_validate_input_method_exists(self):
        """Test BaseTool has validate_input method."""
        tool = BaseTool()
        assert hasattr(tool, "validate_input")

    def test_base_tool_validate_input_with_valid_data(self):
        """Test BaseTool validate_input passes valid data."""
        tool = BaseTool()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        # Should not raise
        tool.validate_input(schema, {"name": "test"})

    def test_base_tool_validate_input_with_missing_required(self):
        """Test BaseTool validate_input raises for missing required."""
        tool = BaseTool()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        with pytest.raises(ToolInputError):
            tool.validate_input(schema, {})


# ========== Test ToolRegistry Class ==========


class TestToolRegistryInit:
    """Unit Tests: ToolRegistry initialization."""

    def test_tool_registry_exists(self):
        """Test ToolRegistry class can be imported."""
        from goz.agent.tools.registry import ToolRegistry  # noqa: F401
        assert ToolRegistry is not None

    def test_tool_registry_init_empty(self):
        """Test ToolRegistry initializes empty."""
        registry = ToolRegistry()
        assert registry is not None

    def test_tool_registry_has_internal_dict(self):
        """Test ToolRegistry has internal storage."""
        registry = ToolRegistry()
        assert hasattr(registry, "_tools")


class TestToolRegistryRegister:
    """Unit Tests: ToolRegistry.register()."""

    def test_tool_registry_register_method_exists(self):
        """Test ToolRegistry has register method."""
        registry = ToolRegistry()
        assert hasattr(registry, "register")

    def test_tool_registry_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        class TestTool:
            name = "test_tool"
            description = "Test"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = TestTool()
        registry.register(tool)
        assert "test_tool" in registry.tool_names

    def test_tool_registry_register_multiple(self):
        """Test registering multiple tools."""
        registry = ToolRegistry()

        class Tool1:
            name = "tool1"
            description = "First"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "1"

        class Tool2:
            name = "tool2"
            description = "Second"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "2"

        registry.register(Tool1())
        registry.register(Tool2())
        assert "tool1" in registry.tool_names
        assert "tool2" in registry.tool_names

    def test_tool_registry_register_duplicate_raises(self):
        """Test registering duplicate tool name raises."""
        registry = ToolRegistry()

        class TestTool:
            name = "duplicate"
            description = "Test"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        registry.register(TestTool())
        with pytest.raises(ValueError):
            registry.register(TestTool())


class TestToolRegistryUnregister:
    """Unit Tests: ToolRegistry.unregister()."""

    def test_tool_registry_unregister_method_exists(self):
        """Test ToolRegistry has unregister method."""
        registry = ToolRegistry()
        assert hasattr(registry, "unregister")

    def test_tool_registry_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()

        class TestTool:
            name = "to_remove"
            description = "Test"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = TestTool()
        registry.register(tool)
        assert "to_remove" in registry.tool_names

        registry.unregister("to_remove")
        assert "to_remove" not in registry.tool_names

    def test_tool_registry_unregister_nonexistent_is_noop(self):
        """Test unregistering non-existent tool doesn't raise."""
        registry = ToolRegistry()
        # Should not raise
        registry.unregister("does_not_exist")


class TestToolRegistryGet:
    """Unit Tests: ToolRegistry.get()."""

    def test_tool_registry_get_method_exists(self):
        """Test ToolRegistry has get method."""
        registry = ToolRegistry()
        assert hasattr(registry, "get")

    def test_tool_registry_get_registered_tool(self):
        """Test getting a registered tool."""
        registry = ToolRegistry()

        class TestTool:
            name = "my_tool"
            description = "Test"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "result"

        tool = TestTool()
        registry.register(tool)
        retrieved = registry.get("my_tool")
        assert retrieved is tool

    def test_tool_registry_get_unregistered_returns_none(self):
        """Test getting unregistered tool returns None."""
        registry = ToolRegistry()
        result = registry.get("does_not_exist")
        assert result is None


class TestToolRegistryListAll:
    """Unit Tests: ToolRegistry.list_all()."""

    def test_tool_registry_list_all_method_exists(self):
        """Test ToolRegistry has list_all method."""
        registry = ToolRegistry()
        assert hasattr(registry, "list_all")

    def test_tool_registry_list_all_empty(self):
        """Test listing all tools when empty."""
        registry = ToolRegistry()
        tools = registry.list_all()
        assert tools == []

    def test_tool_registry_list_all_returns_tools(self):
        """Test listing all registered tools."""
        registry = ToolRegistry()

        class Tool1:
            name = "tool1"
            description = "First"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "1"

        class Tool2:
            name = "tool2"
            description = "Second"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "2"

        t1 = Tool1()
        t2 = Tool2()
        registry.register(t1)
        registry.register(t2)

        tools = registry.list_all()
        assert len(tools) == 2
        assert t1 in tools
        assert t2 in tools


class TestToolRegistryToolNames:
    """Unit Tests: ToolRegistry.tool_names property."""

    def test_tool_registry_tool_names_exists(self):
        """Test ToolRegistry has tool_names property."""
        registry = ToolRegistry()
        assert hasattr(registry, "tool_names")

    def test_tool_registry_tool_names_is_set(self):
        """Test tool_names returns a set."""
        registry = ToolRegistry()
        names = registry.tool_names
        assert isinstance(names, set)

    def test_tool_registry_tool_names_returns_names(self):
        """Test tool_names returns registered tool names."""
        registry = ToolRegistry()

        class Tool1:
            name = "alpha"
            description = "A"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "a"

        class Tool2:
            name = "beta"
            description = "B"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "b"

        registry.register(Tool1())
        registry.register(Tool2())

        names = registry.tool_names
        assert names == {"alpha", "beta"}


class TestToolRegistryOpenAISchema:
    """Unit Tests: ToolRegistry.to_openai_schema()."""

    def test_tool_registry_to_openai_schema_method_exists(self):
        """Test ToolRegistry has to_openai_schema method."""
        registry = ToolRegistry()
        assert hasattr(registry, "to_openai_schema")

    def test_tool_registry_to_openai_schema_empty(self):
        """Test OpenAI schema export when empty."""
        registry = ToolRegistry()
        schema = registry.to_openai_schema()
        assert schema == []

    def test_tool_registry_to_openai_schema_format(self):
        """Test OpenAI schema export format."""
        registry = ToolRegistry()

        class TestTool:
            name = "test_tool"
            description = "A test tool for OpenAI"
            input_schema = {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                },
                "required": ["arg1"],
            }

            async def execute(self, **kwargs):
                return "result"

        registry.register(TestTool())
        schema = registry.to_openai_schema()

        assert len(schema) == 1
        assert schema[0]["name"] == "test_tool"
        assert schema[0]["description"] == "A test tool for OpenAI"
        assert "input_schema" in schema[0] or "parameters" in schema[0]

    def test_tool_registry_to_openai_schema_multiple(self):
        """Test OpenAI schema export with multiple tools."""
        registry = ToolRegistry()

        class Tool1:
            name = "tool1"
            description = "First tool"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "1"

        class Tool2:
            name = "tool2"
            description = "Second tool"
            input_schema = {"type": "object"}

            async def execute(self, **kwargs):
                return "2"

        registry.register(Tool1())
        registry.register(Tool2())
        schema = registry.to_openai_schema()

        assert len(schema) == 2
        names = {s["name"] for s in schema}
        assert names == {"tool1", "tool2"}


# ========== Test Integration ==========


class TestToolRegistryIntegration:
    """Integration Tests: ToolRegistry with actual tools."""

    @pytest.mark.asyncio
    async def test_tool_execution_through_registry(self):
        """Test executing a tool retrieved from registry."""
        registry = ToolRegistry()

        class ExecutableTool(BaseTool):
            name = "echo"
            description = "Echo back input"
            input_schema = {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            }

            async def execute(self, **kwargs):
                return f"Echo: {kwargs.get('message', '')}"

        tool = ExecutableTool()
        registry.register(tool)

        retrieved = registry.get("echo")
        result = await retrieved.execute(message="Hello")
        assert result == "Echo: Hello"

    @pytest.mark.asyncio
    async def test_multiple_tools_execute_independently(self):
        """Test multiple tools execute independently."""
        registry = ToolRegistry()

        class AddTool(BaseTool):
            name = "add"
            description = "Add numbers"
            input_schema = {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            }

            async def execute(self, **kwargs):
                return str(kwargs["a"] + kwargs["b"])

        class MultiplyTool(BaseTool):
            name = "multiply"
            description = "Multiply numbers"
            input_schema = {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            }

            async def execute(self, **kwargs):
                return str(kwargs["a"] * kwargs["b"])

        registry.register(AddTool())
        registry.register(MultiplyTool())

        add_result = await registry.get("add").execute(a=3, b=5)
        mult_result = await registry.get("multiply").execute(a=3, b=5)

        assert add_result == "8"
        assert mult_result == "15"
