"""Tests for T-0008: Usage statistics and quota tracking.

Acceptance criteria tested:
- chat_client.py extracts usage.input_tokens and usage.output_tokens from streaming events
- Per-turn token counts accumulated in session state via UsageAccumulator
- step_finish JSONL event includes tokens and cost
- goz usage command calls monitor endpoints
- Quota/rate limit errors are detected and reported clearly
"""

from __future__ import annotations

import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from goz.agent.chat_client import (
    ChatClient,
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageStart,
    MessageStop,
    UsageDelta,
)
from goz.agent.usage import UsageAccumulator, UsageSnapshot
from goz.api.errors import QuotaError, is_quota_error
from goz.cli.run import emit_step_finish_event, run_prompt_jsonl
from goz.config import Config


@pytest.fixture
def config() -> Config:
    return Config(
        zai_token="test-token",
        zai_base_url="https://api.test.com",
        chat_model="test-model",
        timeout=60,
    )


class TestMessageStartUsageExtraction:
    def test_message_start_carries_usage_fields(self):
        ms = MessageStart(
            id="msg_1",
            model="glm-5-turbo",
            usage_input_tokens=1500,
            usage_cache_read=800,
            usage_cache_creation=200,
        )
        assert ms.usage_input_tokens == 1500
        assert ms.usage_cache_read == 800
        assert ms.usage_cache_creation == 200

    def test_message_start_defaults_to_zero(self):
        ms = MessageStart(id="msg_1", model="test")
        assert ms.usage_input_tokens == 0
        assert ms.usage_cache_read == 0
        assert ms.usage_cache_creation == 0

    def test_convert_message_start_extracts_usage(self, config):
        client = ChatClient(config)

        usage = MagicMock()
        usage.input_tokens = 2000
        usage.cache_read_input_tokens = 500
        usage.cache_creation_input_tokens = 100

        msg = MagicMock()
        msg.id = "msg_abc"
        msg.model = "glm-5-turbo"
        msg.usage = usage

        event = MagicMock()
        event.type = "message_start"
        event.message = msg

        chunk = client._convert_sse_event_to_chunk(event)
        assert isinstance(chunk, MessageStart)
        assert chunk.usage_input_tokens == 2000
        assert chunk.usage_cache_read == 500
        assert chunk.usage_cache_creation == 100

    def test_convert_message_start_handles_missing_usage(self, config):
        client = ChatClient(config)

        msg = MagicMock()
        msg.id = "msg_abc"
        msg.model = "glm-5-turbo"
        msg.usage = None

        event = MagicMock()
        event.type = "message_start"
        event.message = msg

        chunk = client._convert_sse_event_to_chunk(event)
        assert isinstance(chunk, MessageStart)
        assert chunk.usage_input_tokens == 0
        assert chunk.usage_cache_read == 0


class TestUsageDeltaChunk:
    def test_usage_delta_has_output_tokens(self):
        ud = UsageDelta(output_tokens=42)
        assert ud.output_tokens == 42

    def test_usage_delta_defaults_to_zero(self):
        ud = UsageDelta()
        assert ud.output_tokens == 0

    def test_convert_message_delta_extracts_output_tokens(self, config):
        client = ChatClient(config)

        event = MagicMock()
        event.type = "message_delta"
        event.usage = MagicMock()
        event.usage.output_tokens = 350

        chunk = client._convert_sse_event_to_chunk(event)
        assert isinstance(chunk, UsageDelta)
        assert chunk.output_tokens == 350

    def test_convert_message_delta_handles_missing_usage(self, config):
        client = ChatClient(config)

        event = MagicMock()
        event.type = "message_delta"
        event.usage = None

        chunk = client._convert_sse_event_to_chunk(event)
        assert isinstance(chunk, UsageDelta)
        assert chunk.output_tokens == 0

    def test_message_stop_carries_usage(self):
        ms = MessageStop(stop_reason="end_turn", usage_output_tokens=500)
        assert ms.usage_output_tokens == 500

    def test_message_stop_defaults_to_zero(self):
        ms = MessageStop(stop_reason="end_turn")
        assert ms.usage_output_tokens == 0


class TestUsageAccumulator:
    def test_full_turn_accumulation(self):
        acc = UsageAccumulator()
        acc.begin_turn()

        class UsageStart:
            input_tokens = 1000
            cache_read_input_tokens = 200
            cache_creation_input_tokens = 50

        acc.apply_message_start(UsageStart())

        class UsageEnd:
            output_tokens = 500

        acc.apply_message_delta(UsageEnd())

        snap = acc.finalise_turn()
        assert snap.input_tokens == 1000
        assert snap.output_tokens == 500
        assert snap.cache_read_input_tokens == 200
        assert snap.cache_creation_input_tokens == 50

        assert acc.total_input_tokens == 1000
        assert acc.total_output_tokens == 500
        assert acc.turn_count == 1

    def test_multi_turn_accumulation(self):
        acc = UsageAccumulator()

        for i in range(3):
            acc.begin_turn()

            class UStart:
                input_tokens = 100
                cache_read_input_tokens = 0
                cache_creation_input_tokens = 0

            acc.apply_message_start(UStart())

            class UDelta:
                output_tokens = 50

            acc.apply_message_delta(UDelta())
            acc.finalise_turn()

        assert acc.turn_count == 3
        assert acc.total_input_tokens == 300
        assert acc.total_output_tokens == 150

    def test_snapshot_to_dict(self):
        snap = UsageSnapshot(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=20,
            cache_creation_input_tokens=10,
        )
        d = snap.to_dict()
        assert d == {"input": 100, "output": 50, "cache_read": 20, "cache_creation": 10}

    def test_snapshot_cost_usd(self):
        snap = UsageSnapshot(input_tokens=1_000_000, output_tokens=1_000_000)
        cost = snap.cost_usd(model="claude-sonnet-4-20250514")
        assert cost > 0
        assert abs(cost - 18.0) < 0.01

    def test_finalise_turn_empty(self):
        acc = UsageAccumulator()
        snap = acc.finalise_turn()
        assert snap.total_tokens() == 0


class TestStepFinishWithUsage:
    def test_emit_step_finish_with_tokens_and_cost(self):
        stdout = io.StringIO()
        tokens = {"input": 1000, "output": 500, "cache_creation": 50, "cache_read": 200}
        emit_step_finish_event(stdout, "session-1", tokens=tokens, cost=0.015)
        event = json.loads(stdout.getvalue().strip())
        assert event["type"] == "step_finish"
        assert event["part"]["tokens"] == tokens
        assert event["part"]["cost"] == 0.015
        assert event["part"]["session_id"] == "session-1"
        assert event["part"]["continuation"] == {"resume_session_id": "session-1"}

    def test_emit_step_finish_defaults(self):
        stdout = io.StringIO()
        emit_step_finish_event(stdout, "session-2")
        event = json.loads(stdout.getvalue().strip())
        assert event["part"]["tokens"] == {
            "input": 0,
            "output": 0,
            "cache_creation": 0,
            "cache_read": 0,
        }
        assert event["part"]["cost"] == 0.0
        assert event["part"]["continuation"] == {"resume_session_id": "session-2"}


class TestRunPromptJsonlWithUsage:
    @pytest.mark.asyncio
    async def test_step_finish_includes_real_usage(self, config, tmp_path):
        stream = [
            MessageStart(
                id="msg_1",
                model="glm-5-turbo",
                usage_input_tokens=800,
                usage_cache_read=100,
                usage_cache_creation=50,
            ),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Done"),
            ContentBlockStop(index=0),
            UsageDelta(output_tokens=200),
            MessageStop(stop_reason="end_turn"),
        ]

        class FakeClient:
            def __init__(self, *, config):
                self.config = config

            def chat_completion(self, **kwargs):
                async def gen():
                    for chunk in stream:
                        yield chunk

                return gen()

        stdout = io.StringIO()
        exit_code = await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=FakeClient(config=config),
        )
        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        finish = events[-1]
        assert finish["type"] == "step_finish"
        assert finish["part"]["tokens"]["input"] == 800
        assert finish["part"]["tokens"]["output"] == 200
        assert finish["part"]["tokens"]["cache_read"] == 100
        assert finish["part"]["tokens"]["cache_creation"] == 50
        assert finish["part"]["cost"] > 0


class TestQuotaErrorDetection:
    def test_quota_error_is_detected(self):
        err = QuotaError("exceeded", zai_code=1302)
        assert is_quota_error(err)
        assert err.zai_code == 1302

    def test_all_quota_codes_detected(self):
        for code in (1302, 1305, 1308, 1310):
            err = QuotaError("test", zai_code=code)
            assert is_quota_error(err)

    def test_non_quota_error_not_detected(self):
        from goz.api.errors import ApiError

        err = ApiError("regular error")
        assert not is_quota_error(err)

    @pytest.mark.asyncio
    async def test_chat_client_raises_quota_error_for_zai_code(self, config):
        import anthropic

        client = ChatClient(config)
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = '{"error":{"code":1302,"message":"Quota exceeded"}}'

        with patch.object(client._client, "messages") as mock_messages:

            class ErrorCtx:
                async def __aenter__(self):
                    raise anthropic.APIStatusError(
                        message="Quota exceeded",
                        response=mock_response,
                        body={"error": {"code": 1302, "message": "Quota exceeded"}},
                    )

                async def __aexit__(self, *a):
                    pass

            mock_messages.stream.side_effect = [ErrorCtx()]
            with pytest.raises(QuotaError) as exc_info:
                async for _ in client.chat_completion(messages):
                    pass
            assert exc_info.value.zai_code == 1302


class TestMonitorClient:
    @pytest.mark.asyncio
    async def test_fetch_quota_limit(self, config):
        from goz.api.monitor import MonitorClient

        client = MonitorClient(config=config)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 200,
            "data": {
                "limits": [
                    {
                        "type": "TIME_LIMIT",
                        "unit": 5,
                        "usage": 4000,
                        "currentValue": 10,
                        "remaining": 3990,
                        "percentage": 1,
                        "nextResetTime": 1777298698998,
                        "usageDetails": [{"modelCode": "search-prime", "usage": 10}],
                    },
                    {
                        "type": "TOKENS_LIMIT",
                        "unit": 3,
                        "percentage": 3,
                        "nextResetTime": 1775396941330,
                    },
                ],
                "level": "max",
            },
            "success": True,
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("goz.api.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            quota = await client.fetch_quota_limit()

        assert quota.level == "max"
        assert len(quota.limits) == 2
        time_lim = quota.limits[0]
        assert time_lim.type == "TIME_LIMIT"
        assert time_lim.limit == 4000
        assert time_lim.used == 10
        assert time_lim.remaining == 3990

    @pytest.mark.asyncio
    async def test_fetch_model_usage(self, config):
        from goz.api.monitor import MonitorClient

        client = MonitorClient(config=config)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "model": "glm-5-turbo",
                    "input_tokens": 100000,
                    "output_tokens": 50000,
                    "total_tokens": 150000,
                    "cost": 1.25,
                    "requests": 42,
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("goz.api.monitor.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            report = await client.fetch_model_usage(days=7)

        assert report.period_days == 7
        assert len(report.entries) == 1
        assert report.entries[0].model == "glm-5-turbo"
        assert report.entries[0].input_tokens == 100000
        assert report.entries[0].output_tokens == 50000
        assert report.entries[0].cost == 1.25
        assert report.entries[0].requests == 42


class TestUsageCommand:
    @pytest.mark.asyncio
    async def test_cmd_usage_json_output(self, config, capsys):
        from goz.api.monitor import QuotaInfo, QuotaLimit, ModelUsageReport, ModelUsageEntry
        from goz.cli.usage import cmd_usage

        mock_monitor = MagicMock()
        mock_monitor.fetch_quota_limit = AsyncMock(
            return_value=QuotaInfo(
                level="max",
                limits=[
                    QuotaLimit(type="TIME_LIMIT", limit=4000, used=10, remaining=3990, percentage=1, window_hours=5, reset_at=None),
                    QuotaLimit(type="TOKENS_LIMIT", limit=0, used=0, remaining=0, percentage=3, window_hours=3, reset_at=None),
                ],
            )
        )
        mock_monitor.fetch_model_usage = AsyncMock(
            side_effect=lambda days=7: ModelUsageReport(
                period_days=days,
                entries=[
                    ModelUsageEntry(
                        model="glm-5-turbo",
                        input_tokens=100000,
                        output_tokens=50000,
                        total_tokens=150000,
                        cost=1.25,
                        requests=42,
                    )
                ],
            )
        )

        with (
            patch("goz.cli.usage.load_config", return_value=config),
            patch("goz.api.monitor.MonitorClient", return_value=mock_monitor),
        ):
            await cmd_usage(["--json"])

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "level" in data
        assert data["level"] == "max"
        assert "limits" in data
        assert len(data["limits"]) == 2
        assert "7_day" in data
        assert data["7_day"][0]["model"] == "glm-5-turbo"
