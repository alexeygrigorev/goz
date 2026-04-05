"""Main entry point for the goz CLI."""

import asyncio
import json
import itertools
import sys
import threading
import time
from pathlib import Path

from goz import __version__


def _show_thinking_animation(stop_event: threading.Event) -> None:
    """Show a "thinking" animation in a separate thread.

    Args:
        stop_event: Threading event to stop the animation
    """
    animation = ["|", "/", "-", "\\"]
    try:
        for frame in itertools.cycle(animation):
            if stop_event.is_set():
                break
            # Print the animation frame with carriage return to overwrite
            print(f"\r{frame} Thinking...", end="", flush=True)
            time.sleep(0.1)
    finally:
        # Clear the animation line when done
        print("\r" + " " * 20 + "\r", end="", flush=True)


def _print_json(data: object) -> None:
    """Print JSON with stable formatting."""
    print(json.dumps(data, indent=2, ensure_ascii=True))


def _load_json_value(raw_value: str) -> object:
    """Load JSON from an inline value or @file reference."""
    source = raw_value
    if raw_value.startswith("@"):
        source = Path(raw_value[1:]).read_text()

    try:
        return json.loads(source)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def _load_call_arguments(json_arg: str | None, use_stdin: bool) -> dict:
    """Resolve call arguments from --json or --stdin."""
    if json_arg is not None and use_stdin:
        raise ValueError("Use either --json or --stdin, not both")

    if json_arg is None and not use_stdin:
        return {}

    payload = _load_json_value(sys.stdin.read() if use_stdin else json_arg or "{}")
    if not isinstance(payload, dict):
        raise ValueError("Tool arguments must be a JSON object")
    return payload


async def cmd_vision(args: list[str]) -> None:
    """Handle the `goz vision` command.

    Usage:
        goz vision <image> [prompt]           - Analyze image (default)
        goz vision analyze <image> [prompt]   - General analysis
        goz vision ui-to-code <image>         - Convert UI to code
        goz vision extract-text <image>       - OCR text extraction
        goz vision diagnose-error <image>     - Diagnose error screenshot
        goz vision diagram <image>            - Explain diagram
        goz vision chart <image>              - Analyze chart
        goz vision diff <expected> <actual>   - Compare images
        goz vision video <video> [prompt]     - Analyze video

    Options:
        --no-stream     - Disable streaming (wait for full response)
        --output <type> - Output type for ui-to-code (code, prompt, spec, description)
        --language <lang> - Programming language for extract-text
        --context <ctx> - Error context for diagnose-error
        --type <type>   - Diagram type
        --focus <focus> - Chart focus (trends, anomalies, comparisons, insights)

    Args:
        args: Command arguments
    """

    # Check for help flag
    if not args or args[0] in ("--help", "-h", "help"):
        print("""Vision command usage:

  goz vision <image> [prompt]           - Analyze image (default)
  goz vision analyze <image> [prompt]   - General image analysis
  goz vision ui-to-code <image>         - Convert UI to code
  goz vision extract-text <image>       - Extract text (OCR)
  goz vision diagnose-error <image>     - Diagnose error screenshot
  goz vision diagram <image>            - Explain technical diagram
  goz vision chart <image>              - Analyze data visualization
  goz vision diff <expected> <actual>   - Compare two screenshots
  goz vision video <video> [prompt]     - Analyze video content

Options:
  --no-stream           - Disable streaming output
  --output <type>       - ui-to-code output (code, prompt, spec, description)
  --language <lang>     - Programming language for extract-text
  --context <ctx>       - Error context for diagnose-error
  --type <type>         - Diagram type (flowchart, sequence, architecture, etc.)
  --focus <focus>       - Chart focus (trends, anomalies, comparisons, insights)

File constraints:
  Images: 5MB max (JPG, PNG, JPEG)
  Videos: 8MB max (MP4, MOV, M4V)
""")
        return

    from goz.api.vision import VisionClient
    from goz.config import load_config

    config = load_config()
    client = VisionClient(config=config)

    # Parse flags and positional args
    flags = {}
    positional = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg[2:]
            # Check if next arg is a value (not a flag)
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                flags[key] = args[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        elif arg.startswith("-") and len(arg) == 2:
            key = arg[1:]
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                flags[key] = args[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        else:
            positional.append(arg)
            i += 1

    # Determine mode and source
    mode = "analyze"  # Default mode
    source1 = None
    source2 = None
    prompt = None

    # Check if first positional arg is a known subcommand
    known_modes = {
        "analyze",
        "ui-to-code",
        "extract-text",
        "diagnose-error",
        "diagram",
        "chart",
        "diff",
        "video",
    }

    if positional[0] in known_modes:
        mode = positional[0]
        source1 = positional[1] if len(positional) > 1 else None

        if mode == "diff":
            source2 = positional[2] if len(positional) > 2 else None
            prompt = positional[3] if len(positional) > 3 else None
        else:
            prompt = positional[2] if len(positional) > 2 else None
    else:
        # Old behavior: first arg is source
        source1 = positional[0]
        prompt = positional[1] if len(positional) > 1 else None

    # Validate we have a source
    if not source1:
        print("Error: Missing image/video source", file=sys.stderr)
        print("Run 'goz vision --help' for usage", file=sys.stderr)
        sys.exit(1)

    if mode == "diff" and not source2:
        print("Error: diff mode requires two sources: <expected> <actual>", file=sys.stderr)
        sys.exit(1)

    # Build prompt based on mode
    default_prompts = {
        "analyze": "Describe this image in detail.",
        "ui-to-code": "Convert this UI to production-ready code.",
        "extract-text": "Extract all text from this image.",
        "diagnose-error": "Diagnose this error and suggest fixes.",
        "diagram": "Explain this technical diagram.",
        "chart": "Analyze this data visualization.",
        "video": "Analyze this video content.",
    }

    effective_prompt = prompt or default_prompts.get(mode, "Describe this image.")

    # Enhance prompt with mode-specific options
    output_type = flags.get("output", "code")

    if mode == "ui-to-code" and output_type != "code":
        if output_type == "prompt":
            effective_prompt = (
                f"{effective_prompt}\n\n"
                f"Provide a detailed prompt that would generate this UI, "
                f"including layout, components, styling, and functionality."
            )
        elif output_type == "spec":
            effective_prompt = (
                f"{effective_prompt}\n\n"
                f"Provide a technical specification including components, "
                f"props, state management, and styling approach."
            )
        elif output_type == "description":
            effective_prompt = (
                f"{effective_prompt}\n\n"
                f"Provide a detailed description of the UI layout, "
                f"components, colors, and interactions without generating code."
            )

    if mode == "extract-text" and flags.get("language"):
        effective_prompt = (
            f"{effective_prompt}\n\n"
            f"The content is in {flags['language']}. Preserve code syntax and formatting."
        )

    if mode == "diagnose-error" and flags.get("context"):
        effective_prompt = (
            f"{effective_prompt}\n\n"
            f"Context: {flags['context']}\n\n"
            f"Consider this context when diagnosing the error."
        )

    if mode == "diagram" and flags.get("type"):
        effective_prompt = (
            f"{effective_prompt}\n\nThis is a {flags['type']} diagram. Use appropriate terminology."
        )

    if mode == "chart" and flags.get("focus"):
        focus_prompts = {
            "trends": "Focus on identifying trends and patterns over time.",
            "anomalies": "Focus on identifying anomalies, outliers, and unusual data points.",
            "comparisons": "Focus on comparing different data series and values.",
            "insights": "Focus on extracting key insights and actionable conclusions.",
        }
        focus_prompt = focus_prompts.get(flags["focus"], "")
        if focus_prompt:
            effective_prompt = f"{effective_prompt}\n\n{focus_prompt}"

    # Determine if streaming
    no_stream = flags.get("no-stream", False)

    try:
        if mode == "diff":
            # For diff, analyze both images and compare
            if no_stream:
                result1 = await client.analyze(source1, "Describe this image in detail.")
                result2 = await client.analyze(source2, "Describe this image in detail.")
                print(f"Expected Image:\n{result1}\n\n")
                print(f"Actual Image:\n{result2}\n\n")
                print("Note: Use the vision diff command for precise visual comparison.")
            else:
                print("Analyzing expected image...", file=sys.stderr)
                async for chunk in client.analyze_stream(source1, "Describe this image in detail."):
                    print(chunk, end="", flush=True)
                print("\n\nAnalyzing actual image...", file=sys.stderr)
                async for chunk in client.analyze_stream(source2, "Describe this image in detail."):
                    print(chunk, end="", flush=True)
                print("\n\nNote: Use the vision diff command for precise visual comparison.")
        else:
            if no_stream:
                result = await client.analyze(source1, effective_prompt)
                print(result)
            else:
                # Show "thinking" animation while waiting for first chunk
                import threading

                stop_animation = threading.Event()
                animation_thread = threading.Thread(
                    target=_show_thinking_animation, args=(stop_animation,), daemon=True
                )
                animation_thread.start()

                # Stream response
                first_chunk = True
                async for chunk in client.analyze_stream(source1, effective_prompt):
                    if first_chunk:
                        # Stop animation on first chunk
                        stop_animation.set()
                        animation_thread.join(timeout=0.2)
                        first_chunk = False
                    print(chunk, end="", flush=True)
                print()  # New line after streaming completes
                if first_chunk:
                    # In case no chunks were received
                    stop_animation.set()
                    animation_thread.join(timeout=0.2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_search(args: list[str]) -> None:
    """Handle the `goz search` command.

    Usage:
        goz search <query> [options]

    Options:
        --count, -c N       - Number of results (default: 10)
        --domain, -d DOMAIN - Filter to domain
        --recency, -r R     - Time filter (oneDay, oneWeek, oneMonth, oneYear, noLimit)

    Args:
        args: Command arguments
    """
    import argparse

    # Check for help
    if not args or args[0] in ("--help", "-h", "help"):
        print("""Search command usage:

  goz search <query> [options]

Options:
  --count, -c N         Number of results to return (default: 10)
  --domain, -d DOMAIN   Filter results to specific domain
  --recency, -r R       Time filter:
                        - oneDay: Results from last 24 hours
                        - oneWeek: Results from last week
                        - oneMonth: Results from last month
                        - oneYear: Results from last year
                        - noLimit: No time restriction

Examples:
  goz search "python async await"
  goz search "climate change" --count 5
  goz search "AI news" --domain news.ycombinator.com --recency oneWeek
""")
        return

    parser = argparse.ArgumentParser(prog="goz search", add_help=False)
    parser.add_argument("query", help="Search query")
    parser.add_argument("--count", "-c", type=int, help="Number of results")
    parser.add_argument("--domain", "-d", help="Filter to domain")
    parser.add_argument(
        "--recency",
        "-r",
        choices=["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"],
        help="Time filter",
    )

    parsed = parser.parse_args(args)

    from goz.api.search import SearchClient
    from goz.config import load_config

    config = load_config()
    client = SearchClient(config=config)

    try:
        results = await client.search(
            query=parsed.query,
            count=parsed.count,
            domain_filter=parsed.domain,
            recency_filter=parsed.recency,
        )
        for r in results:
            print(f"{r.rank}. {r.title}")
            print(f"   {r.url}")
            if r.summary:
                print(f"   {r.summary[:100]}...")
            print()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_read(args: list[str]) -> None:
    """Handle the `goz read` command.

    Usage:
        goz read <url> [options]

    Options:
        --format, -f FMT  - Output format (markdown, text)
        --timeout, -t N   - Timeout in seconds (default: 20)

    Args:
        args: Command arguments
    """
    import argparse

    # Check for help
    if not args or args[0] in ("--help", "-h", "help"):
        print("""Read command usage:

  goz read <url> [options]

Options:
  --format, -f FMT    Output format:
                      - markdown: GitHub Flavored Markdown (default)
                      - text: Plain text
  --timeout, -t N     Request timeout in seconds (default: 20)

Examples:
  goz read https://example.com
  goz read https://example.com --format text
  goz read https://example.com --timeout 30
""")
        return

    parser = argparse.ArgumentParser(prog="goz read", add_help=False)
    parser.add_argument("url", help="URL to read")
    parser.add_argument(
        "--format", "-f", choices=["markdown", "text"], default="markdown", help="Output format"
    )
    parser.add_argument("--timeout", "-t", type=int, help="Timeout in seconds")

    parsed = parser.parse_args(args)

    from goz.api.reader import ReaderClient
    from goz.config import load_config

    config = load_config()
    client = ReaderClient(config=config)

    try:
        result = await client.read(
            url=parsed.url,
            format=parsed.format,
            timeout=parsed.timeout,
        )
        print(result.content)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_repo(args: list[str]) -> None:
    """Handle the `goz repo` command.

    Usage:
        goz repo search <owner/repo> <query>
        goz repo tree <owner/repo>
        goz repo read <owner/repo> <file_path>

    Args:
        args: Command arguments
    """
    # Check for help or no args
    if not args or args[0] in ("--help", "-h", "help"):
        print("""Repo command usage:

  goz repo search <owner/repo> <query>   Search docs and code in repository
  goz repo tree <owner/repo>             Get repository directory structure
  goz repo read <owner/repo> <path>      Read a file from repository

Search Options:
  --language <lang>   Result language: en (default) or zh

Tree Options:
  --path <path>       Directory path to inspect (default: repo root)
  --depth <n>         Expand subdirectory trees (default: 1)

Examples:
  goz repo search facebook/react "server components"
  goz repo search vercel/next.js "app router" --language en
  goz repo tree vercel/next.js
  goz repo tree vercel/next.js --path packages --depth 2
  goz repo read anthropics/anthropic-sdk-python README.md

Notes:
  - Repository must be public
  - Use "owner/repo" format (e.g., "facebook/react")
  - Paths are relative to repository root
""")
        return

    subcommand = args[0]

    if subcommand == "search":
        # goz repo search <owner/repo> <query> [--language <lang>]
        if len(args) < 3:
            print("Error: repo search requires <owner/repo> and <query>", file=sys.stderr)
            print(
                "Usage: goz repo search <owner/repo> <query> [--language <lang>]", file=sys.stderr
            )
            sys.exit(1)

        repo = args[1]
        query = args[2]
        language = None

        # Parse optional args
        i = 3
        while i < len(args):
            if args[i] == "--language" and i + 1 < len(args):
                language = args[i + 1]
                i += 2
            else:
                i += 1

        from goz.api.repo import RepoClient
        from goz.config import load_config

        config = load_config()
        client = RepoClient(config=config)

        try:
            results = await client.search(repo, query, language)
            for r in results:
                if r.title:
                    print(f"# {r.title}")
                print(r.content)
                if r.url:
                    print(f"URL: {r.url}")
                print()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "tree":
        # goz repo tree <owner/repo> [--path <path>] [--depth <n>]
        if len(args) < 2:
            print("Error: repo tree requires <owner/repo>", file=sys.stderr)
            print(
                "Usage: goz repo tree <owner/repo> [--path <path>] [--depth <n>]", file=sys.stderr
            )
            sys.exit(1)

        repo = args[1]
        path = None
        depth = 1

        # Parse optional args
        i = 2
        while i < len(args):
            if args[i] == "--path" and i + 1 < len(args):
                path = args[i + 1]
                i += 2
            elif args[i] == "--depth" and i + 1 < len(args):
                try:
                    depth = int(args[i + 1])
                except ValueError:
                    print(f"Error: depth must be an integer, got '{args[i + 1]}'", file=sys.stderr)
                    sys.exit(1)
                i += 2
            else:
                i += 1

        from goz.api.repo import RepoClient
        from goz.config import load_config

        config = load_config()
        client = RepoClient(config=config)

        try:
            result = await client.tree(repo, path, depth)
            print(result)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "read":
        # goz repo read <owner/repo> <file_path>
        if len(args) < 3:
            print("Error: repo read requires <owner/repo> and <file_path>", file=sys.stderr)
            print("Usage: goz repo read <owner/repo> <file_path>", file=sys.stderr)
            sys.exit(1)

        repo = args[1]
        file_path = args[2]

        from goz.api.repo import RepoClient
        from goz.config import load_config

        config = load_config()
        client = RepoClient(config=config)

        try:
            result = await client.read(repo, file_path)
            print(result)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Error: Unknown repo subcommand '{subcommand}'", file=sys.stderr)
        print("Run 'goz repo --help' for usage", file=sys.stderr)
        sys.exit(1)


async def cmd_tools(args: list[str]) -> None:
    """Handle the `goz tools` command."""
    import argparse

    if args and args[0] in ("--help", "-h", "help"):
        print("""Tools command usage:

  goz tools [options]

Options:
  --filter TEXT   Filter tool names by substring
  --full          Show full tool schemas as JSON
""")
        return

    parser = argparse.ArgumentParser(prog="goz tools", add_help=False)
    parser.add_argument("--filter", dest="name_filter", help="Filter tool names by substring")
    parser.add_argument("--full", action="store_true", help="Show full tool schemas")
    parsed = parser.parse_args(args)

    from goz.api.mcp import McpClient

    client = McpClient()
    try:
        tools = await client.list_tools()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if parsed.name_filter:
        query = parsed.name_filter.lower()
        tools = [tool for tool in tools if query in str(tool.get("name", "")).lower()]

    if parsed.full:
        _print_json(tools)
        return

    for tool in tools:
        name = tool.get("name")
        if name:
            print(name)


async def cmd_tool(args: list[str]) -> None:
    """Handle the `goz tool <name>` command."""
    if not args or args[0] in ("--help", "-h", "help"):
        print("""Tool command usage:

  goz tool <name>
""")
        return

    from goz.api.mcp import McpClient

    client = McpClient()
    try:
        tool = await client.get_tool(args[0])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if tool is None:
        print(f"Error: Unknown tool '{args[0]}'", file=sys.stderr)
        sys.exit(1)

    _print_json(tool)


async def cmd_call(args: list[str]) -> None:
    """Handle the `goz call <tool>` command."""
    import argparse

    if not args or args[0] in ("--help", "-h", "help"):
        print("""Call command usage:

  goz call <tool> [--json JSON|@file.json] [--stdin] [--dry-run]

Options:
  --json VALUE    Inline JSON object or @path/to/file.json
  --stdin         Read JSON object from stdin
  --dry-run       Print resolved request payload without calling the tool
""")
        return

    parser = argparse.ArgumentParser(prog="goz call", add_help=False)
    parser.add_argument("tool", help="Tool name to call")
    parser.add_argument("--json", dest="json_payload", help="Inline JSON or @file reference")
    parser.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview the request without calling"
    )
    parsed = parser.parse_args(args)

    try:
        arguments = _load_call_arguments(parsed.json_payload, parsed.stdin)
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    request_payload = {
        "name": parsed.tool,
        "arguments": arguments,
    }
    if parsed.dry_run:
        _print_json(request_payload)
        return

    from goz.api.mcp import McpClient

    client = McpClient()
    try:
        result = await client.call_tool(parsed.tool, arguments)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    _print_json(result)


async def cmd_run(args: list[str]) -> None:
    """Handle the `goz run` command."""
    from goz.cli.run import cmd_run as run_cmd

    await run_cmd(args)


def cmd_config(args: list[str]) -> None:
    """Handle the `goz config` command.

    Usage:
        goz config                - Show current config
        goz config get <key>      - Get a single value
        goz config set <key> <val> - Set a value
        goz config list           - List all keys
        goz config edit           - Open in editor

    Args:
        args: Remaining arguments after 'config'
    """
    from goz.config import ConfigManager

    manager = ConfigManager()

    # No subcommand = show current config
    if not args:
        manager.show_config()
        return

    subcommand = args[0]

    if subcommand == "get" and len(args) >= 2:
        key = args[1]
        try:
            manager.get_config(key)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "set" and len(args) >= 2:
        key = args[1]
        value = args[2] if len(args) > 2 else ""
        try:
            manager.set_config(key, value)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand == "list":
        manager.list_keys()

    elif subcommand == "edit":
        try:
            manager.edit_config()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif subcommand in ("--help", "-h", "help"):
        print("""Config command usage:

  goz config                Show current configuration
  goz config get <key>      Get a single configuration value
  goz config set <key> <val> Set a configuration value
  goz config list           List all available keys with descriptions
  goz config edit           Open config file in $EDITOR

Keys:
  zai_token     - Z.AI API authentication token (required)
  zai_base_url  - Base URL for Z.AI API
  timeout       - Request timeout in seconds
  vision_model  - Model for image/video analysis
  chat_model    - Model for chat requests
  temperature   - Generation temperature
  top_p         - Generation top_p sampling
  max_tokens    - Maximum response tokens
""")

    else:
        # Treat as show current config (for backwards compatibility)
        manager.show_config()


def cmd_doctor(args: list[str]) -> None:
    """Handle the `goz doctor` command.

    Usage:
        goz doctor

    Runs environment and connectivity checks.

    Args:
        args: Remaining arguments
    """
    import asyncio

    # Check for help
    if args and args[0] in ("--help", "-h", "help"):
        print("""Doctor command usage:

  goz doctor

Runs diagnostic checks:
  - Config file exists
  - API token is set
  - API endpoint is reachable
""")
        return

    async def run_doctor() -> None:
        from goz.config import load_config, DEFAULT_CONFIG_FILE

        checks_passed = 0
        checks_failed = 0

        # Check 1: Config file
        print("Checking configuration...")
        if DEFAULT_CONFIG_FILE.exists():
            print(f"  [PASS] Config file found at {DEFAULT_CONFIG_FILE}")
            checks_passed += 1
        else:
            print(f"  [FAIL] Config file not found at {DEFAULT_CONFIG_FILE}")
            print("         Run 'goz config' to set up.")
            checks_failed += 1

        # Check 2: Load config and validate token
        try:
            config = load_config()
            if config.zai_token:
                masked = f"****{config.zai_token[-4:]}" if len(config.zai_token) > 4 else "****"
                print(f"  [PASS] API token present ({masked})")
                checks_passed += 1
            else:
                print("  [FAIL] API token not set")
                checks_failed += 1
        except Exception as e:
            print(f"  [FAIL] Error loading config: {e}")
            checks_failed += 1
            return

        # Check 3: API connectivity
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.get(config.zai_base_url)
                print(f"  [PASS] Base URL reachable ({config.zai_base_url})")
                checks_passed += 1
        except (httpx.ConnectError, httpx.NetworkError) as e:
            print(f"  [FAIL] Cannot connect to API: {e}")
            checks_failed += 1
        except Exception as e:
            print(f"  [WARN] Could not test connectivity: {e}")

        # Summary
        print()
        if checks_failed == 0:
            print(f"All checks passed! ({checks_passed}/{checks_passed})")
        else:
            print(f"Some checks failed: {checks_failed} failed, {checks_passed} passed")

    asyncio.run(run_doctor())


def cmd_tui(args: list[str]) -> None:
    """Launch the TUI.

    Args:
        args: Remaining arguments (ignored)
    """
    from goz.tui import run_tui

    run_tui()


def main() -> None:
    """Run the goz CLI.

    This is the entry point for the `goz` command.
    """
    import argparse

    # Check for --help before argparse to handle it properly
    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"""goz v{__version__} - Z.AI Tools

Usage: goz <command> [args] [options]

Commands:
  run       One-shot agent run with JSONL output
  vision    Image and video analysis
  search    Real-time web search
  read      Fetch and parse web pages
  repo      GitHub repository exploration
  tools     List MCP tools
  tool      Show one MCP tool schema
  call      Call an MCP tool directly
  config    Manage configuration
  doctor    Environment + connectivity checks
  usage     Show token usage and quota
  models    List available models with pricing
  tui       Launch interactive terminal UI

Global Options:
  --help, -h     Show this help message
  --version, -v  Show version number

For command-specific help:
  goz vision --help
  goz run --help
  goz search --help
  goz read --help
  goz repo --help
  goz tools --help
  goz tool --help
  goz call --help
  goz config --help
  goz doctor --help
  goz usage --help

Examples:
  goz vision analyze https://example.com/image.png
  goz run --format json "Inspect this repo and report STAGE_RESULT."
  goz vision ui-to-code screenshot.png
  goz search "python async await"
  goz read https://example.com/article
  goz repo tree vercel/next.js
  goz repo search facebook/react "hooks"
  goz tools --filter vision
  goz tool zai.vision.analyze_image
  goz call zai.search.webSearchPrime --json '{{"search_query":"test"}}'
  goz config get zai_token

With no command, launches the interactive TUI.
""")
        return

    parser = argparse.ArgumentParser(
        prog="goz",
        description="goz - Z.AI Tools: vision, search, web reader, and more",
        add_help=False,  # We handle help manually
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    # Agent mode flags (for use with no command)
    parser.add_argument(
        "--load",
        help="Load session on startup (for agent mode)",
    )
    parser.add_argument(
        "--agent",
        help="Start with specific agent type (for agent mode)",
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to run (run, config, vision, search, read, repo, tools, tool, call, doctor, tui)",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments for the command",
    )

    args = parser.parse_args()

    if args.command is None:
        # No command = launch AGENT MODE (interactive coding agent)
        from goz.agent.tui import run_agent_app

        run_agent_app(session_id=args.load, agent_type=args.agent)
        return

    # Dispatch to command handlers
    if args.command == "config":
        cmd_config(args.args)
    elif args.command == "vision":
        asyncio.run(cmd_vision(args.args))
    elif args.command == "run":
        asyncio.run(cmd_run(args.args))
    elif args.command == "search":
        asyncio.run(cmd_search(args.args))
    elif args.command == "read":
        asyncio.run(cmd_read(args.args))
    elif args.command == "repo":
        asyncio.run(cmd_repo(args.args))
    elif args.command == "tools":
        asyncio.run(cmd_tools(args.args))
    elif args.command == "tool":
        asyncio.run(cmd_tool(args.args))
    elif args.command == "call":
        asyncio.run(cmd_call(args.args))
    elif args.command == "doctor":
        cmd_doctor(args.args)
    elif args.command == "usage":
        from goz.cli.usage import cmd_usage as _cmd_usage

        asyncio.run(_cmd_usage(args.args))
    elif args.command == "models":
        from goz.cli.models import cmd_models as _cmd_models

        asyncio.run(_cmd_models(args.args))
    elif args.command in ("tui", "ui"):
        cmd_tui(args.args)
    else:
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
        print("Run 'goz --help' for usage", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
