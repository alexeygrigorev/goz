"""Minimal MCP client for tool discovery and direct tool invocation."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

import httpx

from goz.api.errors import AuthError, ApiError, NetworkError, TimeoutError, ZaiError
from goz.config import Config, load_config


RETRY_COUNT = 2
BASE_DELAY = 1.0

SERVICE_ENDPOINTS = {
    "vision": "https://api.z.ai/api/mcp/vision/mcp",
    "search": "https://api.z.ai/api/mcp/web_search_prime/mcp",
    "reader": "https://api.z.ai/api/mcp/web_reader/mcp",
    "zread": "https://api.z.ai/api/mcp/zread/mcp",
}

TOOL_ENDPOINT_HINTS = (
    ("zai.vision.", "vision"),
    ("zai.search.", "search"),
    ("zai.reader.", "reader"),
    ("zai.zread.", "zread"),
)


class McpClient:
    """Small JSON-RPC MCP client for listing and calling tools."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.zai_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

    async def list_tools(self) -> list[dict[str, Any]]:
        """List tools across known MCP service endpoints."""
        tools_by_name: dict[str, dict[str, Any]] = {}

        for service, endpoint in SERVICE_ENDPOINTS.items():
            response = await self._mcp_request(endpoint, "tools/list", {})
            for tool in self._extract_tools(response):
                name = str(tool.get("name", "")).strip()
                if not name:
                    continue
                normalized = dict(tool)
                normalized.setdefault("_service", service)
                normalized.setdefault("_endpoint", endpoint)
                tools_by_name[name] = normalized

        return [tools_by_name[name] for name in sorted(tools_by_name)]

    async def get_tool(self, name: str) -> dict[str, Any] | None:
        """Get a single tool schema by name."""
        for tool in await self.list_tools():
            if tool.get("name") == name:
                return tool
        return None

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool with JSON arguments."""
        endpoint = self._endpoint_for_tool(name)
        return await self._mcp_request(
            endpoint,
            "tools/call",
            {"name": name, "arguments": arguments},
        )

    def _endpoint_for_tool(self, tool_name: str) -> str:
        for prefix, service in TOOL_ENDPOINT_HINTS:
            if tool_name.startswith(prefix):
                return SERVICE_ENDPOINTS[service]
        raise ValueError(f"Unknown MCP service for tool '{tool_name}'")

    async def _mcp_request(
        self,
        endpoint: str,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        timeout = self.config.timeout
        body = {"method": method, "params": params}
        last_error: Exception | None = None

        for attempt in range(RETRY_COUNT + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(endpoint, json=body, headers=self._headers)

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception as exc:
                        raise ApiError(f"Invalid JSON response: {exc}") from exc

                    if "error" in data:
                        error = data["error"]
                        if isinstance(error, dict):
                            message = str(error.get("message", error))
                            code = error.get("code")
                        else:
                            message = str(error)
                            code = None
                        raise ApiError(
                            f"{message}" if code is None else f"{message} (code: {code})",
                            statusCode=200,
                        )

                    return data

                if response.status_code in (401, 403):
                    raise AuthError(self._parse_error_message(response), statusCode=response.status_code)

                raise ApiError(
                    self._parse_error_message(response),
                    statusCode=response.status_code,
                )

            except httpx.TimeoutException:
                last_error = TimeoutError(timeoutMs=int(timeout * 1000))
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = NetworkError(f"Network error: {exc}")
            except (AuthError, ApiError):
                raise
            except Exception as exc:  # pragma: no cover - defensive fallback
                last_error = exc

            if attempt < RETRY_COUNT:
                await asyncio.sleep(BASE_DELAY * (2 ** attempt))

        if last_error:
            raise last_error
        raise ZaiError("Unknown error occurred")

    def _extract_tools(self, response: dict[str, Any]) -> Iterable[dict[str, Any]]:
        result = response.get("result", {})
        if isinstance(result, dict):
            tools = result.get("tools", [])
            if isinstance(tools, list):
                return [tool for tool in tools if isinstance(tool, dict)]
        return []

    def _parse_error_message(self, response: httpx.Response) -> str:
        try:
            data = response.json()
            if "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return str(error.get("message", error))
                return str(error)
            if "message" in data:
                return str(data["message"])
        except Exception:
            pass
        return response.text
