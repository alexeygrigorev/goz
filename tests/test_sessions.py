"""Tests for session persistence (Issue 27).

Tests follow TDD: written first to verify behavior, then implementation.
"""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from goz.agent.history import ChatMessage, ToolCall
from goz.agent.sessions import Session, SessionInfo, SessionManager


class TestToolCallSerialization:
    """Test ToolCall serialization for session persistence."""

    def test_tool_call_to_dict(self) -> None:
        """Test ToolCall.to_dict() converts to dictionary."""
        tc = ToolCall(id="call_123", name="bash", input={"command": "ls"})
        result = tc.to_dict()
        assert result == {"id": "call_123", "name": "bash", "input": {"command": "ls"}}

    def test_tool_call_from_dict(self) -> None:
        """Test ToolCall.from_dict() creates from dictionary."""
        data = {"id": "call_123", "name": "bash", "input": {"command": "ls"}}
        tc = ToolCall.from_dict(data)
        assert tc.id == "call_123"
        assert tc.name == "bash"
        assert tc.input == {"command": "ls"}

    def test_tool_call_round_trip(self) -> None:
        """Test ToolCall can round-trip through dict."""
        original = ToolCall(id="call_456", name="view_file", input={"path": "/tmp/file.txt"})
        round_trip = ToolCall.from_dict(original.to_dict())
        assert round_trip.id == original.id
        assert round_trip.name == original.name
        assert round_trip.input == original.input


class TestChatMessageSerialization:
    """Test ChatMessage serialization for session persistence."""

    def test_chat_message_to_dict(self) -> None:
        """Test ChatMessage.to_dict() converts to dictionary."""
        msg = ChatMessage(
            role="user",
            content="Hello world",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
        )
        result = msg.to_dict()
        assert result["role"] == "user"
        assert result["content"] == "Hello world"
        assert result["timestamp"] == "2025-01-01T12:00:00"
        assert result["tool_calls"] == []
        assert result["tool_result_id"] is None

    def test_chat_message_to_dict_with_tool_calls(self) -> None:
        """Test ChatMessage.to_dict() includes tool_calls."""
        tc = ToolCall(id="call_123", name="bash", input={"command": "ls"})
        msg = ChatMessage(
            role="assistant",
            content="Running command",
            tool_calls=[tc],
        )
        result = msg.to_dict()
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0] == {"id": "call_123", "name": "bash", "input": {"command": "ls"}}

    def test_chat_message_to_dict_with_tool_result(self) -> None:
        """Test ChatMessage.to_dict() includes tool_result_id."""
        msg = ChatMessage(
            role="tool",
            content="Output: file1.txt",
            tool_result_id="call_123",
        )
        result = msg.to_dict()
        assert result["tool_result_id"] == "call_123"

    def test_chat_message_from_dict(self) -> None:
        """Test ChatMessage.from_dict() creates from dictionary."""
        data = {
            "role": "user",
            "content": "Hello world",
            "timestamp": "2025-01-01T12:00:00",
            "tool_calls": [],
            "tool_result_id": None,
        }
        msg = ChatMessage.from_dict(data)
        assert msg.role == "user"
        assert msg.content == "Hello world"
        assert msg.timestamp == datetime(2025, 1, 1, 12, 0, 0)

    def test_chat_message_from_dict_with_tool_calls(self) -> None:
        """Test ChatMessage.from_dict() restores tool_calls."""
        data = {
            "role": "assistant",
            "content": "Running command",
            "timestamp": "2025-01-01T12:00:00",
            "tool_calls": [{"id": "call_123", "name": "bash", "input": {"command": "ls"}}],
            "tool_result_id": None,
        }
        msg = ChatMessage.from_dict(data)
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "call_123"
        assert msg.tool_calls[0].name == "bash"

    def test_chat_message_round_trip(self) -> None:
        """Test ChatMessage can round-trip through dict."""
        original = ChatMessage(
            role="assistant",
            content="Let me help you",
            tool_calls=[ToolCall(id="call_1", name="view", input={"path": "file.txt"})],
        )
        round_trip = ChatMessage.from_dict(original.to_dict())
        assert round_trip.role == original.role
        assert round_trip.content == original.content
        assert len(round_trip.tool_calls) == len(original.tool_calls)
        assert round_trip.tool_calls[0].id == original.tool_calls[0].id


class TestSessionDataclass:
    """Test Session dataclass for session persistence."""

    def test_session_creation(self) -> None:
        """Test Session can be created with required fields."""
        session = Session(
            id="test-session",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 30, 0),
            working_directory="/home/user/project",
            messages=[],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={"max_tokens": 4096},
        )
        assert session.id == "test-session"
        assert session.working_directory == "/home/user/project"
        assert session.model == "claude-sonnet-4.5"

    def test_session_to_dict(self) -> None:
        """Test Session.to_dict() converts to dictionary."""
        msg = ChatMessage(role="user", content="Hello")
        session = Session(
            id="test-session",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 30, 0),
            working_directory="/home/user/project",
            messages=[msg],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={"max_tokens": 4096},
        )
        result = session.to_dict()
        assert result["id"] == "test-session"
        assert result["created_at"] == "2025-01-01T12:00:00"
        assert result["updated_at"] == "2025-01-01T12:30:00"
        assert result["working_directory"] == "/home/user/project"
        assert result["model"] == "claude-sonnet-4.5"
        assert result["agent_type"] == "general"
        assert result["config_snapshot"] == {"max_tokens": 4096}
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"

    def test_session_from_dict(self) -> None:
        """Test Session.from_dict() creates from dictionary."""
        data = {
            "id": "test-session",
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:30:00",
            "working_directory": "/home/user/project",
            "messages": [{"role": "user", "content": "Hello", "timestamp": "2025-01-01T12:00:00", "tool_calls": [], "tool_result_id": None}],
            "model": "claude-sonnet-4.5",
            "agent_type": "general",
            "config_snapshot": {"max_tokens": 4096},
        }
        session = Session.from_dict(data)
        assert session.id == "test-session"
        assert session.created_at == datetime(2025, 1, 1, 12, 0, 0)
        assert session.updated_at == datetime(2025, 1, 1, 12, 30, 0)
        assert session.working_directory == "/home/user/project"
        assert session.model == "claude-sonnet-4.5"
        assert session.agent_type == "general"
        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"

    def test_session_from_dict_handles_missing_config_snapshot(self) -> None:
        """Test Session.from_dict() handles missing config_snapshot."""
        data = {
            "id": "test-session",
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:30:00",
            "working_directory": "/home/user/project",
            "messages": [],
            "model": "claude-sonnet-4.5",
            "agent_type": "general",
        }
        session = Session.from_dict(data)
        assert session.config_snapshot == {}

    def test_session_round_trip(self) -> None:
        """Test Session can round-trip through dict."""
        msg1 = ChatMessage(role="user", content="Hello")
        msg2 = ChatMessage(
            role="assistant",
            content="Hi there",
            tool_calls=[ToolCall(id="call_1", name="bash", input={"command": "ls"})],
        )
        original = Session(
            id="test-session",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 30, 0),
            working_directory="/home/user/project",
            messages=[msg1, msg2],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={"max_tokens": 4096},
        )
        round_trip = Session.from_dict(original.to_dict())
        assert round_trip.id == original.id
        assert round_trip.working_directory == original.working_directory
        assert round_trip.model == original.model
        assert len(round_trip.messages) == len(original.messages)
        assert round_trip.messages[0].content == original.messages[0].content
        assert len(round_trip.messages[1].tool_calls) == 1


class TestSessionInfo:
    """Test SessionInfo dataclass for session metadata."""

    def test_session_info_creation(self) -> None:
        """Test SessionInfo can be created."""
        info = SessionInfo(
            id="test-session",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 30, 0),
            working_directory="/home/user/project",
            message_count=5,
            model="claude-sonnet-4.5",
            agent_type="general",
        )
        assert info.id == "test-session"
        assert info.message_count == 5
        assert info.working_directory == "/home/user/project"


class TestSessionManager:
    """Test SessionManager for session persistence."""

    @pytest.fixture
    def temp_session_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for sessions."""
        return tmp_path / "sessions"

    @pytest.fixture
    def session_manager(self, temp_session_dir: Path) -> SessionManager:
        """Create a SessionManager with temp directory."""
        return SessionManager(session_dir=temp_session_dir)

    @pytest.fixture
    def sample_session(self) -> Session:
        """Create a sample session for testing."""
        msg1 = ChatMessage(role="user", content="Hello")
        msg2 = ChatMessage(role="assistant", content="Hi there")
        return Session(
            id="test-session",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 30, 0),
            working_directory="/home/user/project",
            messages=[msg1, msg2],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={"max_tokens": 4096},
        )

    def test_session_manager_creates_directory(self, tmp_path: Path) -> None:
        """Test SessionManager creates sessions directory."""
        session_dir = tmp_path / "new_sessions"
        SessionManager(session_dir=session_dir)
        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_session_manager_default_directory(self) -> None:
        """Test SessionManager uses default directory when none provided."""
        sm = SessionManager()
        assert sm.session_dir == SessionManager.DEFAULT_SESSION_DIR

    @pytest.mark.asyncio
    async def test_save_session(self, session_manager: SessionManager, sample_session: Session) -> None:
        """Test save() writes session to file."""
        file_path = await session_manager.save(sample_session)
        assert file_path.exists()
        assert file_path.name == "test-session.json"

        # Verify content
        with open(file_path) as f:
            data = json.load(f)
        assert data["id"] == "test-session"
        assert data["model"] == "claude-sonnet-4.5"
        assert len(data["messages"]) == 2

    @pytest.mark.asyncio
    async def test_save_updates_timestamp(self, session_manager: SessionManager) -> None:
        """Test save() updates the updated_at timestamp."""
        session = Session(
            id="test",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            working_directory="/tmp",
            messages=[],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={},
        )
        original_updated = session.updated_at

        # Mock datetime.now() to return a different time
        with patch("goz.agent.sessions.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 1, 13, 0, 0)
            mock_datetime.fromisoformat = datetime.fromisoformat  # Keep real fromisoformat
            await session_manager.save(session)

        assert session.updated_at > original_updated

    @pytest.mark.asyncio
    async def test_load_session(self, session_manager: SessionManager, sample_session: Session) -> None:
        """Test load() reads session from file."""
        # First save
        await session_manager.save(sample_session)

        # Then load
        loaded = await session_manager.load("test-session")
        assert loaded.id == "test-session"
        assert loaded.working_directory == "/home/user/project"
        assert loaded.model == "claude-sonnet-4.5"
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"
        assert loaded.messages[1].content == "Hi there"

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, session_manager: SessionManager) -> None:
        """Test load() raises FileNotFoundError for non-existent session."""
        with pytest.raises(FileNotFoundError, match="Session not found: nonexistent"):
            await session_manager.load("nonexistent")

    @pytest.mark.asyncio
    async def test_load_corrupted_session(self, session_manager: SessionManager, temp_session_dir: Path) -> None:
        """Test load() raises ValueError for corrupted file."""
        # Create a corrupted file
        bad_file = temp_session_dir / "corrupted.json"
        bad_file.write_text("{invalid json content")

        with pytest.raises(ValueError, match="Corrupted session file"):
            await session_manager.load("corrupted")

    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager: SessionManager, sample_session: Session) -> None:
        """Test delete() removes session file."""
        await session_manager.save(sample_session)
        assert (session_manager.session_dir / "test-session.json").exists()

        result = await session_manager.delete("test-session")
        assert result is True
        assert not (session_manager.session_dir / "test-session.json").exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, session_manager: SessionManager) -> None:
        """Test delete() returns False for non-existent session."""
        result = await session_manager.delete("nonexistent")
        assert result is False

    def test_exists_true(self, session_manager: SessionManager, sample_session: Session) -> None:
        """Test exists() returns True when session exists."""
        import asyncio
        asyncio.run(session_manager.save(sample_session))
        assert session_manager.exists("test-session") is True

    def test_exists_false(self, session_manager: SessionManager) -> None:
        """Test exists() returns False when session doesn't exist."""
        assert session_manager.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_get_info(self, session_manager: SessionManager, sample_session: Session) -> None:
        """Test get_info() returns session metadata."""
        await session_manager.save(sample_session)

        info = await session_manager.get_info("test-session")
        assert info is not None
        assert info.id == "test-session"
        assert info.working_directory == "/home/user/project"
        assert info.message_count == 2
        assert info.model == "claude-sonnet-4.5"
        assert info.agent_type == "general"

    @pytest.mark.asyncio
    async def test_get_info_nonexistent(self, session_manager: SessionManager) -> None:
        """Test get_info() returns None for non-existent session."""
        info = await session_manager.get_info("nonexistent")
        assert info is None

    def test_list_sessions_empty(self, session_manager: SessionManager) -> None:
        """Test list_sessions() returns empty list when no sessions."""
        sessions = session_manager.list_sessions()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_manager: SessionManager, sample_session: Session) -> None:
        """Test list_sessions() returns all sessions."""
        # Save multiple sessions
        await session_manager.save(sample_session)

        session2 = Session(
            id="another-session",
            created_at=datetime(2025, 1, 2, 10, 0, 0),
            updated_at=datetime(2025, 1, 2, 11, 0, 0),
            working_directory="/home/user/other",
            messages=[ChatMessage(role="user", content="Test")],
            model="claude-opus-4.5",
            agent_type="code",
            config_snapshot={},
        )
        await session_manager.save(session2)

        sessions = session_manager.list_sessions()
        assert len(sessions) == 2
        session_ids = {s.id for s in sessions}
        assert "test-session" in session_ids
        assert "another-session" in session_ids

    def test_list_sessions_sorted_by_updated(self, session_manager: SessionManager) -> None:
        """Test list_sessions() sorts by updated_at, newest first."""
        import asyncio

        # Create sessions with different update times
        session1 = Session(
            id="old-session",
            created_at=datetime(2025, 1, 1, 10, 0, 0),
            updated_at=datetime(2025, 1, 1, 10, 0, 0),
            working_directory="/tmp",
            messages=[],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={},
        )
        session2 = Session(
            id="new-session",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            working_directory="/tmp",
            messages=[],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={},
        )
        asyncio.run(session_manager.save(session1))
        asyncio.run(session_manager.save(session2))

        sessions = session_manager.list_sessions()
        # Newest first
        assert sessions[0].id == "new-session"
        assert sessions[1].id == "old-session"

    def test_list_sessions_skips_corrupted(self, session_manager: SessionManager, temp_session_dir: Path) -> None:
        """Test list_sessions() skips corrupted files."""
        import asyncio

        # Save a valid session
        valid = Session(
            id="valid",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            updated_at=datetime(2025, 1, 1, 12, 0, 0),
            working_directory="/tmp",
            messages=[],
            model="claude-sonnet-4.5",
            agent_type="general",
            config_snapshot={},
        )
        asyncio.run(session_manager.save(valid))

        # Create a corrupted file
        (temp_session_dir / "corrupted.json").write_text("not json")

        sessions = session_manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].id == "valid"


class TestSessionRoundTrip:
    """Integration tests for full save/load cycle."""

    @pytest.fixture
    def temp_session_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for sessions."""
        return tmp_path / "sessions"

    @pytest.fixture
    def session_manager(self, temp_session_dir: Path) -> SessionManager:
        """Create a SessionManager with temp directory."""
        return SessionManager(session_dir=temp_session_dir)

    @pytest.mark.asyncio
    async def test_full_round_trip(self, session_manager: SessionManager) -> None:
        """Test session can be saved and loaded with all data intact."""
        # Create complex session
        tc = ToolCall(id="call_123", name="bash", input={"command": "ls -la"})
        messages = [
            ChatMessage(role="user", content="List files"),
            ChatMessage(
                role="assistant",
                content="I'll list the files",
                tool_calls=[tc],
            ),
            ChatMessage(
                role="tool",
                content="file1.txt\nfile2.py",
                tool_result_id="call_123",
            ),
        ]

        original = Session(
            id="complex-session",
            created_at=datetime(2025, 1, 1, 10, 0, 0),
            updated_at=datetime(2025, 1, 1, 10, 30, 0),
            working_directory="/home/user/project",
            messages=messages,
            model="claude-sonnet-4.5",
            agent_type="code",
            config_snapshot={"max_tokens": 8192, "temperature": 0.7},
        )

        # Save and load
        await session_manager.save(original)
        loaded = await session_manager.load("complex-session")

        # Verify all fields
        assert loaded.id == original.id
        assert loaded.working_directory == original.working_directory
        assert loaded.model == original.model
        assert loaded.agent_type == original.agent_type
        assert loaded.config_snapshot == original.config_snapshot
        assert len(loaded.messages) == len(original.messages)

        # Verify message details
        assert loaded.messages[0].content == "List files"
        assert loaded.messages[1].content == "I'll list the files"
        assert len(loaded.messages[1].tool_calls) == 1
        assert loaded.messages[1].tool_calls[0].id == "call_123"
        assert loaded.messages[1].tool_calls[0].name == "bash"
        assert loaded.messages[1].tool_calls[0].input == {"command": "ls -la"}
        assert loaded.messages[2].tool_result_id == "call_123"
