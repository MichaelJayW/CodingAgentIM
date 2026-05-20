"""InboxMessageHandler — queues messages for the active Claude session to process."""

from __future__ import annotations

import json as _json
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
    save_attachment,
)

if TYPE_CHECKING:
    from codingagentim.providers.dingtalk.provider import DingTalkProvider

_LEVEL_COMMANDS = {"/verbose": "verbose", "/normal": "normal", "/quiet": "quiet",
                   "话痨": "verbose", "正常": "normal", "静默": "quiet"}


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

        sender = incoming.sender_nick or ""
        sender_id = incoming.sender_staff_id or incoming.sender_id or ""
        conversation_id = incoming.conversation_id or ""
        is_group = incoming.conversation_type == "2"
        chat_type = "群聊" if is_group else "单聊"

        text, image_paths, audio_path = await self._extract_content(incoming, callback.data)

        if not text and not image_paths and not audio_path:
            return AckMessage.STATUS_OK, "OK"

        msg = Message(
            sender_id=sender_id,
            sender_name=sender,
            conversation_id=conversation_id if is_group else "",
            content=text,
            raw=callback.data,
            image_paths=image_paths,
            audio_path=audio_path,
        )

        if text and (text.lower() in _LEVEL_COMMANDS or text in _LEVEL_COMMANDS):
            level = _LEVEL_COMMANDS.get(text.lower()) or _LEVEL_COMMANDS[text]
            from codingagentim.config import set_reply_level
            set_reply_level(level)
            labels = {"verbose": "话痨", "normal": "正常", "quiet": "静默"}
            try:
                await self.provider.reply_message(
                    msg, f"已切换为【{labels[level]}】模式", msg_type="text",
                )
            except Exception:
                pass
            logger.info("Reply level changed to %s by %s", level, sender)
            return AckMessage.STATUS_OK, "OK"

        desc = text[:80] if text else (f"[图片x{len(image_paths)}]" if image_paths else "[语音]")
        console.print(f"\n[bold cyan]━━━ 收到消息[/bold cyan]({chat_type}) from [bold]{sender}[/bold]: {desc}")
        logger.info("Inbox: %s from %s: %s", chat_type, sender, desc)

        push_inbox(
            text=text,
            sender=sender,
            sender_id=sender_id,
            conversation_id=conversation_id,
            is_group=is_group,
            image_paths=image_paths or None,
            audio_path=audio_path,
        )

        push_notification(
            sender, text or desc, ntype="received", chat=chat_type, sender_id=sender_id,
            image_paths=image_paths or None, audio_path=audio_path,
        )

        from codingagentim.config import get_reply_level
        level = get_reply_level()

        if level in ("verbose", "normal"):
            ack_text = "📥 收到，Coding Agent 正在处理，稍等～" if level == "verbose" else "👌 收到，Coding Agent 处理中"
            try:
                await self.provider.reply_message(msg, ack_text, msg_type="text")
            except Exception as e:
                logger.warning("Failed to send ack: %s", e)

        console.print(f"[bold green]━━━ 已入队[/bold green]")
        return AckMessage.STATUS_OK, "OK"

    async def _extract_content(
        self, incoming: dingtalk_stream.ChatbotMessage, raw_data: dict,
    ) -> tuple[str, list[str], str]:
        """Extract text, image paths, and audio path from an incoming message.

        Returns (text, image_paths, audio_path).
        """
        msgtype = incoming.message_type or "text"
        text = ""
        image_paths: list[str] = []
        audio_path = ""
        robot_code = incoming.robot_code or self.provider._robot_code

        if msgtype == "text":
            text = (incoming.text.content or "").strip() if incoming.text else ""

        elif msgtype == "picture":
            download_codes = incoming.get_image_list() or []
            for i, code in enumerate(download_codes):
                try:
                    data, ct = await self.provider._api.download_media(code, robot_code)
                    path = save_attachment(data, f"image_{i}.png", ct)
                    image_paths.append(path)
                except Exception as e:
                    logger.warning("Failed to download image: %s", e)

        elif msgtype == "richText":
            text_parts = incoming.get_text_list() or []
            text = "\n".join(t for t in text_parts if t)
            download_codes = incoming.get_image_list() or []
            for i, code in enumerate(download_codes):
                try:
                    data, ct = await self.provider._api.download_media(code, robot_code)
                    path = save_attachment(data, f"richtext_image_{i}.png", ct)
                    image_paths.append(path)
                except Exception as e:
                    logger.warning("Failed to download richText image: %s", e)

        elif msgtype == "audio":
            content_data = raw_data.get("content", {})
            if isinstance(content_data, dict):
                download_code = content_data.get("downloadCode", "")
                recognition = content_data.get("recognition", "")
                if download_code:
                    try:
                        data, ct = await self.provider._api.download_media(download_code, robot_code)
                        audio_path = save_attachment(data, "voice.amr", ct)
                    except Exception as e:
                        logger.warning("Failed to download audio: %s", e)
                text = recognition or ""
                if not text and not audio_path:
                    text = "[语音消息，无法识别]"

        else:
            text = (incoming.text.content or "").strip() if incoming.text else ""
            if not text:
                logger.debug("Unhandled message type: %s", msgtype)

        return text, image_paths, audio_path
