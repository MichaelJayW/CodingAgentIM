"""InboxMessageHandler — queues messages for the active Claude session to process."""

from __future__ import annotations

from typing import TYPE_CHECKING

import dingtalk_stream
from dingtalk_stream import AckMessage

from codingagentim.core.message_queue import push_inbox
from codingagentim.core.models import Message
from codingagentim.providers.dingtalk.handlers.base import (
    DeduplicatedHandler,
    console,
    logger,
    push_notification,
)

if TYPE_CHECKING:
    from codingagentim.providers.dingtalk.provider import DingTalkProvider


class InboxMessageHandler(DeduplicatedHandler, dingtalk_stream.ChatbotHandler):
    """Inbox mode: queues messages for the human-facing Claude session to pick up."""

    def __init__(self, provider: DingTalkProvider):
        DeduplicatedHandler.__init__(self)
        dingtalk_stream.ChatbotHandler.__init__(self)
        self.provider = provider

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        if self._is_duplicate(incoming.message_id):
            return AckMessage.STATUS_OK, "OK"
        text = (incoming.text.content or "").strip()

        if not text:
            return AckMessage.STATUS_OK, "OK"

        sender = incoming.sender_nick or ""
        sender_id = incoming.sender_staff_id or incoming.sender_id or ""
        conversation_id = incoming.conversation_id or ""
        is_group = incoming.conversation_type == "2"
        chat_type = "群聊" if is_group else "单聊"

        console.print(f"\n[bold cyan]━━━ 收到消息[/bold cyan]({chat_type}) from [bold]{sender}[/bold]: {text[:80]}")
        logger.info("Inbox: %s from %s: %s", chat_type, sender, text[:100])

        push_inbox(
            text=text,
            sender=sender,
            sender_id=sender_id,
            conversation_id=conversation_id,
            is_group=is_group,
        )

        push_notification(
            sender, text, ntype="received", chat=chat_type, sender_id=sender_id,
        )

        msg = Message(
            sender_id=sender_id,
            sender_name=sender,
            conversation_id=conversation_id if is_group else "",
            content=text,
            raw=callback.data,
        )

        try:
            await self.provider.reply_message(
                msg, "📥 收到，已加入待办队列", msg_type="markdown",
            )
        except Exception as e:
            logger.warning("Failed to send ack: %s", e)

        console.print(f"[bold green]━━━ 已入队[/bold green]")
        return AckMessage.STATUS_OK, "OK"
