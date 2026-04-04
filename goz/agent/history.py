"""Chat history management for the agent.

This module provides classes for managing conversation history:
- ChatMessage: Dataclass for individual chat messages
- ChatHistory: Container for managing message history with compression
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


# Role types for chat messages (Acceptance Criteria 5)
MessageRole = Literal["user", "assistant", "tool", "tool_call", "agent_activity"]


@dataclass
class ToolCall:
    """Represents a tool call in a message.

    Attributes:
        id: Unique identifier for the tool call
        name: Name of the tool being called
        input: Parameters for the tool call
    """

    id: str
    name: str
    input: dict

    def to_dict(self) -> dict:
        """Convert ToolCall to dict for JSON serialization.

        Returns:
            Dict representation of this ToolCall
        """
        return {
            "id": self.id,
            "name": self.name,
            "input": self.input,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        """Create ToolCall from dict.

        Args:
            data: Dict representation of ToolCall

        Returns:
            ToolCall instance
        """
        return cls(
            id=data["id"],
            name=data["name"],
            input=data["input"],
        )


@dataclass
class ChatMessage:
    """A chat message in the conversation history.

    Attributes:
        role: The role of the message sender (user, assistant, tool, etc.)
        content: Text content of the message
        tool_calls: List of tool calls made in this message
        tool_result_id: ID of the tool call this result is for
        timestamp: When the message was created
    """

    role: MessageRole
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert ChatMessage to dict for JSON serialization.

        Returns:
            Dict representation of this ChatMessage
        """
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_result_id": self.tool_result_id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        """Create ChatMessage from dict.

        Args:
            data: Dict representation of ChatMessage

        Returns:
            ChatMessage instance
        """
        return cls(
            role=data["role"],
            content=data["content"],
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            tool_result_id=data.get("tool_result_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class ChatHistory:
    """Manages chat message history with compression support.

    This class stores conversation messages and provides methods for
    adding messages, converting to API format, and compressing old
    messages when approaching the limit.

    Attributes:
        messages: List of ChatMessage objects
        max_messages: Maximum number of messages before compression
    """

    DEFAULT_MAX_MESSAGES: int = 50
    COMPRESS_THRESHOLD: float = 0.8  # Compress at 80% capacity

    def __init__(
        self,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        messages: list[ChatMessage] | None = None,
    ) -> None:
        """Initialize ChatHistory.

        Args:
            max_messages: Maximum messages before compression (default: 50)
            messages: Optional initial list of messages
        """
        self.max_messages = max_messages
        self.messages: list[ChatMessage] = messages if messages is not None else []

    @property
    def message_count(self) -> int:
        """Return the number of messages in history."""
        return len(self.messages)

    def add(self, message: ChatMessage) -> None:
        """Add a message to history.

        Args:
            message: ChatMessage to add

        Triggers compression if approaching max_messages.
        """
        self.messages.append(message)

        # Auto-compress if exceeding threshold
        if self.message_count >= int(self.max_messages * self.COMPRESS_THRESHOLD):
            self.compress()

    def to_api_format(self) -> list[dict]:
        """Convert messages to Anthropic API format.

        Returns:
            List of message dicts compatible with Anthropic's Messages API
        """
        api_messages: list[dict] = []

        for msg in self.messages:
            # Anthropic API only accepts "user" and "assistant" roles in messages.
            # Convert system messages (e.g. compaction summaries) to user messages.
            role = msg.role if msg.role in ("user", "assistant", "tool") else "user"
            api_msg: dict = {"role": role, "content": msg.content}

            # Add tool_calls if present
            if msg.tool_calls:
                # Convert ToolCall objects to dicts (also handle dict input for testing)
                api_msg["tool_calls"] = [
                    {"id": tc.id, "name": tc.name, "input": tc.input}
                    if isinstance(tc, ToolCall)
                    else tc
                    for tc in msg.tool_calls
                ]

            # Handle tool result messages
            if msg.tool_result_id:
                api_msg["tool_result_id"] = msg.tool_result_id
                # In Anthropic format, tool results are from user perspective
                api_msg["role"] = "user"

            api_messages.append(api_msg)

        return api_messages

    def compress(self) -> None:
        """Compress old messages by summarizing them.

        When called, this method:
        1. Takes old messages (keeping recent ones)
        2. Creates a summary message
        3. Replaces old messages with the summary

        The goal is to reduce history to ~50% of max_messages.
        """
        # Only compress if we have enough messages
        threshold = int(self.max_messages * self.COMPRESS_THRESHOLD)
        if self.message_count < threshold:
            return

        # Keep recent messages (last ~40% or at least 2)
        keep_count = max(2, min(self.message_count, int(self.max_messages * 0.4)))
        recent_messages = self.messages[-keep_count:]
        old_messages = self.messages[:-keep_count]

        if not old_messages:
            return

        # Create summary of old messages
        summary = self._create_summary(old_messages)

        # Replace with summary + recent messages
        self.messages = [summary] + recent_messages

    def _create_summary(self, messages: list[ChatMessage]) -> ChatMessage:
        """Create a summary message from a list of messages.

        Args:
            messages: Messages to summarize

        Returns:
            A ChatMessage containing the summary
        """
        # Count message types
        user_count = sum(1 for m in messages if m.role == "user")
        asst_count = sum(1 for m in messages if m.role == "assistant")
        tool_count = sum(1 for m in messages if m.role == "tool")

        # Create summary text
        summary_text = (
            f"[Summary of {len(messages)} previous messages: "
            f"{user_count} user messages, {asst_count} assistant responses"
        )
        if tool_count > 0:
            summary_text += f", {tool_count} tool calls"
        summary_text += "]"

        return ChatMessage(role="system", content=summary_text)

    def clear(self) -> None:
        """Clear all messages from history."""
        self.messages.clear()
