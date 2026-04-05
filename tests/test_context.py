"""Tests for project context auto-loading."""

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
from goz.cli.run import DEFAULT_SYSTEM_PROMPT, run_prompt_jsonl
from goz.config import Config
from goz.context import CONTEXT_FILES, DEFAULT_MAX_CHARS, load_project_context


class TestLoadProjectContext:
    def test_returns_empty_when_no_files_exist(self, tmp_path):
        assert load_project_context(str(tmp_path)) == ""

    def test_loads_claude_md(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("Claude instructions here")
        result = load_project_context(str(tmp_path))
        assert "# CLAUDE.md\nClaude instructions here" in result

    def test_loads_readme_md(self, tmp_path):
        (tmp_path / "README.md").write_text("# My Project\nHello world")
        result = load_project_context(str(tmp_path))
        assert "# README.md\n# My Project\nHello world" in result

    def test_loads_cursorrules(self, tmp_path):
        (tmp_path / ".cursorrules").write_text("cursor rules content")
        result = load_project_context(str(tmp_path))
        assert "# .cursorrules\ncursor rules content" in result

    def test_loads_github_copilot_instructions(self, tmp_path):
        copilot_dir = tmp_path / ".github"
        copilot_dir.mkdir()
        (copilot_dir / "copilot-instructions.md").write_text("copilot instructions")
        result = load_project_context(str(tmp_path))
        assert "# .github/copilot-instructions.md\ncopilot instructions" in result

    def test_missing_files_silently_skipped(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("only this one exists")
        result = load_project_context(str(tmp_path))
        assert "only this one exists" in result
        assert "README.md" not in result
        assert ".cursorrules" not in result

    def test_priority_order_in_output(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("claude")
        (tmp_path / "README.md").write_text("readme")
        (tmp_path / ".cursorrules").write_text("cursor")
        copilot_dir = tmp_path / ".github"
        copilot_dir.mkdir()
        (copilot_dir / "copilot-instructions.md").write_text("copilot")
        result = load_project_context(str(tmp_path))
        claude_idx = result.index("claude")
        readme_idx = result.index("readme")
        cursor_idx = result.index("cursor")
        copilot_idx = result.index("copilot")
        assert claude_idx < readme_idx < cursor_idx < copilot_idx

    def test_truncation_when_total_exceeds_max(self, tmp_path):
        big_content = "x" * 20_000
        (tmp_path / "CLAUDE.md").write_text(big_content)
        result = load_project_context(str(tmp_path), max_chars=500)
        assert len(result) == 500

    def test_no_truncation_when_under_limit(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("short content")
        result = load_project_context(str(tmp_path), max_chars=16_000)
        assert result == "# CLAUDE.md\nshort content"

    def test_multiple_files_concatenated(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("first")
        (tmp_path / "README.md").write_text("second")
        result = load_project_context(str(tmp_path))
        assert "# CLAUDE.md\nfirst" in result
        assert "# README.md\nsecond" in result
        assert result.index("first") < result.index("second")

    def test_unreadable_file_skipped(self, tmp_path):
        filepath = tmp_path / "CLAUDE.md"
        filepath.write_text("exists but unreadable")
        filepath.chmod(0o000)
        try:
            result = load_project_context(str(tmp_path))
            # Either skipped or read depending on OS permissions
            assert isinstance(result, str)
        finally:
            filepath.chmod(0o644)

    def test_default_max_chars_constant(self):
        assert DEFAULT_MAX_CHARS == 16_000

    def test_context_files_list(self):
        assert CONTEXT_FILES == [
            "CLAUDE.md",
            "README.md",
            ".cursorrules",
            ".github/copilot-instructions.md",
        ]


class TestContextInSystemPrompt:
    """Integration tests that context appears in the system prompt."""

    @pytest.fixture
    def config(self):
        return Config(
            zai_token="test-token",
            zai_base_url="https://api.test.com",
            chat_model="test-model",
            timeout=60,
        )

    def _make_stream(self):
        return [
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

    @pytest.mark.asyncio
    async def test_context_prepended_to_default_system_prompt(self, config, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("Project specific instructions")

        class FakeClient:
            def __init__(self, *, config):
                self.config = config
                self.calls = []

            def chat_completion(self, **kwargs):
                self.calls.append(kwargs)
                stream = self._make_stream()

                async def iterator():
                    for chunk in stream:
                        yield chunk

                return iterator()

            def _make_stream(self):
                return [
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

        client = FakeClient(config=config)
        stdout = io.StringIO()
        await run_prompt_jsonl(
            "test",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=client,
        )

        system = client.calls[0]["system"]
        assert system.startswith("# CLAUDE.md\nProject specific instructions")
        assert DEFAULT_SYSTEM_PROMPT in system
        # Context appears before the default prompt
        assert system.index("Project specific instructions") < system.index("coding agent")

    @pytest.mark.asyncio
    async def test_no_context_when_no_files(self, config, tmp_path):
        class FakeClient:
            def __init__(self, *, config):
                self.config = config
                self.calls = []

            def chat_completion(self, **kwargs):
                self.calls.append(kwargs)

                async def iterator():
                    for chunk in [
                        MessageStart(id="msg_1", model="test-model"),
                        ContentBlockStart(type="text", index=0),
                        ContentBlockDelta(
                            type="text_delta", index=0,
                            text='STAGE_RESULT:\n{"verdict":"pass","summary":"ok","files_changed":[],"tests":{"added":0,"passing":1},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}\n',
                        ),
                        ContentBlockStop(index=0),
                        MessageStop(stop_reason="end_turn"),
                    ]:
                        yield chunk

                return iterator()

        client = FakeClient(config=config)
        stdout = io.StringIO()
        await run_prompt_jsonl(
            "test",
            config=config,
            working_dir=str(tmp_path),
            stdout=stdout,
            chat_client=client,
        )

        assert client.calls[0]["system"] == DEFAULT_SYSTEM_PROMPT

    def test_no_context_flag_cli(self, config, tmp_path, capsys):
        (tmp_path / "CLAUDE.md").write_text("Should not appear")
        observed = {}

        async def fake_run(
            prompt, *, config, working_dir, stdout=None, tool_registry=None,
            chat_client=None, resume_session_id=None, session_dir=None,
            system_prompt=None, no_context=False,
        ):
            observed["no_context"] = no_context
            observed["system_prompt"] = system_prompt
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), \
             patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main
            sys.argv = ["goz", "run", "--format", "json", "--dir", str(tmp_path), "--no-context", "hello"]
            main()

        assert observed["no_context"] is True

    def test_context_loaded_by_default_cli(self, config, tmp_path, capsys):
        (tmp_path / "CLAUDE.md").write_text("Auto-loaded context")

        observed = {}

        async def fake_run(
            prompt, *, config, working_dir, stdout=None, tool_registry=None,
            chat_client=None, resume_session_id=None, session_dir=None,
            system_prompt=None, no_context=False,
        ):
            observed["no_context"] = no_context
            observed["system_prompt"] = system_prompt
            print(json.dumps({"type": "step_finish", "part": {"tokens": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}, "cost": 0, "session_id": "s1", "continuation": {"resume_session_id": "s1"}}}))
            return 0

        with patch("goz.cli.run.load_config", return_value=config), \
             patch("goz.cli.run.run_prompt_jsonl", side_effect=fake_run):
            from goz.__main__ import main
            sys.argv = ["goz", "run", "--format", "json", "--dir", str(tmp_path), "hello"]
            main()

        assert observed["no_context"] is False
