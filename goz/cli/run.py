"""JSONL CLI runner for litehive-compatible one-shot agent execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from goz.agent.chat_client import (
    ChatClient,
    Chunk,
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageStart,
    MessageStop,
    UsageDelta,
)
from goz.agent.history import ChatHistory, ChatMessage, ToolCall
from goz.agent.sessions import Session, SessionManager
from goz.agent.usage import UsageAccumulator
from goz.agent.tools import (
    BashTool,
    CreateFileTool,
    GlobTool,
    GrepTool,
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


MAX_ITERATIONS: int | None = None  # No limit by default
DEFAULT_AGENT_TYPE = "engine"
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


def emit_step_finish_event(
    stdout: TextIO,
    session_id: str,
    *,
    tokens: dict[str, int] | None = None,
    cost: float = 0.0,
) -> None:
    _emit_event(
        {
            "type": "step_finish",
            "part": {
                "tokens": tokens or {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0},
                "cost": cost,
                "session_id": session_id,
                "continuation": {"resume_session_id": session_id},
            },
        },
        stdout,
    )


@dataclass
class RunSessionState:
    session_id: str
    created_at: datetime
    history: ChatHistory
    working_dir: str
    agent_type: str
    config: Config
    session_manager: SessionManager
    tool_registry: ToolRegistry

    async def save(self) -> Path:
        session = Session(
            id=self.session_id,
            created_at=self.created_at,
            updated_at=datetime.now(),
            working_directory=self.working_dir,
            messages=list(self.history.messages),
            model=self.config.chat_model,
            agent_type=self.agent_type,
            config_snapshot=self.config.model_dump() if hasattr(self.config, "model_dump") else {},
            tool_state=_serialize_tool_state(self.tool_registry, self.working_dir),
        )
        return await self.session_manager.save(session)


def _serialize_tool_state(tool_registry: ToolRegistry, working_dir: str) -> dict[str, Any]:
    return {
        "working_directory": working_dir,
        "tools": {
            tool.name: {
                "working_dir": getattr(tool, "working_dir", None),
            }
            for tool in tool_registry.list_all()
        },
    }


def build_default_tool_registry(config: Config, working_dir: str) -> ToolRegistry:
    """Create the default tool set for one-shot CLI runs."""
    registry = ToolRegistry()
    registry.register(BashTool(working_dir=working_dir))
    registry.register(ViewFileTool(working_dir=working_dir))
    registry.register(CreateFileTool(working_dir=working_dir))
    registry.register(StrReplaceEditorTool(working_dir=working_dir))
    registry.register(GlobTool(working_dir=working_dir))
    registry.register(GrepTool(working_dir=working_dir))
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


async def _execute_tool_call(
    tool_registry: ToolRegistry, tool_call: dict[str, Any]
) -> tuple[str, bool]:
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
    resume_session_id: str | None = None,
    session_dir: Path | None = None,
) -> int:
    """Execute one agent prompt and emit JSONL events."""
    stdout = stdout or sys.stdout
    session_manager = SessionManager(session_dir=session_dir)
    session: Session | None = None
    if resume_session_id is not None:
        session = await session_manager.load(resume_session_id)
        working_dir = session.working_directory

    history = ChatHistory(messages=list(session.messages) if session else None)
    registry = tool_registry or build_default_tool_registry(config, working_dir)
    client = chat_client or ChatClient(config=config)
    state = RunSessionState(
        session_id=resume_session_id or uuid.uuid4().hex,
        created_at=session.created_at if session else datetime.now(),
        history=history,
        working_dir=working_dir,
        agent_type=session.agent_type if session else DEFAULT_AGENT_TYPE,
        config=config,
        session_manager=session_manager,
        tool_registry=registry,
    )

    if prompt:
        history.add(ChatMessage(role="user", content=_build_prompt(prompt)))

    loop = asyncio.get_running_loop()
    interrupted_by: dict[str, str | None] = {"signal": None}
    current_task = asyncio.current_task()

    async def _handle_interrupt(signame: str) -> None:
        interrupted_by["signal"] = signame
        await state.save()
        if current_task is not None:
            current_task.cancel()

    for signum in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                signum,
                lambda current_signum=signum: asyncio.create_task(
                    _handle_interrupt(signal.Signals(current_signum).name)
                ),
            )
        except (NotImplementedError, RuntimeError):
            continue

    iteration = 0
    try:
        usage_acc = UsageAccumulator()
        while True:
            iteration += 1
            if MAX_ITERATIONS is not None and iteration > MAX_ITERATIONS:
                break
            chunks: list[Chunk] = []
            assistant_chunks: list[str] = []
            usage_acc.begin_turn()

            stream = client.chat_completion(
                messages=history.to_api_format(),
                tools=registry.to_openai_schema(),
                tool_choice="auto",
            )

            async for chunk in stream:
                chunks.append(chunk)
                if (
                    isinstance(chunk, ContentBlockDelta)
                    and chunk.type == "text_delta"
                    and chunk.text
                ):
                    assistant_chunks.append(chunk.text)
                    emit_text_event(chunk.text, stdout)
                elif isinstance(chunk, MessageStart):
                    usage_obj = type(
                        "U",
                        (),
                        {
                            "input_tokens": chunk.usage_input_tokens,
                            "cache_read_input_tokens": chunk.usage_cache_read,
                            "cache_creation_input_tokens": chunk.usage_cache_creation,
                        },
                    )()
                    usage_acc.apply_message_start(usage_obj)
                elif isinstance(chunk, UsageDelta):
                    usage_obj = type("U", (), {"output_tokens": chunk.output_tokens})()
                    usage_acc.apply_message_delta(usage_obj)

            snap = usage_acc.finalise_turn()

            tool_calls = _parse_tool_calls(chunks)
            if not tool_calls:
                history.add(ChatMessage(role="assistant", content="".join(assistant_chunks)))
                emit_step_finish_event(
                    stdout,
                    state.session_id,
                    tokens=snap.to_dict(),
                    cost=snap.cost_usd(model=config.chat_model),
                )
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
    except asyncio.CancelledError:
        emit_error_event(
            "Interrupted", f"Run interrupted by {interrupted_by['signal'] or 'signal'}", stdout
        )
        return 1
    finally:
        for signum in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.remove_signal_handler(signum)
            except (NotImplementedError, RuntimeError):
                continue
        await state.save()

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
  --resume-session ID Resume a previously saved engine session

Examples:
  goz run --format json "Summarize this repo and report STAGE_RESULT."
  goz run --dir /tmp/project --model glm-5 "Run pytest and explain failures."
  goz run --resume-session abc123 "Continue with the next step."
""")
        return

    parser = argparse.ArgumentParser(prog="goz run", add_help=False)
    parser.add_argument("--format", "-f", choices=["json"], default="json", help="Output format")
    parser.add_argument("--dir", dest="working_dir", help="Working directory for the run")
    parser.add_argument("--model", help="Override chat model")
    parser.add_argument(
        "--resume-session", dest="resume_session_id", help="Resume a saved session by ID"
    )
    parser.add_argument("prompt", nargs="*", help="Prompt to execute")
    parsed = parser.parse_args(args)

    if not parsed.prompt and not parsed.resume_session_id:
        raise SystemExit("goz run requires a prompt unless --resume-session is provided")

    try:
        config = load_config()
        if parsed.model:
            config = config.model_copy(update={"chat_model": parsed.model})

        working_dir = str(Path(parsed.working_dir or ".").resolve())
        if parsed.working_dir and not Path(working_dir).exists():
            raise FileNotFoundError(f"Working directory does not exist: {working_dir}")
        if parsed.working_dir and not Path(working_dir).is_dir():
            raise NotADirectoryError(f"Working directory is not a directory: {working_dir}")

        exit_code = await run_prompt_jsonl(
            " ".join(parsed.prompt),
            config=config,
            working_dir=working_dir,
            resume_session_id=parsed.resume_session_id,
        )
    except Exception as exc:
        emit_error_event(type(exc).__name__, str(exc), sys.stdout)
        sys.exit(1)

    if exit_code != 0:
        sys.exit(exit_code)
