"""DingTalk OpenAPI low-level client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from codingagentim.providers.dingtalk.auth import get_access_token, invalidate_token

BASE_URL = "https://api.dingtalk.com"
OLD_BASE_URL = "https://oapi.dingtalk.com"

logger = logging.getLogger(__name__)

MAX_MEDIA_BYTES = 25 * 1024 * 1024  # 25 MiB


class DingTalkAPI:
    def __init__(self, app_key: str | None = None, app_secret: str | None = None):
        self._app_key = app_key
        self._app_secret = app_secret
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

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

        if resp.status_code == 401:
            invalidate_token(self._app_key, self._app_secret)
            token = await self._get_token()
            headers["x-acs-dingtalk-access-token"] = token
            resp = await client.request(method, url, headers=headers, json=json, params=params)

        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    async def get(self, path: str, **kwargs) -> dict[str, Any]:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> dict[str, Any]:
        return await self.request("POST", path, **kwargs)

    async def download_media(self, download_code: str, robot_code: str) -> tuple[bytes, str]:
        """Download a media file (image/audio/file) via DingTalk messageFiles/download API.

        Returns (data_bytes, content_type).
        """
        token = await self._get_token()
        client = self._get_client()

        resp = await client.post(
            f"{BASE_URL}/v1.0/robot/messageFiles/download",
            headers={
                "x-acs-dingtalk-access-token": token,
                "Content-Type": "application/json",
            },
            json={"downloadCode": download_code, "robotCode": robot_code},
        )
        resp.raise_for_status()
        download_url = resp.json().get("downloadUrl", "")
        if not download_url:
            raise ValueError("Empty downloadUrl in response")

        media_resp = await client.get(download_url)
        media_resp.raise_for_status()
        data = media_resp.content
        if len(data) > MAX_MEDIA_BYTES:
            raise ValueError(f"Media too large: {len(data)} bytes (limit {MAX_MEDIA_BYTES})")
        content_type = media_resp.headers.get("content-type", "application/octet-stream")
        logger.debug("Media downloaded: %d bytes, type=%s", len(data), content_type)
        return data, content_type

    async def upload_media(self, data: bytes, filename: str, media_type: str = "image") -> str:
        """Upload media to DingTalk and return media_id.

        media_type: "image", "voice", or "file".
        """
        token = await self._get_token()
        client = self._get_client()

        url = f"{OLD_BASE_URL}/media/upload?access_token={token}&type={media_type}"
        resp = await client.post(
            url,
            files={"media": (filename, data)},
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("errcode", 0) != 0:
            raise ValueError(f"Upload failed: {result.get('errmsg', 'unknown error')}")
        media_id = result.get("media_id", "")
        if not media_id:
            raise ValueError(f"Empty media_id in upload response: {result}")
        logger.debug("Media uploaded: media_id=%s, type=%s, size=%d", media_id, media_type, len(data))
        return media_id
