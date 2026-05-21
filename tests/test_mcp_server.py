"""Tests for MCP server tool functions."""

import json
from unittest.mock import patch

import pytest

from codingagentim.mcp_server import (
    _check_notifications_impl,
    _get_bridge_status_impl,
    check_notifications,
    get_bridge_status,
    get_reply_level,
    mcp,
    poll_notifications,
)


def test_mcp_server_has_all_tools():
    tool_names = [t.name for t in mcp._tool_manager._tools.values()]
    assert "check_notifications" in tool_names
    assert "poll_notifications" in tool_names
    assert "get_reply_level" in tool_names
    assert "set_reply_level" in tool_names
    assert "get_bridge_status" in tool_names
    assert "dingtalk_send_message" in tool_names
    assert "dingtalk_search_contact" in tool_names
    assert "dingtalk_create_todo" in tool_names
    assert "dingtalk_list_calendar" in tool_names
    assert "reply_dingtalk" in tool_names
    assert "reply_image" in tool_names
    assert "reply_file" in tool_names
    assert len(tool_names) == 12


@pytest.mark.asyncio
async def test_check_notifications_empty(tmp_path):
    with patch("codingagentim.mcp_server._NOTIF_FILE", tmp_path / "notif.jsonl"):
        result = await check_notifications()
        assert json.loads(result) == []


@pytest.mark.asyncio
async def test_check_notifications_with_data(tmp_path):
    notif_file = tmp_path / "notif.jsonl"
    offset_file = tmp_path / ".offset"
    notif_file.write_text('{"type":"received","sender":"test","text":"hello"}\n')

    with (
        patch("codingagentim.mcp_server._NOTIF_FILE", notif_file),
        patch("codingagentim.mcp_server._OFFSET_FILE", offset_file),
    ):
        result = await check_notifications()
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["sender"] == "test"


@pytest.mark.asyncio
async def test_poll_notifications_timeout(tmp_path):
    with patch("codingagentim.mcp_server._NOTIF_FILE", tmp_path / "notif.jsonl"):
        result = await poll_notifications(timeout=1, interval=1)
        assert json.loads(result) == []


@pytest.mark.asyncio
async def test_get_reply_level():
    with patch("codingagentim.config.get_reply_level", return_value="normal"):
        result = await get_reply_level()
        assert json.loads(result) == {"level": "normal"}


@pytest.mark.asyncio
async def test_get_bridge_status():
    with patch("codingagentim.mcp_server._get_bridge_status_impl", return_value={"running": False, "pid": None, "recent_log": []}):
        result = await get_bridge_status(log_lines=5)
        parsed = json.loads(result)
        assert parsed["running"] is False


def test_check_notifications_impl_no_file(tmp_path):
    with patch("codingagentim.mcp_server._NOTIF_FILE", tmp_path / "missing.jsonl"):
        assert _check_notifications_impl() == []


def test_check_notifications_impl_tracks_offset(tmp_path):
    notif_file = tmp_path / "notif.jsonl"
    offset_file = tmp_path / ".offset"
    notif_file.write_text('{"type":"received","text":"msg1"}\n{"type":"received","text":"msg2"}\n')

    with (
        patch("codingagentim.mcp_server._NOTIF_FILE", notif_file),
        patch("codingagentim.mcp_server._OFFSET_FILE", offset_file),
    ):
        result = _check_notifications_impl()
        assert len(result) == 2

        result2 = _check_notifications_impl()
        assert result2 == []


def test_mcp_server_name():
    assert mcp.name == "codingagentim"
