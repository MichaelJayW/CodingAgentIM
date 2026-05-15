"""Persistent task store — tracks dispatched agent tasks in ~/.codingagentim/tasks.json."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from codingagentim.config import ensure_config_dir
from codingagentim.core.models import TaskRecord, TaskStatus

TASKS_FILE = Path.home() / ".codingagentim" / "tasks.json"


def _load_all() -> list[dict]:
    if TASKS_FILE.exists():
        try:
            return json.loads(TASKS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_all(tasks: list[dict]) -> None:
    ensure_config_dir()
    TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2, default=str))


def add_task(prompt: str, agent: str = "", sender: str = "", conversation_id: str = "") -> TaskRecord:
    tasks = _load_all()
    task = TaskRecord(
        id=uuid.uuid4().hex[:8],
        prompt=prompt,
        status=TaskStatus.RUNNING,
        agent=agent,
        start_time=datetime.now(),
        sender=sender,
        conversation_id=conversation_id,
    )
    tasks.append(task.model_dump(mode="json"))
    _save_all(tasks)
    return task


def update_task(task_id: str, **kwargs) -> TaskRecord | None:
    tasks = _load_all()
    for i, t in enumerate(tasks):
        if t["id"] == task_id:
            t.update({k: v for k, v in kwargs.items() if v is not None})
            if "end_time" not in kwargs and kwargs.get("status") in ("completed", "failed"):
                t["end_time"] = datetime.now().isoformat()
            tasks[i] = t
            _save_all(tasks)
            return TaskRecord(**t)
    return None


def get_task(task_id: str) -> TaskRecord | None:
    for t in _load_all():
        if t["id"] == task_id:
            return TaskRecord(**t)
    return None


def list_tasks(status: str | None = None, limit: int = 50) -> list[TaskRecord]:
    tasks = _load_all()
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    tasks = tasks[-limit:]
    return [TaskRecord(**t) for t in tasks]


def clean_tasks(keep_running: bool = True) -> int:
    tasks = _load_all()
    before = len(tasks)
    if keep_running:
        tasks = [t for t in tasks if t.get("status") == "running"]
    else:
        tasks = []
    _save_all(tasks)
    return before - len(tasks)
