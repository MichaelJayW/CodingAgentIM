"""DingTalk provider — implements BaseProvider for DingTalk platform."""

from __future__ import annotations

from typing import Any

from codingagentim import config
from codingagentim.core.models import CalendarEvent, Contact, Message, TodoItem
from codingagentim.core.provider import BaseProvider
from codingagentim.core.registry import register
from codingagentim.providers.dingtalk.api import DingTalkAPI
from codingagentim.providers.dingtalk.services.calendar import CalendarService
from codingagentim.providers.dingtalk.services.chat import ChatService
from codingagentim.providers.dingtalk.services.contact import ContactService
from codingagentim.providers.dingtalk.services.todo import TodoService


MAX_MSG_LENGTH = 4000


def _split_message(content: str, max_len: int = MAX_MSG_LENGTH) -> list[str]:
    if len(content) <= max_len:
        return [content]
    chunks = []
    while content:
        if len(content) <= max_len:
            chunks.append(content)
            break
        split_at = content.rfind("\n", 0, max_len)
        if split_at <= 0:
            split_at = max_len
        chunks.append(content[:split_at])
        content = content[split_at:].lstrip("\n")
    return chunks


@register("dingtalk")
class DingTalkProvider(BaseProvider):
    name = "dingtalk"

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        robot_code: str | None = None,
    ):
        self._app_key = app_key or config.get("dingtalk.app_key", "")
        self._app_secret = app_secret or config.get("dingtalk.app_secret", "")
        self._robot_code = robot_code or config.get("dingtalk.robot_code", "")
        self._api = DingTalkAPI(self._app_key, self._app_secret)
        self._chat = ChatService(self._api)
        self._contact = ContactService(self._api)
        self._calendar = CalendarService(self._api)
        self._todo = TodoService(self._api)

    async def send_message(
        self, target: str, content: str, msg_type: str = "text"
    ) -> Message:
        return await self._chat.send_to_group(
            conversation_id=target,
            content=content,
            msg_type=msg_type,
            robot_code=self._robot_code,
        )

    async def send_to_user(
        self, user_ids: list[str], content: str, msg_type: str = "text"
    ) -> Message:
        return await self._chat.send_to_user(
            user_ids=user_ids,
            content=content,
            msg_type=msg_type,
            robot_code=self._robot_code,
        )

    async def reply_message(
        self, original: Message, content: str, msg_type: str = "text"
    ) -> Message:
        if not original.conversation_id and not original.sender_id:
            raise ValueError("Cannot reply: no conversation_id or sender_id in original message")

        chunks = _split_message(content)
        last_result = None
        for chunk in chunks:
            if original.conversation_id:
                last_result = await self.send_message(original.conversation_id, chunk, msg_type)
            else:
                last_result = await self.send_to_user([original.sender_id], chunk, msg_type)
        return last_result

    async def search_contact(self, query: str, limit: int = 10) -> list[Contact]:
        return await self._contact.search(query, limit)

    async def list_calendar_events(self, date: str | None = None) -> list[CalendarEvent]:
        return await self._calendar.list_events(date)

    async def create_todo(self, title: str, **kwargs: Any) -> TodoItem:
        return await self._todo.create(title, **kwargs)
