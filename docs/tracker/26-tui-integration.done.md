# Issue 26: TUI-Agent Integration

## Status
.todo

## Description
Complete integration between TUI and AgentCore, ensuring full chat flow works end-to-end.

## User Scenarios

### Scenario 1: Complete Chat Flow
- User launches goz
- Agent mode starts with welcome screen
- User types: "Hello, what can you do?"
- Agent responds with capabilities list
- User types: "Read main.py and explain it"
- Agent shows "Thinking..." indicator
- Agent shows "Running: view_file" indicator
- File content is displayed
- Agent explains the code
- User sees complete flow

### Scenario 2: Error Recovery
- User types: "Read nonexistent.py"
- Agent attempts to view file
- Tool returns file not found error
- Agent explains to user
- User types: "Oh, I meant utils.py"
- Agent reads correct file
- No crash, clean error handling

### Scenario 3: Long Response Handling
- User asks for detailed explanation
- Agent streams long response
- Response has multiple paragraphs
- User can scroll to see all content
- Auto-scroll follows new content
- User can manually scroll back

### Scenario 4: Multiple Tool Calls
- User asks: "Compare main.py and utils.py"
- Agent calls view_file twice
- Both files displayed
- Agent provides comparison
- All indicators work correctly

### Scenario 5: Session Persistence
- User types: `/save my-session`
- Session is saved
- User quits
- User runs: `goz --load my-session`
- Session is restored
- Chat history is intact

### Scenario 6: Special Commands
- User types: `/help`
- Help dialog appears
- User presses Esc
- Help closes, back to chat
- User types: `/clear`
- Chat history is cleared
- User types: `/quit`
- Confirmation dialog
- User confirms
- App exits

## Acceptance Criteria

### End-to-End Flow
1. `goz` with no args launches agent mode
2. Welcome message is displayed
3. User can type and submit messages
4. Agent responds correctly
5. Streaming responses work word-by-word
6. Tool calls are shown visually
7. Tool results are formatted
8. Errors are handled gracefully

### State Management
9. Thinking indicator shows at right times
10. Planning indicator shows before tools
11. Executing indicator shows tool name
12. All indicators hide when complete
13. State machine transitions work correctly

### Chat History
14. User messages appear in history
15. Assistant messages appear in history
16. Tool calls appear in history
17. Tool results appear in history
18. History is scrollable
19. History auto-scrolls to new messages
20. `/clear` command clears history

### Error Handling
21. Network errors show user-friendly message
22. API errors are displayed
23. Tool errors are displayed
24. Invalid input shows helpful message
25. No crashes on errors
26. App remains responsive after errors

### Commands
27. `/help` shows command list
28. `/quit` or `q` quits with confirmation
29. `/clear` clears chat history
30. `/save <name>` saves session (stub for Issue 27)
31. `/load <name>` loads session (stub for Issue 27)
32. `/agent <type>` switches agent (stub for Issue 29)

### Performance
33. Streaming response feels responsive (< 100ms latency)
34. UI doesn't freeze during tool execution
35. Large outputs (1000+ lines) render smoothly
36. Memory usage is reasonable
37. Scrolling is smooth

## Technical Details

### File Structure
```
goz/agent/tui/
├── app.py           # Update AgentApp
└── screens/
    └── chat.py       # Complete ChatScreen integration
```

### Entry Point
```python
# goz/__main__.py

def main() -> None:
    """Run the goz CLI."""
    import argparse

    parser = argparse.ArgumentParser(...)
    parser.add_argument("command", nargs="?")
    parser.add_argument("args", nargs=argparse.REMAINDER)

    # Agent mode flags
    parser.add_argument("--load", help="Load session")
    parser.add_argument("--agent", help="Start with specific agent")

    args = parser.parse_args()

    # AGENT MODE (default when no command)
    if args.command is None:
        from goz.agent.tui import run_agent_app
        run_agent_app(
            session_id=args.load,
            agent_type=args.agent,
        )
        return

    # CLI MODE (existing commands)
    if args.command == "vision":
        asyncio.run(cmd_vision(args.args))
    # ... etc
```

### run_agent_app()
```python
def run_agent_app(
    session_id: str | None = None,
    agent_type: str | None = None,
) -> None:
    """Run the agent TUI application."""
    app = AgentApp()

    # Load session if specified
    if session_id:
        app.load_session(session_id)

    # Set agent type if specified
    if agent_type:
        app.set_agent_type(agent_type)

    app.run()
```

### ChatScreen Complete
```python
class ChatScreen(Screen):
    """Main chat interface with full integration."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("/", "show_help", "Help"),
        ("c", "clear_history", "Clear"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ThinkingIndicator(id="thinking")
        yield ChatHistoryViewer(id="history")
        yield ChatInput(id="input")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen."""
        self.agent = self.app.agent
        self.show_welcome()

    def show_welcome(self) -> None:
        """Show welcome message."""
        history = self.query_one(ChatHistoryViewer)
        history.add_system_message("""Welcome to goz!

I'm your AI coding assistant. I can help you:
• Read and analyze code
• Create and modify files
• Run terminal commands
• Search the web
• Debug and fix issues

Type your request below or press / for commands.""")

    async def on_chat_input_submitted(
        self,
        event: ChatInput.Submitted,
    ) -> None:
        """Handle user input."""
        user_input = event.value.strip()
        if not user_input:
            return

        # Check for slash commands
        if user_input.startswith("/"):
            await self.handle_slash_command(user_input)
            return

        # Add user message
        history = self.query_one(ChatHistoryViewer)
        history.add_user_message(user_input)

        # Process with agent
        await self.process_agent_turn(user_input)

    async def process_agent_turn(self, user_input: str) -> None:
        """Process a turn with the agent."""
        thinking = self.query_one(ThinkingIndicator)
        history = self.query_one(ChatHistoryViewer)

        try:
            # Start assistant message
            history.start_assistant_message()

            # Stream response
            async for chunk in self.agent.process_turn(user_input):
                # Handle state markers
                if chunk.startswith("\x01"):
                    state, data = self._parse_state_marker(chunk)
                    thinking.set_state(state, data)
                # Handle completion
                elif chunk == "\x00":
                    break
                # Regular content
                else:
                    thinking.set_state("idle")
                    history.append_assistant_content(chunk)

            history.end_assistant_message()
            thinking.set_state("idle")

        except AuthError as e:
            self.show_error(f"Authentication error: {e}")
        except ApiError as e:
            self.show_error(f"API error: {e}")
        except NetworkError as e:
            self.show_error(f"Network error: {e}")
        except Exception as e:
            self.show_error(f"Unexpected error: {e}")

    def _parse_state_marker(self, marker: str) -> tuple[str, str | None]:
        """Parse state update marker."""
        parts = marker[1:].split(":", 1)
        state = parts[0]
        data = parts[1] if len(parts) > 1 else None
        return state, data

    async def handle_slash_command(self, command: str) -> None:
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0]

        if cmd in ("/quit", "/q"):
            await self.action_quit()
        elif cmd == "/clear":
            self.query_one(ChatHistoryViewer).clear()
        elif cmd == "/help":
            self.push_screen(HelpScreen())
        elif cmd == "/save":
            name = parts[1] if len(parts) > 1 else "default"
            await self.app.save_session(name)
            self.notify(f"Session saved: {name}")
        elif cmd == "/load":
            name = parts[1] if len(parts) > 1 else None
            if name:
                await self.app.load_session(name)
                self.notify(f"Session loaded: {name}")
        elif cmd == "/agent":
            agent_type = parts[1] if len(parts) > 1 else None
            if agent_type:
                self.app.set_agent_type(agent_type)
        else:
            self.notify(f"Unknown command: {cmd}", severity="error")

    def action_quit(self) -> None:
        """Quit with confirmation."""
        self.push_screen(
            ConfirmScreen(
                "Quit session?",
                on_confirm=self.app.exit,
            )
        )

    def action_show_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_clear_history(self) -> None:
        """Clear chat history."""
        history = self.query_one(ChatHistoryViewer)
        history.clear()
        self.notify("Chat history cleared")

    def show_error(self, message: str) -> None:
        """Show error message."""
        history = self.query_one(ChatHistoryViewer)
        history.add_error_message(message)
        self.query_one(ThinkingIndicator).set_state("error")
```

### Help Screen
```python
class HelpScreen(Screen):
    """Help screen with command reference."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield HelpContent()
        yield Footer()

class HelpContent(Static):
    """Help content."""

    def render(self) -> RenderableType:
        return Panel(
            Group(
                Text("goz Commands", style="bold"),
                Text(""),
                Text("/help, /?      Show this help", style="cyan"),
                Text("/quit, /q      Quit the session", style="cyan"),
                Text("/clear         Clear chat history", style="cyan"),
                Text("/save <name>   Save current session", style="cyan"),
                Text("/load <name>   Load a session", style="cyan"),
                Text("/agent <type>  Switch agent type", style="cyan"),
                Text(""),
                Text("Agent Types:", style="bold"),
                Text("/general       General purpose (default)", style="yellow"),
                Text("/review        Code reviewer", style="yellow"),
                Text("/test          Test writer", style="yellow"),
                Text("/debug         Debugger", style="yellow"),
                Text(""),
                Text("Press Esc to close", style="dim"),
            ),
            title="Help",
            border_style="blue",
        )
```

### Error Display
```python
class ChatHistoryViewer(VerticalScroll):
    # ... existing ...

    def add_error_message(self, message: str) -> None:
        """Add an error message."""
        error_box = MessageBox(
            content=f"⚠️ {message}",
            role="error",
        )
        self.mount(error_box)
        self.scroll_end()
```

## Dependencies
- Issue 23: Agent App + Chat Screen
- Issue 24: Markdown + Diff Widgets
- Issue 25: Thinking Indicator
- All previous issues

## Related Issues
- Issue 27: Session Save/Load
- Issue 29: Agent Type System

## Log
