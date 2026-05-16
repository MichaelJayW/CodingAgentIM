"""Tests for BridgeMessageHandler and helper functions."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codingagentim.providers.dingtalk.handlers.base import find_claude_bin
from codingagentim.providers.dingtalk.handlers.bridge import BridgeMessageHandler


@pytest.fixture(autouse=True)
def _no_notifications(monkeypatch):
    noop = lambda *a, **kw: None
    monkeypatch.setattr(
        "codingagentim.providers.dingtalk.handlers.base.push_notification", noop,
    )
    monkeypatch.setattr(
        "codingagentim.providers.dingtalk.handlers.bridge.push_notification", noop,
    )


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.reply_message = AsyncMock()
    return provider


def _make_incoming(text: str, sender_nick: str = "Alice", sender_id: str = "u1",
                   conversation_id: str = "conv1", conversation_type: str = "2"):
    msg = MagicMock()
    msg.text.content = text
    msg.sender_nick = sender_nick
    msg.sender_staff_id = sender_id
    msg.sender_id = sender_id
    msg.conversation_id = conversation_id
    msg.conversation_type = conversation_type
    msg.message_id = f"msg_{text[:5]}"
    return msg


class TestFindClaudeBin:
    def test_finds_via_which(self):
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            assert find_claude_bin() == "/usr/local/bin/claude"

    def test_falls_back_to_homebrew(self, tmp_path):
        with patch("shutil.which", return_value=None):
            with patch("codingagentim.providers.dingtalk.handlers.base.Path") as MockPath:
                homebrew = MagicMock()
                homebrew.exists.return_value = True
                homebrew.__str__ = lambda self: "/opt/homebrew/bin/claude"

                def path_side_effect(p):
                    if p == "/opt/homebrew/bin/claude":
                        return homebrew
                    m = MagicMock()
                    m.exists.return_value = False
                    return m

                MockPath.side_effect = path_side_effect
                MockPath.home.return_value = tmp_path
                result = find_claude_bin()
                assert "claude" in result

    def test_returns_claude_as_fallback(self):
        with patch("shutil.which", return_value=None):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("subprocess.run", side_effect=Exception("no npm")):
                    result = find_claude_bin()
                    assert result == "claude"


class TestBridgeMessageHandler:
    @pytest.mark.asyncio
    async def test_empty_message_skipped(self, mock_provider):
        handler = BridgeMessageHandler(mock_provider, session_id="sess1")

        with patch("dingtalk_stream.ChatbotMessage") as MockMsg:
            MockMsg.from_dict.return_value = _make_incoming("   ")
            callback = MagicMock()
            callback.data = {}
            status, _ = await handler.process(callback)

        assert status == 200
        mock_provider.reply_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sends_ack_then_result(self, mock_provider):
        handler = BridgeMessageHandler(mock_provider, session_id="sess1")

        with patch("dingtalk_stream.ChatbotMessage") as MockMsg:
            MockMsg.from_dict.return_value = _make_incoming("写个排序")
            with patch.object(handler, "_run_claude_streaming",
                              new_callable=AsyncMock, return_value=("排序完成", "new_session")):
                with patch("codingagentim.providers.dingtalk.handlers.base.load_sessions", return_value={}):
                    with patch("codingagentim.providers.dingtalk.handlers.base.save_sessions"):
                        callback = MagicMock()
                        callback.data = {}
                        status, _ = await handler.process(callback)

        assert status == 200
        calls = mock_provider.reply_message.call_args_list
        assert len(calls) >= 2
        ack_text = calls[0][0][1]
        assert "收到" in ack_text
        result_text = calls[1][0][1]
        assert "排序完成" in result_text

    @pytest.mark.asyncio
    async def test_tracks_user_session(self, mock_provider):
        handler = BridgeMessageHandler(mock_provider, session_id="main_sess")
        handler._user_sessions = {}

        with patch("dingtalk_stream.ChatbotMessage") as MockMsg:
            MockMsg.from_dict.return_value = _make_incoming("hello")
            with patch.object(handler, "_run_claude_streaming",
                              new_callable=AsyncMock, return_value=("ok", "fork_123")):
                with patch("codingagentim.providers.dingtalk.handlers.base.save_sessions"):
                    callback = MagicMock()
                    callback.data = {}
                    await handler.process(callback)

        assert handler._user_sessions.get("conv1") == "fork_123"

    @pytest.mark.asyncio
    async def test_file_not_found_error(self, mock_provider):
        handler = BridgeMessageHandler(mock_provider, session_id="sess1")

        with patch("dingtalk_stream.ChatbotMessage") as MockMsg:
            MockMsg.from_dict.return_value = _make_incoming("test")
            with patch.object(handler, "_run_claude_streaming",
                              new_callable=AsyncMock, side_effect=FileNotFoundError):
                callback = MagicMock()
                callback.data = {}
                status, _ = await handler.process(callback)

        assert status == 200
        last_call = mock_provider.reply_message.call_args_list[-1]
        assert "未找到" in last_call[0][1]
