"""DingTalk chat / messaging service."""

from __future__ import annotations

import json as _json

from codingagentim.core.models import Message
from codingagentim.providers.dingtalk.api import DingTalkAPI


class ChatService:
    def __init__(self, api: DingTalkAPI):
        self._api = api

    async def send_to_group(
        self,
        conversation_id: str,
        content: str,
        msg_type: str = "text",
        robot_code: str = "",
    ) -> Message:
        if msg_type == "markdown":
            msg_param = {"title": content[:20], "text": content}
        else:
            msg_param = {"content": content}

        body = {
            "robotCode": robot_code,
            "openConversationId": conversation_id,
            "msgKey": "sampleMarkdown" if msg_type == "markdown" else "sampleText",
            "msgParam": _json.dumps(msg_param, ensure_ascii=False),
        }

        result = await self._api.post(
            "/v1.0/robot/groupMessages/send",
            json=body,
        )

        return Message(
            id=result.get("processQueryKey", ""),
            conversation_id=conversation_id,
            content=content,
            msg_type=msg_type,
            raw=result,
        )

    async def send_to_user(
        self,
        user_ids: list[str],
        content: str,
        msg_type: str = "text",
        robot_code: str = "",
    ) -> Message:
        if msg_type == "markdown":
            msg_param = {"title": content[:20], "text": content}
        else:
            msg_param = {"content": content}

        body = {
            "robotCode": robot_code,
            "userIds": user_ids,
            "msgKey": "sampleMarkdown" if msg_type == "markdown" else "sampleText",
            "msgParam": _json.dumps(msg_param, ensure_ascii=False),
        }

        result = await self._api.post(
            "/v1.0/robot/oToMessages/batchSend",
            json=body,
        )

        return Message(
            id=result.get("processQueryKey", ""),
            content=content,
            msg_type=msg_type,
            raw=result,
        )

    async def send_image_to_user(
        self,
        user_ids: list[str],
        image_data: bytes,
        filename: str = "image.png",
        robot_code: str = "",
    ) -> Message:
        media_id = await self._api.upload_media(image_data, filename, "image")
        body = {
            "robotCode": robot_code,
            "userIds": user_ids,
            "msgKey": "sampleImageMsg",
            "msgParam": _json.dumps({"photoURL": media_id}),
        }
        result = await self._api.post("/v1.0/robot/oToMessages/batchSend", json=body)
        return Message(id=result.get("processQueryKey", ""), content=f"[image:{media_id}]", raw=result)

    async def send_file_to_user(
        self,
        user_ids: list[str],
        file_data: bytes,
        filename: str = "file",
        robot_code: str = "",
    ) -> Message:
        media_id = await self._api.upload_media(file_data, filename, "file")
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        body = {
            "robotCode": robot_code,
            "userIds": user_ids,
            "msgKey": "sampleFile",
            "msgParam": _json.dumps({"mediaId": media_id, "fileName": filename, "fileType": ext}),
        }
        result = await self._api.post("/v1.0/robot/oToMessages/batchSend", json=body)
        return Message(id=result.get("processQueryKey", ""), content=f"[file:{filename}]", raw=result)
