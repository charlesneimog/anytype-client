from types import SimpleNamespace

import pytest

from anytype import Discussion, Object, Space, apiEndpoints


class FakeResponse:
    status_code = 200
    content = b"json"

    def json(self):
        return {"data": []}


@pytest.fixture
def request_spy(monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr("anytype.api.requests.request", request)
    return calls


@pytest.fixture
def api():
    return apiEndpoints({"Authorization": "Bearer api-key"})


def test_create_chat_contract(api, request_spy):
    api.createChat("space-1", {"name": "Team"}, dry_run=True, idempotency_key="chat-key")

    call = request_spy[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith("/v2/spaces/space-1/chats")
    assert call["params"] == {"dry_run": "true"}
    assert call["json"] == {"name": "Team"}
    assert call["headers"]["Idempotency-Key"] == "chat-key"


def test_get_chat_messages_contract(api, request_spy):
    api.getChatMessages(
        "space-1",
        "chat-1",
        after="after-order",
        before="before-order",
        limit=20,
        reactions="full",
    )

    call = request_spy[-1]
    assert call["method"] == "GET"
    assert call["url"].endswith("/v2/spaces/space-1/chats/chat-1/messages")
    assert call["params"] == {
        "after": "after-order",
        "before": "before-order",
        "limit": 20,
        "reactions": "full",
    }


def test_add_chat_message_contract(api, request_spy):
    payload = {"text": "Hello", "attachments": ["file-1"], "reply_to": "message-0"}
    api.addChatMessage(
        "space-1", "chat-1", payload, dry_run=True, idempotency_key="message-key"
    )

    call = request_spy[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith("/v2/spaces/space-1/chats/chat-1/messages")
    assert call["params"] == {"dry_run": "true"}
    assert call["json"] == payload
    assert call["headers"]["Idempotency-Key"] == "message-key"


def test_toggle_chat_reaction_contract(api, request_spy):
    api.toggleChatReaction(
        "space-1",
        "chat-1",
        "message-1",
        {"emoji": "👍"},
        dry_run=True,
        idempotency_key="reaction-key",
    )

    call = request_spy[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith(
        "/v2/spaces/space-1/chats/chat-1/messages/message-1/reactions"
    )
    assert call["params"] == {"dry_run": "true"}
    assert call["json"] == {"emoji": "👍"}
    assert call["headers"]["Idempotency-Key"] == "reaction-key"


def test_create_discussion_contract(api, request_spy):
    api.createDiscussion(
        "space-1", "object-1", dry_run=True, idempotency_key="discussion-key"
    )

    call = request_spy[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith("/v2/spaces/space-1/objects/object-1/discussion")
    assert call["params"] == {"dry_run": "true"}
    assert call["json"] is None
    assert call["headers"]["Idempotency-Key"] == "discussion-key"


def test_space_chat_helpers_build_the_documented_payloads():
    calls = []
    backend = SimpleNamespace(
        createChat=lambda *args, **kwargs: calls.append(("create_chat", args, kwargs))
        or {"id": "chat-1"},
        addChatMessage=lambda *args, **kwargs: calls.append(("add_message", args, kwargs))
        or {"id": "message-1"},
        toggleChatReaction=lambda *args, **kwargs: calls.append(("reaction", args, kwargs))
        or {"added": True},
        createDiscussion=lambda *args, **kwargs: calls.append(("discussion", args, kwargs))
        or {"id": "discussion-1", "created": True},
    )
    space = Space._from_api(backend, {"id": "space-1", "name": "Work"})

    assert space.create_chat("Team")["id"] == "chat-1"
    assert space.add_chat_message(
        "chat-1", "Hello", attachments=["file-1"], reply_to="message-0"
    )["id"] == "message-1"
    assert space.toggle_chat_reaction("chat-1", "message-1", "👍")["added"] is True
    discussion = space.create_discussion("object-1")
    assert isinstance(discussion, Discussion)
    assert discussion.id == "discussion-1"
    assert discussion.object_id == "object-1"
    assert discussion.space_id == "space-1"
    assert discussion.created is True

    assert calls[0][1] == ("space-1", {"name": "Team"})
    assert calls[1][1] == (
        "space-1",
        "chat-1",
        {"text": "Hello", "attachments": ["file-1"], "reply_to": "message-0"},
    )
    assert calls[2][1] == ("space-1", "chat-1", "message-1", {"emoji": "👍"})
    assert calls[3][1] == ("space-1", "object-1")


def test_space_get_discussion_returns_bound_discussion():
    backend = SimpleNamespace(
        getObject=lambda *args: {
            "object": {"id": "object-1", "discussion": "discussion-1"}
        },
    )
    space = Space._from_api(backend, {"id": "space-1", "name": "Work"})

    discussion = space.get_discussion("object-1")

    assert isinstance(discussion, Discussion)
    assert discussion.id == "discussion-1"
    assert discussion.object_id == "object-1"
    assert discussion.space_id == "space-1"


def test_discussion_exposes_message_and_reaction_operations():
    calls = []
    backend = SimpleNamespace(
        getChatMessages=lambda *args, **kwargs: calls.append(("messages", args, kwargs))
        or {"messages": []},
        addChatMessage=lambda *args, **kwargs: calls.append(("add", args, kwargs))
        or {"id": "message-1"},
        toggleChatReaction=lambda *args, **kwargs: calls.append(("reaction", args, kwargs))
        or {"added": True},
    )
    discussion = Discussion._from_api(
        backend,
        {"id": "discussion-1", "space_id": "space-1", "object_id": "object-1"},
    )

    assert discussion.get_messages(limit=10, reactions="full") == {"messages": []}
    assert discussion.add_message(
        "Hello", attachments=["file-1"], reply_to="message-0"
    ) == {"id": "message-1"}
    assert discussion.toggle_reaction("message-1", "👍") == {"added": True}

    assert calls[0] == (
        "messages",
        ("space-1", "discussion-1"),
        {"after": None, "before": None, "limit": 10, "reactions": "full"},
    )
    assert calls[1][0:2] == (
        "add",
        (
            "space-1",
            "discussion-1",
            {"text": "Hello", "attachments": ["file-1"], "reply_to": "message-0"},
        ),
    )
    assert calls[2][0:2] == (
        "reaction",
        ("space-1", "discussion-1", "message-1", {"emoji": "👍"}),
    )


def test_space_get_discussion_returns_none_when_object_has_no_discussion():
    backend = SimpleNamespace(
        getObject=lambda *args: {"object": {"id": "object-1"}},
    )
    space = Space._from_api(backend, {"id": "space-1", "name": "Work"})

    assert space.get_discussion("object-1") is None


@pytest.mark.parametrize("value", [None, "", Object()])
def test_space_chat_helpers_reject_missing_ids(value):
    space = Space._from_api(SimpleNamespace(), {"id": "space-1", "name": "Work"})

    with pytest.raises(ValueError, match="non-empty"):
        space.get_chat_messages(value)
