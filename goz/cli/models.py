"""CLI handler for `goz models` command.

Usage:
    goz models                  List available models with pricing
    goz models --json           Output as JSON
    goz models --filter QUERY   Filter models by name
    goz models --capabilities   Show model capabilities
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def _format_price(price: float) -> str:
    """Format a price per million tokens for display."""
    if price == 0.0:
        return "—"
    if price < 0.01:
        return f"${price:.4f}"
    if price < 1.0:
        return f"${price:.2f}"
    return f"${price:.1f}"


def _format_context_window(tokens: int) -> str:
    """Format context window for display."""
    if tokens == 0:
        return "—"
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.0f}K"
    return str(tokens)


def _format_models_table(models: Sequence, show_capabilities: bool = False) -> str:
    """Format models as a human-readable table.

    Args:
        models: Sequence of ModelInfo objects
        show_capabilities: Whether to include capabilities column

    Returns:
        Formatted table string
    """
    if not models:
        return "No models available."

    # Calculate column widths
    id_width = max(len(m.id) for m in models)
    id_width = min(id_width, 40)  # Cap at 40 chars
    name_width = max(len(m.name) for m in models)
    name_width = min(name_width, 30)

    header = f"{'MODEL ID':<{id_width}}  {'NAME':<{name_width}}  {'INPUT':>8}  {'OUTPUT':>8}  {'CONTEXT':>10}"
    if show_capabilities:
        header += "  CAPABILITIES"

    lines = [header, "─" * len(header)]

    for m in models:
        row = (
            f"{m.id:<{id_width}}  "
            f"{m.name:<{name_width}}  "
            f"{_format_price(m.input_price_per_mtok):>8}  "
            f"{_format_price(m.output_price_per_mtok):>8}  "
            f"{_format_context_window(m.context_window):>10}"
        )
        if show_capabilities:
            caps = ", ".join(m.capabilities) if m.capabilities else "—"
            row += f"  {caps}"
        lines.append(row)

    lines.append("")
    lines.append(f"Total: {len(models)} model(s)")
    lines.append("Prices shown per million tokens (USD).")

    return "\n".join(lines)


async def cmd_models(args: list[str]) -> None:
    """Handle the `goz models` command.

    Args:
        args: Command arguments
    """
    # Help
    if not args or args[0] in ("--help", "-h", "help"):
        print("""Models command usage:

  goz models [options]

Options:
  --json, -j           Output as JSON
  --filter, -f QUERY   Filter models by name (case-insensitive substring match)
  --capabilities, -c   Show model capabilities column
  --no-header          Skip the table header (useful for scripting)

Examples:
  goz models
  goz models --json
  goz models --filter vision
  goz models --filter glm --capabilities
""")
        return

    # Parse flags
    use_json = False
    name_filter: str | None = None
    show_capabilities = False
    no_header = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--json", "-j"):
            use_json = True
            i += 1
        elif arg in ("--filter", "-f"):
            if i + 1 < len(args):
                name_filter = args[i + 1]
                i += 2
            else:
                print("Error: --filter requires a query argument", file=sys.stderr)
                sys.exit(1)
        elif arg in ("--capabilities", "-c"):
            show_capabilities = True
            i += 1
        elif arg in ("--no-header",):
            no_header = True
            i += 1
        else:
            print(f"Error: Unknown option '{arg}'", file=sys.stderr)
            print("Run 'goz models --help' for usage", file=sys.stderr)
            sys.exit(1)

    from goz.api.models import ModelsClient
    from goz.config import load_config

    config = load_config()
    client = ModelsClient(config=config)

    try:
        response = await client.fetch_models()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    models = response.models

    # Apply filter
    if name_filter:
        query = name_filter.lower()
        models = [m for m in models if query in m.id.lower() or query in m.name.lower()]

    if use_json:
        # Output as JSON
        output = {
            "total": len(models),
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "owner": m.owner,
                    "description": m.description,
                    "context_window": m.context_window,
                    "input_price_per_mtok": m.input_price_per_mtok,
                    "output_price_per_mtok": m.output_price_per_mtok,
                    "capabilities": m.capabilities,
                }
                for m in models
            ],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Output as table
        if no_header:
            for m in models:
                caps = ", ".join(m.capabilities) if m.capabilities else ""
                parts = [m.id, m.name]
                if m.input_price_per_mtok > 0:
                    parts.append(f"in:{_format_price(m.input_price_per_mtok)}")
                if m.output_price_per_mtok > 0:
                    parts.append(f"out:{_format_price(m.output_price_per_mtok)}")
                if m.context_window > 0:
                    parts.append(f"ctx:{_format_context_window(m.context_window)}")
                if show_capabilities and caps:
                    parts.append(caps)
                print("\t".join(parts))
        else:
            print(_format_models_table(models, show_capabilities=show_capabilities))
