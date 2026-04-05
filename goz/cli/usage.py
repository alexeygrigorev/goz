"""`goz usage` CLI command for displaying usage statistics and quota."""

from __future__ import annotations

import sys

from goz.config import load_config


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _fmt_cost(cost: float) -> str:
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


async def cmd_usage(args: list[str]) -> None:
    if args and args[0] in ("--help", "-h", "help"):
        print("""Usage command:

  goz usage            Show quota remaining and usage aggregates
  goz usage --json     Raw JSON output
  goz usage --days N   Model usage window (default: 7)

Endpoints:
  api.z.ai/api/monitor/usage/quota/limit   - 5-hour quota
  api.z.ai/api/monitor/usage/model-usage   - Model aggregates
""")
        return

    use_json = "--json" in args
    days = 7
    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                pass

    from goz.api.monitor import MonitorClient

    config = load_config()
    client = MonitorClient(config=config)

    try:
        quota = await client.fetch_quota_limit()
    except Exception as exc:
        print(f"Failed to fetch quota: {exc}", file=sys.stderr)
        quota = None

    try:
        usage_7 = await client.fetch_model_usage(days=days)
    except Exception as exc:
        print(f"Failed to fetch {days}-day usage: {exc}", file=sys.stderr)
        usage_7 = None

    try:
        usage_30 = await client.fetch_model_usage(days=30)
    except Exception as exc:
        print(f"Failed to fetch 30-day usage: {exc}", file=sys.stderr)
        usage_30 = None

    if use_json:
        import json

        out: dict = {}
        if quota:
            out["level"] = quota.level
            out["limits"] = [
                {
                    "type": lim.type,
                    "limit": lim.limit,
                    "used": lim.used,
                    "remaining": lim.remaining,
                    "percentage": lim.percentage,
                    "window_hours": lim.window_hours,
                    "details": lim.details,
                }
                for lim in quota.limits
            ]
        if usage_7:
            out[f"{usage_7.period_days}_day"] = [
                {
                    "model": e.model,
                    "input_tokens": e.input_tokens,
                    "output_tokens": e.output_tokens,
                    "total_tokens": e.total_tokens,
                    "cost": e.cost,
                    "requests": e.requests,
                }
                for e in usage_7.entries
            ]
        if usage_30:
            out["30_day"] = [
                {
                    "model": e.model,
                    "input_tokens": e.input_tokens,
                    "output_tokens": e.output_tokens,
                    "total_tokens": e.total_tokens,
                    "cost": e.cost,
                    "requests": e.requests,
                }
                for e in usage_30.entries
            ]
        print(json.dumps(out, indent=2, ensure_ascii=True))
        return

    if quota:
        print(f"Plan: {quota.level}")
        print()
        for lim in quota.limits:
            if lim.type == "TIME_LIMIT":
                print(f"API calls ({lim.window_hours}h window):")
                print(f"  Limit:     {_fmt_tokens(lim.limit)}")
                print(f"  Used:      {_fmt_tokens(lim.used)} ({lim.percentage}%)")
                print(f"  Remaining: {_fmt_tokens(lim.remaining)}")
                if lim.details:
                    print(f"  Breakdown:")
                    for d in lim.details:
                        if d.get("usage", 0) > 0:
                            print(f"    {d['modelCode']}: {d['usage']}")
            elif lim.type == "TOKENS_LIMIT":
                from datetime import datetime
                reset = ""
                if lim.reset_at:
                    reset_dt = datetime.fromtimestamp(lim.reset_at / 1000)
                    reset = f" (resets {reset_dt.strftime('%Y-%m-%d %H:%M')})"
                print(f"Token quota ({lim.window_hours}h window):")
                print(f"  Used: {lim.percentage}%{reset}")
            print()

    if usage_7:
        print(f"Model usage ({usage_7.period_days}-day):")
        if not usage_7.entries:
            print("  (no data)")
        for e in usage_7.entries:
            print(f"  {e.model}")
            print(
                f"    Input:  {_fmt_tokens(e.input_tokens)}  Output: {_fmt_tokens(e.output_tokens)}  Total: {_fmt_tokens(e.total_tokens)}"
            )
            print(f"    Cost:   {_fmt_cost(e.cost)}  Requests: {e.requests}")
        print()

    if usage_30:
        print("Model usage (30-day):")
        if not usage_30.entries:
            print("  (no data)")
        for e in usage_30.entries:
            print(f"  {e.model}")
            print(
                f"    Input:  {_fmt_tokens(e.input_tokens)}  Output: {_fmt_tokens(e.output_tokens)}  Total: {_fmt_tokens(e.total_tokens)}"
            )
            print(f"    Cost:   {_fmt_cost(e.cost)}  Requests: {e.requests}")
