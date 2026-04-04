"""Z.AI Monitor API client for usage statistics and quota tracking.

Provides access to:
- /api/monitor/usage/quota/limit — 5-hour quota remaining
- /api/monitor/usage/model-usage — 7-day and 30-day aggregates
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from goz.config import Config

logger = logging.getLogger(__name__)


@dataclass
class QuotaInfo:
    limit: int
    remaining: int
    used: int
    window_label: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelUsageEntry:
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    requests: int
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelUsageReport:
    period_days: int
    entries: list[ModelUsageEntry] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class MonitorClient:
    def __init__(self, config: Config | None = None) -> None:
        if config is None:
            from goz.config import load_config

            config = load_config()
        self.config = config

    def _base(self) -> str:
        url = self.config.zai_base_url
        if "/api/anthropic" in url:
            url = url.replace("/api/anthropic", "")
        return url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.zai_token}",
            "Content-Type": "application/json",
        }

    async def fetch_quota_limit(self) -> QuotaInfo:
        base = self._base()
        url = f"{base}/api/monitor/usage/quota/limit"
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        if isinstance(data, dict) and "data" in data:
            inner = data["data"]
        elif isinstance(data, dict):
            inner = data
        else:
            inner = {}

        limit = inner.get("limit", inner.get("total", 0))
        used = inner.get("used", inner.get("consumed", 0))
        remaining = inner.get("remaining", max(0, limit - used))
        window = inner.get("window", inner.get("period", "5h"))

        return QuotaInfo(
            limit=limit,
            remaining=remaining,
            used=used,
            window_label=str(window),
            raw=data,
        )

    async def fetch_model_usage(self, days: int = 7) -> ModelUsageReport:
        base = self._base()
        url = f"{base}/api/monitor/usage/model-usage"
        params: dict[str, Any] = {"days": days}

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            data = resp.json()

        entries: list[ModelUsageEntry] = []
        items: list[dict[str, Any]] = []
        if isinstance(data, dict) and "data" in data:
            items = data["data"] if isinstance(data["data"], list) else []
        elif isinstance(data, list):
            items = data

        for item in items:
            entries.append(
                ModelUsageEntry(
                    model=item.get("model", "unknown"),
                    input_tokens=item.get("input_tokens", 0),
                    output_tokens=item.get("output_tokens", 0),
                    total_tokens=item.get(
                        "total_tokens", item.get("input_tokens", 0) + item.get("output_tokens", 0)
                    ),
                    cost=item.get("cost", 0.0),
                    requests=item.get("requests", item.get("request_count", 0)),
                    raw=item,
                )
            )

        return ModelUsageReport(
            period_days=days, entries=entries, raw=data if isinstance(data, dict) else {}
        )
