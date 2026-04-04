"""Z.AI quota and usage monitor API client.

Calls the Z.AI monitor endpoints to retrieve quota limits and historical
usage aggregates for display in the ``goz usage`` CLI command.

Endpoints:
- ``api.z.ai/api/monitor/usage/quota/limit`` → 5-hour quota remaining
- ``api.z.ai/api/monitor/usage/model-usage`` → 7-day and 30-day aggregates
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from goz.config import Config, DEFAULT_ZAI_BASE_URL

logger = logging.getLogger(__name__)

# The monitor API uses a different base than the Anthropic-compatible one.
_MONITOR_BASE = "https://api.z.ai/api/monitor"


@dataclass
class QuotaLimitInfo:
    """Parsed response from the quota/limit endpoint."""

    quota_limit: int = 0
    quota_remaining: int = 0
    quota_used: int = 0
    reset_at: str | None = None

    def usage_percent(self) -> float:
        if self.quota_limit <= 0:
            return 0.0
        return (self.quota_used / self.quota_limit) * 100.0


@dataclass
class ModelUsageAggregate:
    """Parsed response from the model-usage endpoint."""

    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    period: str = ""  # e.g. "7d", "30d"


@dataclass
class QuotaDashboard:
    """Combined quota and usage data for the ``goz usage`` display."""

    quota: QuotaLimitInfo | None = None
    aggregates_7d: list[ModelUsageAggregate] | None = None
    aggregates_30d: list[ModelUsageAggregate] | None = None
    error: str | None = None


class QuotaClient:
    """Client for the Z.AI monitor/usage API."""

    def __init__(self, config: Config | None = None) -> None:
        if config is None:
            from goz.config import load_config
            config = load_config()
        self.config = config
        self._headers = {
            "Authorization": f"Bearer {config.zai_token}",
            "Accept": "application/json",
        }

    async def _get(self, path: str) -> dict[str, Any]:
        """Make an authenticated GET request to the monitor API."""
        url = f"{_MONITOR_BASE}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def get_quota_limit(self) -> QuotaLimitInfo:
        """Fetch 5-hour quota limit and remaining tokens.

        Calls ``api.z.ai/api/monitor/usage/quota/limit``.
        """
        try:
            data = await self._get("usage/quota/limit")
            # The response shape may vary; handle common patterns.
            if isinstance(data, dict):
                return QuotaLimitInfo(
                    quota_limit=data.get("quota_limit", data.get("limit", 0)),
                    quota_remaining=data.get("quota_remaining", data.get("remaining", 0)),
                    quota_used=data.get("quota_used", data.get("used", 0)),
                    reset_at=data.get("reset_at", data.get("resets_at")),
                )
        except httpx.HTTPStatusError as exc:
            logger.warning("Quota limit request failed: %s", exc)
        except Exception as exc:
            logger.warning("Quota limit request error: %s", exc)
        return QuotaLimitInfo()

    async def get_model_usage(self) -> dict[str, list[ModelUsageAggregate]]:
        """Fetch model usage aggregates.

        Calls ``api.z.ai/api/monitor/usage/model-usage``.

        Returns:
            A dict with ``"7d"`` and ``"30d"`` keys mapping to lists of
            :class:`ModelUsageAggregate`.
        """
        result: dict[str, list[ModelUsageAggregate]] = {"7d": [], "30d": []}
        try:
            data = await self._get("usage/model-usage")
            if isinstance(data, list):
                for entry in data:
                    agg = ModelUsageAggregate(
                        model=entry.get("model", entry.get("model_id", "")),
                        input_tokens=entry.get("input_tokens", 0),
                        output_tokens=entry.get("output_tokens", 0),
                        total_tokens=entry.get("total_tokens", entry.get("input_tokens", 0) + entry.get("output_tokens", 0)),
                        period=entry.get("period", ""),
                    )
                    period = agg.period.lower() if agg.period else ""
                    if "30" in period:
                        result["30d"].append(agg)
                    else:
                        result["7d"].append(agg)
            elif isinstance(data, dict):
                for period_key, entries in data.items():
                    key = "30d" if "30" in str(period_key).lower() else "7d"
                    if isinstance(entries, list):
                        for entry in entries:
                            agg = ModelUsageAggregate(
                                model=entry.get("model", entry.get("model_id", "")),
                                input_tokens=entry.get("input_tokens", 0),
                                output_tokens=entry.get("output_tokens", 0),
                                total_tokens=entry.get("total_tokens", entry.get("input_tokens", 0) + entry.get("output_tokens", 0)),
                                period=str(period_key),
                            )
                            result[key].append(agg)
        except httpx.HTTPStatusError as exc:
            logger.warning("Model usage request failed: %s", exc)
        except Exception as exc:
            logger.warning("Model usage request error: %s", exc)
        return result

    async def get_dashboard(self) -> QuotaDashboard:
        """Fetch all quota/usage data for the usage command display."""
        quota = await self.get_quota_limit()
        usage = await self.get_model_usage()
        return QuotaDashboard(
            quota=quota,
            aggregates_7d=usage.get("7d"),
            aggregates_30d=usage.get("30d"),
        )
