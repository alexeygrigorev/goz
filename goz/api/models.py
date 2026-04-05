"""Z.AI Models API client for listing available models with pricing.

Provides access to:
- /api/anthropic/v1/models — List available models
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from goz.config import Config

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a single model.

    Attributes:
        id: Model identifier (e.g., 'glm-5-turbo')
        name: Human-readable model name
        owner: Model provider/owner
        description: Model description (optional)
        context_window: Maximum context window in tokens
        input_price_per_mtok: Input price per million tokens (USD)
        output_price_per_mtok: Output price per million tokens (USD)
        capabilities: List of model capabilities (e.g., ['chat', 'vision'])
        raw: Raw API response data
    """
    id: str
    name: str
    owner: str = ""
    description: str = ""
    context_window: int = 0
    input_price_per_mtok: float = 0.0
    output_price_per_mtok: float = 0.0
    capabilities: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelsResponse:
    """Response from the models list endpoint.

    Attributes:
        models: List of available models
        total: Total number of models available
        raw: Raw API response data
    """
    models: list[ModelInfo] = field(default_factory=list)
    total: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class ModelsClient:
    """Client for fetching available Z.AI models with pricing information."""

    def __init__(self, config: Config | None = None) -> None:
        if config is None:
            from goz.config import load_config
            config = load_config()
        self.config = config

    def _base(self) -> str:
        """Return base URL, stripping any path suffixes."""
        url = self.config.zai_base_url
        # Normalize: api.z.ai/api/anthropic -> api.z.ai
        for suffix in ("/api/anthropic", "/anthropic"):
            if url.rstrip("/").endswith(suffix):
                url = url.rstrip("/")[: -len(suffix)]
                break
        return url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.zai_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def fetch_models(self) -> ModelsResponse:
        """Fetch the list of available models with pricing.

        Tries multiple endpoint patterns:
        1. /api/anthropic/v1/models  (OpenAI-compatible)
        2. /v1/models

        Returns:
            ModelsResponse with list of ModelInfo objects

        Raises:
            httpx.HTTPStatusError: For non-2xx responses
            httpx.NetworkError: For network failures
        """
        base = self._base()

        # Try multiple endpoint patterns
        endpoints = [
            f"{base}/api/anthropic/v1/models",
            f"{base}/v1/models",
        ]

        last_error: Exception | None = None

        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    resp = await client.get(endpoint, headers=self._headers())

                    if resp.status_code == 200:
                        data = resp.json()
                        return self._parse_response(data)

                    if resp.status_code == 404:
                        continue

                    # For other errors, try next endpoint
                    last_error = httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )

            except httpx.ConnectError as e:
                last_error = e
                continue
            except httpx.NetworkError as e:
                last_error = e
                continue

        # All endpoints failed — return empty response rather than raising
        if last_error:
            logger.warning("All model endpoints failed: %s", last_error)

        return ModelsResponse(models=[], total=0, raw={})

    def _parse_response(self, data: Any) -> ModelsResponse:
        """Parse the API response into ModelsResponse.

        Handles various response formats:
        - OpenAI-compatible: {"data": [...], "object": "list"}
        - Anthropic-style: {"data": [...]}
        - Direct list: [...]
        """
        raw = data if isinstance(data, dict) else {"data": data}
        items: list[dict[str, Any]] = []

        if isinstance(data, dict):
            items = data.get("data", [])
        elif isinstance(data, list):
            items = data

        models: list[ModelInfo] = []

        for item in items:
            if not isinstance(item, dict):
                continue

            model_id = item.get("id", item.get("model_id", item.get("name", "")))
            model_name = item.get("name", model_id)

            # Parse pricing — handle various formats
            pricing = item.get("pricing", {})
            if isinstance(pricing, dict):
                input_price = self._parse_price(pricing.get("input", pricing.get("prompt", 0.0)))
                output_price = self._parse_price(pricing.get("output", pricing.get("completion", 0.0)))
            elif isinstance(pricing, str):
                # Format like "0.5/1.5" (input/output per Mtok)
                parts = pricing.split("/")
                input_price = self._parse_price(parts[0]) if len(parts) > 0 else 0.0
                output_price = self._parse_price(parts[1]) if len(parts) > 1 else 0.0
            else:
                input_price = 0.0
                output_price = 0.0

            # Parse capabilities
            capabilities = item.get("capabilities", [])
            if isinstance(capabilities, str):
                capabilities = [c.strip() for c in capabilities.split(",") if c.strip()]
            elif not isinstance(capabilities, list):
                capabilities = []

            # Infer capabilities from model name
            model_id_lower = model_id.lower()
            if "vision" in model_id_lower or "v" in model_id_lower.split("-")[-1:]:
                if "vision" not in capabilities:
                    capabilities.append("vision")
            if "chat" not in capabilities and "glm" in model_id_lower:
                capabilities.append("chat")

            models.append(ModelInfo(
                id=str(model_id),
                name=str(model_name),
                owner=item.get("owner", item.get("organization", "")),
                description=item.get("description", ""),
                context_window=int(item.get("context_window", item.get("max_context", 0))),
                input_price_per_mtok=input_price,
                output_price_per_mtok=output_price,
                capabilities=capabilities,
                raw=item,
            ))

        return ModelsResponse(
            models=models,
            total=len(models),
            raw=raw,
        )

    @staticmethod
    def _parse_price(value: Any) -> float:
        """Parse a price value, handling string and numeric formats.

        Prices may come as:
        - Float: 0.5 (dollars per million tokens)
        - String: "$0.50", "0.50", "0.5"
        """
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Strip currency symbols
            cleaned = value.replace("$", "").replace("€", "").replace("£", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        return 0.0
