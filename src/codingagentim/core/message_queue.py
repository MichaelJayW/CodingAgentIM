"""File-based message queue — inbox/outbox for bridge mode."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from codingagentim.config import ensure_config_dir

INBOX_FILE = Path.home() / ".codingagentim" / "inbox.json"
OUTBOX_FILE = Path.home() / ".codingagentim" / "outbox.json"


def _load(path: Path) -> list[dict]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save(path: Path, data: list[dict]) -> None:
    ensure_config_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def push_inbox(
    text: str,
    sender: str = "",
    sender_id: str = "",
    conversation_id: str = "",
    is_group: bool = True,
) -> dict:
    items = _load(INBOX_FILE)
    msg = {
        "id": uuid.uuid4().hex[:8],
        "text": text,
        "sender": sender,
        "sender_id": sender_id,
        "conversation_id": conversation_id,
        "is_group": is_group,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
    }
    items.append(msg)
    _save(INBOX_FILE, items)
    return msg


def pop_inbox() -> dict | None:
    items = _load(INBOX_FILE)
    for item in items:
        if item["status"] == "pending":
            item["status"] = "processing"
            _save(INBOX_FILE, items)
            return item
    return None


def complete_inbox(msg_id: str) -> None:
    items = _load(INBOX_FILE)
    for item in items:
        if item["id"] == msg_id:
            item["status"] = "done"
    _save(INBOX_FILE, items)


def push_outbox(
    inbox_id: str,
    result: str,
    conversation_id: str = "",
    is_group: bool = True,
    sender_id: str = "",
) -> dict:
    items = _load(OUTBOX_FILE)
    msg = {
        "id": uuid.uuid4().hex[:8],
        "inbox_id": inbox_id,
        "result": result,
        "conversation_id": conversation_id,
        "is_group": is_group,
        "sender_id": sender_id,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
    }
    items.append(msg)
    _save(OUTBOX_FILE, items)
    return msg


def pop_outbox() -> dict | None:
    items = _load(OUTBOX_FILE)
    for item in items:
        if item["status"] == "pending":
            item["status"] = "sending"
            _save(OUTBOX_FILE, items)
            return item
    return None


def complete_outbox(msg_id: str) -> None:
    items = _load(OUTBOX_FILE)
    for item in items:
        if item["id"] == msg_id:
            item["status"] = "sent"
    _save(OUTBOX_FILE, items)


def pending_count() -> int:
    return sum(1 for item in _load(INBOX_FILE) if item["status"] == "pending")
