"""Session persistence for the goz agent.

This module provides classes for saving and loading chat sessions:
- Session: Dataclass for a saved chat session
- SessionInfo: Lightweight metadata about a session
- SessionManager: Manages session files (save, load, list, delete)

Acceptance Criteria:
- AC 1: SessionManager class exists in goz/agent/sessions.py
- AC 2: save() method saves session to file
- AC 3: load() method loads session from file
- AC 4: list_sessions() returns all sessions
- AC 5: delete() method deletes session
- AC 6: exists() checks if session exists
- AC 7: get_info() returns session metadata
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from goz.agent.history import ChatMessage


@dataclass
class Session:
    """A saved chat session.

    Attributes:
        id: Session identifier (filename without .json)
        created_at: When the session was first created
        updated_at: When the session was last modified
        working_directory: Working directory at time of save
        messages: List of chat messages in the session
        model: Model name used for the session
        agent_type: Type of agent used (e.g., "general", "coder")
        config_snapshot: Config settings at time of save
    """

    id: str
    created_at: datetime
    updated_at: datetime
    working_directory: str
    messages: list[ChatMessage]
    model: str
    agent_type: str
    config_snapshot: dict
    tool_state: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert Session to dict for JSON serialization.

        Returns:
            Dict representation of this Session
        """
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "working_directory": self.working_directory,
            "messages": [msg.to_dict() for msg in self.messages],
            "model": self.model,
            "agent_type": self.agent_type,
            "config_snapshot": self.config_snapshot,
            "tool_state": self.tool_state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create Session from dict.

        Args:
            data: Dict representation of Session

        Returns:
            Session instance
        """
        return cls(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            working_directory=data["working_directory"],
            messages=[ChatMessage.from_dict(m) for m in data["messages"]],
            model=data["model"],
            agent_type=data["agent_type"],
            config_snapshot=data.get("config_snapshot", {}),
            tool_state=data.get("tool_state", {}),
        )


@dataclass
class SessionInfo:
    """Metadata about a session (lightweight).

    Attributes:
        id: Session identifier
        created_at: When the session was first created
        updated_at: When the session was last modified
        working_directory: Working directory at time of save
        message_count: Number of messages in the session
        model: Model name used for the session
        agent_type: Type of agent used
    """

    id: str
    created_at: datetime
    updated_at: datetime
    working_directory: str
    message_count: int
    model: str
    agent_type: str


class SessionManager:
    """Manage session persistence.

    This class handles saving, loading, listing, and deleting chat sessions.
    Sessions are stored as JSON files in the session directory.

    Attributes:
        session_dir: Directory where session files are stored
    """

    DEFAULT_SESSION_DIR = Path.home() / ".goz" / "sessions"

    def __init__(self, session_dir: Path | None = None) -> None:
        """Initialize SessionManager.

        Args:
            session_dir: Directory for session files (default: ~/.goz/sessions)
        """
        self.session_dir = session_dir or self.DEFAULT_SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, session: Session) -> Path:
        """Save session to file.

        Args:
            session: Session to save

        Returns:
            Path to saved file
        """
        # Update the timestamp
        session.updated_at = datetime.now()

        file_path = self.session_dir / f"{session.id}.json"

        with open(file_path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        return file_path

    async def load(self, session_id: str) -> Session:
        """Load session from file.

        Args:
            session_id: Session identifier (without .json)

        Returns:
            Loaded Session

        Raises:
            FileNotFoundError: If session doesn't exist
            ValueError: If file is corrupted
        """
        file_path = self.session_dir / f"{session_id}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        try:
            with open(file_path) as f:
                data = json.load(f)
            return Session.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted session file: {e}") from e

    def list_sessions(self) -> list[SessionInfo]:
        """List all saved sessions.

        Returns:
            List of session metadata, sorted by updated_at (newest first)
        """
        sessions: list[SessionInfo] = []

        for file_path in self.session_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                sessions.append(
                    SessionInfo(
                        id=data["id"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        updated_at=datetime.fromisoformat(data["updated_at"]),
                        working_directory=data["working_directory"],
                        message_count=len(data["messages"]),
                        model=data["model"],
                        agent_type=data.get("agent_type", "general"),
                    )
                )
            except (json.JSONDecodeError, KeyError):
                # Skip corrupted files
                continue

        # Sort by updated_at, newest first
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = self.session_dir / f"{session_id}.json"

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Session identifier to check

        Returns:
            True if session exists, False otherwise
        """
        return (self.session_dir / f"{session_id}.json").exists()

    async def get_info(self, session_id: str) -> SessionInfo | None:
        """Get session metadata without loading full session.

        Args:
            session_id: Session identifier

        Returns:
            SessionInfo if session exists, None otherwise
        """
        file_path = self.session_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)

            return SessionInfo(
                id=data["id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                working_directory=data["working_directory"],
                message_count=len(data["messages"]),
                model=data["model"],
                agent_type=data.get("agent_type", "general"),
            )
        except (json.JSONDecodeError, KeyError):
            return None
