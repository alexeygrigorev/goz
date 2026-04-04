# Issue 30: Agent Switching Commands

## Status
.todo

## Description
Implement all agent switching slash commands and ensure seamless transitions between agent types.

## User Scenarios

### Scenario 1: Switch to Code Reviewer
- User is in General Purpose mode
- User types: `/review`
- System acknowledges: "Switched to Code Reviewer agent"
- Header updates to show new agent
- System prompt changes immediately
- Next message uses Code Reviewer persona

### Scenario 2: Short Form Commands
- User types: `/test`
- Switches to Test Writer
- User types: `/debug`
- Switches to Debugger
- User types: `/perf`
- Switches to Performance

### Scenario 3: Full Form Commands
- User types: `/agent reviewer`
- Switches to Code Reviewer
- User types: `/agent test_writer`
- Switches to Test Writer
- Works with both short and full names

### Scenario 4: Invalid Agent Type
- User types: `/agent nonexistent`
- Error message: "Unknown agent type: nonexistent"
- List of valid agent types shown
- User stays in current agent mode
- No crash

### Scenario 5: Switch During Conversation
- User has active conversation
- User types: `/review`
- Agent switches to Code Reviewer
- Chat history is preserved
- System message added: "[Switched to Code Reviewer agent]"
- Conversation continues with new persona

### Scenario 6: Quick Switch List
- User types: `/agent` with no args
- List of all agent types appears
- Shows: icon, name, description, command
- User can see all options
- Press Esc to close without switching

### Scenario 7: Context-Aware Switching
- User asks: "Review this code"
- Agent suggests: "Would you like me to switch to Code Reviewer mode for better analysis?"
- User types: `/review`
- Agent acknowledges and switches
- Continues with specialized analysis

## Acceptance Criteria

### Short Form Commands
1. `/general` switches to General Purpose
2. `/review` switches to Code Reviewer
3. `/test` switches to Test Writer
4. `/docs` switches to Documentation
5. `/refactor` switches to Refactoring
6. `/debug` switches to Debugger
7. `/security` switches to Security Audit
8. `/perf` switches to Performance
9. `/explore` switches to Explore
10. `/plan` switches to Plan

### Full Form Command
11. `/agent <type>` switches to specified agent
12. Accepts short names (review, test, etc.)
13. Accepts full names (reviewer, test_writer, etc.)
14. Accepts enum values (CODE_REVIEWER, etc.)

### Switching Behavior
15. Header updates immediately on switch
16. System message added to chat history
17. Confirmation message shown
18. Chat history preserved
19. Current context maintained
20. Agent type included in session saves

### Agent List Screen
21. `/agent` with no args shows list
22. List shows all 10 agent types
23. Each entry shows icon, name, command
24. Brief description for each
25. Press Esc to close
26. Can press Enter to select

### Error Handling
27. Unknown agent type shows error
28. Error lists valid agent types
29. No crash on invalid input
30. Graceful degradation

### UI Updates
31. Header shows agent icon and name
32. Header uses agent-specific color
33. Welcome message reflects agent type
34. System messages clearly indicate agent switches

## Technical Details

### File Structure
```
goz/agent/tui/screens/
└── agents.py    # AgentListScreen

goz/agent/
└── specialized.py    # Already has definitions from Issue 29
```

### Command Mappings
```python
# From Issue 29, used here

COMMAND_ALIASES: dict[str, AgentType] = {
    # Short forms
    "general": AgentType.GENERAL_PURPOSE,
    "review": AgentType.CODE_REVIEWER,
    "test": AgentType.TEST_WRITER,
    "docs": AgentType.DOCUMENTATION,
    "refactor": AgentType.REFACTORING,
    "debug": AgentType.DEBUGGING,
    "security": AgentType.SECURITY_AUDIT,
    "perf": AgentType.PERFORMANCE,
    "explore": AgentType.EXPLORE,
    "plan": AgentType.PLAN,

    # Full forms
    "general_purpose": AgentType.GENERAL_PURPOSE,
    "reviewer": AgentType.CODE_REVIEWER,
    "code_reviewer": AgentType.CODE_REVIEWER,
    "test_writer": AgentType.TEST_WRITER,
    "documentation": AgentType.DOCUMENTATION,
    "refactoring": AgentType.REFACTORING,
    "debugging": AgentType.DEBUGGING,
    "security_audit": AgentType.SECURITY_AUDIT,
    "performance": AgentType.PERFORMANCE,
}
```

### Command Handler
```python
# In ChatScreen

async def handle_slash_command(self, command: str) -> None:
    """Handle slash commands."""
    parts = command.split()
    cmd = parts[0].lower()
    args = [a.lower() for a in parts[1:]]

    # Agent switching
    if cmd == "/agent":
        await self.cmd_agent(args)

    elif cmd in [f"/{k}" for k in COMMAND_ALIASES.keys()]:
        # Extract agent type from command
        agent_name = cmd[1:]  # Remove leading slash
        await self.switch_agent(agent_name)

async def cmd_agent(self, args: list[str]) -> None:
    """Handle /agent command."""
    if not args:
        # Show agent list
        self.push_screen(AgentListScreen(
            on_select=self.switch_agent,
        ))
        return

    # Switch to specified agent
    await self.switch_agent(args[0])

async def switch_agent(self, agent_name: str) -> None:
    """Switch to a different agent type."""
    # Resolve alias
    agent_type = COMMAND_ALIASES.get(agent_name)

    if agent_type is None:
        # Unknown agent
        valid = ", ".join([f"/{k}" for k in COMMAND_ALIASES.keys()])
        self.notify(
            f"Unknown agent type: {agent_name}\n"
            f"Valid types: {valid}",
            severity="error",
            title="Invalid Agent",
        )
        return

    # Get current and new configs
    old_agent = self.app.agent.current_agent_type
    new_agent = agent_type

    if old_agent == new_agent:
        # Already in this mode
        self.notify(
            f"Already in {new_agent.display_name} mode",
            severity="warning",
        )
        return

    # Switch agent
    self.app.agent.set_agent_type(new_agent)

    # Update header
    self.app.update_header()

    # Add system message to chat
    history = self.query_one(ChatHistoryViewer)
    icon = new_agent.icon
    name = new_agent.display_name
    history.add_system_message(
        f"Switched to {icon} {name} agent"
    )

    # Show notification
    self.notify(f"Switched to {name} mode")
```

### AgentListScreen
```python
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual.containers import VerticalScroll

class AgentListScreen(Screen):
    """Screen for selecting agent type."""

    BINDINGS = [
        ("escape", "pop_screen", "Close"),
        ("q", "pop_screen", "Close"),
    ]

    def __init__(self, on_select: Callable[[str], Awaitable[None]]):
        super().__init__()
        self.on_select = on_select

    def compose(self) -> ComposeResult:
        yield Header()
        yield AgentListView(on_select=self.on_select)
        yield Footer()

class AgentListView(VerticalScroll):
    """List of available agent types."""

    def __init__(self, on_select: Callable[[str], Awaitable[None]]):
        super().__init__()
        self.on_select = on_select

    def render(self) -> RenderableType:
        """Render agent list."""
        text = Text()
        text.append("Available Agent Types\n\n", style="bold cyan")
        text.append("─" * 50, style="dim")
        text.append("\n\n")

        for agent_type, config in AGENT_CONFIGS.items():
            # Find the primary command for this agent
            primary_cmd = None
            for alias, at in COMMAND_ALIASES.items():
                if at == agent_type and len(alias) < 10:
                    # Prefer shorter commands
                    if primary_cmd is None or len(alias) < len(primary_cmd):
                        primary_cmd = alias

            icon = agent_type.icon
            name = config.name

            # Agent entry
            text.append(f"{icon} ", style="bold")
            text.append(f"{name}\n", style="bold cyan")
            text.append(f"  /{primary_cmd or 'agent'}\n", style="yellow")

            # Description (first sentence of system prompt)
            desc = config.system_prompt.split('.')[0] + '.'
            text.append(f"  {desc}\n\n", style="dim")

        text.append("Press ", style="dim")
        text.append("Esc", style="bold")
        text.append(" to close\n", style="dim")

        return text

    def on_key(self, event) -> None:
        """Handle keyboard input."""
        # Allow quick select with number keys
        if event.key.isdigit():
            idx = int(event.key) - 1
            agent_types = list(AGENT_CONFIGS.keys())
            if 0 <= idx < len(agent_types):
                agent_type = agent_types[idx]
                # Find command for this agent
                for alias, at in COMMAND_ALIASES.items():
                    if at == agent_type:
                        asyncio.create_task(self.on_select(alias))
                        return
```

### System Message Display
```python
# In ChatHistoryViewer

def add_system_message(self, content: str) -> None:
    """Add a system message (like agent switch)."""
    msg = MessageBox(
        content=f"ℹ️  {content}",
        role="system",
    )
    self.mount(msg)
    self.scroll_end()
```

### MessageBox Role Styling
```python
class MessageBox(Static):
    """Chat message with role-based styling."""

    def render(self) -> RenderableType:
        if self.role == "system":
            return Panel(
                Text(self.content, style="dim"),
                border_style="blue",
                style="dim",
            )
        # ... other roles
```

### Header Styling by Agent
```python
# In AgentApp

def update_header(self) -> None:
    """Update header based on current agent."""
    agent_type = self.agent.current_agent_type
    icon = agent_type.icon
    name = agent_type.display_name

    # Agent-specific colors
    AGENT_COLORS = {
        AgentType.GENERAL_PURPOSE: "white",
        AgentType.CODE_REVIEWER: "cyan",
        AgentType.TEST_WRITER: "green",
        AgentType.DOCUMENTATION: "blue",
        AgentType.REFACTORING: "yellow",
        AgentType.DEBUGGING: "red",
        AgentType.SECURITY_AUDIT: "magenta",
        AgentType.PERFORMANCE: "bright_yellow",
        AgentType.EXPLORE: "bright_cyan",
        AgentType.PLAN: "bright_blue",
    }

    color = AGENT_COLORS.get(agent_type, "white")
    self.sub_title = f"[{color}]{icon} {name}[/{color}]"
```

### Context Preservation on Switch
```python
async def switch_agent(self, agent_name: str) -> None:
    """Switch agent while preserving context."""
    # Store current context
    old_agent = self.app.agent.current_agent_type

    # Get agent summary before switching
    if old_agent != AgentType.GENERAL_PURPOSE:
        # Add context note about switch
        history = self.query_one(ChatHistoryViewer)
        history.add_system_message(
            f"Context note: Was using {old_agent.display_name}, "
            f"switching to {new_agent.display_name}"
        )

    # Switch agent
    self.app.agent.set_agent_type(new_agent)

    # Rest of switch logic...
```

### Switch Notification Widget
```python
class AgentSwitchNotification(Static):
    """Temporary notification for agent switch."""

    def __init__(self, agent_type: AgentType):
        super().__init__()
        self.agent_type = agent_type

    def render(self) -> RenderableType:
        icon = self.agent_type.icon
        name = self.agent_type.display_name
        return Text(
            f"{icon} Switched to {name}",
            style="bold cyan",
    )

# Show notification briefly
async def show_switch_notification(self, agent_type: AgentType):
    """Show brief notification."""
    notification = AgentSwitchNotification(agent_type)
    self.mount(notification)
    await asyncio.sleep(2)
    notification.remove()
```

## Dependencies
- Issue 29: Agent Type System

## Related Issues
- Issue 31: CLI Flags for Agent Mode

## Log
