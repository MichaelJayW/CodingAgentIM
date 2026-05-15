"""Tests for core data models."""

from codingagentim.core.models import Contact, Message, MessageType, TodoItem


def test_message_defaults():
    msg = Message()
    assert msg.msg_type == MessageType.TEXT
    assert msg.content == ""


def test_message_with_data():
    msg = Message(
        id="123",
        sender_id="user1",
        content="hello",
        conversation_id="conv1",
    )
    assert msg.id == "123"
    assert msg.content == "hello"


def test_contact_model():
    c = Contact(id="u1", name="Test User", email="test@example.com")
    data = c.model_dump()
    assert data["name"] == "Test User"


def test_todo_model():
    t = TodoItem(title="Review PR", done=False)
    assert not t.done
    assert t.title == "Review PR"
