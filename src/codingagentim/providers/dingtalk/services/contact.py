"""DingTalk contact search service."""

from __future__ import annotations

from codingagentim.core.models import Contact
from codingagentim.providers.dingtalk.api import DingTalkAPI


class ContactService:
    def __init__(self, api: DingTalkAPI):
        self._api = api

    async def search(self, query: str, limit: int = 10) -> list[Contact]:
        result = await self._api.post(
            "/v1.0/contact/users/search",
            json={"queryWord": query, "offset": 0, "size": min(limit, 50)},
        )
        contacts = []
        for user in result.get("list", []):
            contacts.append(
                Contact(
                    id=user.get("userId", ""),
                    name=user.get("userName", ""),
                    email=user.get("email", ""),
                    department=", ".join(str(d) for d in user.get("deptIds", [])),
                    avatar_url=user.get("avatar", ""),
                    raw=user,
                )
            )
        return contacts
