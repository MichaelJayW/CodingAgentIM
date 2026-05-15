"""Tests for DingTalk provider — auth, API client, services, and provider integration."""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import httpx
import pytest

from codingagentim.core.models import CalendarEvent, Contact, Message, TodoItem
from codingagentim.providers.dingtalk.api import DingTalkAPI
from codingagentim.providers.dingtalk.services.calendar import CalendarService
from codingagentim.providers.dingtalk.services.chat import ChatService
from codingagentim.providers.dingtalk.services.contact import ContactService
from codingagentim.providers.dingtalk.services.todo import TodoService


# --- Auth ---


@pytest.mark.asyncio
async def test_get_access_token_success():
    from codingagentim.providers.dingtalk import auth

    auth._token_cache.clear()

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"accessToken": "tok_123", "expireIn": 7200}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        token = await auth.get_access_token("key1", "secret1")
        assert token == "tok_123"


@pytest.mark.asyncio
async def test_get_access_token_cached():
    import time
    from codingagentim.providers.dingtalk import auth

    auth._token_cache["key2:secret2"] = ("cached_tok", time.time() + 3600)

    token = await auth.get_access_token("key2", "secret2")
    assert token == "cached_tok"

    auth._token_cache.pop("key2:secret2", None)


@pytest.mark.asyncio
async def test_get_access_token_missing_credentials():
    from codingagentim.providers.dingtalk import auth

    with patch("codingagentim.providers.dingtalk.auth.config") as mock_config:
        mock_config.get.return_value = ""
        with pytest.raises(ValueError, match="app_key and app_secret are required"):
            await auth.get_access_token("", "")


# --- DingTalkAPI ---


@pytest.fixture
def api():
    return DingTalkAPI("test_key", "test_secret")


@pytest.mark.asyncio
async def test_api_get(api):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "ok"}
    mock_resp.raise_for_status = MagicMock()
    mock_resp.status_code = 200

    with patch.object(api, "_get_token", return_value="fake_token"):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await api.get("/v1.0/test")
            assert result == {"result": "ok"}
            client_instance.request.assert_awaited_once()
            call_args = client_instance.request.call_args
            assert call_args[0][0] == "GET"
            assert "api.dingtalk.com" in call_args[0][1]


@pytest.mark.asyncio
async def test_api_post_old_api(api):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True}
    mock_resp.raise_for_status = MagicMock()
    mock_resp.status_code = 200

    with patch.object(api, "_get_token", return_value="fake_token"):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await api.post("/some/path", json={"a": 1}, use_old_api=True)
            assert result == {"success": True}
            call_args = client_instance.request.call_args
            assert "oapi.dingtalk.com" in call_args[0][1]


@pytest.mark.asyncio
async def test_api_204_returns_empty(api):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.status_code = 204

    with patch.object(api, "_get_token", return_value="fake_token"):
        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await api.request("DELETE", "/v1.0/resource/1")
            assert result == {}


# --- ChatService ---


@pytest.fixture
def mock_api():
    api = MagicMock(spec=DingTalkAPI)
    api.post = AsyncMock()
    api.get = AsyncMock()
    return api


@pytest.mark.asyncio
async def test_chat_send_to_group_text(mock_api):
    mock_api.post.return_value = {"processQueryKey": "msg_001"}
    chat = ChatService(mock_api)

    result = await chat.send_to_group("conv_1", "hello", robot_code="bot1")

    assert isinstance(result, Message)
    assert result.id == "msg_001"
    assert result.conversation_id == "conv_1"
    assert result.content == "hello"
    body = mock_api.post.call_args[1]["json"]
    assert body["robotCode"] == "bot1"
    assert body["msgKey"] == "sampleText"


@pytest.mark.asyncio
async def test_chat_send_to_group_markdown(mock_api):
    mock_api.post.return_value = {"processQueryKey": "msg_002"}
    chat = ChatService(mock_api)

    result = await chat.send_to_group("conv_1", "# Title\nbody", msg_type="markdown", robot_code="bot1")

    assert result.msg_type == "markdown"
    body = mock_api.post.call_args[1]["json"]
    assert body["msgKey"] == "sampleMarkdown"


@pytest.mark.asyncio
async def test_chat_send_to_user(mock_api):
    mock_api.post.return_value = {"processQueryKey": "msg_003"}
    chat = ChatService(mock_api)

    result = await chat.send_to_user(["u1", "u2"], "hi", robot_code="bot1")

    assert isinstance(result, Message)
    assert result.id == "msg_003"
    body = mock_api.post.call_args[1]["json"]
    assert body["userIds"] == ["u1", "u2"]


# --- ContactService ---


@pytest.mark.asyncio
async def test_contact_search(mock_api):
    mock_api.post.return_value = {
        "list": [
            {"userId": "u1", "userName": "Alice", "email": "a@x.com", "deptIds": [1, 2], "avatar": ""},
            {"userId": "u2", "userName": "Bob", "email": "b@x.com", "deptIds": [3], "avatar": "url"},
        ]
    }
    contact = ContactService(mock_api)

    results = await contact.search("test", limit=5)

    assert len(results) == 2
    assert all(isinstance(c, Contact) for c in results)
    assert results[0].name == "Alice"
    assert results[1].avatar_url == "url"
    body = mock_api.post.call_args[1]["json"]
    assert body["size"] == 5


@pytest.mark.asyncio
async def test_contact_search_empty(mock_api):
    mock_api.post.return_value = {"list": []}
    contact = ContactService(mock_api)

    results = await contact.search("nobody")
    assert results == []


# --- CalendarService ---


@pytest.mark.asyncio
async def test_calendar_list_events(mock_api):
    mock_api.post.return_value = {
        "events": [
            {
                "id": "evt_1",
                "summary": "Standup",
                "start": {"dateTime": "2026-05-15T09:00:00+08:00"},
                "end": {"dateTime": "2026-05-15T09:30:00+08:00"},
                "location": {"displayName": "Room A"},
                "attendees": [{"displayName": "Alice"}, {"displayName": "Bob"}],
            }
        ]
    }
    cal = CalendarService(mock_api, user_id="me")

    events = await cal.list_events("2026-05-15")

    assert len(events) == 1
    assert isinstance(events[0], CalendarEvent)
    assert events[0].title == "Standup"
    assert events[0].location == "Room A"
    assert events[0].attendees == ["Alice", "Bob"]


@pytest.mark.asyncio
async def test_calendar_list_events_default_date(mock_api):
    mock_api.post.return_value = {"events": []}
    cal = CalendarService(mock_api)

    events = await cal.list_events()
    assert events == []
    mock_api.post.assert_awaited_once()


# --- TodoService ---


@pytest.mark.asyncio
async def test_todo_create(mock_api):
    mock_api.post.return_value = {"id": "todo_1", "subject": "Fix bug", "description": "desc", "done": False}
    todo = TodoService(mock_api, union_id="me")

    result = await todo.create("Fix bug", description="desc")

    assert isinstance(result, TodoItem)
    assert result.id == "todo_1"
    assert result.title == "Fix bug"
    assert result.done is False


@pytest.mark.asyncio
async def test_todo_create_with_due_date(mock_api):
    mock_api.post.return_value = {"id": "todo_2", "subject": "Deploy", "done": False}
    todo = TodoService(mock_api)

    due = datetime(2026, 5, 20, 12, 0)
    await todo.create("Deploy", due_date=due)

    body = mock_api.post.call_args[1]["json"]
    assert "dueTime" in body


@pytest.mark.asyncio
async def test_todo_list(mock_api):
    mock_api.post.return_value = {
        "todoCards": [
            {"taskId": "t1", "subject": "Task A", "description": "", "isDone": False},
            {"taskId": "t2", "subject": "Task B", "description": "done", "isDone": True},
        ]
    }
    todo = TodoService(mock_api)

    items = await todo.list_todos()
    assert len(items) == 2
    assert items[1].done is True


# --- DingTalkProvider integration ---


@pytest.mark.asyncio
async def test_provider_send_message():
    with patch("codingagentim.providers.dingtalk.provider.config") as mock_config:
        mock_config.get.return_value = "test"
        with patch("codingagentim.providers.dingtalk.provider.DingTalkAPI") as MockAPI:
            mock_api_instance = MagicMock()
            mock_api_instance.post = AsyncMock(return_value={"processQueryKey": "msg_p1"})
            MockAPI.return_value = mock_api_instance

            from codingagentim.providers.dingtalk.provider import DingTalkProvider

            provider = DingTalkProvider(app_key="k", app_secret="s", robot_code="r")
            result = await provider.send_message("conv_1", "hello")

            assert isinstance(result, Message)
            assert result.id == "msg_p1"


@pytest.mark.asyncio
async def test_provider_reply_message_to_conversation():
    with patch("codingagentim.providers.dingtalk.provider.config") as mock_config:
        mock_config.get.return_value = "test"
        with patch("codingagentim.providers.dingtalk.provider.DingTalkAPI") as MockAPI:
            mock_api_instance = MagicMock()
            mock_api_instance.post = AsyncMock(return_value={"processQueryKey": "reply_1"})
            MockAPI.return_value = mock_api_instance

            from codingagentim.providers.dingtalk.provider import DingTalkProvider

            provider = DingTalkProvider(app_key="k", app_secret="s", robot_code="r")
            original = Message(conversation_id="conv_1", sender_id="u1", content="hi")
            result = await provider.reply_message(original, "reply text")
            assert isinstance(result, Message)


@pytest.mark.asyncio
async def test_provider_reply_message_to_user():
    with patch("codingagentim.providers.dingtalk.provider.config") as mock_config:
        mock_config.get.return_value = "test"
        with patch("codingagentim.providers.dingtalk.provider.DingTalkAPI") as MockAPI:
            mock_api_instance = MagicMock()
            mock_api_instance.post = AsyncMock(return_value={"processQueryKey": "reply_2"})
            MockAPI.return_value = mock_api_instance

            from codingagentim.providers.dingtalk.provider import DingTalkProvider

            provider = DingTalkProvider(app_key="k", app_secret="s", robot_code="r")
            original = Message(sender_id="u1", content="hi")
            result = await provider.reply_message(original, "reply text")
            assert isinstance(result, Message)


@pytest.mark.asyncio
async def test_provider_reply_message_no_target():
    with patch("codingagentim.providers.dingtalk.provider.config") as mock_config:
        mock_config.get.return_value = "test"
        with patch("codingagentim.providers.dingtalk.provider.DingTalkAPI") as MockAPI:
            MockAPI.return_value = MagicMock()

            from codingagentim.providers.dingtalk.provider import DingTalkProvider

            provider = DingTalkProvider(app_key="k", app_secret="s")
            original = Message(content="hi")
            with pytest.raises(ValueError, match="Cannot reply"):
                await provider.reply_message(original, "reply")


@pytest.mark.asyncio
async def test_provider_search_contact():
    with patch("codingagentim.providers.dingtalk.provider.config") as mock_config:
        mock_config.get.return_value = "test"
        with patch("codingagentim.providers.dingtalk.provider.DingTalkAPI") as MockAPI:
            mock_api_instance = MagicMock()
            mock_api_instance.post = AsyncMock(return_value={
                "list": [{"userId": "u1", "userName": "Alice", "email": "", "deptIds": [], "avatar": ""}]
            })
            MockAPI.return_value = mock_api_instance

            from codingagentim.providers.dingtalk.provider import DingTalkProvider

            provider = DingTalkProvider(app_key="k", app_secret="s")
            results = await provider.search_contact("Alice")
            assert len(results) == 1
            assert results[0].name == "Alice"


@pytest.mark.asyncio
async def test_provider_get_schema():
    with patch("codingagentim.providers.dingtalk.provider.config") as mock_config:
        mock_config.get.return_value = "test"
        with patch("codingagentim.providers.dingtalk.provider.DingTalkAPI"):
            from codingagentim.providers.dingtalk.provider import DingTalkProvider

            provider = DingTalkProvider(app_key="k", app_secret="s")
            schema = provider.get_schema()
            assert schema["provider"] == "dingtalk"
            assert "send_message" in schema["capabilities"]
