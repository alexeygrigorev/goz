# Issue 28: Session Commands

## Status
.todo

## Description
Implement all session-related slash commands: /save, /load, /sessions, /delete, /session.

## User Scenarios

### Scenario 1: /save Command
- User types: `/save`
- System saves to "default" session
- Confirmation shown
- User types: `/save my-work`
- System saves to "my-work" session
- Confirmation shown with path

### Scenario 2: /load Command
- User types: `/load`
- Session list screen appears
- User selects session with arrow keys
- User presses Enter
- Session is loaded
- User returns to chat with restored history

### Scenario 3: /load with Name
- User types: `/load my-work`
- Session is loaded immediately
- No list shown
- Confirmation appears

### Scenario 4: /sessions Command
- User types: `/sessions`
- Session list screen appears
- All sessions shown with metadata
- User can browse but must Esc to return

### Scenario 5: /delete Command
- User types: `/delete old-session`
- Confirmation dialog: "Delete old-session?"
- User confirms
- Session is deleted
- Confirmation shown

### Scenario 6: /session Command
- User types: `/session`
- Session info overlay appears
- Shows: current session name, message count, duration, working directory, agent type
- User presses Esc to close

### Scenario 7: Invalid Session Name
- User types: `/load nonexistent`
- Error message: "Session not found: nonexistent"
- User stays in chat
- No crash

## Acceptance Criteria

### /save Command
1. `/save` saves to "default" session
2. `/save <name>` saves to named session
3. Overwrites existing session with same name
4. Shows confirmation message
5. Creates sessions directory if needed
6. Shows success message with file path

### /load Command
7. `/load` with no name shows session list
8. `/load <name>` loads specific session
9. Restores all messages
10. Restores working directory
11. Restores agent type
12. Shows confirmation message
13. Shows error if session not found

### /sessions Command
14. `/sessions` shows session list screen
15. Each session shows: name, updated time, message count
16. Sessions sorted by recency
17. Press Esc or q to close
18. Press Enter on session to load it

### /delete Command
19. `/delete <name>` shows confirmation
20. Confirmation shows session name
21. User can cancel (Esc/n)
22. User can confirm (Enter/y)
23. Session file is deleted on confirm
24. Shows confirmation message

### /session Command
25. `/session` shows current session info
26. Shows: session name (or "unsaved")
27. Shows: message count
28. Shows: current agent type
29. Shows: working directory
30. Shows: duration (if loaded from save)
31. Press any key to close

### Session List Screen
32. SessionListScreen shows all sessions
33. Supports keyboard navigation
34. Shows session metadata
35. Visual indication of selected session
36. Enter to load, Esc to close

### Error Handling
37. Loading non-existent session shows error
38. Deleting non-existent session shows error
39. Permission errors handled gracefully
40. Corrupted session files skipped in list

## Technical Details

### File Structure
```
goz/agent/tui/screens/
└── session.py    # SessionListScreen, SessionInfoScreen

goz/agent/tui/widgets/
└── session.py    # SessionList, SessionInfo
```

### Command Handler
```python
# In ChatScreen

async def handle_slash_command(self, command: str) -> None:
    """Handle slash commands."""
    parts = command.split()
    cmd = parts[0]
    args = parts[1:]

    if cmd == "/save":
        await self.cmd_save(args)

    elif cmd == "/load":
        await self.cmd_load(args)

    elif cmd in ("/sessions", "/ls"):
        await self.cmd_sessions()

    elif cmd == "/delete":
        await self.cmd_delete(args)

    elif cmd == "/session":
        await self.cmd_session()
```

### /save Command
```python
async def cmd_save(self, args: list[str]) -> None:
    """Handle /save command."""
    session_id = args[0] if args else "default"

    try:
        await self.app.save_session(session_id)
        self.notify(
            f"Session saved: {session_id}",
            title="Session Saved",
        )

        # Add system message to chat
        history = self.query_one(ChatHistoryViewer)
        history.add_system_message(
            f"💾 Session saved to: {self.app.session_manager.session_dir / session_id}.json"
        )

    except Exception as e:
        self.notify(
            f"Failed to save session: {e}",
            severity="error",
            title="Save Failed",
        )
```

### /load Command
```python
async def cmd_load(self, args: list[str]) -> None:
    """Handle /load command."""
    if not args:
        # Show session list
        self.push_screen(SessionListScreen(
            session_manager=self.app.session_manager,
            on_load=self.app.load_session,
        ))
        return

    session_id = args[0]

    try:
        await self.app.load_session(session_id)
        self.notify(f"Session loaded: {session_id}")

        # Add system message
        history = self.query_one(ChatHistoryViewer)
        history.add_system_message(
            f"📂 Session loaded: {session_id}\n"
            f"Messages restored: {len(self.app.agent.history.messages)}"
        )

    except FileNotFoundError:
        self.notify(
            f"Session not found: {session_id}",
            severity="error",
        )
    except Exception as e:
        self.notify(
            f"Failed to load session: {e}",
            severity="error",
        )
```

### /sessions Command
```python
async def cmd_sessions(self) -> None:
    """Handle /sessions command."""
    self.push_screen(SessionListScreen(
        session_manager=self.app.session_manager,
        on_load=self.app.load_session,
    ))
```

### /delete Command
```python
async def cmd_delete(self, args: list[str]) -> None:
    """Handle /delete command."""
    if not args:
        self.notify("Usage: /delete <session-name>", severity="warning")
        return

    session_id = args[0]

    # Show confirmation dialog
    self.push_screen(ConfirmScreen(
        message=f"Delete session '{session_id}'?",
        on_confirm=lambda: self._do_delete(session_id),
    ))

async def _do_delete(self, session_id: str) -> None:
    """Actually delete the session."""
    try:
        deleted = await self.app.session_manager.delete(session_id)

        if deleted:
            self.notify(f"Session deleted: {session_id}")
            history = self.query_one(ChatHistoryViewer)
            history.add_system_message(f"🗑️ Session deleted: {session_id}")
        else:
            self.notify(
                f"Session not found: {session_id}",
                severity="error",
            )

    except Exception as e:
        self.notify(
            f"Failed to delete session: {e}",
            severity="error",
        )
```

### /session Command
```python
async def cmd_session(self) -> None:
    """Handle /session command."""
    # Gather session info
    info = {
        "name": self.app.session_id or "unsaved",
        "messages": len(self.app.agent.history.messages),
        "agent": self.app.current_agent_type.value,
        "directory": os.getcwd(),
        "model": self.app.config.chat_model,
    }

    # Show info screen
    self.push_screen(SessionInfoScreen(info=info))
```

### SessionListScreen
```python
from textual.widgets import ListView, ListItem

class SessionListScreen(Screen):
    """Screen for listing and selecting sessions."""

    def __init__(
        self,
        session_manager: SessionManager,
        on_load: Callable[[str], Awaitable[None]],
    ):
        super().__init__()
        self.session_manager = session_manager
        self.on_load = on_load

    def compose(self) -> ComposeResult:
        yield Header()
        yield SessionListView(id="list")
        yield Footer()

    async def on_mount(self) -> None:
        """Load sessions on mount."""
        list_view = self.query_one(SessionListView)
        sessions = await self.session_manager.list_sessions()
        list_view.set_sessions(sessions)

class SessionListView(ListView):
    """List view for sessions."""

    def set_sessions(self, sessions: list[SessionInfo]) -> None:
        """Set sessions to display."""
        self.clear()

        for s in sessions:
            item = ListItem(
                SessionItem(session=s),
                id=s.id,
            )
            self.append(item)

    async def on_list_item_selected(self, event: ListItem.Selected) -> None:
        """Handle session selection."""
        session_id = event.item.id
        # Load session and close screen
        await self.app.on_load(session_id)
        self.app.pop_screen()

class SessionItem(Static):
    """Display a single session in the list."""

    def __init__(self, session: SessionInfo):
        super().__init__()
        self.session = session

    def render(self) -> RenderableType:
        s = self.session
        text = Text()
        text.append(f"{s.id}\n", style="bold cyan")
        text.append(f"  📝 {s.message_count} messages  ", style="dim")
        text.append(f"  🕒 {s.updated_at.strftime('%Y-%m-%d %H:%M')}\n", style="dim")
        text.append(f"  📁 {s.working_directory}\n", style="dim")
        text.append(f"  🤖 {s.agent_type}", style="dim")
        return text
```

### SessionInfoScreen
```python
class SessionInfoScreen(Screen):
    """Screen showing current session info."""

    def __init__(self, info: dict):
        super().__init__()
        self.info = info

    def compose(self) -> ComposeResult:
        yield Header()
        yield SessionInfoDisplay(info=self.info)
        yield Footer()

    def on_key(self, event) -> None:
        """Close on any key."""
        if event.key != "escape":  # Let escape pass through
            self.app.pop_screen()

class SessionInfoDisplay(Static):
    """Display session info."""

    def __init__(self, info: dict):
        super().__init__()
        self.info = info

    def render(self) -> RenderableType:
        i = self.info
        return Panel(
            Group(
                Text("Current Session", style="bold"),
                Text(""),
                self._row("Name:", i["name"]),
                self._row("Messages:", str(i["messages"])),
                self._row("Agent:", i["agent"]),
                self._row("Model:", i["model"]),
                self._row("Directory:", i["directory"]),
                Text(""),
                Text("[dim]Press any key to close[/dim]"),
            ),
            title="Session Info",
            border_style="blue",
        )

    def _row(self, label: str, value: str) -> Text:
        return Text.assemble(
            label, " ",
            value, "\n",
            style="bold",
        )
```

### ConfirmScreen
```python
class ConfirmScreen(Screen):
    """Confirmation dialog."""

    def __init__(
        self,
        message: str,
        on_confirm: Callable[[], None],
    ):
        super().__init__()
        self.message = message
        self.on_confirm = on_confirm

    def compose(self) -> ComposeResult:
        yield ConfirmDialog(message=self.message)

    def on_confirm_dialog_confirmed(self) -> None:
        """Handle confirmation."""
        self.on_confirm()
        self.app.pop_screen()

    def on_confirm_dialog_cancelled(self) -> None:
        """Handle cancellation."""
        self.app.pop_screen()

class ConfirmDialog(Static):
    """Dialog widget."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def render(self) -> RenderableType:
        return Panel(
            Group(
                Text(self.message, style="bold"),
                Text(""),
                Text("[y] Yes  [n] No", style="dim"),
            ),
            title="Confirm",
            border_style="yellow",
        )

    def on_key(self, event) -> None:
        """Handle key press."""
        if event.key == "y" or event.key == "enter":
            self.post_message(ConfirmDialog.Confirmed(self))
        elif event.key == "n" or event.key == "escape":
            self.post_message(ConfirmDialog.Cancelled(self))

    class Confirmed(Message):
        """User confirmed."""

    class Cancelled(Message):
        """User cancelled."""
```

## Dependencies
- Issue 27: Session Persistence

## Related Issues
- Issue 29: Agent Type System

## Log
