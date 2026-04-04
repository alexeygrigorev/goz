# Issue 31: CLI Flags for Agent Mode

## Status
.todo

## Description
Add CLI flags for agent mode: --load, --agent, --session, and update help text.

## User Scenarios

### Scenario 1: Load Session from CLI
- User runs: `goz --load my-session`
- Agent mode starts
- Session "my-session" is loaded immediately
- Chat history is restored
- User can continue conversation

### Scenario 2: Start with Specific Agent
- User runs: `goz --agent reviewer`
- Agent mode starts
- Code Reviewer agent is active
- Header shows: "goz - [👁️ Code Reviewer]"
- System prompt is set accordingly

### Scenario 3: Combined Flags
- User runs: `goz --load my-session --agent test`
- Session is loaded
- Agent is set to Test Writer (overrides session's agent)
- User sees both applied

### Scenario 4: Show Sessions
- User runs: `goz --list-sessions`
- Lists all saved sessions
- Shows: name, updated time, message count
- Exits after listing

### Scenario 5: Delete Session from CLI
- User runs: `goz --delete-session old-session`
- Confirmation prompt
- User confirms
- Session is deleted
- Exits

### Scenario 6: Updated Help Text
- User runs: `goz --help`
- Help shows all commands
- Agent mode is listed as default behavior
- New flags are documented
- Examples are provided

## Acceptance Criteria

### New CLI Flags
1. `--load <name>` loads session on start
2. `--agent <type>` sets agent type on start
3. `--list-sessions` lists all sessions and exits
4. `--delete-session <name>` deletes session with confirmation
5. `--new-session` starts fresh without loading default

### Flag Behavior
6. `--load` loads session before starting TUI
7. `--agent` sets agent type before starting TUI
8. Flags can be combined
9. `--agent` overrides session's agent type
10. Invalid session name shows error and exits

### Help Text Updates
11. `goz --help` shows all new flags
12. Agent mode described as default behavior
13. Examples show common usage patterns
14. Agent types are documented
15. Session commands are documented

### Error Handling
16. Invalid agent type shows error
17. Non-existent session shows error
18. Permission errors handled
19. Clear error messages for all failures

### Exit Codes
20. Successful start = 0
21. Invalid flag = 1
22. Session not found = 2
23. Permission denied = 3

## Technical Details

### CLI Argument Updates
```python
# goz/__main__.py

def main() -> None:
    """Run the goz CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="goz",
        description="goz - Z.AI Interactive Coding Agent",
        epilog="With no command, launches the interactive agent mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Positional command (optional)
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to run (config, vision, search, read, repo, doctor)",
    )

    # Remaining arguments for command
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments for the command",
    )

    # Agent mode flags (only apply when no command)
    parser.add_argument(
        "--load",
        metavar="SESSION",
        help="Load session on startup",
    )
    parser.add_argument(
        "--agent",
        metavar="TYPE",
        choices=[
            "general", "review", "reviewer", "test", "test_writer",
            "docs", "documentation", "refactor", "refactoring",
            "debug", "debugging", "security", "perf", "performance",
            "explore", "plan",
        ],
        help="Start with specific agent type",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all saved sessions and exit",
    )
    parser.add_argument(
        "--delete-session",
        metavar="NAME",
        help="Delete a saved session",
    )
    parser.add_argument(
        "--new-session",
        action="store_true",
        help="Start fresh session (don't load auto-saved)",
    )

    # Existing flags
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Handle agent-only flags (require no command)
    if args.command is None:
        # Check for agent-only flags that should exit
        if args.list_sessions:
            run_list_sessions()
            return

        if args.delete_session:
            run_delete_session(args.delete_session)
            return

        # Launch agent mode
        run_agent_mode(
            session_id=args.load,
            agent_type=args.agent,
            new_session=args.new_session,
        )
        return

    # Dispatch to command handlers (existing)
    if args.command == "config":
        cmd_config(args.args)
    # ... etc
```

### run_agent_mode()
```python
def run_agent_mode(
    session_id: str | None = None,
    agent_type: str | None = None,
    new_session: bool = False,
) -> None:
    """Run the agent TUI application.

    Args:
        session_id: Session to load on startup
        agent_type: Agent type to use
        new_session: Don't load auto-saved session
    """
    from goz.agent.tui import run_agent_app

    try:
        run_agent_app(
            session_id=session_id,
            agent_type=agent_type,
            new_session=new_session,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

### run_list_sessions()
```python
def run_list_sessions() -> None:
    """List all sessions and exit."""
    import asyncio
    from goz.agent.sessions import SessionManager

    async def _list():
        manager = SessionManager()
        sessions = await manager.list_sessions()

        if not sessions:
            print("No saved sessions found.")
            return

        print("Saved Sessions:")
        print("─" * 50)

        for s in sessions:
            print(f"\n{cyan(s.id)}")
            print(f"  Updated: {s.updated_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Messages: {s.message_count}")
            print(f"  Agent: {s.agent_type}")
            print(f"  Directory: {s.working_directory}")

    from rich.console import Console
    from rich import print as rprint

    asyncio.run(_list())
```

### run_delete_session()
```python
def run_delete_session(session_id: str) -> None:
    """Delete a session with confirmation."""
    import asyncio
    from goz.agent.sessions import SessionManager

    async def _delete():
        manager = SessionManager()

        # Check session exists
        info = await manager.get_info(session_id)
        if info is None:
            print(f"Error: Session not found: {session_id}", file=sys.stderr)
            sys.exit(2)

        # Confirm
        response = input(f"Delete session '{session_id}'? [y/N]: ")
        if response.lower() != "y":
            print("Cancelled.")
            return

        # Delete
        deleted = await manager.delete(session_id)
        if deleted:
            print(f"Session deleted: {session_id}")
        else:
            print(f"Error: Failed to delete session", file=sys.stderr)
            sys.exit(1)

    asyncio.run(_delete())
```

### Updated Help Text
```
goz v0.1.0 - Z.AI Interactive Coding Agent

Usage: goz [COMMAND] [OPTIONS] [ARGS...]

With no command, launches the interactive agent mode.

Agent Mode Options:
  --load SESSION        Load session on startup
  --agent TYPE          Start with specific agent type:
                        general, review, test, docs, refactor,
                        debug, security, perf, explore, plan
  --list-sessions       List all saved sessions and exit
  --delete-session N    Delete a saved session
  --new-session         Start fresh (don't load auto-saved)

Commands:
  config                Manage configuration
  vision                Image and video analysis
  search                Real-time web search
  read                  Fetch and parse web pages
  repo                  GitHub repository exploration
  doctor                Environment + connectivity checks

Global Options:
  --version             Show version number
  --help, -h            Show this help message

Examples:
  goz                   Start interactive agent
  goz --agent review    Start as code reviewer
  goz --load my-work    Resume saved session
  goz vision analyze image.png
  goz search "python async"
  goz read https://example.com
```

### AgentApp Updates
```python
# goz/agent/tui/app.py

class AgentApp(App[None]):
    """Agent application with CLI flag support."""

    def __init__(
        self,
        session_id: str | None = None,
        agent_type: str | None = None,
        new_session: bool = False,
    ):
        super().__init__()
        self.session_manager = SessionManager()
        self.session_id = session_id
        self.initial_agent_type = agent_type
        self.new_session = new_session

        # Load config
        self.config = load_config()

        # Initialize agent
        self.agent = AgentCore(self.config)

    async def on_mount(self) -> None:
        """Initialize on mount."""
        # Set initial agent type
        if self.initial_agent_type:
            self.agent.set_agent_type(self.initial_agent_type)

        # Load session if specified
        if self.session_id and not self.new_session:
            try:
                await self.load_session(self.session_id)
            except FileNotFoundError:
                self.notify(f"Session not found: {self.session_id}", severity="error")
            except Exception as e:
                self.notify(f"Failed to load session: {e}", severity="error")
        elif not self.new_session:
            # Try to load default auto-saved session
            try:
                if self.session_manager.exists("default"):
                    await self.load_session("default")
            except Exception:
                pass  # Continue without session

        # Update header
        self.update_header()

        # Push chat screen
        self.push_screen("chat")
```

### run_agent_app() Entry Point
```python
# goz/agent/tui/__init__.py

def run_agent_app(
    session_id: str | None = None,
    agent_type: str | None = None,
    new_session: bool = False,
) -> None:
    """Run the agent TUI application.

    Args:
        session_id: Optional session ID to load
        agent_type: Optional agent type to start with
        new_session: Skip loading auto-saved session
    """
    app = AgentApp(
        session_id=session_id,
        agent_type=agent_type,
        new_session=new_session,
    )
    app.run()
```

### Error Handling
```python
import sys

def run_agent_mode(...) -> None:
    """Run agent mode with error handling."""
    try:
        run_agent_app(...)
    except FileNotFoundError as e:
        print(f"Session not found: {e}", file=sys.stderr)
        print("\nAvailable sessions:", file=sys.stderr)
        run_list_sessions()
        sys.exit(2)
    except ValueError as e:
        print(f"Invalid input: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
```

## Dependencies
- Issue 27: Session Persistence
- Issue 28: Session Commands
- Issue 29: Agent Type System

## Related Issues
- Issue 32: Error Handling + Edge Cases

## Log
