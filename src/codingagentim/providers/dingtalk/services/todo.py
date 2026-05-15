"""DingTalk todo service."""

from __future__ import annotations

from typing import Any

from codingagentim.core.models import TodoItem
from codingagentim.providers.dingtalk.api import DingTalkAPI


class TodoService:
    def __init__(self, api: DingTalkAPI, union_id: str = "me"):
        self._api = api
        self._union_id = union_id

    async def create(self, title: str, **kwargs: Any) -> TodoItem:
        body: dict[str, Any] = {
            "subject": title,
            "description": kwargs.get("description", ""),
        }
        if "due_date" in kwargs:
            body["dueTime"] = int(kwargs["due_date"].timestamp() * 1000)

        result = await self._api.post(
            f"/v1.0/todo/users/{self._union_id}/tasks",
            json=body,
        )

        return TodoItem(
            id=result.get("id", ""),
            title=result.get("subject", title),
            description=result.get("description", ""),
            done=result.get("done", False),
            raw=result,
        )

    async def list_todos(self, done: bool | None = None) -> list[TodoItem]:
        result = await self._api.post(
            f"/v1.0/todo/users/{self._union_id}/tasks/query",
            json={"isDone": done} if done is not None else {},
        )

        items = []
        for task in result.get("todoCards", []):
            items.append(
                TodoItem(
                    id=task.get("taskId", ""),
                    title=task.get("subject", ""),
                    description=task.get("description", ""),
                    done=task.get("isDone", False),
                    raw=task,
                )
            )
        return items
