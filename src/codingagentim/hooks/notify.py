"""Hook notification entry point — called by AI coding tool hooks."""

from __future__ import annotations

import asyncio
import sys

from codingagentim import config
from codingagentim.core.registry import get_provider
from codingagentim.hooks.adapters import parse_hook_data


def run_notify(source_tool: str, event_type: str) -> None:
    raw_input = ""
    if not sys.stdin.isatty():
        raw_input = sys.stdin.read()

    hook_data = parse_hook_data(source_tool, raw_input)
    hook_data["event"] = event_type

    provider_name = config.get("default_provider", "dingtalk")
    target = config.get("hook.notify_target", "")
    if not target:
        print("Warning: hook.notify_target not configured, skipping notification")
        return

    summary = hook_data.get("summary", "")
    tool_name = hook_data.get("tool", source_tool)
    text = f"[{tool_name}] {event_type}: {summary}" if summary else f"[{tool_name}] {event_type}"

    asyncio.run(_send(provider_name, target, text))


async def _send(provider_name: str, target: str, text: str) -> None:
    import codingagentim.providers.dingtalk  # noqa: F401 — ensure provider is registered

    provider = get_provider(provider_name)
    await provider.send_message(target, text)
    print(f"Notification sent to {provider_name}")
