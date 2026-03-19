"""Main entry point for the goz CLI."""

import sys

from goz import __version__


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
    else:
        print(f"Command '{args.command}' not yet implemented")


if __name__ == "__main__":
    main()
