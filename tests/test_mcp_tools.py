"""Tests for MCP tool discovery and direct tool calling."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from goz.api.errors import ApiError
from goz.api.mcp import McpClient


class TestMcpClient:
    """Unit tests for MCP client transport and normalization."""

    @pytest.mark.asyncio
    async def test_list_tools_aggregates_and_sorts_tools(self):
        client = McpClient(config=type("Config", (), {"zai_token": "token", "timeout": 5})())

        responses = {
            "https://api.z.ai/api/mcp/vision/mcp": {
                "result": {"tools": [{"name": "zai.vision.analyze_image"}]}
            },
            "https://api.z.ai/api/mcp/web_search_prime/mcp": {
                "result": {"tools": [{"name": "zai.search.webSearchPrime"}]}
            },
            "https://api.z.ai/api/mcp/web_reader/mcp": {
                "result": {"tools": [{"name": "zai.reader.read_url"}]}
            },
            "https://api.z.ai/api/mcp/zread/mcp": {
                "result": {"tools": [{"name": "zai.zread.read_file"}]}
            },
        }

        async def fake_request(endpoint: str, method: str, params: dict):
            assert method == "tools/list"
            assert params == {}
            return responses[endpoint]

        with patch.object(client, "_mcp_request", side_effect=fake_request):
            tools = await client.list_tools()

        assert [tool["name"] for tool in tools] == [
            "zai.reader.read_url",
            "zai.search.webSearchPrime",
            "zai.vision.analyze_image",
            "zai.zread.read_file",
        ]
        assert tools[0]["_service"] == "reader"

    @pytest.mark.asyncio
    async def test_call_tool_uses_endpoint_for_tool_prefix(self):
        client = McpClient(config=type("Config", (), {"zai_token": "token", "timeout": 5})())

        with patch.object(client, "_mcp_request", new=AsyncMock(return_value={"result": {"ok": True}})) as mock_request:
            result = await client.call_tool("zai.search.webSearchPrime", {"search_query": "test"})

        assert result == {"result": {"ok": True}}
        mock_request.assert_awaited_once_with(
            "https://api.z.ai/api/mcp/web_search_prime/mcp",
            "tools/call",
            {
                "name": "zai.search.webSearchPrime",
                "arguments": {"search_query": "test"},
            },
        )

    @pytest.mark.asyncio
    async def test_mcp_request_raises_api_error_for_json_rpc_error(self):
        client = McpClient(config=type("Config", (), {"zai_token": "token", "timeout": 5})())
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"error": {"message": "broken", "code": -1}}

        http_client = AsyncMock()
        http_client.__aenter__.return_value = http_client
        http_client.__aexit__.return_value = None
        http_client.post.return_value = response

        with patch("goz.api.mcp.httpx.AsyncClient", return_value=http_client):
            with pytest.raises(ApiError) as excinfo:
                await client._mcp_request("https://example.com/mcp", "tools/list", {})

        assert "broken" in str(excinfo.value)


class TestMcpCli:
    """CLI-level tests for tools, tool, and call commands."""

    def _patch_config(self):
        return patch(
            "goz.api.mcp.load_config",
            return_value=type("Config", (), {"zai_token": "token", "timeout": 5})(),
        )

    def test_goz_tools_lists_names(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.list_tools", new=AsyncMock(return_value=[
            {"name": "zai.search.webSearchPrime"},
            {"name": "zai.vision.analyze_image"},
        ])):
            from goz.__main__ import main
            sys.argv = ["goz", "tools"]
            main()

        captured = capsys.readouterr()
        assert captured.out.splitlines() == [
            "zai.search.webSearchPrime",
            "zai.vision.analyze_image",
        ]

    def test_goz_tools_filter_and_full(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.list_tools", new=AsyncMock(return_value=[
            {"name": "zai.search.webSearchPrime", "description": "search"},
            {"name": "zai.vision.analyze_image", "description": "vision"},
        ])):
            from goz.__main__ import main
            sys.argv = ["goz", "tools", "--filter", "vision", "--full"]
            main()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data == [{"name": "zai.vision.analyze_image", "description": "vision"}]

    def test_goz_tool_shows_schema(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.get_tool", new=AsyncMock(return_value={
            "name": "zai.vision.analyze_image",
            "inputSchema": {"type": "object"},
        })):
            from goz.__main__ import main
            sys.argv = ["goz", "tool", "zai.vision.analyze_image"]
            main()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["name"] == "zai.vision.analyze_image"

    def test_goz_tool_unknown_exits_nonzero(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.get_tool", new=AsyncMock(return_value=None)):
            from goz.__main__ import main
            sys.argv = ["goz", "tool", "missing.tool"]
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "Unknown tool 'missing.tool'" in captured.err

    def test_goz_call_with_inline_json(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.call_tool", new=AsyncMock(return_value={"result": {"ok": True}})) as mock_call:
            from goz.__main__ import main
            sys.argv = ["goz", "call", "zai.search.webSearchPrime", "--json", '{"search_query":"test"}']
            main()

        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"result": {"ok": True}}
        mock_call.assert_awaited_once_with("zai.search.webSearchPrime", {"search_query": "test"})

    def test_goz_call_reads_json_from_file(self, tmp_path: Path, capsys):
        payload_file = tmp_path / "payload.json"
        payload_file.write_text('{"search_query":"file"}')

        with self._patch_config(), patch("goz.api.mcp.McpClient.call_tool", new=AsyncMock(return_value={"result": {"ok": True}})) as mock_call:
            from goz.__main__ import main
            sys.argv = ["goz", "call", "zai.search.webSearchPrime", "--json", f"@{payload_file}"]
            main()

        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"result": {"ok": True}}
        mock_call.assert_awaited_once_with("zai.search.webSearchPrime", {"search_query": "file"})

    def test_goz_call_reads_json_from_stdin(self, monkeypatch: pytest.MonkeyPatch, capsys):
        monkeypatch.setattr("sys.stdin", type("FakeStdin", (), {"read": lambda self: '{"search_query":"stdin"}'})())

        with self._patch_config(), patch("goz.api.mcp.McpClient.call_tool", new=AsyncMock(return_value={"result": {"ok": True}})) as mock_call:
            from goz.__main__ import main
            sys.argv = ["goz", "call", "zai.search.webSearchPrime", "--stdin"]
            main()

        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"result": {"ok": True}}
        mock_call.assert_awaited_once_with("zai.search.webSearchPrime", {"search_query": "stdin"})

    def test_goz_call_dry_run_prints_resolved_payload(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.call_tool", new=AsyncMock()) as mock_call:
            from goz.__main__ import main
            sys.argv = ["goz", "call", "zai.search.webSearchPrime", "--json", '{"search_query":"test"}', "--dry-run"]
            main()

        captured = capsys.readouterr()
        assert json.loads(captured.out) == {
            "name": "zai.search.webSearchPrime",
            "arguments": {"search_query": "test"},
        }
        mock_call.assert_not_called()

    def test_goz_call_rejects_ambiguous_input_sources(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.call_tool", new=AsyncMock()):
            from goz.__main__ import main
            sys.argv = ["goz", "call", "zai.search.webSearchPrime", "--json", "{}", "--stdin"]
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "Use either --json or --stdin, not both" in captured.err

    def test_goz_call_rejects_invalid_json(self, capsys):
        with self._patch_config(), patch("goz.api.mcp.McpClient.call_tool", new=AsyncMock()):
            from goz.__main__ import main
            sys.argv = ["goz", "call", "zai.search.webSearchPrime", "--json", "{oops"]
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.err
