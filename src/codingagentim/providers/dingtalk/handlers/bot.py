"""BotMessageHandler — dispatches messages to coding agent CLIs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import dingtalk_stream
from dingtalk_stream import AckMessage

from codingagentim.core.dispatcher import AgentDispatcher
from codingagentim.core.models import Message
from codingagentim.providers.dingtalk.handlers.base import (
    DeduplicatedHandler,
    console,
    logger,
)

if TYPE_CHECKING:
    from codingagentim.providers.dingtalk.provider import DingTalkProvider


class BotMessageHandler(DeduplicatedHandler, dingtalk_stream.ChatbotHandler):
    def __init__(self, provider: DingTalkProvider, dispatcher: AgentDispatcher):
        DeduplicatedHandler.__init__(self)
        dingtalk_stream.ChatbotHandler.__init__(self)
        self.provider = provider
        self.dispatcher = dispatcher

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        if self._is_duplicate(incoming.message_id):
            return AckMessage.STATUS_OK, "OK"
        text = (incoming.text.content or "").strip()

        if not text:
            return AckMessage.STATUS_OK, "OK"

        sender = incoming.sender_nick or ""
        conversation_id = incoming.conversation_id or ""
        is_group = incoming.conversation_type == "2"
        chat_type = "群聊" if is_group else "单聊"

        console.print(f"\n[bold cyan]━━━ 收到消息[/bold cyan]({chat_type}) from [bold]{sender}[/bold]: {text[:80]}")
        console.print(f"[dim]  Dispatching to {self.dispatcher.default_agent}...[/dim]")
        logger.info("Received %s message from %s: %s", chat_type, sender, text[:100])

        msg = Message(
            sender_id=incoming.sender_staff_id or incoming.sender_id,
            sender_name=sender,
            conversation_id=conversation_id if is_group else "",
            content=text,
            raw=callback.data,
        )

        try:
            await self.provider.reply_message(
                msg, f"⏳ 收到「{text[:20]}」，正在处理...", msg_type="markdown",
            )
        except Exception as e:
            logger.warning("Failed to send ack reply: %s", e)

        progress_count = 0

        async def on_progress(line: str) -> None:
            nonlocal progress_count
            if progress_count >= 3:
                return
            progress_count += 1
            snippet = line[:60] + ("..." if len(line) > 60 else "")
            try:
                await self.provider.reply_message(
                    msg, f"🔄 {snippet}", msg_type="markdown",
                )
            except Exception as e:
                logger.warning("Failed to send progress: %s", e)

        def on_output(line: str) -> None:
            console.print(f"[dim]│[/dim] {line}", end="", highlight=False)

        result = await self.dispatcher.dispatch(
            text,
            on_output=on_output,
            on_progress=on_progress,
            sender=sender,
            conversation_id=conversation_id,
        )

        status_style = "green" if result.exit_code == 0 else "red"
        console.print(f"[bold {status_style}]━━━ 完成[/bold {status_style}] exit={result.exit_code}")

        reply = self._format_result_markdown(text, result)
        try:
            await self.provider.reply_message(msg, reply, msg_type="markdown")
        except Exception as e:
            logger.error("Failed to send result reply: %s", e)

        return AckMessage.STATUS_OK, "OK"

    @staticmethod
    def _format_result_markdown(prompt: str, result) -> str:
        status = "✅ 完成" if result.exit_code == 0 else "❌ 失败"
        parts = [f"### {status}"]
        parts.append(f"**任务**: {prompt[:50]}")
        parts.append(f"**Agent**: {result.agent}")
        if result.summary:
            parts.append(f"\n{result.summary[:1500]}")
        return "\n\n".join(parts)
