"""Unit tests for Session Persistence (Issue 27).

Tests cover:
- Session dataclass with serialization
- SessionManager class for save/load/list/delete
- ChatMessage and ToolCall serialization
- SessionInfo metadata
- File format and error handling
"""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from goz.agent.history import ChatMessage, ToolCall


class TestSessionDataclass:
    """Unit Tests: Session dataclass."""

    def test_session_can_be_imported(self):
        """Test Session class can be imported."""
        from goz.agent.sessions import Session  # noqa: F401
        assert Session is not None

    def test_session_has_required_fields(self):
        """Test Session has all required fields."""
        from goz.agent.sessions import Session

        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test/dir",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        assert session.id == "test-session"
        assert session.working_directory == "/test/dir"
        assert session.messages == []
        assert session.model == "claude-3"
        assert session.agent_type == "general"

    def test_session_to_dict(self):
        """Test Session.to_dict() produces correct format."""
        from goz.agent.sessions import Session

        now = datetime.now()
        session = Session(
            id="test-session",
            created_at=now,
            updated_at=now,
            working_directory="/test/dir",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={"key": "value"},
        )

        data = session.to_dict()

        assert data["id"] == "test-session"
        assert data["working_directory"] == "/test/dir"
        assert data["messages"] == []
        assert data["model"] == "claude-3"
        assert data["agent_type"] == "general"
        assert data["config_snapshot"] == {"key": "value"}
        assert "created_at" in data
        assert "updated_at" in data

    def test_session_from_dict(self):
        """Test Session.from_dict() creates Session correctly."""
        from goz.agent.sessions import Session

        now = datetime.now()
        data = {
            "id": "test-session",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "working_directory": "/test/dir",
            "messages": [],
            "model": "claude-3",
            "agent_type": "general",
            "config_snapshot": {},
        }

        session = Session.from_dict(data)

        assert session.id == "test-session"
        assert session.working_directory == "/test/dir"
        assert session.messages == []
        assert session.model == "claude-3"
        assert session.agent_type == "general"

    def test_session_roundtrip(self):
        """Test Session can roundtrip through dict."""
        from goz.agent.sessions import Session

        msg = ChatMessage(role="user", content="Hello")
        original = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test/dir",
            messages=[msg],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = Session.from_dict(data)

        assert restored.id == original.id
        assert restored.working_directory == original.working_directory
        assert len(restored.messages) == 1
        assert restored.messages[0].role == "user"
        assert restored.messages[0].content == "Hello"


class TestSessionInfo:
    """Unit Tests: SessionInfo dataclass."""

    def test_session_info_can_be_imported(self):
        """Test SessionInfo class can be imported."""
        from goz.agent.sessions import SessionInfo  # noqa: F401
        assert SessionInfo is not None

    def test_session_info_has_required_fields(self):
        """Test SessionInfo has all required fields."""
        from goz.agent.sessions import SessionInfo

        now = datetime.now()
        info = SessionInfo(
            id="test-session",
            created_at=now,
            updated_at=now,
            working_directory="/test/dir",
            message_count=5,
            model="claude-3",
            agent_type="general",
        )

        assert info.id == "test-session"
        assert info.message_count == 5
        assert info.model == "claude-3"
        assert info.agent_type == "general"


class TestChatMessageSerialization:
    """Unit Tests: ChatMessage serialization for sessions."""

    def test_chat_message_to_dict(self):
        """Test ChatMessage.to_dict() produces correct format."""
        msg = ChatMessage(role="user", content="Hello")

        data = msg.to_dict()

        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert "timestamp" in data

    def test_chat_message_from_dict(self):
        """Test ChatMessage.from_dict() creates message correctly."""
        now = datetime.now()
        data = {
            "role": "user",
            "content": "Hello",
            "timestamp": now.isoformat(),
            "tool_calls": [],
            "tool_result_id": None,
        }

        msg = ChatMessage.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_message_roundtrip(self):
        """Test ChatMessage can roundtrip through dict."""
        original = ChatMessage(role="user", content="Hello")

        data = original.to_dict()
        restored = ChatMessage.from_dict(data)

        assert restored.role == original.role
        assert restored.content == original.content

    def test_chat_message_with_tool_calls(self):
        """Test ChatMessage serializes tool calls."""
        tc = ToolCall(id="call-1", name="bash", input={"command": "ls"})
        msg = ChatMessage(role="assistant", content="Thinking...", tool_calls=[tc])

        data = msg.to_dict()

        assert "tool_calls" in data
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["id"] == "call-1"
        assert data["tool_calls"][0]["name"] == "bash"

    def test_chat_message_from_dict_with_tool_calls(self):
        """Test ChatMessage.from_dict() handles tool calls."""
        now = datetime.now()
        data = {
            "role": "assistant",
            "content": "Thinking...",
            "timestamp": now.isoformat(),
            "tool_calls": [
                {"id": "call-1", "name": "bash", "input": {"command": "ls"}}
            ],
            "tool_result_id": None,
        }

        msg = ChatMessage.from_dict(data)

        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "call-1"
        assert msg.tool_calls[0].name == "bash"


class TestToolCallSerialization:
    """Unit Tests: ToolCall serialization for sessions."""

    def test_tool_call_to_dict(self):
        """Test ToolCall.to_dict() produces correct format."""
        tc = ToolCall(id="call-1", name="bash", input={"command": "ls"})

        data = tc.to_dict()

        assert data["id"] == "call-1"
        assert data["name"] == "bash"
        assert data["input"] == {"command": "ls"}

    def test_tool_call_from_dict(self):
        """Test ToolCall.from_dict() creates ToolCall correctly."""
        data = {"id": "call-1", "name": "bash", "input": {"command": "ls"}}

        tc = ToolCall.from_dict(data)

        assert tc.id == "call-1"
        assert tc.name == "bash"
        assert tc.input == {"command": "ls"}


class TestSessionManager:
    """Unit Tests: SessionManager class."""

    def test_session_manager_can_be_imported(self):
        """Test SessionManager class can be imported."""
        from goz.agent.sessions import SessionManager  # noqa: F401
        assert SessionManager is not None

    def test_session_manager_has_default_session_dir(self):
        """Test SessionManager has default session directory."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager()

        assert sm.session_dir is not None
        assert "goz" in str(sm.session_dir)
        assert "sessions" in str(sm.session_dir)

    def test_session_manager_creates_session_dir(self, tmp_path):
        """Test SessionManager creates session directory."""
        from goz.agent.sessions import SessionManager

        session_dir = tmp_path / "sessions"
        sm = SessionManager(session_dir=session_dir)

        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_session_manager_save_method_exists(self, tmp_path):
        """Test SessionManager has save method."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        assert hasattr(sm, "save")
        assert callable(sm.save)

    def test_session_manager_load_method_exists(self, tmp_path):
        """Test SessionManager has load method."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        assert hasattr(sm, "load")
        assert callable(sm.load)

    def test_session_manager_list_sessions_method_exists(self, tmp_path):
        """Test SessionManager has list_sessions method."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        assert hasattr(sm, "list_sessions")
        assert callable(sm.list_sessions)

    def test_session_manager_delete_method_exists(self, tmp_path):
        """Test SessionManager has delete method."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        assert hasattr(sm, "delete")
        assert callable(sm.delete)

    def test_session_manager_exists_method_exists(self, tmp_path):
        """Test SessionManager has exists method."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        assert hasattr(sm, "exists")
        assert callable(sm.exists)

    def test_session_manager_get_info_method_exists(self, tmp_path):
        """Test SessionManager has get_info method."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        assert hasattr(sm, "get_info")
        assert callable(sm.get_info)


class TestSessionManagerSave:
    """Integration Tests: SessionManager.save()."""

    @pytest.mark.asyncio
    async def test_save_creates_json_file(self, tmp_path):
        """Test save() creates a JSON file."""
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        await sm.save(session)

        file_path = tmp_path / "test-session.json"
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_save_creates_valid_json(self, tmp_path):
        """Test save() creates valid JSON."""
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        await sm.save(session)

        file_path = tmp_path / "test-session.json"
        with open(file_path) as f:
            data = json.load(f)

        assert data["id"] == "test-session"

    @pytest.mark.asyncio
    async def test_save_includes_messages(self, tmp_path):
        """Test save() includes messages in JSON."""
        from goz.agent.history import ChatMessage
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)
        msg = ChatMessage(role="user", content="Hello")
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[msg],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        await sm.save(session)

        file_path = tmp_path / "test-session.json"
        with open(file_path) as f:
            data = json.load(f)

        assert len(data["messages"]) == 1
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_save_returns_file_path(self, tmp_path):
        """Test save() returns the file path."""
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        result = await sm.save(session)

        assert result == tmp_path / "test-session.json"


class TestSessionManagerLoad:
    """Integration Tests: SessionManager.load()."""

    @pytest.mark.asyncio
    async def test_load_existing_session(self, tmp_path):
        """Test load() loads existing session."""
        from goz.agent.history import ChatMessage
        from goz.agent.sessions import Session, SessionManager

        # First save a session
        sm = SessionManager(session_dir=tmp_path)
        msg = ChatMessage(role="user", content="Hello")
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[msg],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )
        await sm.save(session)

        # Then load it
        loaded = await sm.load("test-session")

        assert loaded.id == "test-session"
        assert loaded.working_directory == "/test"
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_load_nonexistent_session_raises_error(self, tmp_path):
        """Test load() raises FileNotFoundError for non-existent session."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        with pytest.raises(FileNotFoundError):
            await sm.load("nonexistent")


class TestSessionManagerList:
    """Integration Tests: SessionManager.list_sessions()."""

    @pytest.mark.asyncio
    async def test_list_sessions_returns_empty_initially(self, tmp_path):
        """Test list_sessions() returns empty list when no sessions."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        sessions = sm.list_sessions()

        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_sessions_returns_all_sessions(self, tmp_path):
        """Test list_sessions() returns all saved sessions."""
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)

        # Create two sessions
        session1 = Session(
            id="session1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test1",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )
        session2 = Session(
            id="session2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test2",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        await sm.save(session1)
        await sm.save(session2)

        sessions = sm.list_sessions()

        assert len(sessions) == 2
        session_ids = {s.id for s in sessions}
        assert "session1" in session_ids
        assert "session2" in session_ids

    @pytest.mark.asyncio
    async def test_list_sessions_sorted_by_updated_at(self, tmp_path):
        """Test list_sessions() sorts by updated_at, newest first."""
        from goz.agent.sessions import Session, SessionManager
        from datetime import timedelta

        sm = SessionManager(session_dir=tmp_path)

        # Create sessions with different timestamps
        now = datetime.now()
        session1 = Session(
            id="session1",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
            working_directory="/test1",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )
        session2 = Session(
            id="session2",
            created_at=now,
            updated_at=now,
            working_directory="/test2",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )

        await sm.save(session1)
        await sm.save(session2)

        sessions = sm.list_sessions()

        # Newest first
        assert sessions[0].id == "session2"
        assert sessions[1].id == "session1"


class TestSessionManagerDelete:
    """Integration Tests: SessionManager.delete()."""

    @pytest.mark.asyncio
    async def test_delete_existing_session(self, tmp_path):
        """Test delete() deletes existing session."""
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )
        await sm.save(session)

        result = await sm.delete("test-session")

        assert result is True
        assert not (tmp_path / "test-session.json").exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, tmp_path):
        """Test delete() returns False for non-existent session."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        result = await sm.delete("nonexistent")

        assert result is False


class TestSessionManagerExists:
    """Integration Tests: SessionManager.exists()."""

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing(self, tmp_path):
        """Test exists() returns True for existing session."""
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )
        await sm.save(session)

        assert sm.exists("test-session") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_nonexistent(self, tmp_path):
        """Test exists() returns False for non-existent session."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        assert sm.exists("nonexistent") is False


class TestSessionManagerGetInfo:
    """Integration Tests: SessionManager.get_info()."""

    @pytest.mark.asyncio
    async def test_get_info_returns_session_info(self, tmp_path):
        """Test get_info() returns SessionInfo for existing session."""
        from goz.agent.history import ChatMessage
        from goz.agent.sessions import Session, SessionManager

        sm = SessionManager(session_dir=tmp_path)
        msg = ChatMessage(role="user", content="Hello")
        session = Session(
            id="test-session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            working_directory="/test",
            messages=[msg, msg],
            model="claude-3",
            agent_type="general",
            config_snapshot={},
        )
        await sm.save(session)

        info = await sm.get_info("test-session")

        assert info is not None
        assert info.id == "test-session"
        assert info.message_count == 2
        assert info.model == "claude-3"
        assert info.agent_type == "general"

    @pytest.mark.asyncio
    async def test_get_info_returns_none_for_nonexistent(self, tmp_path):
        """Test get_info() returns None for non-existent session."""
        from goz.agent.sessions import SessionManager

        sm = SessionManager(session_dir=tmp_path)

        info = await sm.get_info("nonexistent")

        assert info is None
