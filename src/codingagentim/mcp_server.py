"""MCP Server mode — exposes codingagentim capabilities as MCP tools (stdio transport)."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_HOME = Path.home()
_NOTIF_FILE = _HOME / ".codingagentim" / "notifications.jsonl"
_OFFSET_FILE = _HOME / ".codingagentim" / ".notif_mcp_offset"
_LOG_FILE = _HOME / ".codingagentim" / "bridge.err.log"
_LABEL = "com.codingagentim.bridge"


async def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "codingagentim", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return None  # type: ignore

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": _get_tools()},
        }

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = await _call_tool(tool_name, arguments)
        except Exception as e:
            sys.stderr.write(f"Tool call error ({tool_name}): {e}\n")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": str(e)}, ensure_ascii=False)}],
                    "isError": True,
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def _get_tools() -> list[dict]:
    return [
        {
            "name": "check_notifications",
            "description": (
                "检查钉钉 bridge 新通知。返回自上次检查以来的新消息列表"
                "（received/completed/failed），自动更新已读偏移。"
                "无新通知时返回空列表，此时不要向用户输出任何内容。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "poll_notifications",
            "description": (
                "长轮询钉钉通知。阻塞等待直到有新通知或超时。"
                "支持秒级响应，适合替代分钟级 cron。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "integer",
                        "description": "最长等待秒数（默认 30）",
                        "default": 30,
                    },
                    "interval": {
                        "type": "integer",
                        "description": "检查间隔秒数（默认 5）",
                        "default": 5,
                    },
                },
            },
        },
        {
            "name": "get_reply_level",
            "description": (
                "获取当前钉钉回复级别。verbose=话痨（发关键中间进展+结果），"
                "normal=正常（收到+结果），quiet=静默（只发最终结果）。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "set_reply_level",
            "description": (
                "设置钉钉回复级别。verbose=话痨（发关键中间进展+结果），"
                "normal=正常（收到+结果），quiet=静默（只发最终结果）。"
                "也可以通过钉钉发 /verbose /normal /quiet 修改。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["verbose", "normal", "quiet"],
                        "description": "回复级别",
                    },
                },
                "required": ["level"],
            },
        },
        {
            "name": "get_bridge_status",
            "description": "获取钉钉 bridge daemon 运行状态和最近活动日志。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "log_lines": {
                        "type": "integer",
                        "description": "返回最近几行日志（默认 10）",
                        "default": 10,
                    },
                },
            },
        },
        {
            "name": "dingtalk_send_message",
            "description": "Send a message to a DingTalk group or user",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Group conversation ID"},
                    "content": {"type": "string", "description": "Message content"},
                    "msg_type": {
                        "type": "string",
                        "enum": ["text", "markdown"],
                        "default": "text",
                    },
                },
                "required": ["target", "content"],
            },
        },
        {
            "name": "dingtalk_search_contact",
            "description": "Search DingTalk contacts by name or keyword",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
        {
            "name": "dingtalk_create_todo",
            "description": "Create a DingTalk todo item",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Todo title"},
                    "description": {"type": "string", "default": ""},
                },
                "required": ["title"],
            },
        },
        {
            "name": "dingtalk_list_calendar",
            "description": "List DingTalk calendar events for a given date",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)",
                    },
                },
            },
        },
        {
            "name": "reply_dingtalk",
            "description": (
                "回复钉钉用户消息。用于在完成任务后将结果发送给发消息的用户。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sender_id": {
                        "type": "string",
                        "description": "用户 ID（从 check_notifications 返回的 sender_id 字段获取）",
                    },
                    "content": {
                        "type": "string",
                        "description": "回复内容",
                    },
                    "msg_type": {
                        "type": "string",
                        "enum": ["text", "markdown"],
                        "default": "markdown",
                    },
                },
                "required": ["sender_id", "content"],
            },
        },
        {
            "name": "reply_image",
            "description": (
                "发送图片给钉钉用户。支持本地文件路径。"
                "用于发送截图、生成的图片等给发消息的用户。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sender_id": {
                        "type": "string",
                        "description": "用户 ID（从 check_notifications 返回的 sender_id 字段获取）",
                    },
                    "image_path": {
                        "type": "string",
                        "description": "本地图片文件路径",
                    },
                },
                "required": ["sender_id", "image_path"],
            },
        },
        {
            "name": "reply_file",
            "description": (
                "发送文件给钉钉用户。支持本地文件路径。"
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sender_id": {
                        "type": "string",
                        "description": "用户 ID（从 check_notifications 返回的 sender_id 字段获取）",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "本地文件路径",
                    },
                },
                "required": ["sender_id", "file_path"],
            },
        },
    ]


async def _poll_notifications(timeout: int = 30, interval: int = 5) -> list[dict]:
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        notifs = _check_notifications()
        if notifs:
            return notifs
        await asyncio.sleep(interval)
    return []


def _check_notifications() -> list[dict]:
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


_check_notifications_impl = _check_notifications


def _get_bridge_status(log_lines: int = 10) -> dict:
    status: dict[str, Any] = {"running": False, "pid": None, "recent_log": []}

    try:
        result = subprocess.run(
            ["launchctl", "print", f"gui/{_get_uid()}/{_LABEL}"],
            capture_output=True, text=True, timeout=5,
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


async def _call_tool(name: str, arguments: dict) -> Any:
    if name == "check_notifications":
        return _check_notifications()

    if name == "poll_notifications":
        return await _poll_notifications(
            timeout=arguments.get("timeout", 30),
            interval=arguments.get("interval", 5),
        )

    if name == "get_reply_level":
        from codingagentim.config import get_reply_level
        return {"level": get_reply_level()}

    if name == "set_reply_level":
        from codingagentim.config import set_reply_level, get_reply_level
        set_reply_level(arguments["level"])
        return {"level": get_reply_level(), "status": "ok"}

    if name == "get_bridge_status":
        return _get_bridge_status(arguments.get("log_lines", 10))

    from codingagentim.providers.dingtalk import DingTalkProvider

    provider = DingTalkProvider()

    if name == "dingtalk_send_message":
        msg = await provider.send_message(
            arguments["target"],
            arguments["content"],
            arguments.get("msg_type", "text"),
        )
        return msg.model_dump(mode="json")

    if name == "dingtalk_search_contact":
        contacts = await provider.search_contact(
            arguments["query"], arguments.get("limit", 10)
        )
        return [c.model_dump(mode="json") for c in contacts]

    if name == "dingtalk_create_todo":
        todo = await provider.create_todo(
            arguments["title"], description=arguments.get("description", "")
        )
        return todo.model_dump(mode="json")

    if name == "dingtalk_list_calendar":
        events = await provider.list_calendar_events(arguments.get("date"))
        return [e.model_dump(mode="json") for e in events]

    if name == "reply_dingtalk":
        result = await provider.send_to_user(
            user_ids=[arguments["sender_id"]],
            content=arguments["content"],
            msg_type=arguments.get("msg_type", "markdown"),
        )
        return result.model_dump(mode="json")

    if name == "reply_image":
        image_path = arguments["image_path"]
        image_file = Path(image_path)
        if not image_file.exists():
            return {"error": f"File not found: {image_path}"}
        image_data = image_file.read_bytes()
        result = await provider.send_image_to_user(
            user_ids=[arguments["sender_id"]],
            image_data=image_data,
            filename=image_file.name,
        )
        return result.model_dump(mode="json")

    if name == "reply_file":
        file_path = arguments["file_path"]
        local_file = Path(file_path)
        if not local_file.exists():
            return {"error": f"File not found: {file_path}"}
        file_data = local_file.read_bytes()
        result = await provider.send_file_to_user(
            user_ids=[arguments["sender_id"]],
            file_data=file_data,
            filename=local_file.name,
        )
        return result.model_dump(mode="json")

    return {"error": f"Unknown tool: {name}"}


async def serve_stdio() -> None:
    loop = asyncio.get_event_loop()
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    def _read_message() -> bytes | None:
        header = b""
        while True:
            line = stdin.readline()
            if not line:
                return None
            if line == b"\r\n" or line == b"\n":
                break
            header += line

        content_length = 0
        for h in header.decode().split("\r\n"):
            if h.lower().startswith("content-length:"):
                content_length = int(h.split(":")[1].strip())

        if content_length == 0:
            return b""
        return stdin.read(content_length)

    while True:
        try:
            body = await loop.run_in_executor(None, _read_message)
            if body is None:
                break
            if not body:
                continue

            request = json.loads(body.decode())
            response = await handle_request(request)

            if response is None:
                continue

            response_bytes = json.dumps(response).encode()
            message = f"Content-Length: {len(response_bytes)}\r\n\r\n".encode() + response_bytes
            stdout.write(message)
            stdout.flush()

        except (ConnectionError, OSError):
            break
        except Exception as e:
            sys.stderr.write(f"MCP server error: {e}\n")


def run_mcp_server() -> None:
    asyncio.run(serve_stdio())
