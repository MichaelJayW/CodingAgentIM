"""Tests for task store (persistent agent task tracking)."""

import pytest

from codingagentim.core.models import TaskRecord, TaskStatus
from codingagentim.core.task_store import (
    add_task,
    clean_tasks,
    get_task,
    list_tasks,
    update_task,
)


@pytest.fixture(autouse=True)
def tmp_task_file(tmp_path, monkeypatch):
    tasks_file = tmp_path / "tasks.json"
    monkeypatch.setattr("codingagentim.core.task_store.TASKS_FILE", tasks_file)
    monkeypatch.setattr("codingagentim.core.task_store.ensure_config_dir", lambda: None)
    return tasks_file


class TestAddTask:
    def test_creates_running_task(self):
        task = add_task("write tests", agent="claude", sender="Alice")
        assert isinstance(task, TaskRecord)
        assert task.prompt == "write tests"
        assert task.agent == "claude"
        assert task.sender == "Alice"
        assert task.status == TaskStatus.RUNNING
        assert task.start_time is not None
        assert len(task.id) == 8

    def test_persists_to_file(self, tmp_task_file):
        add_task("hello")
        assert tmp_task_file.exists()
        import json
        data = json.loads(tmp_task_file.read_text())
        assert len(data) == 1


class TestGetTask:
    def test_get_existing(self):
        task = add_task("test")
        found = get_task(task.id)
        assert found is not None
        assert found.id == task.id
        assert found.prompt == "test"

    def test_get_nonexistent(self):
        assert get_task("nope") is None


class TestUpdateTask:
    def test_update_status(self):
        task = add_task("run")
        updated = update_task(task.id, status="completed", summary="done")
        assert updated.status == TaskStatus.COMPLETED
        assert updated.summary == "done"
        assert updated.end_time is not None

    def test_update_failed_sets_end_time(self):
        task = add_task("run")
        updated = update_task(task.id, status="failed")
        assert updated.end_time is not None

    def test_update_nonexistent(self):
        assert update_task("nope", status="completed") is None


class TestListTasks:
    def test_list_all(self):
        add_task("a")
        add_task("b")
        add_task("c")
        assert len(list_tasks()) == 3

    def test_list_with_status_filter(self):
        t1 = add_task("a")
        add_task("b")
        update_task(t1.id, status="completed")
        running = list_tasks(status="running")
        assert len(running) == 1
        assert running[0].prompt == "b"

    def test_list_with_limit(self):
        for i in range(10):
            add_task(f"task_{i}")
        assert len(list_tasks(limit=3)) == 3

    def test_list_empty(self):
        assert list_tasks() == []


class TestCleanTasks:
    def test_clean_keeps_running(self):
        t1 = add_task("running")
        t2 = add_task("done")
        update_task(t2.id, status="completed")
        removed = clean_tasks(keep_running=True)
        assert removed == 1
        assert len(list_tasks()) == 1
        assert list_tasks()[0].id == t1.id

    def test_clean_all(self):
        add_task("a")
        add_task("b")
        removed = clean_tasks(keep_running=False)
        assert removed == 2
        assert list_tasks() == []
