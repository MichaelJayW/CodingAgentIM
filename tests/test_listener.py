"""Tests for DingTalk listener."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codingagentim.core.dispatcher import AgentDispatcher
from codingagentim.core.models import AgentResult
from codingagentim.providers.dingtalk.listener import BotMessageHandler


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.reply_message = AsyncMock()
    return provider


@pytest.fixture
def mock_dispatcher():
    dispatcher = MagicMock(spec=AgentDispatcher)
    dispatcher.dispatch = AsyncMock(
        return_value=AgentResult(
            exit_code=0,
            stdout="done",
            agent="claude",
            summary="Task completed successfully",
        )
    )
    return dispatcher


def _make_callback(text: str, sender_nick: str = "test_user") -> MagicMock:
    callback = MagicMock()
    callback.data = {
        "text": {"content": text},
        "senderNick": sender_nick,
        "senderStaffId": "staff_123",
        "senderId": "sender_456",
        "conversationId": "conv_789",
    }
    return callback


@pytest.mark.asyncio
async def test_process_dispatches_to_agent(mock_provider, mock_dispatcher):
    handler = BotMessageHandler(mock_provider, mock_dispatcher)

    with patch("dingtalk_stream.ChatbotMessage") as MockMsg:
        msg_instance = MagicMock()
        msg_instance.text.content = "refactor auth module"
        msg_instance.sender_staff_id = "staff_123"
        msg_instance.sender_id = "sender_456"
        msg_instance.sender_nick = "test_user"
        msg_instance.conversation_id = "conv_789"
        MockMsg.from_dict.return_value = msg_instance

        callback = _make_callback("refactor auth module")
        status, msg = await handler.process(callback)

    assert status == 200
    mock_dispatcher.dispatch.assert_awaited_once_with("refactor auth module")
    assert mock_provider.reply_message.await_count == 2


@pytest.mark.asyncio
async def test_process_empty_message_skips(mock_provider, mock_dispatcher):
    handler = BotMessageHandler(mock_provider, mock_dispatcher)

    with patch("dingtalk_stream.ChatbotMessage") as MockMsg:
        msg_instance = MagicMock()
        msg_instance.text.content = "   "
        MockMsg.from_dict.return_value = msg_instance

        callback = _make_callback("   ")
        status, msg = await handler.process(callback)

    assert status == 200
    mock_dispatcher.dispatch.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_handles_reply_failure(mock_provider, mock_dispatcher):
    handler = BotMessageHandler(mock_provider, mock_dispatcher)
    mock_provider.reply_message = AsyncMock(side_effect=[Exception("network error"), None])

    with patch("dingtalk_stream.ChatbotMessage") as MockMsg:
        msg_instance = MagicMock()
        msg_instance.text.content = "test"
        msg_instance.sender_staff_id = "staff_123"
        msg_instance.sender_id = "sender_456"
        msg_instance.sender_nick = "tester"
        msg_instance.conversation_id = "conv_789"
        MockMsg.from_dict.return_value = msg_instance

        callback = _make_callback("test")
        status, _ = await handler.process(callback)

    assert status == 200
    mock_dispatcher.dispatch.assert_awaited_once()
