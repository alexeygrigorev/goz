"""Integration test: goz run uses tools with real API.

Runs goz in JSON mode and verifies the agent actually calls tools
(glob, view_file, bash) instead of just chatting.
"""
import json
import subprocess
import sys


def run_goz(prompt: str, working_dir: str = ".") -> list[dict]:
    """Run goz in JSON mode and return parsed JSONL events."""
    result = subprocess.run(
        [sys.executable, "-m", "goz", "run", "--format", "json", "--dir", working_dir, prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    events = []
    for line in result.stdout.strip().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def extract_tool_calls(events: list[dict]) -> list[dict]:
    """Extract tool_use events from JSONL output."""
    return [e for e in events if e.get("type") == "tool_use"]


def extract_text(events: list[dict]) -> str:
    """Concatenate all text events."""
    return "".join(
        e["part"]["text"]
        for e in events
        if e.get("type") == "text" and "part" in e and "text" in e["part"]
    )


def test_goz_run_uses_glob_tool():
    """Agent should use glob tool when asked to find files."""
    events = run_goz("Find all Python files in the goz/ directory. Use the glob tool.")
    tool_calls = extract_tool_calls(events)

    assert len(tool_calls) > 0, f"Expected tool calls, got none. Events: {events[:5]}"

    tool_names = [tc["part"]["name"] for tc in tool_calls]
    assert "glob" in tool_names, f"Expected 'glob' tool call, got: {tool_names}"

    # Verify glob returned results (not an error)
    glob_calls = [tc for tc in tool_calls if tc["part"]["name"] == "glob"]
    for call in glob_calls:
        assert not call["part"].get("is_error"), f"Glob tool errored: {call['part']['output']}"


def test_goz_run_uses_view_file_tool():
    """Agent should use view_file tool when asked to read a file."""
    events = run_goz("Read the file pyproject.toml and tell me the project name.")
    tool_calls = extract_tool_calls(events)

    assert len(tool_calls) > 0, f"Expected tool calls, got none."

    tool_names = [tc["part"]["name"] for tc in tool_calls]
    assert "view_file" in tool_names, f"Expected 'view_file' tool call, got: {tool_names}"


def test_goz_run_uses_bash_tool():
    """Agent should use bash tool when asked to run a command."""
    events = run_goz("Run 'echo hello_from_goz' using the bash tool and show me the output.")
    tool_calls = extract_tool_calls(events)

    assert len(tool_calls) > 0, f"Expected tool calls, got none."

    tool_names = [tc["part"]["name"] for tc in tool_calls]
    assert "bash" in tool_names, f"Expected 'bash' tool call, got: {tool_names}"

    bash_calls = [tc for tc in tool_calls if tc["part"]["name"] == "bash"]
    outputs = [tc["part"]["output"] for tc in bash_calls]
    assert any("hello_from_goz" in o for o in outputs), f"Expected bash output with 'hello_from_goz', got: {outputs}"


def test_goz_run_tool_inputs_not_empty():
    """Tool calls should have non-empty inputs (regression for input_schema bug)."""
    events = run_goz("Use the glob tool to find all *.py files.")
    tool_calls = extract_tool_calls(events)

    assert len(tool_calls) > 0, "Expected tool calls"

    for tc in tool_calls:
        inp = tc["part"].get("input", {})
        assert inp != {}, f"Tool {tc['part']['name']} called with empty input: {tc}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
