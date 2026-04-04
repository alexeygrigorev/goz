"""JSONL CLI runner for litehive-compatible one-shot agent execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from goz.agent.chat_client import ChatClient, Chunk, ContentBlockDelta, ContentBlockStart, ContentBlockStop
from goz.agent.history import ChatHistory, ChatMessage, ToolCall
from goz.agent.tools import (
    BashTool,
    CreateFileTool,
    ReadTool,
    RepoReadTool,
    RepoSearchTool,
    RepoTreeTool,
    SearchTool,
    StrReplaceEditorTool,
    ToolRegistry,
    ViewFileTool,
)
from goz.config import Config, load_config


MAX_ITERATIONS = 10
STEP_FINISH_TOKENS = {
    "input": 0,
    "output": 0,
    "cache_creation": 0,
    "cache_read": 0,
}
STAGE_RESULT_INSTRUCTION = """

End your final answer with:
STAGE_RESULT:
{"verdict":"pass","summary":"one-line summary","files_changed":["path/to/file"],"tests":{"added":0,"passing":0},"warnings":[],"follow_up_tasks":[],"acceptance_criteria":[]}

Return valid JSON after STAGE_RESULT:. Include a verdict.
""".strip()


def _emit_event(event: dict[str, Any], stdout: TextIO) -> None:
    stdout.write(json.dumps(event, ensure_ascii=True) + "\n")
    stdout.flush()


def emit_text_event(text: str, stdout: TextIO) -> None:
    _emit_event({"type": "text", "part": {"text": text}}, stdout)


def emit_tool_use_event(
    tool_call: dict[str, Any],
    result: str,
    stdout: TextIO,
    *,
    is_error: bool = False,
) -> None:
    _emit_event(
        {
            "type": "tool_use",
            "part": {
                "id": tool_call["id"],
                "name": tool_call["name"],
                "input": tool_call["input"],
                "output": result,
                "is_error": is_error,
            },
        },
        stdout,
    )


def emit_error_event(name: str, message: str, stdout: TextIO) -> None:
    _emit_event(
        {
            "type": "error",
            "error": {
                "name": name,
                "data": {"message": message},
            },
        },
        stdout,
    )


def emit_step_finish_event(stdout: TextIO) -> None:
    _emit_event(
        {
            "type": "step_finish",
            "part": {
                "tokens": dict(STEP_FINISH_TOKENS),
                "cost": 0,
            },
        },
        stdout,
    )


def build_default_tool_registry(config: Config, working_dir: str) -> ToolRegistry:
    """Create the default tool set for one-shot CLI runs."""
    registry = ToolRegistry()
    registry.register(BashTool(working_dir=working_dir))
    registry.register(ViewFileTool(working_dir=working_dir))
    registry.register(CreateFileTool(working_dir=working_dir))
    registry.register(StrReplaceEditorTool(working_dir=working_dir))
    registry.register(SearchTool(config))
    registry.register(ReadTool(config))
    registry.register(RepoSearchTool(config))
    registry.register(RepoTreeTool(config))
    registry.register(RepoReadTool(config))
    return registry


def _build_prompt(user_prompt: str) -> str:
    return f"{user_prompt.rstrip()}\n\n{STAGE_RESULT_INSTRUCTION}"


def _parse_tool_calls(chunks: list[Chunk]) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []
    tool_calls_by_index: dict[int, dict[str, Any]] = {}

    for chunk in chunks:
        if isinstance(chunk, ContentBlockStart) and chunk.type == "tool_use":
            tool_calls_by_index[chunk.index] = {
                "id": chunk.id or "",
                "name": chunk.name or "",
                "input_json": [],
            }
        elif isinstance(chunk, ContentBlockDelta) and chunk.type == "input_json_delta":
            block = tool_calls_by_index.get(chunk.index)
            if block is not None and chunk.partial_json:
                block["input_json"].append(chunk.partial_json)
        elif isinstance(chunk, ContentBlockStop):
            block = tool_calls_by_index.get(chunk.index)
            if block is None:
                continue
            input_text = "".join(block.pop("input_json"))
            try:
                parsed_input = json.loads(input_text) if input_text else {}
            except json.JSONDecodeError:
                parsed_input = {"raw": input_text}
            tool_calls.append(
                {
                    "id": block["id"],
                    "name": block["name"],
                    "input": parsed_input,
                }
            )

    return tool_calls


async def _execute_tool_call(tool_registry: ToolRegistry, tool_call: dict[str, Any]) -> tuple[str, bool]:
    tool = tool_registry.get(tool_call["name"])
    if tool is None:
        return f"Tool not found: {tool_call['name']}", True

    try:
        result = await asyncio.wait_for(tool.execute(**tool_call["input"]), timeout=300)
    except asyncio.TimeoutError:
        return f"Tool {tool_call['name']} timed out after 300 seconds", True
    except Exception as exc:
        return f"Tool {tool_call['name']} failed: {exc}", True

    return str(result), False


async def run_prompt_jsonl(
    prompt: str,
    *,
    config: Config,
    working_dir: str,
    stdout: TextIO | None = None,
    tool_registry: ToolRegistry | None = None,
    chat_client: ChatClient | None = None,
) -> int:
    """Execute one agent prompt and emit JSONL events."""
    stdout = stdout or sys.stdout
    history = ChatHistory()
    registry = tool_registry or build_default_tool_registry(config, working_dir)
    client = chat_client or ChatClient(config=config)

    history.add(ChatMessage(role="user", content=_build_prompt(prompt)))

    for _ in range(MAX_ITERATIONS):
        chunks: list[Chunk] = []
        assistant_chunks: list[str] = []

        stream = client.chat_completion(
            messages=history.to_api_format(),
            tools=registry.to_openai_schema(),
            tool_choice="auto",
        )

        async for chunk in stream:
            chunks.append(chunk)
            if isinstance(chunk, ContentBlockDelta) and chunk.type == "text_delta" and chunk.text:
                assistant_chunks.append(chunk.text)
                emit_text_event(chunk.text, stdout)

        tool_calls = _parse_tool_calls(chunks)
        if not tool_calls:
            history.add(ChatMessage(role="assistant", content="".join(assistant_chunks)))
            emit_step_finish_event(stdout)
            return 0

        history.add(
            ChatMessage(
                role="assistant",
                content="".join(assistant_chunks),
                tool_calls=[
                    ToolCall(
                        id=tool_call["id"],
                        name=tool_call["name"],
                        input=tool_call["input"],
                    )
                    for tool_call in tool_calls
                ],
            )
        )

        for tool_call in tool_calls:
            result, is_error = await _execute_tool_call(registry, tool_call)
            emit_tool_use_event(tool_call, result, stdout, is_error=is_error)
            history.add(
                ChatMessage(
                    role="tool",
                    content=result,
                    tool_result_id=tool_call["id"],
                )
            )

    emit_error_event("MaxIterationsExceeded", f"Exceeded {MAX_ITERATIONS} agent iterations", stdout)
    return 1


async def cmd_run(args: list[str]) -> None:
    """Handle the `goz run` command."""
    if not args or args[0] in ("--help", "-h", "help"):
        print("""Run command usage:

  goz run [options] <prompt>

Options:
  --format, -f json   Output ExternalCLIAdapter-compatible JSONL (default: json)
  --dir DIR           Working directory for file and shell tools
  --model MODEL       Override chat model for this invocation

Examples:
  goz run --format json "Summarize this repo and report STAGE_RESULT."
  goz run --dir /tmp/project --model glm-5 "Run pytest and explain failures."
""")
        return

    parser = argparse.ArgumentParser(prog="goz run", add_help=False)
    parser.add_argument("--format", "-f", choices=["json"], default="json", help="Output format")
    parser.add_argument("--dir", dest="working_dir", help="Working directory for the run")
    parser.add_argument("--model", help="Override chat model")
    parser.add_argument("prompt", nargs="+", help="Prompt to execute")
    parsed = parser.parse_args(args)

    try:
        config = load_config()
        if parsed.model:
            config = config.model_copy(update={"chat_model": parsed.model})

        working_dir = str(Path(parsed.working_dir or ".").resolve())
        if not Path(working_dir).exists():
            raise FileNotFoundError(f"Working directory does not exist: {working_dir}")
        if not Path(working_dir).is_dir():
            raise NotADirectoryError(f"Working directory is not a directory: {working_dir}")

        exit_code = await run_prompt_jsonl(
            " ".join(parsed.prompt),
            config=config,
            working_dir=working_dir,
        )
    except Exception as exc:
        emit_error_event(type(exc).__name__, str(exc), sys.stdout)
        sys.exit(1)

    if exit_code != 0:
        sys.exit(exit_code)
