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
from goz.api.errors import TimeoutError as ApiTimeoutError
from goz.cli.run import (
    AUTO_MODEL,
    DEFAULT_FALLBACK_CHAIN,
    DEFAULT_MODEL_TIMEOUT,
    DEFAULT_SYSTEM_PROMPT,
    FallingBackChatClient,
    build_default_tool_registry,
    run_prompt_jsonl,
)
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
        event_types = [event["type"] for event in events]
        # tool_stream events may appear before tool_use for bash commands
        assert event_types[0] in ("tool_stream", "tool_use")
        assert "tool_use" in event_types
        assert event_types[-1] == "step_finish"

        tool_use_events = [e for e in events if e["type"] == "tool_use"]
        assert tool_use_events[0]["part"]["name"] == "bash"
        assert tool_use_events[0]["part"]["input"] == {"command": "pwd"}
        assert events[-1]["part"] == {
            "tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0},
            "cost": 0,
            "session_id": events[-1]["part"]["session_id"],
            "continuation": {"resume_session_id": events[-1]["part"]["session_id"]},
        }
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
        assert registry.get("write_file").working_dir == str(tmp_path)
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
    async def test_model_fallback_event_emitted_in_run_prompt_jsonl(self, config, tmp_path):
        """run_prompt_jsonl emits model_fallback events when the client falls back."""
        good_chunks = [
            MessageStart(id="msg_2", model="glm-4-long"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(
                type="text_delta",
                index=0,
                text='STAGE_RESULT:\n{"verdict":"pass","summary":"ok","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
            ),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                if self.model == "glm-5-turbo":
                    async def slow():
                        await asyncio.sleep(100)
                        yield
                    return slow()
                else:
                    async def iterator():
                        for chunk in good_chunks:
                            yield chunk
                    return iterator()

        from goz.cli.run import FallingBackChatClient

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=1,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        stdout = io.StringIO()
        exit_code = await run_prompt_jsonl(
            "Fallback test",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=fb,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        event_types = [event["type"] for event in events]
        assert "model_fallback" in event_types
        fb_event = next(e for e in events if e["type"] == "model_fallback")
        assert fb_event["part"]["from_model"] == "glm-5-turbo"
        assert fb_event["part"]["to_model"] == "glm-4-long"
        assert fb_event["part"]["elapsed_seconds"] >= 0.9

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
            system_prompt=None, no_context=False,
            max_tokens_budget=None,
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
            system_prompt=None, no_context=False,
            max_tokens_budget=None,
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
            system_prompt=None, no_context=False,
            max_tokens_budget=None,
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
            system_prompt=None, no_context=False,
            max_tokens_budget=None,
        ):
            observed["system_prompt"] = system_prompt
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--no-system-prompt", "hello"]
            main()

        assert observed["system_prompt"] == ""

    def test_goz_run_cli_creates_fallback_client_with_model_auto(self, config, capsys):
        """When --model auto is passed, a FallingBackChatClient is created."""
        from goz.cli.run import FallingBackChatClient

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
            system_prompt=None, no_context=False,
            max_tokens_budget=None,
        ):
            observed["chat_client_type"] = type(chat_client).__name__
            assert isinstance(chat_client, FallingBackChatClient)
            observed["per_model_timeout"] = chat_client.per_model_timeout
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--model", "auto", "--model-timeout", "30", "hello"]
            main()

        assert observed["chat_client_type"] == "FallingBackChatClient"
        assert observed["per_model_timeout"] == 30

    def test_goz_run_cli_model_chain_flag(self, config, capsys):
        """--model-chain customises the fallback chain when using --model auto."""
        from goz.cli.run import FallingBackChatClient

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
            system_prompt=None, no_context=False,
            max_tokens_budget=None,
        ):
            observed["chat_client_type"] = type(chat_client).__name__
            assert isinstance(chat_client, FallingBackChatClient)
            observed["chain"] = chat_client.chain
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--model", "auto", "--model-chain", "glm-5.1,glm-4-long,glm-4-flash", "hello"]
            main()

        assert observed["chat_client_type"] == "FallingBackChatClient"
        assert observed["chain"] == ["glm-5.1", "glm-4-long", "glm-4-flash"]

    def test_goz_run_cli_does_not_create_fallback_client_with_explicit_model(self, config, capsys):
        """When an explicit model is passed, no FallingBackChatClient is created."""
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
            system_prompt=None, no_context=False,
            max_tokens_budget=None,
        ):
            observed["chat_client"] = chat_client
            observed["model"] = config.chat_model
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main

            sys.argv = ["goz", "run", "--format", "json", "--model", "glm-4-flash", "hello"]
            main()

        assert observed["chat_client"] is None
        assert observed["model"] == "glm-4-flash"

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
        assert event["type"] == "error"
        assert event["error"] == {
            "name": "RuntimeError",
            "data": {"message": "bad run"},
        }


class TestParallelToolExecution:
    """Tests for parallel execution of multiple tool calls via asyncio.gather."""

    @pytest.fixture
    def config(self) -> Config:
        return Config(
            zai_token="test-token",
            zai_base_url="https://api.test.com",
            chat_model="test-model",
            timeout=60,
        )

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_execute_concurrently(self, config, tmp_path):
        """Multiple tool calls in one response execute concurrently."""
        import time

        first_stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="tool_use", index=0, id="call_1", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"sleep 0.2"}'),
            ContentBlockStop(index=0),
            ContentBlockStart(type="tool_use", index=1, id="call_2", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=1, partial_json='{"command":"sleep 0.2"}'),
            ContentBlockStop(index=1),
            MessageStop(stop_reason="tool_use"),
        ]
        second_stream = [
            MessageStart(id="msg_2", model="test-model"),
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
        chat_client = FakeChatClient([first_stream, second_stream], config=config)

        start = time.monotonic()
        exit_code = await run_prompt_jsonl(
            "Run two sleeps",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
        )
        elapsed = time.monotonic() - start

        assert exit_code == 0
        # If sequential, would be ~0.4s+. With parallel, should be ~0.2-0.3s.
        assert elapsed < 0.35, f"Tools appear to have run sequentially ({elapsed:.2f}s)"

        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        tool_use_events = [e for e in events if e["type"] == "tool_use"]
        assert len(tool_use_events) == 2
        assert tool_use_events[0]["part"]["id"] == "call_1"
        assert tool_use_events[1]["part"]["id"] == "call_2"

    @pytest.mark.asyncio
    async def test_results_returned_in_same_order_as_tool_calls(self, config, tmp_path):
        """Results are returned in the same order as the tool calls."""
        first_stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="tool_use", index=0, id="call_a", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"echo first"}'),
            ContentBlockStop(index=0),
            ContentBlockStart(type="tool_use", index=1, id="call_b", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=1, partial_json='{"command":"echo second"}'),
            ContentBlockStop(index=1),
            ContentBlockStart(type="tool_use", index=2, id="call_c", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=2, partial_json='{"command":"echo third"}'),
            ContentBlockStop(index=2),
            MessageStop(stop_reason="tool_use"),
        ]
        second_stream = [
            MessageStart(id="msg_2", model="test-model"),
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
        chat_client = FakeChatClient([first_stream, second_stream], config=config)

        exit_code = await run_prompt_jsonl(
            "Run three echos",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        tool_use_events = [e for e in events if e["type"] == "tool_use"]
        assert len(tool_use_events) == 3
        assert tool_use_events[0]["part"]["id"] == "call_a"
        assert tool_use_events[1]["part"]["id"] == "call_b"
        assert tool_use_events[2]["part"]["id"] == "call_c"

    @pytest.mark.asyncio
    async def test_individual_tool_failure_doesnt_prevent_others(self, config, tmp_path):
        """Individual tool failures don't prevent other tools from completing."""
        first_stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="tool_use", index=0, id="call_ok", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"echo ok"}'),
            ContentBlockStop(index=0),
            ContentBlockStart(type="tool_use", index=1, id="call_bad", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=1, partial_json='{"command":"exit 1"}'),
            ContentBlockStop(index=1),
            MessageStop(stop_reason="tool_use"),
        ]
        second_stream = [
            MessageStart(id="msg_2", model="test-model"),
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
        chat_client = FakeChatClient([first_stream, second_stream], config=config)

        exit_code = await run_prompt_jsonl(
            "Run ok and fail",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        tool_use_events = [e for e in events if e["type"] == "tool_use"]
        assert len(tool_use_events) == 2
        # Both tools should have completed
        assert tool_use_events[0]["part"]["id"] == "call_ok"
        assert tool_use_events[1]["part"]["id"] == "call_bad"

    @pytest.mark.asyncio
    async def test_single_tool_call_behavior_unchanged(self, config, tmp_path):
        """Single tool call behavior is unchanged from sequential execution."""
        first_stream = [
            MessageStart(id="msg_1", model="test-model"),
            ContentBlockStart(type="tool_use", index=0, id="call_1", name="bash"),
            ContentBlockDelta(type="input_json_delta", index=0, partial_json='{"command":"echo hello"}'),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="tool_use"),
        ]
        second_stream = [
            MessageStart(id="msg_2", model="test-model"),
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
        chat_client = FakeChatClient([first_stream, second_stream], config=config)

        exit_code = await run_prompt_jsonl(
            "Run echo",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=chat_client,
        )

        assert exit_code == 0
        events = [json.loads(line) for line in stdout.getvalue().splitlines()]
        tool_use_events = [e for e in events if e["type"] == "tool_use"]
        assert len(tool_use_events) == 1
        assert tool_use_events[0]["part"]["name"] == "bash"
        assert tool_use_events[0]["part"]["input"] == {"command": "echo hello"}


class TestFallingBackChatClient:
    """Tests for the FallingBackChatClient timeout-based model fallback."""

    def _make_config(self) -> Config:
        return Config(
            zai_token="test-token",
            zai_base_url="https://api.test.com",
            chat_model="test-model",
            timeout=60,
        )

    @pytest.mark.asyncio
    async def test_first_model_succeeds_no_fallback(self):
        """When the first model responds in time, no fallback occurs."""
        config = self._make_config()
        stream_chunks = [
            MessageStart(id="msg_1", model="glm-5-turbo"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Hello"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        call_log: list[str] = []

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                call_log.append(self.model)
                async def iterator():
                    for chunk in stream_chunks:
                        yield chunk
                return iterator()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=5,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        chunks = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

        assert call_log == ["glm-5-turbo"]
        assert len(chunks) == len(stream_chunks)

    @pytest.mark.asyncio
    async def test_timeout_on_first_model_falls_back_to_second(self):
        """When the first model times out, the second model is tried."""
        config = self._make_config()
        good_chunks = [
            MessageStart(id="msg_2", model="glm-4-long"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Fallback"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        call_log: list[str] = []

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                call_log.append(self.model)
                if self.model == "glm-5-turbo":
                    # Simulate timeout: never yield anything
                    async def slow():
                        await asyncio.sleep(100)
                        yield
                    return slow()
                else:
                    async def iterator():
                        for chunk in good_chunks:
                            yield chunk
                    return iterator()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=1,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        chunks = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

        assert call_log == ["glm-5-turbo", "glm-4-long"]
        assert len(chunks) == len(good_chunks)

    @pytest.mark.asyncio
    async def test_all_models_timeout_raises_error(self):
        """When all models time out, an ApiTimeoutError is raised."""
        config = self._make_config()

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                async def slow():
                    await asyncio.sleep(100)
                    yield
                return slow()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long", "glm-4-flash"],
            per_model_timeout=1,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        with pytest.raises(ApiTimeoutError):
            async for _ in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
                pass

    @pytest.mark.asyncio
    async def test_non_timeout_error_propagates_immediately(self):
        """Non-timeout errors from the first model propagate without fallback."""
        config = self._make_config()

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                async def failing():
                    raise RuntimeError("auth failure")
                    yield
                return failing()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=5,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        with pytest.raises(RuntimeError, match="auth failure"):
            async for _ in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
                pass

    @pytest.mark.asyncio
    async def test_second_model_also_times_out_tries_third(self):
        """When the first two models time out, the third is tried and succeeds."""
        config = self._make_config()
        good_chunks = [
            MessageStart(id="msg_3", model="glm-4-flash"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Third time lucky"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        call_log: list[str] = []

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                call_log.append(self.model)
                if self.model == "glm-4-flash":
                    async def iterator():
                        for chunk in good_chunks:
                            yield chunk
                    return iterator()
                else:
                    async def slow():
                        await asyncio.sleep(100)
                        yield
                    return slow()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long", "glm-4-flash"],
            per_model_timeout=1,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        chunks = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

        assert call_log == ["glm-5-turbo", "glm-4-long", "glm-4-flash"]
        assert len(chunks) == len(good_chunks)

    def test_default_fallback_chain_constants(self):
        """Verify the default constants are sensible."""
        assert AUTO_MODEL == "auto"
        assert len(DEFAULT_FALLBACK_CHAIN) == 3
        assert DEFAULT_MODEL_TIMEOUT == 60
        assert all(isinstance(m, str) for m in DEFAULT_FALLBACK_CHAIN)

    @pytest.mark.asyncio
    async def test_fallback_records_event_on_timeout(self):
        """A ModelFallbackEvent is recorded when the first model times out."""
        config = self._make_config()
        good_chunks = [
            MessageStart(id="msg_2", model="glm-4-long"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Fallback"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                if self.model == "glm-5-turbo":
                    async def slow():
                        await asyncio.sleep(100)
                        yield
                    return slow()
                else:
                    async def iterator():
                        for chunk in good_chunks:
                            yield chunk
                    return iterator()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=1,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        chunks = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

        assert len(fb.fallback_events) == 1
        evt = fb.fallback_events[0]
        assert evt.from_model == "glm-5-turbo"
        assert evt.to_model == "glm-4-long"
        assert evt.elapsed_seconds >= 0.9

    @pytest.mark.asyncio
    async def test_no_fallback_event_when_first_model_succeeds(self):
        """No ModelFallbackEvent is recorded when the first model responds."""
        config = self._make_config()
        stream_chunks = [
            MessageStart(id="msg_1", model="glm-5-turbo"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Hello"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                async def iterator():
                    for chunk in stream_chunks:
                        yield chunk
                return iterator()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=5,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        chunks = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
            chunks.append(chunk)

        assert len(fb.fallback_events) == 0

    @pytest.mark.asyncio
    async def test_pinned_model_used_for_subsequent_calls(self):
        """Once a model responds, it is pinned and used for all remaining turns."""
        config = self._make_config()
        first_chunks = [
            MessageStart(id="msg_1", model="glm-5-turbo"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="First"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]
        second_chunks = [
            MessageStart(id="msg_2", model="glm-5-turbo"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Second"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        call_log: list[str] = []

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                call_log.append(self.model)
                chunks = first_chunks if len(call_log) == 1 else second_chunks
                async def iterator():
                    for chunk in chunks:
                        yield chunk
                return iterator()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=5,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        # First call
        chunks1 = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
            chunks1.append(chunk)
        assert call_log == ["glm-5-turbo"]
        assert fb._pinned_model == "glm-5-turbo"

        # Second call should reuse the pinned model
        chunks2 = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi again"}]):
            chunks2.append(chunk)
        assert call_log == ["glm-5-turbo", "glm-5-turbo"]
        assert len(chunks2) == len(second_chunks)

    @pytest.mark.asyncio
    async def test_fallback_pins_second_model_for_subsequent_calls(self):
        """After falling back to the second model, it is pinned for remaining turns."""
        config = self._make_config()
        good_chunks = [
            MessageStart(id="msg_2", model="glm-4-long"),
            ContentBlockStart(type="text", index=0),
            ContentBlockDelta(type="text_delta", index=0, text="Fallback"),
            ContentBlockStop(index=0),
            MessageStop(stop_reason="end_turn"),
        ]

        call_log: list[str] = []

        class StubClient:
            def __init__(self, model: str):
                self.model = model

            def chat_completion(self, **kwargs):
                call_log.append(self.model)
                if self.model == "glm-5-turbo":
                    async def slow():
                        await asyncio.sleep(100)
                        yield
                    return slow()
                else:
                    async def iterator():
                        for chunk in good_chunks:
                            yield chunk
                    return iterator()

        fb = FallingBackChatClient(
            config=config,
            chain=["glm-5-turbo", "glm-4-long"],
            per_model_timeout=1,
        )
        fb._get_client = lambda m: StubClient(m)  # type: ignore[assignment]

        # First call falls back from glm-5-turbo to glm-4-long
        chunks1 = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi"}]):
            chunks1.append(chunk)
        assert call_log == ["glm-5-turbo", "glm-4-long"]
        assert fb._pinned_model == "glm-4-long"

        # Second call should use the pinned model directly
        chunks2 = []
        async for chunk in fb.chat_completion(messages=[{"role": "user", "content": "hi again"}]):
            chunks2.append(chunk)
        assert call_log == ["glm-5-turbo", "glm-4-long", "glm-4-long"]
        assert len(chunks2) == len(good_chunks)
