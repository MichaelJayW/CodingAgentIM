"""DingTalk authentication — App Key/Secret based access token management."""

from __future__ import annotations

import asyncio
import time

import httpx

from codingagentim import config

DINGTALK_TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/accessToken"

_token_cache: dict[str, tuple[str, float]] = {}
_token_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _token_lock
    if _token_lock is None:
        _token_lock = asyncio.Lock()
    return _token_lock


async def get_access_token(app_key: str | None = None, app_secret: str | None = None) -> str:
    app_key = app_key or config.get("dingtalk.app_key", "")
    app_secret = app_secret or config.get("dingtalk.app_secret", "")

    if not app_key or not app_secret:
        raise ValueError(
            "DingTalk app_key and app_secret are required. "
            "Run `codingagentim auth login dingtalk` or set them in ~/.codingagentim/config.toml"
        )

    cache_key = f"{app_key}:{app_secret}"
    if cache_key in _token_cache:
        token, expires_at = _token_cache[cache_key]
        if time.time() < expires_at - 60:
            return token

    async with _get_lock():
        if cache_key in _token_cache:
            token, expires_at = _token_cache[cache_key]
            if time.time() < expires_at - 60:
                return token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                DINGTALK_TOKEN_URL,
                json={"appKey": app_key, "appSecret": app_secret},
            )
            resp.raise_for_status()
            data = resp.json()

        token = data["accessToken"]
        expires_in = data.get("expireIn", 7200)
        _token_cache[cache_key] = (token, time.time() + expires_in)
        return token


def invalidate_token(app_key: str | None = None, app_secret: str | None = None) -> None:
    app_key = app_key or config.get("dingtalk.app_key", "")
    app_secret = app_secret or config.get("dingtalk.app_secret", "")
    cache_key = f"{app_key}:{app_secret}"
    _token_cache.pop(cache_key, None)
