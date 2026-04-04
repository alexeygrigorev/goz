"""Unit tests for chat history management (Issue 15)."""
from datetime import datetime

import pytest

from goz.agent.history import ChatMessage, ChatHistory


class TestChatMessage:
    """Unit Tests: ChatMessage dataclass."""

    def test_chat_message_creation_with_required_fields(self):
        """Test ChatMessage can be created with required fields."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls == []
        assert msg.tool_result_id is None
        assert isinstance(msg.timestamp, datetime)

    def test_chat_message_with_all_fields(self):
        """Test ChatMessage can be created with all fields."""
        now = datetime.now()
        msg = ChatMessage(
            role="assistant",
            content="Response",
            tool_calls=[{"name": "test"}],
            tool_result_id="result-123",
            timestamp=now,
        )
        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert msg.tool_calls == [{"name": "test"}]
        assert msg.tool_result_id == "result-123"
        assert msg.timestamp == now

    def test_chat_message_role_types(self):
        """Test ChatMessage accepts all valid role types."""
        valid_roles = ["user", "assistant", "tool", "tool_call", "agent_activity"]
        for role in valid_roles:
            msg = ChatMessage(role=role, content=f"Message from {role}")
            assert msg.role == role

    def test_chat_message_defaults(self):
        """Test ChatMessage has correct default values."""
        msg = ChatMessage(role="user", content="test")
        assert msg.tool_calls == []
        assert msg.tool_result_id is None
        # Default timestamp should be close to now
        assert (datetime.now() - msg.timestamp).total_seconds() < 1


class TestChatHistoryInit:
    """Unit Tests: ChatHistory initialization."""

    def test_chat_history_default_init(self):
        """Test ChatHistory initializes with default max_messages."""
        history = ChatHistory()
        assert history.messages == []
        assert history.max_messages == 50
        assert history.message_count == 0

    def test_chat_history_custom_max_messages(self):
        """Test ChatHistory initializes with custom max_messages."""
        history = ChatHistory(max_messages=100)
        assert history.max_messages == 100

    def test_chat_history_with_initial_messages(self):
        """Test ChatHistory can be initialized with messages."""
        msgs = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
        ]
        history = ChatHistory(messages=msgs)
        assert history.message_count == 2
        assert history.messages[0].content == "Hello"

    def test_chat_history_message_count_property(self):
        """Test message_count property returns correct count."""
        history = ChatHistory()
        assert history.message_count == 0

        history.add(ChatMessage(role="user", content="First"))
        assert history.message_count == 1

        history.add(ChatMessage(role="assistant", content="Second"))
        assert history.message_count == 2


class TestChatHistoryAdd:
    """Unit Tests: ChatHistory.add() method."""

    def test_add_single_message(self):
        """Test adding a single message to history."""
        history = ChatHistory()
        msg = ChatMessage(role="user", content="Hello")
        history.add(msg)
        assert history.message_count == 1
        assert history.messages[0] == msg

    def test_add_multiple_messages(self):
        """Test adding multiple messages in order."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content="First"))
        history.add(ChatMessage(role="assistant", content="Second"))
        history.add(ChatMessage(role="user", content="Third"))

        assert history.message_count == 3
        assert history.messages[0].content == "First"
        assert history.messages[1].content == "Second"
        assert history.messages[2].content == "Third"

    def test_add_with_auto_compress_when_exceeding_limit(self):
        """Test compress is triggered when exceeding max_messages."""
        # Use small max for testing
        history = ChatHistory(max_messages=4)
        history.add(ChatMessage(role="user", content="1"))
        history.add(ChatMessage(role="assistant", content="2"))
        history.add(ChatMessage(role="user", content="3"))
        # At 80% capacity (3.2), should not trigger yet
        assert history.message_count == 3

        # Add 4th message - exceeds 80%
        history.add(ChatMessage(role="assistant", content="4"))
        # After compress, should have fewer messages
        # Summary message + recent messages
        assert history.message_count < 4


class TestChatHistoryToApiFormat:
    """Unit Tests: ChatHistory.to_api_format() method."""

    def test_to_api_format_empty_history(self):
        """Test to_api_format returns empty list for empty history."""
        history = ChatHistory()
        result = history.to_api_format()
        assert result == []

    def test_to_api_format_simple_user_message(self):
        """Test to_api_format formats simple user message."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content="Hello"))
        result = history.to_api_format()
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_to_api_format_simple_assistant_message(self):
        """Test to_api_format formats assistant message."""
        history = ChatHistory()
        history.add(ChatMessage(role="assistant", content="Response"))
        result = history.to_api_format()
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Response"

    def test_to_api_format_with_tool_call(self):
        """Test to_api_format formats message with tool calls."""
        history = ChatHistory()
        msg = ChatMessage(
            role="assistant",
            content="Let me check",
            tool_calls=[{"id": "call_123", "name": "search", "input": {"query": "test"}}],
        )
        history.add(msg)
        result = history.to_api_format()
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Let me check"
        assert "tool_calls" in result[0] or "toolUse" in result[0]

    def test_to_api_format_with_tool_result(self):
        """Test to_api_format formats tool result message."""
        history = ChatHistory()
        msg = ChatMessage(
            role="tool",
            content="Result data",
            tool_result_id="call_123",
        )
        history.add(msg)
        result = history.to_api_format()
        assert len(result) == 1
        # Tool results in Anthropic format
        assert result[0]["role"] == "user" or "tool_result_id" in result[0]

    def test_to_api_format_preserves_order(self):
        """Test to_api_format preserves message order."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content="First"))
        history.add(ChatMessage(role="assistant", content="Second"))
        history.add(ChatMessage(role="user", content="Third"))

        result = history.to_api_format()
        assert result[0]["content"] == "First"
        assert result[1]["content"] == "Second"
        assert result[2]["content"] == "Third"

    def test_to_api_format_valid_anthropic_format(self):
        """Test to_api_format returns valid Anthropic message structure."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content="Hello"))
        history.add(ChatMessage(role="assistant", content="Hi"))

        result = history.to_api_format()
        # Each message should have role and content
        for msg in result:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["user", "assistant", "tool"]


class TestChatHistoryCompress:
    """Unit Tests: ChatHistory.compress() method."""

    def test_compress_empty_history(self):
        """Test compress on empty history does nothing."""
        history = ChatHistory()
        history.compress()
        assert history.message_count == 0

    def test_compress_below_threshold(self):
        """Test compress does nothing when below threshold."""
        history = ChatHistory(max_messages=50)
        # Add 10 messages (well below 80% threshold)
        for i in range(10):
            history.add(ChatMessage(role="user", content=f"Message {i}"))

        initial_count = history.message_count
        history.compress()
        assert history.message_count == initial_count

    def test_compress_above_threshold_adds_summary(self):
        """Test compress adds summary when above threshold."""
        history = ChatHistory(max_messages=10)
        # Add 8 messages (exceeds 80% of 10 = 8)
        for i in range(8):
            if i % 2 == 0:
                history.add(ChatMessage(role="user", content=f"User message {i}"))
            else:
                history.add(ChatMessage(role="assistant", content=f"Assistant message {i}"))

        history.compress()
        # Should have summary message + some recent messages
        assert history.message_count > 0
        # Should have summary at the beginning
        assert history.messages[0].role == "system" or "summary" in history.messages[0].content.lower()

    def test_compress_reduces_message_count(self):
        """Test compress reduces total message count."""
        history = ChatHistory(max_messages=10)
        # Fill to just below threshold
        for i in range(9):
            history.add(ChatMessage(role="user", content=f"Message {i}"))

        # Trigger compress by adding more
        history.add(ChatMessage(role="assistant", content="Last"))
        # Should compress due to exceeding threshold
        if history.message_count >= 8:  # Only compress if threshold met
            history.compress()
            # After compression, should be reduced
            assert history.message_count < 10


class TestChatHistoryClear:
    """Unit Tests: ChatHistory.clear() method."""

    def test_clear_removes_all_messages(self):
        """Test clear removes all messages."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content="First"))
        history.add(ChatMessage(role="assistant", content="Second"))
        assert history.message_count == 2

        history.clear()
        assert history.message_count == 0
        assert history.messages == []

    def test_clear_allows_readding(self):
        """Test clear allows adding new messages after."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content="First"))
        history.clear()
        assert history.message_count == 0

        history.add(ChatMessage(role="user", content="New message"))
        assert history.message_count == 1
        assert history.messages[0].content == "New message"


class TestChatHistoryEdgeCases:
    """Edge Case Tests for ChatHistory."""

    def test_empty_content_message(self):
        """Test message with empty content."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content=""))
        assert history.message_count == 1

    def test_very_long_message_content(self):
        """Test message with very long content."""
        history = ChatHistory()
        long_content = "x" * 10000
        history.add(ChatMessage(role="assistant", content=long_content))
        assert history.message_count == 1
        assert len(history.messages[0].content) == 10000

    def test_unicode_content(self):
        """Test message with unicode content."""
        history = ChatHistory()
        unicode_content = "Hello 世界 🌍"
        history.add(ChatMessage(role="user", content=unicode_content))
        assert history.messages[0].content == unicode_content

    def test_tool_call_with_empty_list(self):
        """Test message with empty tool_calls list."""
        history = ChatHistory()
        msg = ChatMessage(role="assistant", content="No tools", tool_calls=[])
        history.add(msg)
        assert history.message_count == 1

    def test_get_messages_by_role(self):
        """Test filtering messages by role if supported."""
        history = ChatHistory()
        history.add(ChatMessage(role="user", content="U1"))
        history.add(ChatMessage(role="assistant", content="A1"))
        history.add(ChatMessage(role="user", content="U2"))

        # Get user messages
        user_msgs = [m for m in history.messages if m.role == "user"]
        assert len(user_msgs) == 2

        # Get assistant messages
        asst_msgs = [m for m in history.messages if m.role == "assistant"]
        assert len(asst_msgs) == 1
