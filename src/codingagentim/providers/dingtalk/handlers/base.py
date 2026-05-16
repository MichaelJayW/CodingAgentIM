"""Shared utilities for DingTalk handlers."""

from __future__ import annotations

import json as _json
import logging
import shutil
import time
from collections import OrderedDict
from pathlib import Path

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

_SESSIONS_FILE = Path.home() / ".codingagentim" / "sessions.json"
_CONVERSATIONS_FILE = Path.home() / ".codingagentim" / "conversations.json"
_DEDUP_MAX = 200


class DeduplicatedHandler:
    """Mixin for message deduplication using msgId."""

    def __init__(self):
        self._seen_msgs: OrderedDict[str, float] = OrderedDict()

    def _is_duplicate(self, msg_id: str) -> bool:
        if not msg_id:
            return False
        if msg_id in self._seen_msgs:
            return True
        self._seen_msgs[msg_id] = time.monotonic()
        while len(self._seen_msgs) > _DEDUP_MAX:
            self._seen_msgs.popitem(last=False)
        return False


def find_claude_bin() -> str:
    found = shutil.which("claude")
    if found:
        return found
    home = Path.home()
    candidates = [
        Path("/opt/homebrew/bin/claude"),
        Path("/usr/local/bin/claude"),
        home / ".local" / "bin" / "claude",
        home / ".claude" / "local" / "claude",
    ]
    try:
        import subprocess
        npm_prefix = subprocess.run(
            ["npm", "config", "get", "prefix"],
            capture_output=True, text=True, timeout=5,
        )
        if npm_prefix.returncode == 0:
            candidates.append(Path(npm_prefix.stdout.strip()) / "bin" / "claude")
    except Exception:
        pass
    for p in candidates:
        if p.exists():
            return str(p)
    return "claude"


def load_sessions() -> dict[str, str]:
    if _SESSIONS_FILE.exists():
        try:
            return _json.loads(_SESSIONS_FILE.read_text())
        except (ValueError, OSError):
            return {}
    return {}


def save_sessions(sessions: dict[str, str]) -> None:
    _SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SESSIONS_FILE.write_text(_json.dumps(sessions, ensure_ascii=False, indent=2))


def load_conversations() -> dict[str, list[dict]]:
    if _CONVERSATIONS_FILE.exists():
        try:
            return _json.loads(_CONVERSATIONS_FILE.read_text())
        except (ValueError, OSError):
            return {}
    return {}


def save_conversations(conversations: dict[str, list[dict]]) -> None:
    _CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONVERSATIONS_FILE.write_text(_json.dumps(conversations, ensure_ascii=False))


_NOTIF_FILE = Path.home() / ".codingagentim" / "notifications.jsonl"
_NOTIF_MAX_SIZE = 512 * 1024  # 512 KB — rotate when exceeded
_NOTIF_KEEP_LINES = 200       # keep last N lines after rotation


def _rotate_notifications() -> None:
    """Rotate notifications.jsonl when it exceeds _NOTIF_MAX_SIZE."""
    try:
        if not _NOTIF_FILE.exists() or _NOTIF_FILE.stat().st_size <= _NOTIF_MAX_SIZE:
            return
        lines = _NOTIF_FILE.read_text().strip().splitlines()
        kept = lines[-_NOTIF_KEEP_LINES:]
        _NOTIF_FILE.write_text("\n".join(kept) + "\n")
        offset_file = _NOTIF_FILE.parent / ".poll_offset"
        if offset_file.exists():
            offset_file.write_text("0")
        mcp_offset = _NOTIF_FILE.parent / ".notif_mcp_offset"
        if mcp_offset.exists():
            mcp_offset.write_text("0")
    except OSError:
        pass


def push_notification(
    sender: str, text: str, ntype: str = "received", chat: str = "",
    result: str = "", sender_id: str = "",
) -> None:
    from datetime import datetime, timezone
    data = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sender": sender,
        "text": text[:100],
        "type": ntype,
        "chat": chat,
    }
    if sender_id:
        data["sender_id"] = sender_id
    if result:
        data["result"] = result[:200]
    entry = _json.dumps(data, ensure_ascii=False)
    try:
        _NOTIF_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_NOTIF_FILE, "a") as f:
            f.write(entry + "\n")
    except OSError:
        pass
    _rotate_notifications()
