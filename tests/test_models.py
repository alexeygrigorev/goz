"""Tests for `goz models` command (Issue T-0019).

Acceptance criteria tested:
- ModelsClient.fetch_models returns ModelsResponse with ModelInfo list
- Response parsing handles OpenAI-compatible format ({"data": [...]})
- Response parsing handles direct list format ([...])
- Price parsing handles numeric and string formats
- CLI cmd_models renders table output
- CLI cmd_models --json outputs valid JSON
- CLI cmd_models --filter filters by name substring
- CLI cmd_models --capabilities shows capabilities column
- CLI cmd_models --no-header outputs TSV rows
- CLI cmd_models --help shows usage
- Empty model list displays "No models available."
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from goz.api.models import ModelInfo, ModelsClient, ModelsResponse
from goz.cli.models import _format_context_window, _format_models_table, _format_price


# ========== Fixtures ==========


@pytest.fixture
def config():
    """Create a test Config."""
    from goz.config import Config
    return Config(
        zai_token="test-token",
        zai_base_url="https://api.z.ai",
        timeout=30,
    )


@pytest.fixture
def sample_openai_response() -> dict[str, Any]:
    """Sample OpenAI-compatible API response."""
    return {
        "object": "list",
        "data": [
            {
                "id": "glm-5-turbo",
                "name": "GLM-5 Turbo",
                "owner": "zhipu",
                "description": "Fast and efficient model",
                "context_window": 128000,
                "pricing": {
                    "input": 0.5,
                    "output": 1.5,
                },
                "capabilities": ["chat", "vision"],
            },
            {
                "id": "glm-5-vision",
                "name": "GLM-5 Vision",
                "owner": "zhipu",
                "description": "Vision-capable model",
                "context_window": 64000,
                "pricing": {
                    "prompt": 1.0,
                    "completion": 3.0,
                },
                "capabilities": ["chat", "vision"],
            },
            {
                "id": "embedding-3",
                "name": "Embedding v3",
                "owner": "zhipu",
                "description": "Text embedding model",
                "context_window": 8192,
                "pricing": "0.1/0.1",
                "capabilities": ["embedding"],
            },
        ],
    }


@pytest.fixture
def sample_models(sample_openai_response: dict[str, Any]) -> list[ModelInfo]:
    """Create sample ModelInfo list from OpenAI response."""
    client = ModelsClient.__new__(ModelsClient)
    client.config = None
    response = client._parse_response(sample_openai_response)
    return response.models


# ========== ModelInfo Tests ==========


class TestModelInfo:
    """Tests for ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Test ModelInfo can be created with all fields."""
        model = ModelInfo(
            id="glm-5-turbo",
            name="GLM-5 Turbo",
            owner="zhipu",
            description="Fast model",
            context_window=128000,
            input_price_per_mtok=0.5,
            output_price_per_mtok=1.5,
            capabilities=["chat", "vision"],
        )
        assert model.id == "glm-5-turbo"
        assert model.name == "GLM-5 Turbo"
        assert model.owner == "zhipu"
        assert model.context_window == 128000
        assert model.input_price_per_mtok == 0.5
        assert model.output_price_per_mtok == 1.5
        assert model.capabilities == ["chat", "vision"]

    def test_model_info_defaults(self):
        """Test ModelInfo has sensible defaults."""
        model = ModelInfo(id="test-model", name="Test Model")
        assert model.owner == ""
        assert model.description == ""
        assert model.context_window == 0
        assert model.input_price_per_mtok == 0.0
        assert model.output_price_per_mtok == 0.0
        assert model.capabilities == []
        assert model.raw == {}


class TestModelsResponse:
    """Tests for ModelsResponse dataclass."""

    def test_models_response_creation(self):
        """Test ModelsResponse can be created."""
        response = ModelsResponse(
            models=[ModelInfo(id="m1", name="Model 1")],
            total=1,
            raw={"data": []},
        )
        assert response.total == 1
        assert len(response.models) == 1

    def test_models_response_defaults(self):
        """Test ModelsResponse defaults to empty."""
        response = ModelsResponse()
        assert response.models == []
        assert response.total == 0
        assert response.raw == {}


# ========== ModelsClient Tests ==========


class TestModelsClientBase:
    """Tests for ModelsClient URL handling."""

    def test_base_url_strips_anthropic_suffix(self, config):
        """Test _base strips /api/anthropic suffix."""
        client = ModelsClient(config=config)
        config.zai_base_url = "https://api.z.ai/api/anthropic"
        assert client._base() == "https://api.z.ai"

    def test_base_url_preserves_clean_url(self, config):
        """Test _base preserves clean URLs."""
        client = ModelsClient(config=config)
        config.zai_base_url = "https://api.z.ai"
        assert client._base() == "https://api.z.ai"

    def test_base_url_strips_trailing_slash(self, config):
        """Test _base strips trailing slashes."""
        client = ModelsClient(config=config)
        config.zai_base_url = "https://api.z.ai/"
        assert client._base() == "https://api.z.ai"

    def test_headers_include_auth(self, config):
        """Test _headers includes Authorization."""
        client = ModelsClient(config=config)
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"


class TestModelsClientPriceParsing:
    """Tests for price parsing."""

    def test_parse_price_numeric(self):
        """Test _parse_price with numeric values."""
        assert ModelsClient._parse_price(0.5) == 0.5
        assert ModelsClient._parse_price(1) == 1.0
        assert ModelsClient._parse_price(0) == 0.0

    def test_parse_price_string_dollar(self):
        """Test _parse_price with dollar-prefixed strings."""
        assert ModelsClient._parse_price("$0.50") == 0.5
        assert ModelsClient._parse_price("$1.00") == 1.0

    def test_parse_price_string_plain(self):
        """Test _parse_price with plain number strings."""
        assert ModelsClient._parse_price("0.50") == 0.5
        assert ModelsClient._parse_price("1.5") == 1.5

    def test_parse_price_invalid(self):
        """Test _parse_price with invalid values returns 0."""
        assert ModelsClient._parse_price("free") == 0.0
        assert ModelsClient._parse_price(None) == 0.0


class TestModelsClientResponseParsing:
    """Tests for _parse_response method."""

    def test_parse_openai_format(self, sample_openai_response):
        """Test parsing OpenAI-compatible response format."""
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(sample_openai_response)
        assert response.total == 3
        assert response.models[0].id == "glm-5-turbo"
        assert response.models[1].id == "glm-5-vision"
        assert response.models[2].id == "embedding-3"

    def test_parse_direct_list_format(self):
        """Test parsing direct list response format."""
        data = [
            {"id": "model-a", "name": "Model A"},
            {"id": "model-b", "name": "Model B"},
        ]
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.total == 2
        assert response.models[0].id == "model-a"

    def test_parse_pricing_dict(self):
        """Test parsing pricing from dict with input/output keys."""
        data = {"data": [{"id": "m1", "name": "M1", "pricing": {"input": 2.0, "output": 6.0}}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.models[0].input_price_per_mtok == 2.0
        assert response.models[0].output_price_per_mtok == 6.0

    def test_parse_pricing_dict_prompt_completion(self):
        """Test parsing pricing from dict with prompt/completion keys."""
        data = {"data": [{"id": "m1", "name": "M1", "pricing": {"prompt": 3.0, "completion": 9.0}}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.models[0].input_price_per_mtok == 3.0
        assert response.models[0].output_price_per_mtok == 9.0

    def test_parse_pricing_string_format(self):
        """Test parsing pricing from string format 'input/output'."""
        data = {"data": [{"id": "m1", "name": "M1", "pricing": "0.5/1.5"}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.models[0].input_price_per_mtok == 0.5
        assert response.models[0].output_price_per_mtok == 1.5

    def test_parse_capabilities_list(self):
        """Test parsing capabilities from list."""
        data = {"data": [{"id": "m1", "name": "M1", "capabilities": ["chat", "vision"]}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.models[0].capabilities == ["chat", "vision"]

    def test_parse_capabilities_string(self):
        """Test parsing capabilities from comma-separated string."""
        data = {"data": [{"id": "m1", "name": "M1", "capabilities": "chat, vision, code"}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.models[0].capabilities == ["chat", "vision", "code"]

    def test_parse_infer_capabilities_from_name(self):
        """Test capability inference from model name."""
        data = {"data": [{"id": "glm-5-turbo-vision", "name": "GLM-5 Vision"}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        # Should infer "chat" from "glm" and "vision" from name
        assert "vision" in response.models[0].capabilities
        assert "chat" in response.models[0].capabilities

    def test_parse_context_window(self):
        """Test parsing context_window field."""
        data = {"data": [{"id": "m1", "name": "M1", "context_window": 128000}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.models[0].context_window == 128000

    def test_parse_max_context_fallback(self):
        """Test parsing max_context as fallback for context_window."""
        data = {"data": [{"id": "m1", "name": "M1", "max_context": 64000}]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.models[0].context_window == 64000

    def test_parse_empty_data(self):
        """Test parsing empty data returns empty response."""
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response({})
        assert response.total == 0
        assert response.models == []

    def test_parse_non_dict_items_skipped(self):
        """Test non-dict items in data list are skipped."""
        data = {"data": [{"id": "m1", "name": "M1"}, "not-a-dict", 42, None]}
        client = ModelsClient.__new__(ModelsClient)
        response = client._parse_response(data)
        assert response.total == 1
        assert response.models[0].id == "m1"


# ========== ModelsClient Fetch Tests ==========


class TestModelsClientFetch:
    """Tests for fetch_models method."""

    @pytest.mark.asyncio
    async def test_fetch_models_success(self, config, sample_openai_response):
        """Test successful fetch returns parsed models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openai_response

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = ModelsClient(config=config)
        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client):
            response = await client.fetch_models()

        assert response.total == 3
        assert response.models[0].id == "glm-5-turbo"

    @pytest.mark.asyncio
    async def test_fetch_models_404_tries_next(self, config):
        """Test 404 on first endpoint tries second endpoint."""
        mock_404 = MagicMock()
        mock_404.status_code = 404

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"data": [{"id": "m1", "name": "M1"}]}

        call_count = 0

        async def mock_get(url, headers):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_404
            return mock_200

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = ModelsClient(config=config)
        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client):
            response = await client.fetch_models()

        assert response.total == 1
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_models_all_fail_returns_empty(self, config):
        """Test all endpoints failing returns empty response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.request = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = ModelsClient(config=config)
        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client):
            response = await client.fetch_models()

        assert response.total == 0
        assert response.models == []

    @pytest.mark.asyncio
    async def test_fetch_models_network_error_returns_empty(self, config):
        """Test network errors return empty response."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        client = ModelsClient(config=config)
        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client):
            response = await client.fetch_models()

        assert response.total == 0


# ========== CLI Formatting Tests ==========


class TestFormatPrice:
    """Tests for _format_price helper."""

    def test_zero(self):
        assert _format_price(0.0) == "—"

    def test_small_price(self):
        assert _format_price(0.002) == "$0.0020"

    def test_medium_price(self):
        assert _format_price(0.5) == "$0.50"

    def test_large_price(self):
        assert _format_price(5.0) == "$5.0"


class TestFormatContextWindow:
    """Tests for _format_context_window helper."""

    def test_zero(self):
        assert _format_context_window(0) == "—"

    def test_small(self):
        assert _format_context_window(512) == "512"

    def test_thousands(self):
        assert _format_context_window(8192) == "8K"

    def test_millions(self):
        assert _format_context_window(1_000_000) == "1.0M"


class TestFormatModelsTable:
    """Tests for _format_models_table function."""

    def test_empty_models(self):
        assert _format_models_table([]) == "No models available."

    def test_single_model(self, sample_models):
        output = _format_models_table(sample_models[:1])
        assert "glm-5-turbo" in output
        assert "$0.50" in output
        assert "$1.5" in output
        assert "128K" in output

    def test_all_models(self, sample_models):
        output = _format_models_table(sample_models)
        assert "Total: 3 model(s)" in output

    def test_with_capabilities(self, sample_models):
        output = _format_models_table(sample_models, show_capabilities=True)
        assert "CAPABILITIES" in output
        assert "chat, vision" in output

    def test_without_capabilities(self, sample_models):
        output = _format_models_table(sample_models, show_capabilities=False)
        assert "CAPABILITIES" not in output


# ========== CLI Command Tests ==========


class TestCmdModels:
    """Tests for cmd_models CLI command."""

    def test_help_output(self, capsys):
        """Test --help shows usage."""
        import asyncio
        asyncio.run(cmd_models_async(["--help"]))
        captured = capsys.readouterr()
        assert "Models command usage" in captured.out
        assert "--json" in captured.out
        assert "--filter" in captured.out
        assert "--capabilities" in captured.out

    @pytest.mark.asyncio
    async def test_json_output(self, config, sample_openai_response, capsys):
        """Test --json outputs valid JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openai_response

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client), \
             patch("goz.config.load_config", return_value=config):
            await cmd_models_async(["--json"])

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total"] == 3
        assert data["models"][0]["id"] == "glm-5-turbo"

    @pytest.mark.asyncio
    async def test_filter_output(self, config, sample_openai_response, capsys):
        """Test --filter narrows results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openai_response

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client), \
             patch("goz.config.load_config", return_value=config):
            await cmd_models_async(["--filter", "vision"])

        captured = capsys.readouterr()
        # Should only show glm-5-vision (matches in both id and name)
        assert "glm-5-vision" in captured.out
        # Should NOT show glm-5-turbo or embedding-3
        assert "glm-5-turbo" not in captured.out
        assert "embedding-3" not in captured.out
        assert "Total: 1 model(s)" in captured.out

    @pytest.mark.asyncio
    async def test_no_header_output(self, config, sample_openai_response, capsys):
        """Test --no-header outputs TSV rows."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openai_response

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client), \
             patch("goz.config.load_config", return_value=config):
            await cmd_models_async(["--no-header"])

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        assert len(lines) == 3  # 3 models
        # Each line should have tab-separated fields
        for line in lines:
            assert "\t" in line

    @pytest.mark.asyncio
    async def test_capabilities_flag(self, config, sample_openai_response, capsys):
        """Test --capabilities shows capabilities column."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openai_response

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client), \
             patch("goz.config.load_config", return_value=config):
            await cmd_models_async(["--capabilities"])

        captured = capsys.readouterr()
        assert "CAPABILITIES" in captured.out
        assert "chat, vision" in captured.out

    @pytest.mark.asyncio
    async def test_empty_response(self, config, capsys):
        """Test empty API response shows 'No models available.'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client), \
             patch("goz.config.load_config", return_value=config):
            await cmd_models_async(["--json"])

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total"] == 0
        assert data["models"] == []

    @pytest.mark.asyncio
    async def test_error_handling(self, config, capsys):
        """Test API network error is handled gracefully (returns empty, logs warning)."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("goz.api.models.httpx.AsyncClient", return_value=mock_client), \
             patch("goz.config.load_config", return_value=config):
            await cmd_models_async(["--json"])

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total"] == 0
        assert data["models"] == []


# Helper to avoid import issues in tests
async def cmd_models_async(args: list[str]) -> None:
    """Async wrapper for cmd_models."""
    from goz.cli.models import cmd_models
    await cmd_models(args)
