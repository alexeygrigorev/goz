# Issue 29: Agent Type System

## Status
.todo

## Description
Implement the specialized agent type system with unique system prompts for different coding tasks.

## User Scenarios

### Scenario 1: Switch to Code Reviewer
- User types: `/review`
- Agent switches to Code Reviewer mode
- Header shows: "goz - [Code Reviewer]"
- System prompt changes to code review persona
- User types: "Review main.py"
- Agent provides focused code review feedback

### Scenario 2: Switch to Test Writer
- User types: `/test`
- Agent switches to Test Writer mode
- Header shows: "goz - [Test Writer]"
- System prompt changes to test-focused persona
- User types: "Write tests for utils.py"
- Agent generates comprehensive tests

### Scenario 3: Switch to Debugger
- User types: `/debug`
- Agent switches to Debugger mode
- System prompt changes to debugging persona
- User types: "This test is failing, help me fix it"
- Agent systematically diagnoses the issue

### Scenario 4: List Agent Types
- User types: `/agent` with no argument
- List of all agent types appears
- Each with description
- User selects one
- Agent switches to selected type

### Scenario 5: CLI Flag
- User runs: `goz --agent reviewer`
- Agent starts in Code Reviewer mode
- Welcome message reflects agent type
- User can immediately use specialized features

### Scenario 6: Session Preserves Agent
- User saves session while in Debugger mode
- User quits
- User loads session
- Agent restores Debugger mode
- Header shows correct agent type

## Acceptance Criteria

### AgentType Enum
1. `AgentType` enum exists in `goz/agent/specialized.py`
2. Has 10 types: GENERAL_PURPOSE, CODE_REVIEWER, TEST_WRITER, DOCUMENTATION, REFACTORING, DEBUGGING, SECURITY_AUDIT, PERFORMANCE, EXPLORE, PLAN
3. Each has string value for display

### AgentConfig Dataclass
4. `AgentConfig` dataclass exists
5. Has fields: type, name, system_prompt, temperature
6. All 10 agents have configs defined
7. System prompts are detailed and specific

### Agent Core Integration
8. `AgentCore` has `current_agent_type` property
9. `AgentCore.set_agent_type()` method works
10. `AgentCore.get_system_prompt()` returns current agent's prompt
11. Chat requests include system prompt

### Commands
12. `/agent` with no args lists agent types
13. `/agent <type>` switches to that agent
14. `/general` switches to general purpose
15. `/review` switches to code reviewer
16. `/test` switches to test writer
17. `/docs` switches to documentation
18. `/refactor` switches to refactoring
19. `/debug` switches to debugging
20. `/security` switches to security audit
21. `/perf` switches to performance
22. `/explore` switches to explore
23. `/plan` switches to plan

### UI Updates
24. Header shows current agent type
25. Header updates when agent switches
26. Agent type shown in brackets
27. Welcome message reflects agent type

### Session Integration
28. Session saves agent type
29. Session loads restore agent type
30. Agent type shown in session info

## Technical Details

### File Structure
```
goz/agent/
└── specialized.py    # AgentType, AgentConfig, AGENT_CONFIGS
```

### AgentType Enum
```python
from enum import Enum

class AgentType(Enum):
    """Specialized agent types."""

    GENERAL_PURPOSE = "general"
    CODE_REVIEWER = "reviewer"
    TEST_WRITER = "test_writer"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    SECURITY_AUDIT = "security"
    PERFORMANCE = "performance"
    EXPLORE = "explore"
    PLAN = "plan"

    @property
    def display_name(self) -> str:
        """Get display name for this agent type."""
        return DISPLAY_NAMES.get(self, self.value)

    @property
    def icon(self) -> str:
        """Get icon for this agent type."""
        return ICONS.get(self, "🤖")

DISPLAY_NAMES = {
    AgentType.GENERAL_PURPOSE: "General Purpose",
    AgentType.CODE_REVIEWER: "Code Reviewer",
    AgentType.TEST_WRITER: "Test Writer",
    AgentType.DOCUMENTATION: "Documentation",
    AgentType.REFACTORING: "Refactoring",
    AgentType.DEBUGGING: "Debugger",
    AgentType.SECURITY_AUDIT: "Security",
    AgentType.PERFORMANCE: "Performance",
    AgentType.EXPLORE: "Explore",
    AgentType.PLAN: "Plan",
}

ICONS = {
    AgentType.GENERAL_PURPOSE: "🤖",
    AgentType.CODE_REVIEWER: "👁️",
    AgentType.TEST_WRITER: "🧪",
    AgentType.DOCUMENTATION: "📚",
    AgentType.REFACTORING: "🔨",
    AgentType.DEBUGGING: "🐛",
    AgentType.SECURITY_AUDIT: "🔒",
    AgentType.PERFORMANCE: "⚡",
    AgentType.EXPLORE: "🔍",
    AgentType.PLAN: "📋",
}
```

### AgentConfig
```python
from dataclasses import dataclass

@dataclass
class AgentConfig:
    """Configuration for a specialized agent."""

    type: AgentType
    name: str
    system_prompt: str
    temperature: float = 0.7
```

### Agent Configurations
```python
AGENT_CONFIGS: dict[AgentType, AgentConfig] = {
    AgentType.GENERAL_PURPOSE: AgentConfig(
        type=AgentType.GENERAL_PURPOSE,
        name="General Purpose",
        system_prompt="""You are a helpful AI coding assistant named goz.

You can help with:
- Reading and analyzing code
- Writing and modifying code
- Running terminal commands
- Searching for information
- Debugging and fixing issues

Be direct and practical. Focus on solving the user's problem.""",
        temperature=0.7,
    ),

    AgentType.CODE_REVIEWER: AgentConfig(
        type=AgentType.CODE_REVIEWER,
        name="Code Reviewer",
        system_prompt="""You are an expert code reviewer.

Your role is to:
- Analyze code for quality and best practices
- Identify potential bugs and edge cases
- Suggest improvements for readability
- Check for security vulnerabilities
- Verify proper error handling

Be constructive and specific. Point out both strengths and areas for improvement.""",
        temperature=0.6,
    ),

    AgentType.TEST_WRITER: AgentConfig(
        type=AgentType.TEST_WRITER,
        name="Test Writer",
        system_prompt="""You are a test-focused developer.

Your role is to:
- Write comprehensive unit tests
- Cover edge cases and error conditions
- Use appropriate testing frameworks
- Ensure tests are readable and maintainable
- Follow test-driven development principles

Write tests that are thorough, clear, and well-organized.""",
        temperature=0.5,
    ),

    AgentType.DOCUMENTATION: AgentConfig(
        type=AgentType.DOCUMENTATION,
        name="Documentation",
        system_prompt="""You are a technical documentation specialist.

Your role is to:
- Write clear and concise documentation
- Create README files and guides
- Document APIs and functions
- Explain complex concepts simply
- Structure information logically

Focus on clarity, completeness, and user experience.""",
        temperature=0.6,
    ),

    AgentType.REFACTORING: AgentConfig(
        type=AgentType.REFACTORING,
        name="Refactoring",
        system_prompt="""You are a code refactoring expert.

Your role is to:
- Improve code structure and organization
- Reduce duplication and complexity
- Apply design patterns appropriately
- Maintain existing functionality
- Explain refactoring decisions

Focus on making code cleaner, more maintainable, and more efficient.""",
        temperature=0.6,
    ),

    AgentType.DEBUGGING: AgentConfig(
        type=AgentType.DEBUGGING,
        name="Debugger",
        system_prompt="""You are a debugging specialist.

Your role is to:
- Systematically diagnose issues
- Identify root causes
- Propose and verify fixes
- Explain debugging steps
- Prevent similar issues

Be methodical. Gather information, form hypotheses, test, and verify.""",
        temperature=0.5,
    ),

    AgentType.SECURITY_AUDIT: AgentConfig(
        type=AgentType.SECURITY_AUDIT,
        name="Security",
        system_prompt="""You are a security specialist.

Your role is to:
- Identify security vulnerabilities
- Check for common attack vectors
- Verify secure coding practices
- Suggest security improvements
- Explain security implications

Focus on: injection, XSS, authentication, authorization, data exposure.""",
        temperature=0.5,
    ),

    AgentType.PERFORMANCE: AgentConfig(
        type=AgentType.PERFORMANCE,
        name="Performance",
        system_prompt="""You are a performance optimization expert.

Your role is to:
- Identify performance bottlenecks
- Suggest optimization strategies
- Analyze algorithmic complexity
- Recommend caching and data structure improvements
- Measure and profile performance

Focus on measurable improvements and practical optimizations.""",
        temperature=0.6,
    ),

    AgentType.EXPLORE: AgentConfig(
        type=AgentType.EXPLORE,
        name="Explore",
        system_prompt="""You are a codebase exploration expert.

Your role is to:
- Understand code structure quickly
- Identify key components and patterns
- Explain architecture and design
- Find specific code locations
- Summarize functionality

Be concise but thorough. Help the user navigate unfamiliar code.""",
        temperature=0.7,
    ),

    AgentType.PLAN: AgentConfig(
        type=AgentType.PLAN,
        name="Plan",
        system_prompt="""You are a technical planning specialist.

Your role is to:
- Break down complex tasks
- Create implementation plans
- Identify dependencies and risks
- Estimate effort and complexity
- Suggest appropriate approaches

Focus on clear, actionable plans with specific steps.""",
        temperature=0.6,
    ),
}

# Command aliases
COMMAND_ALIASES: dict[str, AgentType] = {
    "general": AgentType.GENERAL_PURPOSE,
    "review": AgentType.CODE_REVIEWER,
    "reviewer": AgentType.CODE_REVIEWER,
    "test": AgentType.TEST_WRITER,
    "writer": AgentType.TEST_WRITER,
    "docs": AgentType.DOCUMENTATION,
    "documentation": AgentType.DOCUMENTATION,
    "refactor": AgentType.REFACTORING,
    "refactoring": AgentType.REFACTORING,
    "debug": AgentType.DEBUGGING,
    "debugging": AgentType.DEBUGGING,
    "security": AgentType.SECURITY_AUDIT,
    "perf": AgentType.PERFORMANCE,
    "performance": AgentType.PERFORMANCE,
    "explore": AgentType.EXPLORE,
    "plan": AgentType.PLAN,
}
```

### AgentCore Integration
```python
class AgentCore:
    """Agent core with specialized agent support."""

    def __init__(self, config: Config):
        self.config = config
        self.current_agent_type = AgentType.GENERAL_PURPOSE

    def set_agent_type(self, agent_type: AgentType | str) -> None:
        """Set the current agent type."""
        if isinstance(agent_type, str):
            agent_type = COMMAND_ALIASES.get(agent_type, AgentType.GENERAL_PURPOSE)
        self.current_agent_type = agent_type

    def get_system_prompt(self) -> str:
        """Get the system prompt for current agent type."""
        config = AGENT_CONFIGS.get(self.current_agent_type)
        return config.system_prompt if config else ""

    def get_temperature(self) -> float:
        """Get the temperature for current agent type."""
        config = AGENT_CONFIGS.get(self.current_agent_type)
        return config.temperature if config else self.config.temperature
```

### Chat Integration
```python
async def chat_completion(self, messages: list[dict], **kwargs) -> AsyncIterator:
    """Make chat completion with system prompt."""
    # Add system message as first message
    system_prompt = self.get_system_prompt()

    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(messages)

    # Use agent-specific temperature
    temperature = kwargs.get("temperature", self.get_temperature())

    return await self.api.chat_completion(
        messages=api_messages,
        temperature=temperature,
        **kwargs,
    )
```

### Command Handler
```python
async def handle_slash_command(self, command: str) -> None:
    """Handle slash commands."""
    parts = command.split()
    cmd = parts[0]
    args = parts[1:]

    # Agent switching commands
    if cmd in ("/agent",):
        if not args:
            await self.show_agent_list()
        else:
            await self.switch_agent(args[0])

    elif cmd in COMMAND_ALIASES:
        await self.switch_agent(cmd)
```

### Agent List Screen
```python
class AgentListScreen(Screen):
    """Screen for selecting agent type."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield AgentListView()
        yield Footer()

class AgentListView(Static):
    """List of available agent types."""

    def render(self) -> RenderableType:
        text = Text()
        text.append("Available Agent Types\n\n", style="bold")

        for agent_type, config in AGENT_CONFIGS.items():
            icon = agent_type.icon
            name = config.name
            cmd = COMMAND_ALIASES.inv.get(agent_type, [""])[0]

            text.append(f"{icon} ", style="bold")
            text.append(f"{name}", style="cyan")
            text.append(f"  /{cmd}\n", style="dim")
            text.append(f"    {config.system_prompt.split('.')[0]}.\n\n", style="dim")

        return text
```

### Header Update
```python
# In AgentApp
def update_header(self) -> None:
    """Update header with current agent info."""
    agent_type = self.agent.current_agent_type
    icon = agent_type.icon
    name = agent_type.display_name

    self.sub_title = f"[{icon} {name}]"
```

## Dependencies
- Issue 15: Agent Core
- Issue 26: TUI-Agent Integration

## Related Issues
- Issue 30: Agent Switching Commands

## Log
