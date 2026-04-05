"""Usage tracking for Z.AI token consumption and cost.

This module provides data structures and utilities for tracking token usage
across streaming API responses, computing costs, and accumulating per-session
statistics.

Acceptance Criteria (T-0008):
- Per-turn token counts extracted from message_start/message_delta events
- Accumulated in session state
- step_finish JSONL event includes tokens and cost
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# Approximate per-Mtoken pricing (USD) for common models.
# These are best-effort estimates; actual billing comes from the API.
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "glm-5-turbo": {"input": 2.0, "output": 8.0, "cache_read": 0.5, "cache_creation": 2.5},
    "glm-4.6v": {"input": 2.0, "output": 8.0, "cache_read": 0.5, "cache_creation": 2.5},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_creation": 3.75},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_creation": 3.75},
}

_DEFAULT_PRICING = {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_creation": 3.75}


def _get_pricing(model: str) -> dict[str, float]:
    """Return pricing dict for *model*, falling back to defaults."""
    for key, pricing in _MODEL_PRICING.items():
        if key in model:
            return pricing
    return _DEFAULT_PRICING


@dataclass
class UsageSnapshot:
    """Token counts from a single API response (one streaming turn).

    Attributes:
        input_tokens: Total input tokens for the request.
        output_tokens: Total output tokens generated.
        cache_read_input_tokens: Tokens served from prompt cache (read).
        cache_creation_input_tokens: Tokens stored into prompt cache (write).
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def cost_usd(self, model: str = "") -> float:
        """Compute approximate USD cost for this snapshot."""
        pricing = _get_pricing(model)
        return (
            self.input_tokens * pricing["input"]
            + self.output_tokens * pricing["output"]
            + self.cache_read_input_tokens * pricing["cache_read"]
            + self.cache_creation_input_tokens * pricing["cache_creation"]
        ) / 1_000_000.0

    def total_tokens(self) -> int:
        """Return the sum of all token counts."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for JSONL emission)."""
        return {
            "input": self.input_tokens,
            "output": self.output_tokens,
            "cache_read": self.cache_read_input_tokens,
            "cache_creation": self.cache_creation_input_tokens,
        }


@dataclass
class UsageAccumulator:
    """Accumulates usage across multiple turns in a session.

    Usage is captured in two phases per streaming response:
    1. ``message_start`` carries initial input / cache tokens.
    2. ``message_delta`` carries the final output token count.

    The accumulator merges these into a :class:`UsageSnapshot` per turn
    and maintains running totals.
    """

    # Running totals across all turns
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0
    turn_count: int = 0

    # Per-turn snapshots (append-only)
    turns: list[UsageSnapshot] = field(default_factory=list)

    # --- Streaming helpers ---------------------------------------------------

    def begin_turn(self) -> None:
        """Prepare for a new streaming turn."""
        self.turns.append(UsageSnapshot())

    def apply_message_start(self, usage: object) -> None:
        """Merge ``message_start`` usage data into the current turn.

        Args:
            usage: An object with ``input_tokens``, optionally
                ``cache_read_input_tokens`` and ``cache_creation_input_tokens``.
        """
        if not self.turns:
            self.begin_turn()
        snap = self.turns[-1]
        snap.input_tokens = getattr(usage, "input_tokens", 0) or 0
        snap.cache_read_input_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
        snap.cache_creation_input_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0

    def apply_message_delta(self, usage: object) -> None:
        """Merge ``message_delta`` usage data into the current turn.

        Args:
            usage: An object with ``output_tokens``, optionally cumulative
                ``input_tokens``, ``cache_read_input_tokens``, etc.
        """
        if not self.turns:
            self.begin_turn()
        snap = self.turns[-1]
        # message_delta carries cumulative output_tokens
        snap.output_tokens = getattr(usage, "output_tokens", 0) or 0
        # Update input/cache if provided (some APIs send cumulative totals here)
        if hasattr(usage, "input_tokens") and usage.input_tokens is not None:
            snap.input_tokens = usage.input_tokens
        if hasattr(usage, "cache_read_input_tokens") and usage.cache_read_input_tokens is not None:
            snap.cache_read_input_tokens = usage.cache_read_input_tokens
        if hasattr(usage, "cache_creation_input_tokens") and usage.cache_creation_input_tokens is not None:
            snap.cache_creation_input_tokens = usage.cache_creation_input_tokens

    def finalise_turn(self) -> UsageSnapshot:
        """Close the current turn, roll into running totals, and return it."""
        if not self.turns:
            return UsageSnapshot()
        snap = self.turns[-1]
        self.total_input_tokens += snap.input_tokens
        self.total_output_tokens += snap.output_tokens
        self.total_cache_read_tokens += snap.cache_read_input_tokens
        self.total_cache_creation_tokens += snap.cache_creation_input_tokens
        self.turn_count += 1
        return snap

    def current_turn_snapshot(self) -> UsageSnapshot:
        """Return the in-progress snapshot for the current turn."""
        if not self.turns:
            return UsageSnapshot()
        return self.turns[-1]

    # --- Aggregation ---------------------------------------------------------

    def total_tokens(self) -> int:
        return (
            self.total_input_tokens
            + self.total_output_tokens
            + self.total_cache_read_tokens
            + self.total_cache_creation_tokens
        )

    def total_cost_usd(self, model: str = "") -> float:
        pricing = _get_pricing(model)
        return (
            self.total_input_tokens * pricing["input"]
            + self.total_output_tokens * pricing["output"]
            + self.total_cache_read_tokens * pricing["cache_read"]
            + self.total_cache_creation_tokens * pricing["cache_creation"]
        ) / 1_000_000.0

    def to_dict(self) -> dict:
        """Serialise full accumulator state."""
        return {
            "turn_count": self.turn_count,
            "total_input": self.total_input_tokens,
            "total_output": self.total_output_tokens,
            "total_cache_read": self.total_cache_read_tokens,
            "total_cache_creation": self.total_cache_creation_tokens,
            "total_tokens": self.total_tokens(),
            "turns": [t.to_dict() for t in self.turns],
        }


@dataclass
class TokenBudget:
    """Tracks cumulative token usage against a budget.

    Uses an existing UsageAccumulator to check input+output token totals
    after each turn.  Emits warning at 80% and signals stop at 100%.

    Attributes:
        budget: Maximum total tokens allowed (input + output).
        warning_threshold: Fraction of budget at which a warning is emitted (default 0.8).
        warning_emitted: Whether the warning has already been emitted this session.
        exceeded: Whether the budget has been exceeded.
    """

    budget: int
    warning_threshold: float = 0.8
    warning_emitted: bool = False
    exceeded: bool = False

    def check(self, acc: UsageAccumulator) -> tuple[bool, bool]:
        """Check the accumulator against the budget.

        Returns:
            (should_warn, should_stop) tuple.  ``should_warn`` is True the
            first time usage crosses the warning threshold.  ``should_stop``
            is True once usage reaches or exceeds the budget.
        """
        total = acc.total_input_tokens + acc.total_output_tokens
        should_warn = False
        should_stop = False

        if total >= self.budget:
            self.exceeded = True
            should_stop = True
        elif not self.warning_emitted and total >= int(self.budget * self.warning_threshold):
            self.warning_emitted = True
            should_warn = True

        return should_warn, should_stop
