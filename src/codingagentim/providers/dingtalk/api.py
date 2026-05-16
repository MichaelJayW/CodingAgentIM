"""DingTalk OpenAPI low-level client."""

from __future__ import annotations

from typing import Any

import httpx

from codingagentim.providers.dingtalk.auth import get_access_token

BASE_URL = "https://api.dingtalk.com"
OLD_BASE_URL = "https://oapi.dingtalk.com"


class DingTalkAPI:
    def __init__(self, app_key: str | None = None, app_secret: str | None = None):
        self._app_key = app_key
        self._app_secret = app_secret
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _get_token(self) -> str:
        return await get_access_token(self._app_key, self._app_secret)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        use_old_api: bool = False,
    ) -> dict[str, Any]:
        token = await self._get_token()
        base = OLD_BASE_URL if use_old_api else BASE_URL
        url = f"{base}{path}"

        headers = {
            "x-acs-dingtalk-access-token": token,
            "Content-Type": "application/json",
        }

        client = self._get_client()
        resp = await client.request(
            method,
            url,
            headers=headers,
            json=json,
            params=params,
        )
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    async def get(self, path: str, **kwargs) -> dict[str, Any]:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> dict[str, Any]:
        return await self.request("POST", path, **kwargs)
