"""MCP Server mode — exposes codingagentim capabilities as MCP tools (stdio transport).

Uses the official `mcp` SDK (FastMCP) for proper protocol negotiation and compatibility
with Claude Code and other MCP clients.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

_HOME = Path.home()
_NOTIF_FILE = _HOME / ".codingagentim" / "notifications.jsonl"
_OFFSET_FILE = _HOME / ".codingagentim" / ".notif_mcp_offset"
_LOG_FILE = _HOME / ".codingagentim" / "bridge.err.log"
_LABEL = "com.codingagentim.bridge"

mcp = FastMCP("codingagentim", log_level="WARNING")


# --- Tools ---


@mcp.tool()
async def check_notifications() -> str:
    """检查钉钉 bridge 新通知。返回自上次检查以来的新消息列表（received/completed/failed），自动更新已读偏移。无新通知时返回空列表，此时不要向用户输出任何内容。"""
    return json.dumps(_check_notifications_impl(), ensure_ascii=False)


@mcp.tool()
async def poll_notifications(timeout: int = 30, interval: int = 5) -> str:
    """长轮询钉钉通知。阻塞等待直到有新通知或超时。支持秒级响应，适合替代分钟级 cron。"""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        notifs = _check_notifications_impl()
        if notifs:
            return json.dumps(notifs, ensure_ascii=False)
        await asyncio.sleep(interval)
    return "[]"


@mcp.tool()
async def get_reply_level() -> str:
    """获取当前钉钉回复级别。verbose=话痨（发关键中间进展+结果），normal=正常（收到+结果），quiet=静默（只发最终结果）。"""
    from codingagentim.config import get_reply_level as _get_level

    return json.dumps({"level": _get_level()}, ensure_ascii=False)


@mcp.tool()
async def set_reply_level(level: str) -> str:
    """设置钉钉回复级别。verbose=话痨，normal=正常，quiet=静默。也可以通过钉钉发 /verbose /normal /quiet 修改。"""
    from codingagentim.config import set_reply_level as _set_level, get_reply_level as _get_level

    _set_level(level)
    return json.dumps({"level": _get_level(), "status": "ok"}, ensure_ascii=False)


@mcp.tool()
async def get_bridge_status(log_lines: int = 10) -> str:
    """获取钉钉 bridge daemon 运行状态和最近活动日志。"""
    return json.dumps(_get_bridge_status_impl(log_lines), ensure_ascii=False)


@mcp.tool()
async def dingtalk_send_message(target: str, content: str, msg_type: str = "text") -> str:
    """Send a message to a DingTalk group or user."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    provider = DingTalkProvider()
    msg = await provider.send_message(target, content, msg_type)
    return json.dumps(msg.model_dump(mode="json"), ensure_ascii=False)


@mcp.tool()
async def dingtalk_search_contact(query: str, limit: int = 10) -> str:
    """Search DingTalk contacts by name or keyword."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    provider = DingTalkProvider()
    contacts = await provider.search_contact(query, limit)
    return json.dumps([c.model_dump(mode="json") for c in contacts], ensure_ascii=False)


@mcp.tool()
async def dingtalk_create_todo(title: str, description: str = "") -> str:
    """Create a DingTalk todo item."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    provider = DingTalkProvider()
    todo = await provider.create_todo(title, description=description)
    return json.dumps(todo.model_dump(mode="json"), ensure_ascii=False)


@mcp.tool()
async def dingtalk_list_calendar(date: str = "") -> str:
    """List DingTalk calendar events for a given date (YYYY-MM-DD format, default: today)."""
    from codingagentim.providers.dingtalk import DingTalkProvider

    provider = DingTalkProvider()
    events = await provider.list_calendar_events(date or None)
    return json.dumps([e.model_dump(mode="json") for e in events], ensure_ascii=False)


@mcp.tool()
async def reply_dingtalk(sender_id: str, content: str, msg_type: str = "markdown") -> str:
    """回复钉钉用户消息。用于在完成任务后将结果发送给发消息的用户。"""
    from codingagentim.providers.dingtalk import DingTalkProvider

    provider = DingTalkProvider()
    result = await provider.send_to_user(
        user_ids=[sender_id], content=content, msg_type=msg_type
    )
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)


@mcp.tool()
async def reply_image(sender_id: str, image_path: str) -> str:
    """发送图片给钉钉用户。支持本地文件路径。用于发送截图、生成的图片等给发消息的用户。"""
    from codingagentim.providers.dingtalk import DingTalkProvider

    image_file = Path(image_path)
    if not image_file.exists():
        return json.dumps({"error": f"File not found: {image_path}"})

    provider = DingTalkProvider()
    image_data = image_file.read_bytes()
    result = await provider.send_image_to_user(
        user_ids=[sender_id], image_data=image_data, filename=image_file.name
    )
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)


@mcp.tool()
async def reply_file(sender_id: str, file_path: str) -> str:
    """发送文件给钉钉用户。支持本地文件路径。"""
    from codingagentim.providers.dingtalk import DingTalkProvider

    local_file = Path(file_path)
    if not local_file.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    provider = DingTalkProvider()
    file_data = local_file.read_bytes()
    result = await provider.send_file_to_user(
        user_ids=[sender_id], file_data=file_data, filename=local_file.name
    )
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)


# --- Internal helpers ---


def _check_notifications_impl() -> list[dict]:
    if not _NOTIF_FILE.exists():
        return []

    try:
        size = _NOTIF_FILE.stat().st_size
    except OSError:
        return []

    offset = 0
    try:
        offset = int(_OFFSET_FILE.read_text().strip())
    except (OSError, ValueError):
        pass

    if size < offset:
        offset = 0
    elif size == offset:
        return []

    try:
        with open(_NOTIF_FILE, "rb") as f:
            f.seek(offset)
            new_data = f.read().decode("utf-8").strip()
    except OSError:
        return []

    if not new_data:
        return []

    try:
        _OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
        _OFFSET_FILE.write_text(str(size))
    except OSError:
        pass

    notifications = []
    for line in new_data.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            notifications.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            pass

    return notifications


_check_notifications = _check_notifications_impl


def _get_bridge_status_impl(log_lines: int = 10) -> dict:
    status: dict[str, Any] = {"running": False, "pid": None, "recent_log": []}

    try:
        result = subprocess.run(
            ["launchctl", "print", f"gui/{_get_uid()}/{_LABEL}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            status["running"] = "state = running" in result.stdout
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("pid ="):
                    status["pid"] = int(line.split("=")[1].strip())
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass

    if _LOG_FILE.exists():
        try:
            lines = _LOG_FILE.read_text().strip().splitlines()
            status["recent_log"] = lines[-log_lines:]
        except OSError:
            pass

    return status


def _get_uid() -> int:
    import os

    return os.getuid()


def run_mcp_server() -> None:
    mcp.run(transport="stdio")
