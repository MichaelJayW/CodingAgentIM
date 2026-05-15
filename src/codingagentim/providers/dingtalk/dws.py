"""DingTalk DWS (DingTalk WorkStation) CLI bridge.

Provides a thin wrapper around the `dws` CLI tool for operations
that are easier or only available through the local DWS client,
such as file uploads, approval workflows, and local identity.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass


@dataclass
class DWSResult:
    success: bool
    data: dict
    raw_output: str


class DWSBridge:
    def __init__(self, dws_path: str | None = None):
        self._dws = dws_path or shutil.which("dws") or "dws"

    def available(self) -> bool:
        return shutil.which(self._dws) is not None

    async def _run(self, *args: str) -> DWSResult:
        try:
            proc = await asyncio.create_subprocess_exec(
                self._dws, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            raw = stdout.decode().strip()

            if proc.returncode != 0:
                return DWSResult(
                    success=False,
                    data={"error": stderr.decode().strip() or raw},
                    raw_output=raw,
                )

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"output": raw}

            return DWSResult(success=True, data=data, raw_output=raw)
        except FileNotFoundError:
            return DWSResult(
                success=False,
                data={"error": f"dws CLI not found at '{self._dws}'"},
                raw_output="",
            )

    async def whoami(self) -> DWSResult:
        return await self._run("whoami", "--format", "json")

    async def upload_file(self, file_path: str, space_id: str = "") -> DWSResult:
        args = ["file", "upload", file_path]
        if space_id:
            args.extend(["--space-id", space_id])
        args.extend(["--format", "json"])
        return await self._run(*args)

    async def send_message(self, conversation_id: str, content: str) -> DWSResult:
        return await self._run(
            "message", "send",
            "--conversation-id", conversation_id,
            "--content", content,
            "--format", "json",
        )

    async def list_spaces(self) -> DWSResult:
        return await self._run("space", "list", "--format", "json")
