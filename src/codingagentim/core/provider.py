"""Base provider interface for all IM platforms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from codingagentim.core.models import CalendarEvent, Contact, Message, TodoItem


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def send_message(
        self, target: str, content: str, msg_type: str = "text"
    ) -> Message:
        ...

    @abstractmethod
    async def reply_message(
        self, original: Message, content: str, msg_type: str = "text"
    ) -> Message:
        ...

    @abstractmethod
    async def search_contact(self, query: str, limit: int = 10) -> list[Contact]:
        ...

    @abstractmethod
    async def list_calendar_events(self, date: str | None = None) -> list[CalendarEvent]:
        ...

    @abstractmethod
    async def create_todo(self, title: str, **kwargs: Any) -> TodoItem:
        ...

    def get_schema(self) -> dict:
        return {
            "provider": self.name,
            "capabilities": [
                "send_message",
                "reply_message",
                "search_contact",
                "list_calendar_events",
                "create_todo",
            ],
        }
