"""Adapters for different AI coding tool hook data formats."""

from __future__ import annotations

import json
from typing import Any


def parse_hook_data(source_tool: str, raw_input: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_input)
    except json.JSONDecodeError:
        data = {"text": raw_input}

    adapter = _adapters.get(source_tool, _default_adapter)
    return adapter(data)


def _claude_code_adapter(data: dict) -> dict[str, Any]:
    return {
        "tool": "claude-code",
        "event": data.get("event", "task_complete"),
        "summary": data.get("result", data.get("summary", "")),
        "session_id": data.get("session_id", ""),
        "cost": data.get("cost", ""),
    }


def _codex_adapter(data: dict) -> dict[str, Any]:
    return {
        "tool": "codex",
        "event": data.get("event", "task_complete"),
        "summary": data.get("output", data.get("summary", "")),
    }


def _default_adapter(data: dict) -> dict[str, Any]:
    return {
        "tool": "unknown",
        "event": "task_complete",
        "summary": data.get("summary", data.get("text", str(data))),
    }


_adapters = {
    "claude-code": _claude_code_adapter,
    "codex": _codex_adapter,
    "gemini": _default_adapter,
    "opencode": _default_adapter,
}
