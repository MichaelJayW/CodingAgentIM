"""Tests for the file-based message queue (inbox/outbox)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from codingagentim.core.message_queue import (
    INBOX_FILE,
    OUTBOX_FILE,
    _load,
    _save,
    complete_inbox,
    complete_outbox,
    pending_count,
    pop_inbox,
    pop_outbox,
    push_inbox,
    push_outbox,
)


@pytest.fixture(autouse=True)
def tmp_queue_files(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox.json"
    outbox = tmp_path / "outbox.json"
    monkeypatch.setattr("codingagentim.core.message_queue.INBOX_FILE", inbox)
    monkeypatch.setattr("codingagentim.core.message_queue.OUTBOX_FILE", outbox)
    monkeypatch.setattr("codingagentim.core.message_queue.ensure_config_dir", lambda: None)
    return inbox, outbox


class TestLoad:
    def test_load_missing_file(self, tmp_path):
        assert _load(tmp_path / "nope.json") == []

    def test_load_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not json!")
        assert _load(f) == []

    def test_load_valid(self, tmp_path):
        f = tmp_path / "ok.json"
        f.write_text('[{"id": "1"}]')
        assert _load(f) == [{"id": "1"}]


class TestInbox:
    def test_push_inbox_creates_message(self):
        msg = push_inbox("hello", sender="Alice", sender_id="u1", conversation_id="c1")
        assert msg["text"] == "hello"
        assert msg["sender"] == "Alice"
        assert msg["sender_id"] == "u1"
        assert msg["status"] == "pending"
        assert len(msg["id"]) == 8

    def test_push_inbox_appends(self):
        push_inbox("first")
        push_inbox("second")
        assert pending_count() == 2

    def test_pop_inbox_returns_first_pending(self):
        push_inbox("msg1")
        push_inbox("msg2")
        popped = pop_inbox()
        assert popped["text"] == "msg1"
        assert popped["status"] == "processing"

    def test_pop_inbox_skips_processing(self):
        push_inbox("msg1")
        push_inbox("msg2")
        pop_inbox()  # msg1 -> processing
        popped = pop_inbox()
        assert popped["text"] == "msg2"

    def test_pop_inbox_empty(self):
        assert pop_inbox() is None

    def test_complete_inbox(self):
        msg = push_inbox("task")
        complete_inbox(msg["id"])
        assert pop_inbox() is None
        assert pending_count() == 0

    def test_pending_count(self):
        push_inbox("a")
        push_inbox("b")
        push_inbox("c")
        pop_inbox()  # a -> processing
        assert pending_count() == 2


class TestOutbox:
    def test_push_outbox(self):
        msg = push_outbox("inbox1", "result text", conversation_id="c1", sender_id="u1")
        assert msg["inbox_id"] == "inbox1"
        assert msg["result"] == "result text"
        assert msg["status"] == "pending"

    def test_pop_outbox(self):
        push_outbox("i1", "r1")
        popped = pop_outbox()
        assert popped["result"] == "r1"
        assert popped["status"] == "sending"

    def test_pop_outbox_empty(self):
        assert pop_outbox() is None

    def test_complete_outbox(self):
        msg = push_outbox("i1", "r1")
        complete_outbox(msg["id"])
        assert pop_outbox() is None
