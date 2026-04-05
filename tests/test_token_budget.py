"""Tests for T-0022: Token budgeting with auto-stop and warnings.

Acceptance criteria tested:
- TokenBudget tracks cumulative input+output tokens via UsageAccumulator
- Warning emitted at 80% budget consumption
- budget_exceeded event emitted when stopping
- Without budget, no limit is enforced (current behavior)
- --max-tokens-budget CLI flag passes through to run_prompt_jsonl
"""

from __future__ import annotations

import io
import json
import sys
from unittest.mock import patch

import pytest

from goz.agent.chat_client import (
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageStart,
    MessageStop,
    UsageDelta,
)
from goz.agent.usage import TokenBudget, UsageAccumulator
from goz.cli.run import (
    emit_budget_exceeded_event,
    emit_budget_warning_event,
    run_prompt_jsonl,
)
from goz.config import Config


class FakeChatClient:
    def __init__(self, streams, *, config):
        self.streams = list(streams)
        self.config = config
        self.calls: list[dict] = []

    def chat_completion(self, **kwargs):
        self.calls.append(kwargs)
        stream = self.streams.pop(0)

        async def iterator():
            for chunk in stream:
                yield chunk

        return iterator()


@pytest.fixture
def config() -> Config:
    return Config(
        zai_token="test-token",
        zai_base_url="https://api.test.com",
        chat_model="test-model",
        timeout=60,
    )


class TestTokenBudget:
    def test_no_warning_when_below_threshold(self):
        budget = TokenBudget(budget=1000)
        acc = UsageAccumulator()
        acc.total_input_tokens = 500
        acc.total_output_tokens = 200
        should_warn, should_stop = budget.check(acc)
        assert not should_warn
        assert not should_stop

    def test_warning_at_80_percent(self):
        budget = TokenBudget(budget=1000)
        acc = UsageAccumulator()
        acc.total_input_tokens = 600
        acc.total_output_tokens = 200  # total=800 = 80%
        should_warn, should_stop = budget.check(acc)
        assert should_warn
        assert not should_stop

    def test_warning_emitted_only_once(self):
        budget = TokenBudget(budget=1000)
        acc = UsageAccumulator()
        acc.total_input_tokens = 800
        acc.total_output_tokens = 0

        should_warn1, _ = budget.check(acc)
        assert should_warn1

        # Same totals — no second warning
        should_warn2, _ = budget.check(acc)
        assert not should_warn2

    def test_stop_at_100_percent(self):
        budget = TokenBudget(budget=1000)
        acc = UsageAccumulator()
        acc.total_input_tokens = 600
        acc.total_output_tokens = 400  # total=1000
        should_warn, should_stop = budget.check(acc)
        assert should_stop

    def test_stop_when_exceeded(self):
        budget = TokenBudget(budget=1000)
        acc = UsageAccumulator()
        acc.total_input_tokens = 700
        acc.total_output_tokens = 400  # total=1100
        should_warn, should_stop = budget.check(acc)
        assert should_stop
        assert budget.exceeded

    def test_custom_warning_threshold(self):
        budget = TokenBudget(budget=1000, warning_threshold=0.5)
        acc = UsageAccumulator()
        acc.total_input_tokens = 500
        acc.total_output_tokens = 0  # total=500 = 50%
        should_warn, should_stop = budget.check(acc)
        assert should_warn
        assert not should_stop

    def test_no_warning_when_exactly_below_threshold(self):
        budget = TokenBudget(budget=1000)
        acc = UsageAccumulator()
        acc.total_input_tokens = 799
        acc.total_output_tokens = 0  # total=799 < 800
        should_warn, should_stop = budget.check(acc)
        assert not should_warn
        assert not should_stop


class TestBudgetEventEmitters:
    def test_emit_budget_warning_event(self):
        stdout = io.StringIO()
        emit_budget_warning_event(stdout, total_tokens=800, budget=1000, threshold=0.8)
        event = json.loads(stdout.getvalue().strip())
        assert event["type"] == "budget_warning"
        assert event["part"]["total_tokens"] == 800
        assert event["part"]["budget"] == 1000
        assert event["part"]["threshold"] == 0.8

    def test_emit_budget_exceeded_event(self):
        stdout = io.StringIO()
        emit_budget_exceeded_event(stdout, total_tokens=1050, budget=1000)
        event = json.loads(stdout.getvalue().strip())
        assert event["type"] == "budget_exceeded"
        assert event["part"]["total_tokens"] == 1050
        assert event["part"]["budget"] == 1000


class TestRunPromptJsonlWithBudget:
    @pytest.mark.asyncio
    async def test_no_budget_no_limit(self, config, tmp_path):
        """Without max_tokens_budget, the run proceeds normally."""
        stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Done"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        stdout = io.StringIO()
        chat_client = FakeChatClient([stream], config=config)

        exit_code = await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
        )
        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        types = [e["type"] for e in events]
        assert "budget_warning" not in types
        assert "budget_exceeded" not in types

    @pytest.mark.asyncio
    async def test_budget_exceeded_stops_loop(self, config, tmp_path):
        """When cumulative tokens exceed budget, the loop stops and budget_exceeded is emitted."""
        first_stream = [
            MessageStart(
                id="msg_1",
                model="test-model",
                usage_input_tokens=600,
                usage_cache_read=0,
                usage_cache_creation=0,
            ),
            ContentBlockStart(type="tool_use", index=0, id="call_1", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"echo hi"}'),
            ContentBlockStop(index=0),
            UsageDelta(output_tokens=200),
            MessageStop(stop_reason="tool_use"),
        ]
        second_stream = [
            MessageStart(
                id="msg_2",
                model="test-model",
                usage_input_tokens=300,
                usage_cache_read=0,
                usage_cache_creation=0,
            ),
            ContentBlockStart(type="tool_use", index=0, id="call_2", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"echo bye"}'),
            ContentBlockStop(index=0),
            UsageDelta(output_tokens=100),
            MessageStop(stop_reason="tool_use"),
        ]
        # third_stream would be next but budget should stop before it
        third_stream = [
            MessageStart(id="msg_3", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Should not reach"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        stdout = io.StringIO()
        chat_client = FakeChatClient([first_stream, second_stream, third_stream], config=config)

        # Budget of 1000 tokens: first turn = 600+200=800 (warning at 80%),
        # second turn = 300+100=400, cumulative = 1200 (exceeded)
        exit_code = await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
            max_tokens_budget=1000,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        types = [e["type"] for e in events]

        assert "budget_warning" in types
        assert "budget_exceeded" in types

        budget_exceeded = next(e for e in events if e["type"] == "budget_exceeded")
        assert budget_exceeded["part"]["budget"] == 1000
        assert budget_exceeded["part"]["total_tokens"] >= 1000

        # Third stream should not have been consumed
        assert len(chat_client.calls) == 2

    @pytest.mark.asyncio
    async def test_budget_warning_emitted_once(self, config, tmp_path):
        """Warning is emitted exactly once when crossing 80%."""
        first_stream = [
            MessageStart(
                id="msg_1",
                model="test-model",
                usage_input_tokens=700,
                usage_cache_read=0,
                usage_cache_creation=0,
            ),
            ContentBlockStart(type="tool_use", index=0, id="call_1", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"echo a"}'),
            ContentBlockStop(index=0),
            UsageDelta(output_tokens=100),
            MessageStop(stop_reason="tool_use"),
        ]
        second_stream = [
            MessageStart(
                id="msg_2",
                model="test-model",
                usage_input_tokens=200,
                usage_cache_read=0,
                usage_cache_creation=0,
            ),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Done"),
            ContentBlockStop(index=0),
            UsageDelta(output_tokens=50),
            MessageStop(stop_reason="end_turn"),
        ]

        stdout = io.StringIO()
        chat_client = FakeChatClient([first_stream, second_stream], config=config)

        # Budget of 1000: first turn = 800 (warning at 80%), second turn = 250, total = 1050 (exceeded)
        exit_code = await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
            max_tokens_budget=1000,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        warning_count = sum(1 for e in events if e["type"] == "budget_warning")
        assert warning_count == 1

    @pytest.mark.asyncio
    async def test_budget_exceeded_on_final_text_turn(self, config, tmp_path):
        """Budget exceeded on a turn with no tool calls still stops gracefully."""
        stream = [
            MessageStart(
                id="msg_1",
                model="test-model",
                usage_input_tokens=600,
                usage_cache_read=0,
                usage_cache_creation=0,
            ),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Done"),
            ContentBlockStop(index=0),
            UsageDelta(output_tokens=500),
            MessageStop(stop_reason="end_turn"),
        ]

        stdout = io.StringIO()
        chat_client = FakeChatClient([stream], config=config)

        # Budget 1000: total = 1100 (exceeded), but it's a final text turn
        exit_code = await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
            max_tokens_budget=1000,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        types = [e["type"] for e in events]

        # budget_exceeded should be emitted, then step_finish
        assert "budget_exceeded" in types
        assert "step_finish" in types

        # step_finish should be the last event
        assert events[-1]["type"] == "step_finish"


class TestCliMaxTokensBudgetFlag:
    def test_cli_passes_max_tokens_budget(self, config, capsys):
        """--max-tokens-budget is parsed and passed to run_prompt_jsonl."""
        observed = {}

        async def fake_run(
            prompt,
            *,
            config,
            working_dir,
            stdout=None,
            tool_registry=None,
            chat_client=None,
            resume_session_id=None,
            session_dir=None,
            system_prompt=None,
            max_tokens_budget=None,
        ):
            observed["max_tokens_budget"] = max_tokens_budget
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--max-tokens-budget", "100000", "hello"]
            main()

        assert observed["max_tokens_budget"] == 100000

    def test_cli_default_no_budget(self, config, capsys):
        """Without --max-tokens-budget, None is passed."""
        observed = {}

        async def fake_run(
            prompt,
            *,
            config,
            working_dir,
            stdout=None,
            tool_registry=None,
            chat_client=None,
            resume_session_id=None,
            session_dir=None,
            system_prompt=None,
            max_tokens_budget=None,
        ):
            observed["max_tokens_budget"] = max_tokens_budget
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "hello"]
            main()

        assert observed["max_tokens_budget"] is None
