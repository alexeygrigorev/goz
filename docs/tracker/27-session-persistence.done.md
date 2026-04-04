# Issue 27: Session Save/Load

## Status
.done

## Description
Implement session persistence for saving and loading chat conversations.

## User Scenarios

### Scenario 1: Save Session
- User has been chatting for a while
- User types: `/save my-project`
- Session is saved to ~/.goz/sessions/my-project.json
- Confirmation message shown: "Session saved: my-project"
- File contains: messages, working directory, model, timestamp

### Scenario 2: Load Session
- User runs: `goz --load my-project`
- Session file is read
- Chat history is restored
- Working directory is restored
- User sees their previous conversation
- Can continue from where they left off

### Scenario 3: List Sessions
- User types: `/sessions` or `/ls`
- All saved sessions are listed
- Each shows: name, created time, message count, working directory
- User can see which session to load

### Scenario 4: Delete Session
- User types: `/delete old-session`
- Confirmation dialog shown
- User confirms
- Session file is deleted
- Confirmation message shown

### Scenario 5: Auto-Save
- User is chatting
- Every 10 messages, session auto-saves to "default"
- If user quits without saving, can recover with `/load default`
- User notified of auto-save

### Scenario 6: Session Info
- User types: `/session`
- Current session info shown
- Shows: message count, current agent, working directory, duration
- Shows if unsaved changes exist

## Acceptance Criteria

### SessionManager
1. `SessionManager` class exists in `goz/agent/sessions.py`
2. `save()` method saves session to file
3. `load()` method loads session from file
4. `list_sessions()` returns all sessions
5. `delete()` method deletes session
6. `exists()` checks if session exists
7. `get_info()` returns session metadata

### Session Data Structure
8. `Session` dataclass has: id, created_at, working_dir, messages, model, agent_type
9. Session includes all chat messages
10. Session includes working directory
11. Session includes timestamp
12. Session includes model used
13. Session includes agent type

### File Format
14. Sessions saved as JSON
15. File location: ~/.goz/sessions/
16. File naming: {session_id}.json
17. Messages are serializable
18. Tool calls are serializable
19. Can round-trip (save & load) correctly

### Commands
20. `/save <name>` saves session
21. `/load <name>` loads session
22. `/sessions` lists sessions
23. `/delete <name>` deletes session
24. `/session` shows current info
25. `goz --load <name>` CLI flag works

### Auto-Save
26. Session auto-saves every N messages
27. Auto-save goes to "default" session
28. User can disable auto-save
29. User notified on auto-save

### Error Handling
30. Loading non-existent session shows error
31. Corrupted session file shows helpful error
32. Permission errors handled gracefully

## Technical Details

### File Structure
```
goz/agent/
└── sessions.py    # Session, SessionManager

~/.goz/
└── sessions/
    ├── default.json
    ├── my-project.json
    └── ...
```

### Session Data Structure
```python
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal

@dataclass
class Session:
    """A saved chat session."""

    id: str  # Session identifier (filename)
    created_at: datetime
    updated_at: datetime
    working_directory: str
    messages: list[ChatMessage]
    model: str
    agent_type: str
    config_snapshot: dict  # Config settings at time of save

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "working_directory": self.working_directory,
            "messages": [msg.to_dict() for msg in self.messages],
            "model": self.model,
            "agent_type": self.agent_type,
            "config_snapshot": self.config_snapshot,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create from dict (JSON loaded)."""
        return cls(
            id=data["id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            working_directory=data["working_directory"],
            messages=[ChatMessage.from_dict(m) for m in data["messages"]],
            model=data["model"],
            agent_type=data["agent_type"],
            config_snapshot=data.get("config_snapshot", {}),
        )
```

### ChatMessage Serialization
```python
@dataclass
class ChatMessage:
    """Chat message with serialization support."""

    role: Literal["user", "assistant", "tool", "tool_call", "agent_activity"]
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dict."""
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_result_id": self.tool_result_id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        """Create from dict."""
        return cls(
            role=data["role"],
            content=data["content"],
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            tool_result_id=data.get("tool_result_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
```

### SessionManager
```python
from pathlib import Path
import json
import os

class SessionManager:
    """Manage session persistence."""

    DEFAULT_SESSION_DIR = Path.home() / ".goz" / "sessions"

    def __init__(self, session_dir: Path | None = None):
        self.session_dir = session_dir or self.DEFAULT_SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, session: Session) -> Path:
        """Save session to file.

        Args:
            session: Session to save

        Returns:
            Path to saved file
        """
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
            raise ValueError(f"Corrupted session file: {e}")

    def list_sessions(self) -> list[SessionInfo]:
        """List all saved sessions.

        Returns:
            List of session metadata
        """
        sessions = []

        for file_path in self.session_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                sessions.append(SessionInfo(
                    id=data["id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    working_directory=data["working_directory"],
                    message_count=len(data["messages"]),
                    model=data["model"],
                    agent_type=data.get("agent_type", "general"),
                ))
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
        """Check if session exists."""
        return (self.session_dir / f"{session_id}.json").exists()

    async def get_info(self, session_id: str) -> SessionInfo | None:
        """Get session metadata without loading full session."""
        file_path = self.session_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

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
```

### SessionInfo
```python
@dataclass
class SessionInfo:
    """Metadata about a session (lightweight)."""

    id: str
    created_at: datetime
    updated_at: datetime
    working_directory: str
    message_count: int
    model: str
    agent_type: str
```

### AgentApp Integration
```python
class AgentApp(App[None]):
    """Agent app with session support."""

    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.session_id = None
        self.auto_save_interval = 10  # messages
        self.message_count = 0

    async def save_session(self, session_id: str) -> None:
        """Save current session."""
        session = Session(
            id=session_id,
            created_at=datetime.now(),  # Or from existing
            updated_at=datetime.now(),
            working_directory=os.getcwd(),
            messages=self.agent.history.messages,
            model=self.config.chat_model,
            agent_type=self.current_agent_type.value,
            config_snapshot=self.config.model_dump(),
        )

        await self.session_manager.save(session)
        self.session_id = session_id

    async def load_session(self, session_id: str) -> None:
        """Load a session."""
        session = await self.session_manager.load(session_id)

        # Restore chat history
        self.agent.history.messages = session.messages

        # Restore agent type
        self.set_agent_type(session.agent_type)

        # Change to working directory
        os.chdir(session.working_directory)

        self.session_id = session.id
        self.message_count = len(session.messages)

    def check_auto_save(self) -> None:
        """Check if we should auto-save."""
        if self.message_count % self.auto_save_interval == 0:
            asyncio.create_task(self.save_session("default"))
```

### Command Integration
```python
# In ChatScreen

async def handle_slash_command(self, command: str) -> None:
    """Handle slash commands."""
    parts = command.split()
    cmd = parts[0]

    if cmd == "/save":
        name = parts[1] if len(parts) > 1 else "default"
        await self.app.save_session(name)
        self.notify(f"Session saved: {name}")

    elif cmd == "/load":
        name = parts[1] if len(parts) > 1 else None
        if not name:
            # Show session list
            await self.show_session_list()
        else:
            await self.app.load_session(name)
            self.notify(f"Session loaded: {name}")

    elif cmd in ("/sessions", "/ls"):
        await self.show_session_list()

    elif cmd == "/delete":
        name = parts[1] if len(parts) > 1 else None
        if name:
            await self.delete_session(name)

    elif cmd == "/session":
        await self.show_session_info()
```

### Session List Screen
```python
class SessionListScreen(Screen):
    """Screen for listing and selecting sessions."""

    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session_manager = session_manager

    async def on_mount(self) -> None:
        """Load sessions on mount."""
        self.sessions = await self.session_manager.list_sessions()
        self.update_content()

    def update_content(self) -> None:
        """Update session list display."""
        content = Text()
        content.append("Saved Sessions\n", style="bold")
        content.append("━" * 50, style="dim")
        content.append("\n\n")

        for s in self.sessions:
            content.append(f"{s.id}\n", style="cyan")
            content.append(f"  Updated: {s.updated_at.strftime('%Y-%m-%d %H:%M')}\n", style="dim")
            content.append(f"  Messages: {s.message_count}\n", style="dim")
            content.append(f"  Directory: {s.working_directory}\n", style="dim")
            content.append("\n")

        self.query_one(Static).update(content)
```

## Dependencies
- Issue 15: Agent Core + Chat History
- Issue 26: TUI-Agent Integration

## Related Issues
- Issue 28: Session Commands

## Log
- 2025-03-19: Implemented Session persistence with TDD approach.
  - Created `goz/agent/sessions.py` with Session, SessionInfo, and SessionManager classes.
  - Session dataclass with: id, created_at, updated_at, working_dir, messages, model, agent_type, config_snapshot.
  - SessionManager with: save(), load(), list_sessions(), delete(), exists(), get_info().
  - JSON serialization/deserialization (to_dict/from_dict methods) for Session.
  - Session directory: ~/.goz/sessions/
  - Handles ChatMessage serialization (already implemented in history.py).
  - Handles ToolCall serialization (already implemented in history.py).
  - Error handling for non-existent sessions, corrupted files.
  - Added @pytest.mark.asyncio decorator to async tests.
  - All 33 tests pass.
