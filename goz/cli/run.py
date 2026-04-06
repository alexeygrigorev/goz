"""JSONL CLI runner for litehive-compatible one-shot agent execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, TextIO

from goz.agent.chat_client import (
    ChatClient,
    Chunk,
    ContentBlockDelta,
    ContentBlockStart,
    ContentBlockStop,
    MessageStart,
    UsageDelta,
)
from goz.agent.history import ChatHistory, ChatMessage, ToolCall
from goz.agent.sessions import Session, SessionManager
from goz.agent.usage import TokenBudget, UsageAccumulator
from goz.agent.tools import (
    BashTool,
    CreateFileTool,
    DescribeImageTool,
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
from goz.api.errors import (
    ApiError,
    AuthError,
    NetworkError,
    QuotaError,
    TimeoutError as ApiTimeoutError,
    ZaiError,
)
from goz.config import Config, load_config
from goz.context import load_project_context

logger = logging.getLogger(__name__)

MAX_ITERATIONS: int | None = None  # No limit by default
DEFAULT_AGENT_TYPE = "engine"

AGENT_LOOP_MAX_RETRIES = 3
AGENT_LOOP_BACKOFF_DELAYS = [2, 4, 8]  # seconds


def is_retryable_error(exc: Exception) -> bool:
    """Classify whether an exception is transient and worth retrying."""
    if isinstance(exc, AuthError):
        return False
    if isinstance(exc, QuotaError):
        return False
    if isinstance(exc, ApiError):
        status = exc.statusCode
        if status is not None:
            return status == 429 or status >= 500
        return False
    if isinstance(exc, (NetworkError, ApiTimeoutError)):
        return True
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    return False


def emit_quota_exceeded_event(
    stdout: TextIO,
    *,
    code: str,
    message: str,
    help: str,
) -> None:
    _emit_event(
        {
            "type": "quota_exceeded",
            "error": {
                "code": code,
                "message": message,
                "help": help,
            },
        },
        stdout,
    )

AUTO_MODEL = "auto"

DEFAULT_FALLBACK_CHAIN: list[str] = [
    "glm-5.1",
    "glm-5",
    "glm-5-turbo",
]

DEFAULT_MODEL_TIMEOUT: int = 60  # seconds per model attempt


@dataclass
class ModelFallbackEvent:
    """Record of a model fallback that occurred during auto-selection."""

    from_model: str
    to_model: str
    elapsed_seconds: float


class FallingBackChatClient:
    """Wraps ChatClient to provide timeout-based fallback through a model chain.

    On the first ``chat_completion`` call, the wrapper tries models in the
    chain. If a model times out (no first chunk within *per_model_timeout*
    seconds), it moves to the next model.  Once a model responds, it is
    pinned for all subsequent calls in the session.  Non-timeout errors
    are propagated immediately.

    Fallback events are recorded in ``fallback_events`` for JSONL emission.
    """

    def __init__(
        self,
        config: Config,
        chain: list[str] | None = None,
        per_model_timeout: int = DEFAULT_MODEL_TIMEOUT,
    ) -> None:
        self.config = config
        self.chain = chain or list(DEFAULT_FALLBACK_CHAIN)
        self.per_model_timeout = per_model_timeout
        self._clients: dict[str, ChatClient] = {}
        self._pinned_model: str | None = None
        self.fallback_events: list[ModelFallbackEvent] = []

    def _get_client(self, model: str) -> ChatClient:
        if model not in self._clients:
            cfg = self.config.model_copy(update={"chat_model": model})
            self._clients[model] = ChatClient(config=cfg)
        return self._clients[model]

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict = "auto",
        stream: bool = True,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str | None = None,
    ) -> AsyncIterator[Chunk]:
        # If a model has already been pinned, use it directly.
        if self._pinned_model is not None:
            client = self._get_client(self._pinned_model)
            async for chunk in client.chat_completion(
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                system=system,
            ):
                yield chunk
            return

        last_error: Exception | None = None
        for model in self.chain:
            client = self._get_client(model)
            start_time = time.monotonic()
            try:
                stream_iter = client.chat_completion(
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    stream=stream,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    system=system,
                )
                # Wrap the stream so we can detect timeouts on first-chunk latency.
                first_chunk_received = asyncio.Event()

                async def _wrapped() -> AsyncIterator[Chunk]:
                    async for chunk in stream_iter:
                        first_chunk_received.set()
                        yield chunk

                wrapped_iter = _wrapped()

                # Wait for the first chunk with a timeout.
                try:
                    first_chunk = await asyncio.wait_for(
                        wrapped_iter.__anext__(), timeout=self.per_model_timeout
                    )
                except (StopAsyncIteration, asyncio.TimeoutError):
                    if not first_chunk_received.is_set():
                        elapsed = time.monotonic() - start_time
                        logger.warning(
                            "Model %s timed out waiting for first chunk (%ds), trying next",
                            model,
                            self.per_model_timeout,
                        )
                        self.fallback_events.append(
                            ModelFallbackEvent(
                                from_model=model,
                                to_model=self.chain[self.chain.index(model) + 1]
                                if self.chain.index(model) + 1 < len(self.chain)
                                else "none",
                                elapsed_seconds=round(elapsed, 2),
                            )
                        )
                        last_error = ApiTimeoutError(
                            timeoutMs=self.per_model_timeout * 1000
                        )
                        continue
                    return  # empty stream, nothing to yield

                # First chunk received in time — pin this model for the session.
                self._pinned_model = model
                yield first_chunk
                async for chunk in wrapped_iter:
                    yield chunk
                return  # success

            except ApiTimeoutError:
                elapsed = time.monotonic() - start_time
                logger.warning(
                    "Model %s timed out, trying next model in chain", model
                )
                self.fallback_events.append(
                    ModelFallbackEvent(
                        from_model=model,
                        to_model=self.chain[self.chain.index(model) + 1]
                        if self.chain.index(model) + 1 < len(self.chain)
                        else "none",
                        elapsed_seconds=round(elapsed, 2),
                    )
                )
                last_error = ApiTimeoutError(timeoutMs=self.per_model_timeout * 1000)
                continue
            except Exception:
                raise  # non-timeout errors propagate immediately

        # All models exhausted
        raise last_error or ApiTimeoutError(timeoutMs=self.per_model_timeout * 1000)


DEFAULT_SYSTEM_PROMPT = """\
You are a coding agent. You complete software engineering tasks by using tools to read, write, search, and run commands. Act autonomously — do not ask permission or wait for confirmation.

# How to work

- Persist until the task is fully resolved end-to-end. Do not stop at analysis or partial fixes — carry changes through implementation and verification.
- Work iteratively: read context, make changes, verify with tests or inspection, repeat until done.
- When you encounter errors, diagnose them with tools (read logs, inspect files, run commands) and fix them. Do not give up or ask for help.
- If the task is unclear, make reasonable assumptions and proceed. State assumptions briefly.

# Tool usage

- Use tools proactively. Prefer dedicated tools (view_file, glob, grep) over shell commands (cat, find, grep) when available.
- When multiple tool calls are independent, make them all in parallel in the same response.
- Always read a file before modifying it. Never propose changes to code you haven't seen.
- Use bash for running tests, installing dependencies, git operations, and other terminal tasks.

# Code quality

- Keep changes minimal and focused on the task. Do not add features, refactoring, or improvements beyond what was asked.
- Do not add comments, docstrings, or type annotations to code you did not change.
- Do not add error handling or validation for scenarios that cannot happen. Trust internal code and framework guarantees — only validate at system boundaries.
- Fix root causes, not surface-level patches. Three similar lines of code are better than a premature abstraction.
- Follow existing project conventions for naming, formatting, structure, and library usage.
- Never assume a library is available — verify it is already used in the project before importing it.

# Testing

- After making changes, verify they work. Run the most specific test for the code you changed first, then broaden.
- Do not assume a specific test framework — check project configuration (pyproject.toml, package.json, Makefile, etc.) first.
- If the project has tests, run them. If it has linting, run it. Do not skip verification.

# Safety

- Never introduce security vulnerabilities (command injection, XSS, SQL injection, path traversal).
- Never log, print, or commit secrets, API keys, tokens, or credentials.
- Be cautious with irreversible actions (deleting files, force-pushing, dropping tables). Prefer safe alternatives.
- Do not commit to git unless the task explicitly requires it.

# Communication

- Be concise. Fewer than 3 lines of explanatory text per response. Lead with actions, not reasoning.
- Skip introductions, acknowledgments, transitions, and summaries.
- When reporting results, state what you did and what the outcome was. No filler.
""".strip()


def _emit_event(event: dict[str, Any], stdout: TextIO) -> None:
    event["timestamp"] = datetime.now(tz=__import__('datetime').timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
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


def emit_tool_stream_event(
    tool_call_id: str,
    tool_name: str,
    line: str,
    source: str,
    stdout: TextIO,
) -> None:
    _emit_event(
        {
            "type": "tool_stream",
            "part": {
                "id": tool_call_id,
                "name": tool_name,
                "line": line,
                "source": source,
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


def emit_model_fallback_event(
    stdout: TextIO,
    *,
    from_model: str,
    to_model: str,
    elapsed_seconds: float,
) -> None:
    _emit_event(
        {
            "type": "model_fallback",
            "part": {
                "from_model": from_model,
                "to_model": to_model,
                "elapsed_seconds": elapsed_seconds,
            },
        },
        stdout,
    )


def emit_budget_warning_event(
    stdout: TextIO,
    *,
    total_tokens: int,
    budget: int,
    threshold: float,
) -> None:
    _emit_event(
        {
            "type": "budget_warning",
            "part": {
                "total_tokens": total_tokens,
                "budget": budget,
                "threshold": threshold,
            },
        },
        stdout,
    )


def emit_budget_exceeded_event(
    stdout: TextIO,
    *,
    total_tokens: int,
    budget: int,
) -> None:
    _emit_event(
        {
            "type": "budget_exceeded",
            "part": {
                "total_tokens": total_tokens,
                "budget": budget,
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
    registry.register(DescribeImageTool(config))
    return registry


def _build_prompt(user_prompt: str) -> str:
    return user_prompt.rstrip()


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


def _is_transient_tool_error(exc: Exception) -> bool:
    """Check if a tool execution error is transient and worth one retry."""
    return isinstance(exc, (asyncio.TimeoutError, ConnectionError, TimeoutError))


async def _execute_tool_call(
    tool_registry: ToolRegistry,
    tool_call: dict[str, Any],
    *,
    stdout: TextIO | None = None,
) -> tuple[str, bool]:
    tool = tool_registry.get(tool_call["name"])
    if tool is None:
        return f"Tool not found: {tool_call['name']}", True

    # Build streaming callback for bash tool when stdout is available
    stream_callback = None
    if stdout is not None and tool_call["name"] == "bash":
        call_id = tool_call["id"]
        tool_name = tool_call["name"]

        def stream_callback(line: str, source: str) -> None:
            emit_tool_stream_event(call_id, tool_name, line, source, stdout)

    kwargs = dict(tool_call["input"])
    if stream_callback is not None:
        kwargs["stream_callback"] = stream_callback

    for attempt in range(2):
        try:
            result = await asyncio.wait_for(tool.execute(**kwargs), timeout=300)
            return str(result), False
        except Exception as exc:
            if attempt == 0 and _is_transient_tool_error(exc):
                logger.info("Tool %s failed with transient error, retrying: %s", tool_call["name"], exc)
                continue
            if isinstance(exc, asyncio.TimeoutError):
                return f"Tool {tool_call['name']} timed out after 300 seconds", True
            return f"Tool {tool_call['name']} failed: {exc}", True

    return f"Tool {tool_call['name']} failed after retry", True


async def run_prompt_jsonl(
    prompt: str,
    *,
    config: Config,
    working_dir: str,
    stdout: TextIO | None = None,
    tool_registry: ToolRegistry | None = None,
    chat_client: ChatClient | FallingBackChatClient | None = None,
    resume_session_id: str | None = None,
    session_dir: Path | None = None,
    system_prompt: str | None = None,
    no_context: bool = False,
    max_tokens_budget: int | None = None,
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
    token_budget: TokenBudget | None = TokenBudget(max_tokens_budget) if max_tokens_budget is not None else None
    try:
        usage_acc = UsageAccumulator()
        while True:
            iteration += 1
            if MAX_ITERATIONS is not None and iteration > MAX_ITERATIONS:
                break

            effective_system = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
            if effective_system == DEFAULT_SYSTEM_PROMPT and not no_context:
                project_ctx = load_project_context(working_dir)
                if project_ctx:
                    effective_system = project_ctx + "\n\n" + effective_system

            # Agent-loop retry with exponential backoff
            last_error: Exception | None = None
            for retry_attempt in range(AGENT_LOOP_MAX_RETRIES + 1):
                chunks = []
                assistant_chunks = []
                usage_acc.begin_turn()
                try:
                    stream = client.chat_completion(
                        messages=history.to_api_format(),
                        tools=registry.to_openai_schema(),
                        tool_choice="auto",
                        system=effective_system,
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
                    last_error = None
                    break  # success
                except QuotaError as exc:
                    emit_quota_exceeded_event(
                        stdout,
                        code=exc.code,
                        message=exc.message,
                        help=exc.help or "",
                    )
                    return 2
                except Exception as exc:
                    if not is_retryable_error(exc) or retry_attempt >= AGENT_LOOP_MAX_RETRIES:
                        last_error = exc
                        break
                    delay = AGENT_LOOP_BACKOFF_DELAYS[retry_attempt]
                    logger.warning(
                        "Agent loop retryable error (attempt %d/%d), retrying in %ds: %s",
                        retry_attempt + 1,
                        AGENT_LOOP_MAX_RETRIES,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                    last_error = exc

            if last_error is not None:
                raise last_error

            # Emit any model_fallback events that occurred during this turn.
            if isinstance(client, FallingBackChatClient):
                for evt in client.fallback_events:
                    emit_model_fallback_event(
                        stdout,
                        from_model=evt.from_model,
                        to_model=evt.to_model,
                        elapsed_seconds=evt.elapsed_seconds,
                    )
                client.fallback_events.clear()

            snap = usage_acc.finalise_turn()

            # Token budget check
            if token_budget is not None:
                should_warn, should_stop = token_budget.check(usage_acc)
                if should_warn:
                    total = usage_acc.total_input_tokens + usage_acc.total_output_tokens
                    emit_budget_warning_event(
                        stdout,
                        total_tokens=total,
                        budget=token_budget.budget,
                        threshold=token_budget.warning_threshold,
                    )
                if should_stop:
                    total = usage_acc.total_input_tokens + usage_acc.total_output_tokens
                    emit_budget_exceeded_event(
                        stdout,
                        total_tokens=total,
                        budget=token_budget.budget,
                    )
                    history.add(ChatMessage(role="assistant", content="".join(assistant_chunks)))
                    emit_step_finish_event(
                        stdout,
                        state.session_id,
                        tokens=snap.to_dict(),
                        cost=snap.cost_usd(model=config.chat_model),
                    )
                    return 0

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

            # Execute tool calls concurrently and collect results in order
            async def _run_one(tc: dict) -> tuple[dict, str, bool]:
                res, err = await _execute_tool_call(registry, tc, stdout=stdout)
                return tc, res, err

            raw_outcomes = await asyncio.gather(
                *(_run_one(tc) for tc in tool_calls),
                return_exceptions=True,
            )
            # Unwrap any unexpected exceptions from gather into error tuples
            outcomes: list[tuple[dict, str, bool]] = []
            for i, outcome in enumerate(raw_outcomes):
                if isinstance(outcome, BaseException):
                    tc = tool_calls[i]
                    outcomes.append((tc, f"Tool {tc['name']} failed: {outcome}", True))
                else:
                    outcomes.append(outcome)
            for tc, result, is_error in outcomes:
                emit_tool_use_event(tc, result, stdout, is_error=is_error)
                history.add(
                    ChatMessage(
                        role="tool",
                        content=result,
                        tool_result_id=tc["id"],
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
  --format, -f json        Output ExternalCLIAdapter-compatible JSONL (default: json)
  --dir DIR                Working directory for file and shell tools
  --model MODEL            Override chat model (use 'auto' for timeout-based fallback)
  --model-chain MODELS     Comma-separated model chain for --model auto (default: glm-5.1,glm-5,glm-5-turbo)
  --model-timeout SECS     Per-model timeout in seconds when using --model auto (default: 60)
  --resume-session ID      Resume a previously saved engine session
  --system-prompt TEXT     Override the default coding agent system prompt
  --no-system-prompt       Disable the default system prompt entirely
  --no-context             Disable auto-loading of project context files
  --max-tokens-budget N    Stop the agent loop after N cumulative tokens (input+output)

Examples:
  goz run --format json "Summarize this repo."
  goz run --dir /tmp/project --model glm-5 "Run pytest and explain failures."
  goz run --model auto "Fix the failing test."
  goz run --model auto --model-timeout 30 "Quick task with aggressive fallback."
  goz run --model auto --model-chain "glm-5.1,glm-4-long,glm-4-flash" "Custom chain."
  goz run --resume-session abc123 "Continue with the next step."
  goz run --system-prompt 'You are a helpful assistant.' "Hello"
  goz run --no-system-prompt "Just chat with me"
  goz run --no-context "Skip project context loading"
""")
        return

    parser = argparse.ArgumentParser(prog="goz run", add_help=False)
    parser.add_argument("--format", "-f", choices=["json"], default="json", help="Output format")
    parser.add_argument("--dir", dest="working_dir", help="Working directory for the run")
    parser.add_argument("--model", help="Override chat model (use 'auto' for timeout-based fallback)")
    parser.add_argument(
        "--model-chain", dest="model_chain",
        help="Comma-separated model chain for --model auto (default: glm-5.1,glm-5,glm-5-turbo)",
    )
    parser.add_argument(
        "--model-timeout", dest="model_timeout", type=int, default=DEFAULT_MODEL_TIMEOUT,
        help=f"Per-model timeout in seconds for --model auto (default: {DEFAULT_MODEL_TIMEOUT})",
    )
    parser.add_argument(
        "--resume-session", dest="resume_session_id", help="Resume a saved session by ID"
    )
    parser.add_argument(
        "--system-prompt", dest="system_prompt", default=None,
        help="Override the default coding agent system prompt",
    )
    parser.add_argument(
        "--no-system-prompt", dest="no_system_prompt", action="store_true",
        help="Disable the default system prompt entirely",
    )
    parser.add_argument(
        "--no-context", dest="no_context", action="store_true",
        help="Disable auto-loading of project context files",
    )
    parser.add_argument(
        "--max-tokens-budget", dest="max_tokens_budget", type=int, default=None,
        help="Stop the agent loop after N cumulative tokens (input+output)",
    )
    parser.add_argument("prompt", nargs="*", help="Prompt to execute")
    parsed = parser.parse_args(args)

    if not parsed.prompt and not parsed.resume_session_id:
        raise SystemExit("goz run requires a prompt unless --resume-session is provided")

    try:
        config = load_config()
        use_auto_model = parsed.model and parsed.model.lower() == AUTO_MODEL
        if parsed.model and not use_auto_model:
            config = config.model_copy(update={"chat_model": parsed.model})

        working_dir = str(Path(parsed.working_dir or ".").resolve())
        if parsed.working_dir and not Path(working_dir).exists():
            raise FileNotFoundError(f"Working directory does not exist: {working_dir}")
        if parsed.working_dir and not Path(working_dir).is_dir():
            raise NotADirectoryError(f"Working directory is not a directory: {working_dir}")

        # Resolve system prompt: --no-system-prompt wins, then --system-prompt, then default
        system_prompt: str | None = None
        if parsed.no_system_prompt:
            system_prompt = ""
        elif parsed.system_prompt is not None:
            system_prompt = parsed.system_prompt

        chat_client: ChatClient | FallingBackChatClient | None = None
        if use_auto_model:
            chain: list[str] | None = None
            if parsed.model_chain:
                chain = [m.strip() for m in parsed.model_chain.split(",") if m.strip()]
            chat_client = FallingBackChatClient(
                config=config,
                chain=chain,
                per_model_timeout=parsed.model_timeout,
            )

        exit_code = await run_prompt_jsonl(
            " ".join(parsed.prompt),
            config=config,
            working_dir=working_dir,
            resume_session_id=parsed.resume_session_id,
            system_prompt=system_prompt,
            chat_client=chat_client,
            no_context=parsed.no_context,
            max_tokens_budget=parsed.max_tokens_budget,
        )
    except Exception as exc:
        emit_error_event(type(exc).__name__, str(exc), sys.stdout)
        sys.exit(1)

    if exit_code != 0:
        sys.exit(exit_code)
