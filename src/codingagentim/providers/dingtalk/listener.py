"""DingTalk Stream listener — reverse link entry point (IM → Agent)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import dingtalk_stream
from dingtalk_stream import AckMessage

from codingagentim import config
from codingagentim.core.dispatcher import AgentDispatcher
from codingagentim.core.models import Message

if TYPE_CHECKING:
    from codingagentim.providers.dingtalk.provider import DingTalkProvider

logger = logging.getLogger(__name__)


class BotMessageHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, provider: DingTalkProvider, dispatcher: AgentDispatcher):
        super().__init__()
        self.provider = provider
        self.dispatcher = dispatcher

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        text = (incoming.text.content or "").strip()

        if not text:
            return AckMessage.STATUS_OK, "OK"

        logger.info("Received message from %s: %s", incoming.sender_nick, text[:100])

        msg = Message(
            sender_id=incoming.sender_staff_id or incoming.sender_id,
            sender_name=incoming.sender_nick or "",
            conversation_id=incoming.conversation_id or "",
            content=text,
            raw=callback.data,
        )

        try:
            await self.provider.reply_message(msg, "收到，正在处理...")
        except Exception as e:
            logger.warning("Failed to send ack reply: %s", e)

        result = await self.dispatcher.dispatch(text)

        try:
            await self.provider.reply_message(msg, result.summary or "Done (no output)")
        except Exception as e:
            logger.error("Failed to send result reply: %s", e)

        return AckMessage.STATUS_OK, "OK"


class DingTalkListener:
    def __init__(
        self,
        provider: DingTalkProvider,
        dispatcher: AgentDispatcher,
        app_key: str | None = None,
        app_secret: str | None = None,
    ):
        self.provider = provider
        self.dispatcher = dispatcher
        self._app_key = app_key or config.get("dingtalk.app_key", "")
        self._app_secret = app_secret or config.get("dingtalk.app_secret", "")

    def start(self) -> None:
        credential = dingtalk_stream.Credential(self._app_key, self._app_secret)
        client = dingtalk_stream.DingTalkStreamClient(credential)

        handler = BotMessageHandler(self.provider, self.dispatcher)
        client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            handler,
        )

        logger.info("Starting DingTalk stream listener...")
        client.start_forever()
