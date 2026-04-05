"""Tests for error recovery: retries, rate-limit handling, quota errors."""

from __future__ import annotations

import asyncio
import io
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from goz.agent.history import ChatMessage, ChatHistory
from goz.agent.tools.registry import ToolRegistry
from goz.api.errors import ApiError, TimeoutError as ApiTimeoutError, AuthError, NetworkError, QuotaError
from goz.cli.run import (
    AGENT_LOOP_BACKOFF_DELAYS,
    AGENT_LOOP_MAX_RETRIES,
    _execute_tool_call,
    _is_transient_tool_error,
    is_retryable_error,
)
from goz.config import Config
from goz.agent.chat_client import (
    ContentBlockDelta,
    MessageStart,
    UsageDelta,
)


# ---------------------------------------------------------------------------
# is_retryable_error
# ---------------------------------------------------------------------------

class TestIsRetryableError:
    def test_auth_error_not_retryable(self):
        assert not is_retryable_error(AuthError("bad key"))

    def test_quota_error_not_retryable(self):
        assert not is_retryable_error(QuotaError(message="over limit"))

    def test_api_error_429_retryable(self):
        err = ApiError("rate limited", statusCode=429)
        assert is_retryable_error(err)

    def test_api_error_500_retryable(self):
        err = ApiError("internal error", statusCode=500)
        assert is_retryable_error(err)

    def test_api_error_502_retryable(self):
        err = ApiError("bad gateway", statusCode=502)
        assert is_retryable_error(err)

    def test_api_error_400_not_retryable(self):
        err = ApiError("bad request", statusCode=400)
        assert not is_retryable_error(err)

    def test_api_error_404_not_retryable(self):
        err = ApiError("not found", statusCode=404)
        assert not is_retryable_error(err)

    def test_network_error_retryable(self):
        assert is_retryable_error(NetworkError("connection reset"))

    def test_timeout_error_retryable(self):
        assert is_retryable_error(ApiTimeoutError("timed out"))

    def test_connection_error_retryable(self):
        assert is_retryable_error(ConnectionError("refused"))

    def test_timeout_error_builtin_retryable(self):
        assert is_retryable_error(TimeoutError("deadline exceeded"))

    def test_generic_error_not_retryable(self):
        assert not is_retryable_error(ValueError("bad value"))


# ---------------------------------------------------------------------------
# _is_transient_tool_error
# ---------------------------------------------------------------------------

class TestIsTransientToolError:
    def test_timeout_is_transient(self):
        assert _is_transient_tool_error(asyncio.TimeoutError())

    def test_connection_error_is_transient(self):
        assert _is_transient_tool_error(ConnectionError("refused"))

    def test_timeout_error_is_transient(self):
        assert _is_transient_tool_error(TimeoutError("deadline"))

    def test_value_error_is_not_transient(self):
        assert not _is_transient_tool_error(ValueError("bad input"))


# ---------------------------------------------------------------------------
# _execute_tool_call retry
# ---------------------------------------------------------------------------

class TestExecuteToolCallRetry:
    @pytest.fixture
    def registry(self) -> ToolRegistry:
        reg = ToolRegistry()
        tool = MagicMock()
        tool.name = "bash"
        return reg

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        tool = MagicMock()
        tool.name = "bash"
        tool.execute = AsyncMock(return_value="ok")

        registry = ToolRegistry()
        registry.register(tool)

        result, is_error = await _execute_tool_call(
            registry,
            {"id": "c1", "name": "bash", "input": {"command": "echo hi"}},
        )
        assert result == "ok"
        assert not is_error
        assert tool.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_transient_error_retried(self):
        tool = MagicMock()
        tool.name = "bash"

        call_count = 0

        async def _execute(**kwargs: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError()
            return "success"

        tool.execute = _execute

        registry = ToolRegistry()
        registry.register(tool)

        result, is_error = await _execute_tool_call(
            registry,
            {"id": "c1", "name": "bash", "input": {"command": "echo hi"}},
        )
        assert result == "success"
        assert not is_error
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_transient_error_no_retry(self):
        tool = MagicMock()
        tool.name = "bash"
        tool.execute = AsyncMock(side_effect=ValueError("bad input"))

        registry = ToolRegistry()
        registry.register(tool)

        result, is_error = await _execute_tool_call(
            registry,
            {"id": "c1", "name": "bash", "input": {"command": "echo hi"}},
        )
        assert is_error
        assert "bad input" in result
        assert tool.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_transient_error_twice_fails(self):
        tool = MagicMock()
        tool.name = "bash"
        tool.execute = AsyncMock(side_effect=asyncio.TimeoutError())

        registry = ToolRegistry()
        registry.register(tool)

        result, is_error = await _execute_tool_call(
            registry,
            {"id": "c1", "name": "bash", "input": {"command": "echo hi"}},
        )
        assert is_error
        assert tool.execute.call_count == 2  # initial + 1 retry


# ---------------------------------------------------------------------------
# Agent loop retry (integration-level)
# ---------------------------------------------------------------------------

def _make_text_chunk(text: str) -> ContentBlockDelta:
    return ContentBlockDelta(type="text_delta", index=0, text=text)


def _make_message_start() -> MessageStart:
    return MessageStart(
        id="msg_test",
        model="test-model",
        usage_input_tokens=10,
        usage_cache_read=0,
        usage_cache_creation=0,
    )


def _make_usage_delta() -> UsageDelta:
    return UsageDelta(output_tokens=5)


class TestAgentLoopRetry:
    """Test the agent loop retry logic in run_prompt_jsonl."""

    @pytest.mark.asyncio
    async def test_quota_error_emits_event_and_returns_2(self):
        from goz.cli.run import run_prompt_jsonl

        config = Config(zai_token="test-token", chat_model="test-model")
        client = MagicMock()
        call_count = 0

        async def _failing_stream(**kwargs: Any):
            nonlocal call_count
            call_count += 1
            raise QuotaError(
                message="Token quota exceeded",
                zai_code=1302,
            )
            yield  # make this an async generator  # noqa: unreachable

        client.chat_completion = _failing_stream

        buf = io.StringIO()
        exit_code = await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir="/tmp",
            stdout=buf,
            chat_client=client,
            no_context=True,
        )
        assert exit_code == 2

        output = buf.getvalue()
        # Should contain a quota_exceeded event
        lines = [l for l in output.strip().split("\n") if l.strip()]
        found_quota = False
        for line in lines:
            evt = json.loads(line)
            if evt.get("type") == "quota_exceeded":
                found_quota = True
                assert evt["error"]["code"] == "QuotaExceededError"
                assert "Token quota exceeded" in evt["error"]["message"]
        assert found_quota, f"Expected quota_exceeded event, got: {lines}"

    @pytest.mark.asyncio
    async def test_retryable_error_retried_then_succeeds(self):
        from goz.cli.run import run_prompt_jsonl

        config = Config(zai_token="test-token", chat_model="test-model")
        client = MagicMock()
        call_count = 0

        async def _stream(**kwargs: Any):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise NetworkError("connection reset")
            # Second call succeeds with a simple text response
            yield _make_message_start()
            yield _make_text_chunk("hello")
            yield _make_usage_delta()

        client.chat_completion = _stream

        buf = io.StringIO()
        with patch("goz.cli.run.asyncio.sleep", new_callable=AsyncMock):
            exit_code = await run_prompt_jsonl(
                "test prompt",
                config=config,
                working_dir="/tmp",
                stdout=buf,
                chat_client=client,
                no_context=True,
            )
        assert exit_code == 0
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises(self):
        from goz.cli.run import run_prompt_jsonl

        config = Config(zai_token="test-token", chat_model="test-model")
        client = MagicMock()

        async def _stream(**kwargs: Any):
            raise ValueError("something unexpected")
            yield  # make this an async generator  # noqa: unreachable

        client.chat_completion = _stream

        buf = io.StringIO()
        with pytest.raises(ValueError, match="something unexpected"):
            await run_prompt_jsonl(
                "test prompt",
                config=config,
                working_dir="/tmp",
                stdout=buf,
                chat_client=client,
                no_context=True,
            )

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_raises(self):
        from goz.cli.run import run_prompt_jsonl

        config = Config(zai_token="test-token", chat_model="test-model")
        client = MagicMock()

        async def _stream(**kwargs: Any):
            raise NetworkError("persistent failure")
            yield  # make this an async generator  # noqa: unreachable

        client.chat_completion = _stream

        buf = io.StringIO()
        with patch("goz.cli.run.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(NetworkError, match="persistent failure"):
                await run_prompt_jsonl(
                    "test prompt",
                    config=config,
                    working_dir="/tmp",
                    stdout=buf,
                    chat_client=client,
                    no_context=True,
                )

    @pytest.mark.asyncio
    async def test_auth_error_not_retried(self):
        from goz.cli.run import run_prompt_jsonl

        config = Config(zai_token="test-token", chat_model="test-model")
        client = MagicMock()
        call_count = 0

        async def _stream(**kwargs: Any):
            nonlocal call_count
            call_count += 1
            raise AuthError("invalid API key")
            yield  # make this an async generator  # noqa: unreachable

        client.chat_completion = _stream

        buf = io.StringIO()
        with pytest.raises(AuthError, match="invalid API key"):
            await run_prompt_jsonl(
                "test prompt",
                config=config,
                working_dir="/tmp",
                stdout=buf,
                chat_client=client,
                no_context=True,
            )
        # Should only be called once (no retry)
        assert call_count == 1
