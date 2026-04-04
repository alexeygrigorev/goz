# Issue 25: Thinking Indicator

## Status
.todo

## Description
Implement visual indicators for agent thinking, tool execution, and processing states.

## User Scenarios

### Scenario 1: Thinking State
- User sends message
- Agent starts thinking
- Chat screen shows "Thinking..." indicator
- Indicator animates (pulsing or spinning)
- When response starts, indicator disappears

### Scenario 2: Planning Tools State
- Agent receives API response with tool calls
- State transitions to PLANNING_TOOLS
- Chat screen shows "Planning actions..." indicator
- List of planned tools shown

### Scenario 3: Executing Tool State
- Agent executes view_file tool
- Chat screen shows "[Tool: view_file]"
- Shows "Reading: main.py"
- While executing, shows progress indicator

### Scenario 4: Streaming Response
- Agent streams text response
- No "thinking" indicator (active streaming)
- Each chunk appears as it arrives
- Cursor/indicator shows streaming active

### Scenario 5: Error State
- Tool execution fails
- Error indicator shown in red
- Error message displayed
- State returns to ready

## Acceptance Criteria

1. `ThinkingIndicator` widget exists in `goz/agent/tui/widgets/thinking.py`
2. Shows animated "Thinking..." text
3. Pulsing animation (opacity changes)
4. Or spinning character animation (|, /, -, \)
5. Displays when agent is thinking
6. Hides when response starts
7. Shows tool name when executing tools
8. Shows different styles for different states
9. Red indicator for errors
10. Green indicator for successful completion

## Technical Details

### File Structure
```
goz/agent/tui/widgets/
└── thinking.py   # ThinkingIndicator
```

### ThinkingIndicator Widget
```python
from textual.widgets import Static
from textual import on
from textual.timer import Timer

class ThinkingIndicator(Static):
    """Animated indicator for agent thinking."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state = "idle"  # idle, thinking, planning, executing, error
        self.tool_name = None
        self.animation_frame = 0
        self.timer = None

    def on_mount(self) -> None:
        """Start animation timer."""
        self.timer = self.set_interval(0.1, self.animate)

    def animate(self) -> None:
        """Update animation frame."""
        self.animation_frame = (self.animation_frame + 1) % 4
        self.update_content()

    def set_state(
        self,
        state: str,
        tool_name: str | None = None,
    ) -> None:
        """Set the current state."""
        self.state = state
        self.tool_name = tool_name
        self.visible = (state != "idle")
        self.update_content()

    def update_content(self) -> None:
        """Update display based on state."""
        frames = ["|", "/", "-", "\\"]

        if self.state == "thinking":
            frame = frames[self.animation_frame]
            self.update(f"[dim]{frame} Thinking...[/dim]")

        elif self.state == "planning":
            frame = frames[self.animation_frame]
            self.update(f"[cyan]{frame} Planning actions...[/cyan]")

        elif self.state == "executing":
            frame = frames[self.animation_frame]
            tool = self.tool_name or "tool"
            self.update(f"[yellow]{frame} Running: {tool}[/yellow]")

        elif self.state == "error":
            self.update("[red]✗ Error occurred[/red]")

        elif self.state == "idle":
            self.visible = False
```

### ChatScreen Integration
```python
class ChatScreen(Screen):
    """Chat screen with thinking indicator."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield ThinkingIndicator(id="thinking")
        yield ChatHistoryViewer(id="history")
        yield ChatInput(id="input")
        yield Footer()

    async def process_agent_turn(self, user_input: str) -> None:
        """Process turn with state updates."""
        thinking = self.query_one(ThinkingIndicator)
        history = self.query_one(ChatHistoryViewer)

        # Show thinking
        thinking.set_state("thinking")

        # Start streaming
        response_started = False
        async for chunk in self.agent.process_turn(user_input):
            if not response_started and chunk and chunk != "\x00":
                # First chunk = response started
                response_started = True
                thinking.set_state("idle")

            # Handle state updates from agent
            if chunk.startswith("\x01"):  # State marker
                state, data = self.parse_state_marker(chunk)
                if state == "planning":
                    thinking.set_state("planning")
                elif state == "executing":
                    thinking.set_state("executing", data)
                elif state == "error":
                    thinking.set_state("error")
            else:
                history.append_assistant_content(chunk)

        thinking.set_state("idle")
```

### State Markers
```python
# Special markers for state updates
STATE_MARKERS = {
    "THINKING": "\x01THINKING",
    "PLANNING": "\x01PLANNING",
    "EXECUTING": "\x01EXECUTING:",
    "ERROR": "\x01ERROR:",
    "DONE": "\x00",
}

# In AgentCore.process_turn()
async def process_turn(self, user_input: str) -> AsyncIterator[str]:
    # Update state
    yield "\x01THINKING"

    # Call API...
    # If tools returned:
    yield "\x01PLANNING"

    for tool_call in tool_calls:
        yield f"\x01EXECUTING:{tool_call.name}"
        # Execute tool...

    # Streaming response
    async for chunk in response:
        yield chunk

    yield "\x00"  # Done
```

### Progress Bar (for long operations)
```python
from textual.widgets import ProgressBar

class ToolProgress(Static):
    """Progress bar for long-running tools."""

    def __init__(self, tool_name: str, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.progress = 0.0

    def compose(self) -> ComposeResult:
        yield Text(f"{self.tool_name}")
        yield ProgressBar(total=100, show_eta=True)

    def update_progress(self, value: float) -> None:
        """Update progress (0-100)."""
        bar = self.query_one(ProgressBar)
        bar.advance = value - self.progress
        self.progress = value
```

### Inline Thinking Indicator
```python
class InlineThinking(Static):
    """Compact inline indicator."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dots = 0
        self.set_interval(0.5, self.add_dot)

    def add_dot(self) -> None:
        """Add another dot."""
        self.dots = (self.dots + 1) % 4
        self.update("[dim]" + "." * self.dots + " [/dim]")
```

### State Colors
```python
STATE_STYLES = {
    "thinking": {"style": "dim", "icon": "…"},
    "planning": {"style": "cyan", "icon": "⚙"},
    "executing": {"style": "yellow", "icon": "▶"},
    "success": {"style": "green", "icon": "✓"},
    "error": {"style": "red", "icon": "✗"},
}
```

### Animation Options

#### Option 1: Spinning Character
```python
FRAMES = ["|", "/", "-", "\\"]

def update_spinner(self):
    frame = FRAMES[self.frame_index]
    self.update(f"[dim]{frame} Working...[/dim]")
```

#### Option 2: Pulsing Dots
```python
def update_dots(self):
    dots = "." * (self.frame_index + 1)
    self.update(f"[dim]Working{dots}[/dim]")
```

#### Option 3: Unicode Spinner
```python
UNICODE_FRAMES = ["◐", "◓", "◑", "◒"]
# Or: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
```

### CSS Styling
```css
ThinkingIndicator {
    dock: top;
    padding: 0 1;
    height: 1;
    background: $background;
}

ThinkingIndicator.thinking {
    text-style: dim;
}

ThinkingIndicator.planning {
    text-style: bold cyan;
}

ThinkingIndicator.executing {
    text-style: bold yellow;
}

ThinkingIndicator.error {
    text-style: bold red;
    background: $error 20%;
}
```

## Dependencies
- Issue 23: Agent App + Chat Screen
- Issue 16: Stream Processor + State Machine

## Related Issues
- Issue 26: TUI-Agent Integration

## Log

### 2025-03-19 - Completed by SWE Agent

**TDD Process:**

1. **Write tests FIRST** - Created `tests/test_thinking_widget.py` with 30 tests covering:
   - Class existence and initialization
   - State management (idle, thinking, planning, executing, error, success)
   - Animation behavior
   - Rendering for each state
   - Styling (dim, cyan, yellow, red, green)

2. **Tests FAILED** - Verified tests failed before implementation (module did not exist)

3. **Implemented code** - Created `goz/tui/widgets/thinking.py`:
   - `ThinkingIndicator` class inheriting from `Static`
   - Spinner animation with frames: `|`, `/`, `-`, `\`
   - `set_state()` method for state transitions
   - `animate()` method called every 0.1s via timer
   - `update_content()` for updating display
   - CSS styling for each state

4. **Tests PASSED** - All 30 tests pass

**Files Created:**
- `goz/tui/widgets/thinking.py` - ThinkingIndicator widget (189 lines)
- `tests/test_thinking_widget.py` - Test suite (230 lines)

**Files Modified:**
- `goz/tui/widgets/__init__.py` - Added ThinkingIndicator export

**Acceptance Criteria Met:**
1. ✅ ThinkingIndicator widget exists in `goz/tui/widgets/thinking.py`
2. ✅ Shows animated "Thinking..." text
3. ✅ Spinning character animation (|, /, -, \\)
4. ✅ Displays when agent is thinking (visible=True for non-idle states)
5. ✅ Hides when response starts (visible=False for idle state)
6. ✅ Shows tool name when executing tools
7. ✅ Different styles for different states (dim, cyan, yellow, red, green)
8. ✅ Red indicator for errors
9. ✅ Green indicator for successful completion
