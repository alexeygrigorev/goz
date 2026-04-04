"""Tests for `goz run` JSONL CLI mode."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from goz.agent.chat_client import (
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageStart,
    MessageStop,
)
from goz.cli.run import build_default_tool_registry, run_prompt_jsonl
from goz.config import Config


@pytest.fixture
def config() -> Config:
    return Config(
        zai_token="test-token",
        zai_base_url="https://api.test.com",
        chat_model="test-model",
        timeout=60,
    )


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


class TestRunPromptJsonl:
    @pytest.mark.asyncio
    async def test_emits_jsonl_events_and_step_finish(self, config, tmp_path):
        first_stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="tool_use", index=0, id="call_1", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"pwd"}'),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="tool_use"),
        ]
        second_stream = [
            MessageStart(id="msg_2", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Answer\n"),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"ok","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        stdout = io.StringIO()
        chat_client = FakeChatClient([first_stream, second_stream], config=config)

        exit_code = await run_prompt_jsonl(
            "Run pwd and report",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        assert [event["type"] for event in events] == ["tool_use", "text", "text", "step_finish"]
        assert events[0]["part"]["name"] == "bash"
        assert events[0]["part"]["input"] == {"command": "pwd"}
        assert events[-1]["part"] == {
            "tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0},
            "cost": 0,
        }
        combined_text = "".join(event["part"]["text"] for event in events if event["type"] == "text")
        assert "STAGE_RESULT:" in combined_text
        assert '"verdict":"pass"' in combined_text
        assert "STAGE_RESULT:" in chat_client.calls[0]["messages"][0]["content"]
        assert chat_client.calls[0]["tools"]

    @pytest.mark.asyncio
    async def test_raises_when_chat_fails(self, config, tmp_path):
        class FailingChatClient:
            def chat_completion(self, **kwargs):
                async def iterator():
                    raise RuntimeError("boom")
                    yield

                return iterator()

        stdout = io.StringIO()
        with pytest.raises(RuntimeError):
            await run_prompt_jsonl(
                "fail",
                config=config,
                working_dir=str(tmp_path),
                stdout=stdout,
                chat_client=FailingChatClient(),
            )

    def test_build_default_tool_registry_uses_working_directory(self, config, tmp_path):
        registry = build_default_tool_registry(config, str(tmp_path))

        assert registry.get("bash").working_dir == str(tmp_path)
        assert registry.get("view_file").working_dir == str(tmp_path)
        assert registry.get("create_file").working_dir == str(tmp_path)
        assert registry.get("str_replace_editor").working_dir == str(tmp_path)


class TestRunCli:
    def test_goz_run_cli_supports_model_override_and_json_output(self, config, capsys):
        observed = {}

        async def fake_run(prompt, *, config, working_dir, stdout=None, tool_registry=None, chat_client=None):
            observed["prompt"] = prompt
            observed["model"] = config.chat_model
            observed["working_dir"] = working_dir
            print(json.dumps({"type": "text", "part": {"text": "ok"}}))
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--dir", ".", "--model", "override-model", "hello", "world"]
            main()

        captured = capsys.readouterr()
        events = [json.loads(line) for line in captured.out.splitlines()]
        assert events[0]["type"] == "text"
        assert events[1]["type"] == "step_finish"
        assert observed == {
            "prompt": "hello world",
            "model": "override-model",
            "working_dir": str(Path(".").resolve()),
        }

    def test_goz_run_cli_emits_error_and_nonzero_exit(self, config, capsys):
        with patch("goz.cli.run.load_config", return_value=config), patch(
            "goz.cli.run.run_prompt_jsonl",
            side_effect=RuntimeError("bad run"),
        ):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "hello"]
            with pytest.raises(SystemExit) as excinfo:
                main()

        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        assert excinfo.value.code == 1
        assert event == {
            "type": "error",
            "error": {
                "name": "RuntimeError",
                "data": {"message": "bad run"},
            },
        }
