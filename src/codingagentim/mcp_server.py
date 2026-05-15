"""MCP Server mode — exposes codingagentim capabilities as MCP tools (stdio transport)."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any


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
        result = await _call_tool(tool_name, arguments)
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
    ]


async def _call_tool(name: str, arguments: dict) -> Any:
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

    return {"error": f"Unknown tool: {name}"}


async def serve_stdio() -> None:
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    transport, _ = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.Protocol, sys.stdout
    )

    while True:
        try:
            header = b""
            while True:
                line = await reader.readline()
                if line == b"\r\n" or line == b"\n":
                    break
                header += line
                if not line:
                    return

            content_length = 0
            for h in header.decode().split("\r\n"):
                if h.lower().startswith("content-length:"):
                    content_length = int(h.split(":")[1].strip())

            if content_length == 0:
                continue

            body = await reader.readexactly(content_length)
            request = json.loads(body.decode())
            response = await handle_request(request)

            if response is None:
                continue

            response_bytes = json.dumps(response).encode()
            message = f"Content-Length: {len(response_bytes)}\r\n\r\n".encode() + response_bytes
            transport.write(message)

        except (asyncio.IncompleteReadError, ConnectionError):
            break
        except Exception as e:
            sys.stderr.write(f"MCP server error: {e}\n")


def run_mcp_server() -> None:
    asyncio.run(serve_stdio())
