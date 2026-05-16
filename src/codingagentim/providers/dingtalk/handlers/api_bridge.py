"""APIBridgeMessageHandler — direct Anthropic API mode, no CLI overhead."""

from __future__ import annotations

from typing import TYPE_CHECKING

import dingtalk_stream
from dingtalk_stream import AckMessage

from codingagentim.core.models import Message
from codingagentim.providers.dingtalk.handlers.base import (
    DeduplicatedHandler,
    console,
    load_conversations,
    logger,
    push_notification,
    save_conversations,
)

if TYPE_CHECKING:
    from codingagentim.providers.dingtalk.provider import DingTalkProvider


class APIBridgeMessageHandler(DeduplicatedHandler, dingtalk_stream.ChatbotHandler):
    """Direct Anthropic API mode: fastest response, no CLI overhead."""

    def __init__(self, provider: DingTalkProvider, model: str = "", system_prompt: str = ""):
        DeduplicatedHandler.__init__(self)
        dingtalk_stream.ChatbotHandler.__init__(self)
        self.provider = provider
        self._model = model
        self._system_prompt = system_prompt or (
            "你是一个AI编程助手，通过钉钉与用户交流。"
            "用中文回复，简洁清晰。如果用户请求编程任务，给出代码和解释。"
        )
        self._conversations: dict[str, list[dict]] = load_conversations()
        self._anthropic_client = None

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
        user_key = conversation_id if is_group else sender_id

        console.print(f"\n[bold cyan]━━━ 收到消息[/bold cyan]({chat_type}) from [bold]{sender}[/bold]: {text[:80]}")
        logger.info("API mode: %s from %s: %s", chat_type, sender, text[:100])
        push_notification(sender, text, ntype="received", chat=chat_type)

        msg = Message(
            sender_id=sender_id,
            sender_name=sender,
            conversation_id=conversation_id if is_group else "",
            content=text,
            raw=callback.data,
        )

        if text.strip().lower() in ("/clear", "/reset", "清除上下文", "重置对话"):
            self._conversations.pop(user_key, None)
            save_conversations(self._conversations)
            try:
                await self.provider.reply_message(msg, "对话已重置 ✨", msg_type="markdown")
            except Exception:
                pass
            return AckMessage.STATUS_OK, "OK"

        try:
            await self.provider.reply_message(msg, "⏳ [CodingAgentIM] 思考中...", msg_type="markdown")
        except Exception as e:
            logger.warning("Failed to send ack: %s", e)

        history = self._conversations.setdefault(user_key, [])
        history.append({"role": "user", "content": text})
        if len(history) > 40:
            history[:] = history[-30:]

        try:
            result_text = await self._call_api(history, msg)
            history.append({"role": "assistant", "content": result_text})
            save_conversations(self._conversations)
            console.print(f"[bold green]━━━ 完成[/bold green] ({len(result_text)} chars)")
            push_notification(sender, text, ntype="completed", chat=chat_type, result=result_text)
        except Exception as e:
            logger.error("API call failed: %s", e)
            result_text = f"API 调用失败: {e}"
            history.pop()
            console.print(f"[bold red]━━━ 失败[/bold red] {e}")
            push_notification(sender, text, ntype="failed", chat=chat_type, result=result_text)

        if not result_text.strip():
            result_text = "（处理完成，但无输出内容）"

        try:
            reply = result_text.rstrip() + "\n\n---\n*Powered by CodingAgentIM*"
            await self.provider.reply_message(msg, reply, msg_type="markdown")
        except Exception as e:
            logger.error("Failed to send result: %s", e)

        return AckMessage.STATUS_OK, "OK"

    def _get_anthropic_client(self):
        if self._anthropic_client is None:
            import os
            import anthropic

            api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
            base_url = os.environ.get("ANTHROPIC_BASE_URL") or None
            self._anthropic_client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url)
        return self._anthropic_client

    async def _call_api(self, messages: list[dict], msg: Message) -> str:
        import os

        model = self._model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        client = self._get_anthropic_client()

        try:
            collected = []

            async with client.messages.stream(
                model=model,
                max_tokens=4096,
                system=self._system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    collected.append(text)

            result = "".join(collected)
            if result:
                return result
        except Exception as e:
            logger.warning("Streaming failed, falling back to non-streaming: %s", e)

        logger.info("Streaming returned empty, trying non-streaming request")
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=self._system_prompt,
            messages=messages,
        )
        for block in response.content:
            if hasattr(block, "text"):
                return block.text

        return "（AI 未返回有效内容，请重试）"
