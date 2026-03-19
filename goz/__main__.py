"""Main entry point for the goz CLI."""

import asyncio
import sys

from goz import __version__


async def cmd_vision(args: list[str]) -> None:
    """Handle the `goz vision` command.

    Usage:
        goz vision <image_path_or_url> [prompt]

    Args:
        args: [image_path_or_url, prompt]
    """
    if not args:
        print("Usage: goz vision <image_path_or_url> [prompt]", file=sys.stderr)
        sys.exit(1)

    from goz.api.vision import VisionClient
    from goz.config import load_config

    config = load_config()
    client = VisionClient(config=config)

    image = args[0]
    prompt = args[1] if len(args) > 1 else "Describe this image in detail."

    try:
        result = await client.analyze(image, prompt)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def cmd_search(args: list[str]) -> None:
    """Handle the `goz search` command.

    Usage:
        goz search <query> [--count N] [--domain DOMAIN] [--recency R]

    Args:
        args: Command arguments
    """
    import argparse

    parser = argparse.ArgumentParser(prog="goz search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--count", "-c", type=int, help="Number of results")
    parser.add_argument("--domain", "-d", help="Filter to domain")
    parser.add_argument("--recency", "-r",
                        choices=["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"],
                        help="Time filter")

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
        goz read <url> [--format FORMAT] [--timeout N]

    Args:
        args: Command arguments
    """
    import argparse

    parser = argparse.ArgumentParser(prog="goz read")
    parser.add_argument("url", help="URL to read")
    parser.add_argument("--format", "-f", choices=["markdown", "text"],
                        default="markdown", help="Output format")
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


def cmd_config(args: list[str]) -> None:
    """Handle the `goz config` command.

    Args:
        args: Remaining arguments after 'config'
    """
    from goz.config import ConfigManager

    manager = ConfigManager()

    # Handle `goz config set <key> <value>`
    if len(args) >= 2 and args[0] == "set":
        key = args[1]
        value = args[2] if len(args) > 2 else ""
        try:
            manager.set_config(key, value)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Handle `goz config` (show current config)
    manager.show_config()


def main() -> None:
    """Run the goz CLI.

    This is the entry point for the `goz` command.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="goz",
        description="goz - Z.AI Tools: vision, search, web reader, and more",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Command to run (config, vision, search, read, doctor)",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments for the command",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # Dispatch to command handlers
    if args.command == "config":
        cmd_config(args.args)
    elif args.command == "vision":
        asyncio.run(cmd_vision(args.args))
    elif args.command == "search":
        asyncio.run(cmd_search(args.args))
    elif args.command == "read":
        asyncio.run(cmd_read(args.args))
    else:
        print(f"Command '{args.command}' not yet implemented")


if __name__ == "__main__":
    main()
