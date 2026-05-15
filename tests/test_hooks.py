"""Tests for hook adapters."""

from codingagentim.hooks.adapters import parse_hook_data


def test_claude_code_adapter():
    raw = '{"event": "task_complete", "result": "PR created", "session_id": "abc"}'
    data = parse_hook_data("claude-code", raw)
    assert data["tool"] == "claude-code"
    assert data["summary"] == "PR created"


def test_codex_adapter():
    raw = '{"output": "Done refactoring"}'
    data = parse_hook_data("codex", raw)
    assert data["tool"] == "codex"
    assert data["summary"] == "Done refactoring"


def test_unknown_tool():
    raw = '{"text": "hello"}'
    data = parse_hook_data("some-tool", raw)
    assert data["tool"] == "unknown"


def test_invalid_json():
    data = parse_hook_data("claude-code", "not json")
    assert data["tool"] == "claude-code"
