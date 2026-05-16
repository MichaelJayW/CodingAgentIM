"""Tests for MCP server request handling."""

import pytest

from codingagentim.mcp_server import _get_tools, handle_request


@pytest.mark.asyncio
async def test_initialize():
    resp = await handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "codingagentim"
    assert "protocolVersion" in resp["result"]


@pytest.mark.asyncio
async def test_notifications_initialized_returns_none():
    resp = await handle_request(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    assert resp is None


@pytest.mark.asyncio
async def test_tools_list():
    resp = await handle_request(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    )
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "dingtalk_send_message" in tool_names
    assert "dingtalk_search_contact" in tool_names
    assert "dingtalk_create_todo" in tool_names
    assert "dingtalk_list_calendar" in tool_names


@pytest.mark.asyncio
async def test_unknown_method():
    resp = await handle_request(
        {"jsonrpc": "2.0", "id": 3, "method": "nonexistent/method"}
    )
    assert "error" in resp
    assert resp["error"]["code"] == -32601


def test_get_tools_schema_valid():
    tools = _get_tools()
    assert len(tools) == 7
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"


@pytest.mark.asyncio
async def test_tools_call_unknown_tool():
    resp = await handle_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
    )
    content = resp["result"]["content"][0]["text"]
    assert "Unknown tool" in content
