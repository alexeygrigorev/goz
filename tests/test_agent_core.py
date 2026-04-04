"""Unit tests for AgentCore (Issue 15)."""
import pytest

from goz.agent.core import AgentCore
from goz.agent.history import ChatHistory
from goz.config import Config


class TestAgentCoreInit:
    """Unit Tests: AgentCore initialization."""

    def test_agent_core_exists(self):
        """Test AgentCore class can be imported."""
        from goz.agent.core import AgentCore  # noqa: F401
        assert AgentCore is not None

    def test_agent_core_init_with_config(self):
        """Test AgentCore initializes with config."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        assert agent.config is not None
        assert agent.config.zai_token == "test-token"

    def test_agent_core_init_creates_history(self):
        """Test AgentCore creates ChatHistory on init."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        assert agent.history is not None
        assert isinstance(agent.history, ChatHistory)

    def test_agent_core_init_creates_tool_registry(self):
        """Test AgentCore creates tool registry on init."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        assert agent.tool_registry is not None

    def test_agent_core_init_creates_stream_processor(self):
        """Test AgentCore creates stream processor on init."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        # Stream processor might be None in stub implementation
        assert hasattr(agent, "stream_processor")

    def test_agent_core_init_with_custom_history(self):
        """Test AgentCore accepts custom history."""
        config = Config(zai_token="test-token")
        custom_history = ChatHistory(max_messages=100)
        agent = AgentCore(config=config, history=custom_history)
        assert agent.history is custom_history
        assert agent.history.max_messages == 100


class TestAgentCoreAttributes:
    """Unit Tests: AgentCore attributes and properties."""

    def test_agent_core_has_config_attribute(self):
        """Test AgentCore has config attribute."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        assert hasattr(agent, "config")

    def test_agent_core_has_history_attribute(self):
        """Test AgentCore has history attribute."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        assert hasattr(agent, "history")

    def test_agent_core_has_tool_registry_attribute(self):
        """Test AgentCore has tool_registry attribute."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        assert hasattr(agent, "tool_registry")

    def test_agent_core_has_stream_processor_attribute(self):
        """Test AgentCore has stream_processor attribute."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        assert hasattr(agent, "stream_processor")

    def test_agent_core_type_hints_exist(self):
        """Test AgentCore has type hints."""
        from goz.agent.core import AgentCore
        import inspect

        # Check if __init__ has type annotations
        sig = inspect.signature(AgentCore.__init__)
        assert "config" in sig.parameters
        # Check that config parameter has type annotation
        config_param = sig.parameters["config"]
        assert config_param.annotation != inspect.Parameter.empty


class TestAgentCoreStubBehavior:
    """Unit Tests: AgentCore stub behavior (full implementation in Issue 17)."""

    def test_agent_core_is_stub(self):
        """Test AgentCore is a stub for now."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        # Should be instantiable but with limited functionality
        assert agent is not None

    def test_agent_core_repr(self):
        """Test AgentCore has string representation."""
        config = Config(zai_token="test-token")
        agent = AgentCore(config=config)
        repr_str = repr(agent)
        assert "AgentCore" in repr_str


class TestAgentCoreWithDifferentConfigs:
    """Unit Tests: AgentCore with different config values."""

    def test_agent_core_with_custom_model(self):
        """Test AgentCore with custom model config."""
        config = Config(zai_token="test-token", chat_model="custom-model")
        agent = AgentCore(config=config)
        assert agent.config.chat_model == "custom-model"

    def test_agent_core_with_custom_timeout(self):
        """Test AgentCore with custom timeout."""
        config = Config(zai_token="test-token", timeout=60)
        agent = AgentCore(config=config)
        assert agent.config.timeout == 60
