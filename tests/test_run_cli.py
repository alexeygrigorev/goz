"""Tests for `goz run` JSONL CLI mode."""

from __future__ import annotations

import asyncio
import io
import json
import signal
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
from goz.cli.run import DEFAULT_SYSTEM_PROMPT, build_default_tool_registry, run_prompt_jsonl
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
            "session_id": events[-1]["part"]["session_id"],
            "continuation": {"resume_session_id": events[-1]["part"]["session_id"]},
        }
        combined_text = "".join(event["part"]["text"] for event in events if event["type"] == "text")
        assert chat_client.calls[0]["tools"]

    @pytest.mark.asyncio
    async def test_saves_session_state_to_disk(self, config, tmp_path):
        stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"ok","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        stdout = io.StringIO()
        chat_client = FakeChatClient([stream], config=config)

        await run_prompt_jsonl(
            "Persist this run",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
            session_dir=tmp_path / "sessions",
        )

        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        session_id = events[-1]["part"]["session_id"]
        session_path = tmp_path / "sessions" / f"{session_id}.json"

        assert session_path.exists()
        data = json.loads(session_path.read_text())
        assert data["id"] == session_id
        assert data["working_directory"] == str(tmp_path)
        assert data["agent_type"] == "engine"
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert data["tool_state"]["working_directory"] == str(tmp_path)
        assert data["tool_state"]["tools"]["bash"]["working_dir"] == str(tmp_path)

    @pytest.mark.asyncio
    async def test_resume_session_reuses_saved_history(self, config, tmp_path):
        first_stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"first","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        second_stream = [
            MessageStart(id="msg_2", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"second","files_changed":[],"tests":{"added":0,"passing":2},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        first_stdout = io.StringIO()
        second_stdout = io.StringIO()
        session_dir = tmp_path / "sessions"

        first_client = FakeChatClient([first_stream], config=config)
        await run_prompt_jsonl(
            "First turn",
            config=config,
            working_dir=str(tmp_path),
            stdout=first_stdout,
            chat_client=first_client,
            session_dir=session_dir,
        )
        first_events = [json.loads(line) for line in first_stdout.getvalue().splitlines()]
        session_id = first_events[-1]["part"]["session_id"]

        second_client = FakeChatClient([second_stream], config=config)
        await run_prompt_jsonl(
            "Second turn",
            config=config,
            working_dir="/unused",
            stdout=second_stdout,
            chat_client=second_client,
            resume_session_id=session_id,
            session_dir=session_dir,
        )

        second_call_messages = second_client.calls[0]["messages"]
        assert second_call_messages[0]["content"].startswith("First turn")
        assert "second" not in second_call_messages[0]["content"].lower()
        assert second_call_messages[1]["role"] == "assistant"
        assert second_call_messages[2]["content"].startswith("Second turn")

    @pytest.mark.asyncio
    async def test_saves_session_on_interrupt(self, config, tmp_path, monkeypatch):
        wait_for_interrupt = asyncio.Event()
        registered_handlers: dict[int, object] = {}

        class HangingChatClient:
            def __init__(self, *, config):
                self.config = config

            def chat_completion(self, **kwargs):
                async def iterator():
                    await wait_for_interrupt.wait()
                    yield ContentBlockDelta(type="text_delta", index=0, text="unreachable")

                return iterator()

        loop = asyncio.get_running_loop()

        def fake_add_signal_handler(signum, callback):
            registered_handlers[signum] = callback

        def fake_remove_signal_handler(signum):
            registered_handlers.pop(signum, None)

        monkeypatch.setattr(loop, "add_signal_handler", fake_add_signal_handler)
        monkeypatch.setattr(loop, "remove_signal_handler", fake_remove_signal_handler)

        task = asyncio.create_task(
            run_prompt_jsonl(
                "Interrupt me",
                config=config,
                working_dir=str(tmp_path),
                stdout=io.StringIO(),
                chat_client=HangingChatClient(config=config),
                session_dir=tmp_path / "sessions",
            )
        )

        await asyncio.sleep(0)
        registered_handlers[signal.SIGTERM]()
        wait_for_interrupt.set()
        exit_code = await task

        session_files = list((tmp_path / "sessions").glob("*.json"))
        assert exit_code == 1
        assert len(session_files) == 1
        data = json.loads(session_files[0].read_text())
        assert data["messages"][0]["content"].startswith("Interrupt me")

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

    @pytest.mark.asyncio
    async def test_default_system_prompt_used_when_none_provided(self, config, tmp_path):
        stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"ok","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        stdout = io.StringIO()
        chat_client = FakeChatClient([stream], config=config)

        await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
        )

        assert chat_client.calls[0]["system"] == DEFAULT_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_custom_system_prompt_overrides_default(self, config, tmp_path):
        stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"ok","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        stdout = io.StringIO()
        chat_client = FakeChatClient([stream], config=config)

        await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
            system_prompt="Custom system prompt here",
        )

        assert chat_client.calls[0]["system"] == "Custom system prompt here"

    @pytest.mark.asyncio
    async def test_empty_system_prompt_disables_default(self, config, tmp_path):
        stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"ok","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        stdout = io.StringIO()
        chat_client = FakeChatClient([stream], config=config)

        await run_prompt_jsonl(
            "test prompt",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
            system_prompt="",
        )

        # run_prompt_jsonl passes system="" to chat_completion;
        # the real client would skip adding it to params (empty string is falsy)
        assert chat_client.calls[0].get("system") == ""


class TestRunCli:
    def test_goz_run_cli_supports_model_override_and_json_output(self, config, capsys):
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
        ):
            observed["prompt"] = prompt
            observed["model"] = config.chat_model
            observed["working_dir"] = working_dir
            observed["resume_session_id"] = resume_session_id
            observed["system_prompt"] = system_prompt
            print(json.dumps({"type": "text", "part": {"text": "ok"}}))
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "session-1", "continuation": {"resume_session_id": "session-1"}}}))
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
            "resume_session_id": None,
            "system_prompt": None,
        }

    def test_goz_run_cli_supports_resume_session_without_prompt(self, config, capsys):
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
        ):
            observed["prompt"] = prompt
            observed["resume_session_id"] = resume_session_id
            observed["system_prompt"] = system_prompt
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": resume_session_id, "continuation": {"resume_session_id": resume_session_id}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--resume-session", "resume-123"]
            main()

        captured = capsys.readouterr()
        events = [json.loads(line) for line in captured.out.splitlines()]
        assert events[0]["part"]["session_id"] == "resume-123"
        assert observed == {
            "prompt": "",
            "resume_session_id": "resume-123",
            "system_prompt": None,
        }

    def test_goz_run_cli_passes_system_prompt_flag(self, config, capsys):
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
        ):
            observed["system_prompt"] = system_prompt
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--system-prompt", "Custom prompt", "hello"]
            main()

        assert observed["system_prompt"] == "Custom prompt"

    def test_goz_run_cli_no_system_prompt_flag(self, config, capsys):
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
        ):
            observed["system_prompt"] = system_prompt
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--no-system-prompt", "hello"]
            main()

        assert observed["system_prompt"] == ""

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
