# Issue 32: Error Handling + Edge Cases

## Status
.todo

## Description
Implement comprehensive error handling for all agent operations and edge cases.

## User Scenarios

### Scenario 1: Network Error During Chat
- User sends message
- Network connection drops
- Agent shows: "Connection error. Retrying..."
- Retry succeeds
- Response continues normally
- User sees minimal disruption

### Scenario 2: API Rate Limit
- User sends many messages quickly
- API returns 429 rate limit
- Agent shows: "Rate limited. Waiting before retry..."
- Waits appropriate time
- Retries automatically
- Continues conversation

### Scenario 3: Invalid Tool Input
- Agent calls tool with invalid input
- Tool raises ToolInputError
- Error message shown to user
- Agent asks for clarification
- User provides correct input
- Tool succeeds

### Scenario 4: File Permission Error
- Agent tries to edit read-only file
- Tool raises PermissionError
- Error shown: "Cannot edit file: permission denied"
- Agent suggests checking file permissions
- User fixes permissions
- Continues

### Scenario 5: Tool Timeout
- Agent runs long bash command
- Command exceeds timeout
- TimeoutError raised
- Error shown: "Command timed out after 300s"
- Agent suggests breaking into smaller tasks
- User continues

### Scenario 6: Corrupted Session
- User tries to load corrupted session
- JSON decode error
- Clear error shown: "Session file is corrupted"
- User advised to delete and start fresh
- No crash

### Scenario 7: Out of Context
- Long conversation exceeds context window
- History compression triggers
- Old messages summarized
- Conversation continues
- User may notice summary in history

### Scenario 8: Invalid Agent Type
- User types: `/agent nonexistent`
- Error shown: "Unknown agent type: nonexistent"
- List of valid types shown
- User can try again
- No crash

### Scenario 9: Empty Input
- User presses Enter with no text
- Input is ignored
- No API call made
- User stays in chat

### Scenario 10: Very Long Input
- User pastes 10000 characters
- Input is accepted
- Sent to API
- API handles as configured
- If too long, API returns error
- Error shown to user

## Acceptance Criteria

### Network Errors
1. Connection errors show user-friendly message
2. Timeout errors show timeout duration
3. Retry logic works correctly
4. Max retries respected
5. After max retries, user is informed
6. User can retry manually

### API Errors
7. 401 errors show authentication message
8. 429 errors show rate limit message
9. 500 errors show server error message
10. Error messages include actionable suggestions
11. No crashes on API errors

### Tool Errors
12. ToolInputError shows which field was invalid
13. FileNotFoundError shows file path
14. PermissionError shows operation that failed
15. TimeoutError shows timeout duration
16. ToolExecutionError shows tool name and error

### Session Errors
17. Corrupted session shows decode error
18. Non-existent session shows not found
19. Permission denied shows path
20. Create session directory if missing
21. Handle disk full errors

### UI Errors
22. TUI doesn't freeze on errors
23. Errors shown in visible notifications
24. Long error messages are scrollable
25. User can dismiss error dialogs
26. Error states clear automatically

### Edge Cases
27. Empty input is ignored
28. Whitespace-only input is ignored
29. Very long input is handled
30. Special characters in input preserved
31. Unicode input handled correctly
32. Concurrent input handling

### Recovery
33. User can continue after error
34. Context preserved after recoverable errors
35. Clear button works during errors
36. Quit works during errors
37. No resource leaks on errors

## Technical Details

### File Structure
```
goz/agent/
└── errors.py    # Agent-specific error classes

goz/agent/tui/
└── widgets/
    └── errors.py    # Error display widgets
```

### Agent Error Classes
```python
# goz/agent/errors.py

class AgentError(ZaiError):
    """Base error for agent operations."""

class ContextWindowExceededError(AgentError):
    """Chat history exceeds context window."""

class ToolExecutionError(AgentError):
    """Tool execution failed."""

    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"{tool_name}: {message}")

class SessionCorruptedError(AgentError):
    """Session file is corrupted."""

class RetryableError(AgentError):
    """Error that can be retried."""

class MaxRetriesExceededError(AgentError):
    """Maximum retries exceeded."""
```

### Error Handler
```python
# goz/agent/error_handler.py

class ErrorHandler:
    """Centralized error handling for agent."""

    def __init__(self, notifier: Callable[[str, str], None]):
        """
        Args:
            notifier: Function to show notifications (title, message)
        """
        self.notifier = notifier

    async def handle_error(
        self,
        error: Exception,
        context: str | None = None,
    ) -> bool:
        """Handle an error.

        Args:
            error: The error to handle
            context: Optional context string

        Returns:
            True if error was recoverable, False otherwise
        """
        # Network errors - retry
        if isinstance(error, httpx.NetworkError):
            self.notifier(
                "Network Error",
                "Connection failed. Retrying...",
            )
            return True  # Recoverable

        if isinstance(error, httpx.TimeoutException):
            self.notifier(
                "Timeout",
                "Request timed out. Please try again.",
            )
            return False  # Not recoverable

        # API errors
        if isinstance(error, AuthError):
            self.notifier(
                "Authentication Error",
                "Please check your API token in config.",
            )
            return False

        if isinstance(error, ApiError):
            if error.statusCode == 429:
                self.notifier(
                    "Rate Limited",
                    "Too many requests. Please wait a moment.",
                )
                return True  # Recoverable after wait
            else:
                self.notifier(
                    "API Error",
                    f"Server error: {error}",
                )
                return False

        # Tool errors
        if isinstance(error, ToolExecutionError):
            self.notifier(
                f"Tool Error: {error.tool_name}",
                str(error),
            )
            return True  # Recoverable - can try different approach

        if isinstance(error, ToolInputError):
            self.notifier(
                "Invalid Input",
                str(error),
            )
            return True  # Recoverable

        # Session errors
        if isinstance(error, SessionCorruptedError):
            self.notifier(
                "Session Corrupted",
                "The session file is corrupted. Please start a new session.",
            )
            return False

        if isinstance(error, FileNotFoundError):
            self.notifier(
                "Not Found",
                str(error),
            )
            return False

        # Generic error
        self.notifier(
            "Error",
            f"An error occurred: {error}",
        )
        return False
```

### Retry Logic
```python
# goz/agent/core.py

class AgentCore:
    """Agent with retry logic."""

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    async def process_turn_with_retry(
        self,
        user_input: str,
    ) -> AsyncIterator[str]:
        """Process turn with automatic retry on recoverable errors."""
        retry_count = 0

        while retry_count <= self.MAX_RETRIES:
            try:
                async for chunk in self.process_turn(user_input):
                    yield chunk
                return  # Success

            except RetryableError as e:
                retry_count += 1
                if retry_count <= self.MAX_RETRIES:
                    # Notify and retry
                    yield f"\x01RETRY:{retry_count}"
                    await asyncio.sleep(self.RETRY_DELAY * retry_count)
                else:
                    # Max retries exceeded
                    raise MaxRetriesExceededError(
                        f"Failed after {self.MAX_RETRIES} retries"
                    )
```

### Error Display Widget
```python
# goz/agent/tui/widgets/errors.py

from textual.widgets import Static
from rich.panel import Panel
from rich.text import Text

class ErrorDisplay(Static):
    """Widget for displaying errors."""

    def __init__(
        self,
        title: str,
        message: str,
        severity: str = "error",
    ):
        super().__init__()
        self.title = title
        self.message = message
        self.severity = severity

    def render(self) -> RenderableType:
        # Color by severity
        styles = {
            "error": "red",
            "warning": "yellow",
            "info": "blue",
        }

        style = styles.get(self.severity, "white")

        return Panel(
            Text.assemble(
                (self.title + "\n\n", "bold"),
                (self.message, style),
            ),
            title=self.title,
            border_style=style,
            title_align="left",
        )

class RetryNotification(Static):
    """Notification for retry operations."""

    def __init__(self, retry_count: int, max_retries: int):
        super().__init__()
        self.retry_count = retry_count
        self.max_retries = max_retries

    def render(self) -> RenderableType:
        dots = "..." if self.retry_count < self.max_retries else ""
        return Text(
            f"⚠️  Connection failed. Retrying ({self.retry_count}/{self.max_retries}){dots}",
            style="yellow",
        )
```

### Input Validation
```python
# goz/agent/tui/screens/chat.py

class ChatScreen(Screen):
    """Chat screen with input validation."""

    async def on_chat_input_submitted(
        self,
        event: ChatInput.Submitted,
    ) -> None:
        """Handle user input with validation."""
        user_input = event.value.strip()

        # Validate input
        if not user_input:
            return  # Empty input, ignore

        if len(user_input) > 100000:  # 100k characters
            self.notify(
                "Input too long. Please keep it under 100,000 characters.",
                severity="error",
            )
            return

        # Check for slash commands
        if user_input.startswith("/"):
            await self.handle_slash_command(user_input)
            return

        # Process normally
        await self.process_agent_turn(user_input)
```

### Context Window Management
```python
# goz/agent/history.py

class ChatHistory:
    """Chat history with context window management."""

    MAX_MESSAGES = 50
    MAX_TOKENS = 100000  # Approximate

    async def add(self, message: ChatMessage) -> None:
        """Add message with context window check."""
        self.messages.append(message)

        # Check if we need to compress
        if self._should_compress():
            await self.compress()

    def _should_compress(self) -> bool:
        """Check if history should be compressed."""
        # Compress at 80% of limit
        return len(self.messages) >= int(self.MAX_MESSAGES * 0.8)

    async def compress(self) -> None:
        """Compress history by summarizing old messages."""
        if len(self.messages) < self.MAX_MESSAGES:
            return

        # Keep recent messages, summarize old ones
        recent = self.messages[-20:]
        to_summarize = self.messages[:-20]

        # Create summary (could use API for this)
        summary_text = self._create_summary(to_summarize)

        summary_message = ChatMessage(
            role="system",
            content=f"[Previous conversation summarized: {summary_text}]",
        )

        self.messages = [summary_message] + recent
```

### Graceful Shutdown
```python
# goz/agent/tui/app.py

class AgentApp(App[None]):
    """Agent app with graceful shutdown."""

    def action_quit(self) -> None:
        """Quit with optional session save."""
        if self._has_unsaved_changes():
            self.push_screen(ConfirmQuitScreen(
                on_save=self._save_and_quit,
                on_discard=self.app.exit,
                on_cancel=lambda: None,
            ))
        else:
            self.app.exit()

    def _has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        # Check if message count > 0 and no session saved
        return (
            len(self.agent.history.messages) > 0
            and self.session_id is None
        )

    async def _save_and_quit(self) -> None:
        """Save session and quit."""
        await self.save_session("default")
        self.app.exit()

class ConfirmQuitScreen(Screen):
    """Confirmation screen for quitting with unsaved changes."""

    def __init__(
        self,
        on_save: Callable[[], Awaitable[None]],
        on_discard: Callable[[], None],
        on_cancel: Callable[[], None],
    ):
        super().__init__()
        self.on_save = on_save
        self.on_discard = on_discard
        self.on_cancel = on_cancel

    def compose(self) -> ComposeResult:
        yield QuitConfirmDialog()

    def on_quit_confirmed(self, action: str) -> None:
        """Handle user choice."""
        if action == "save":
            asyncio.create_task(self.on_save())
        elif action == "discard":
            self.on_discard()
        else:
            self.on_cancel()
```

### Session Corruption Recovery
```python
# goz/agent/sessions.py

class SessionManager:
    """Session manager with corruption handling."""

    async def load(self, session_id: str) -> Session:
        """Load session with corruption handling."""
        file_path = self.session_dir / f"{session_id}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        try:
            with open(file_path) as f:
                data = json.load(f)
            return Session.from_dict(data)

        except json.JSONDecodeError as e:
            # Corrupted session
            # Back up the corrupted file
            backup_path = file_path.with_suffix(".json.corrupted")
            file_path.rename(backup_path)

            raise SessionCorruptedError(
                f"Session file is corrupted. "
                f"Backup saved to {backup_path.name}"
            )
```

## Dependencies
- All previous issues

## Related Issues
- None (final issue)

## Log
