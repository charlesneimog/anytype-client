from types import SimpleNamespace

import pytest

from anytype import Anytype, Object, Space, apiEndpoints
from anytype.api import MIN_API_VERSION, ResponseHasError


class FakeResponse:
    def __init__(self, payload=None, status_code=200, version=MIN_API_VERSION):
        self._payload = payload
        self.status_code = status_code
        self.headers = {} if version is None else {"Anytype-Version": version}
        self.content = b"" if payload is None else b"json"

    def json(self):
        return self._payload


@pytest.fixture
def request_spy(monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        call = {"method": method, "url": url, **kwargs}
        files = kwargs.get("files")
        if files:
            uploaded = files["file"]
            if isinstance(uploaded, tuple):
                call["uploaded_name"] = uploaded[0]
                call["uploaded_bytes"] = uploaded[1].read()
        calls.append(call)
        return FakeResponse({"data": []})

    monkeypatch.setattr("anytype.api.requests.request", request)
    return calls


@pytest.fixture
def api():
    return apiEndpoints(
        {
            "Authorization": "Bearer api-key",
            "Content-Type": "application/json",
        }
    )


def test_uses_2025_11_08_api_version(api):
    assert api.headers["Anytype-Version"] == "2025-11-08"


def test_create_api_key_contract(api, request_spy):
    api.getToken("challenge-123", "1234")

    assert request_spy[-1]["method"] == "POST"
    assert request_spy[-1]["url"].endswith("/v1/auth/api_keys")
    assert request_spy[-1]["json"] == {
        "challenge_id": "challenge-123",
        "code": "1234",
    }


def test_global_search_contract_with_all_optional_fields(api, request_spy):
    filters = {
        "operator": "and",
        "conditions": [{"property_key": "done", "condition": "eq", "checkbox": False}],
    }
    sort = {"direction": "asc", "property_key": "name"}

    api.globalSearch(
        "roadmap",
        offset=20,
        limit=50,
        types=["page", "task"],
        sort=sort,
        filters=filters,
    )

    assert request_spy[-1]["method"] == "POST"
    assert request_spy[-1]["url"].endswith("/v1/search")
    assert request_spy[-1]["params"] == {"offset": 20, "limit": 50}
    assert request_spy[-1]["json"] == {
        "query": "roadmap",
        "types": ["page", "task"],
        "sort": sort,
        "filters": filters,
    }


@pytest.mark.parametrize(
    ("case", "invoke", "path", "filters"),
    [
        (
            "spaces",
            lambda client, values: client.getSpaces(2, 25, values),
            "/v1/spaces",
            {"name[contains]": "project"},
        ),
        (
            "chats",
            lambda client, values: client.getChats("space-1", 2, 25, values),
            "/v1/spaces/space-1/chats",
            {"name[contains]": "team"},
        ),
        (
            "members",
            lambda client, values: client.getMembers("space-1", 2, 25, values),
            "/v1/spaces/space-1/members",
            {"name[ne]": "john"},
        ),
        (
            "objects",
            lambda client, values: client.getObjects("space-1", 2, 25, values),
            "/v1/spaces/space-1/objects",
            {"type": "page", "created_date[gte]": "2024-01-01"},
        ),
        (
            "properties",
            lambda client, values: client.getProperties("space-1", 2, 25, values),
            "/v1/spaces/space-1/properties",
            {"name[contains]": "date"},
        ),
        (
            "tags",
            lambda client, values: client.getTags("space-1", "property-1", 2, 25, values),
            "/v1/spaces/space-1/properties/property-1/tags",
            {"name[contains]": "urgent"},
        ),
        (
            "types",
            lambda client, values: client.getTypes("space-1", 2, 25, values),
            "/v1/spaces/space-1/types",
            {"name[contains]": "task"},
        ),
        (
            "templates",
            lambda client, values: client.getTemplates("space-1", "type-1", 2, 25, values),
            "/v1/spaces/space-1/types/type-1/templates",
            {"name[contains]": "invoice"},
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_list_endpoint_contracts(api, request_spy, case, invoke, path, filters):
    invoke(api, filters)

    assert request_spy[-1]["method"] == "GET", case
    assert request_spy[-1]["url"].endswith(path), case
    assert request_spy[-1]["params"] == {**filters, "offset": 2, "limit": 25}, case


def test_upload_file_contract_builds_multipart_without_json_content_type(
    api, request_spy, tmp_path
):
    path = tmp_path / "photo.png"
    path.write_bytes(b"png-data")

    api.uploadFile("space-1", path)

    call = request_spy[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith("/v1/spaces/space-1/files")
    assert call["uploaded_name"] == "photo.png"
    assert call["uploaded_bytes"] == b"png-data"
    assert "Content-Type" not in call["headers"]
    assert call["headers"]["Authorization"] == "Bearer api-key"


def test_add_list_objects_contract_accepts_object_id_list(api, request_spy):
    api.addObjectsToList("space-1", "list-1", ["object-1", "object-2"])

    assert request_spy[-1]["method"] == "POST"
    assert request_spy[-1]["url"].endswith("/v1/spaces/space-1/lists/list-1/objects")
    assert request_spy[-1]["json"] == {"objects": ["object-1", "object-2"]}


def test_space_exposes_chat_objects_and_file_upload():
    backend = SimpleNamespace(
        getChats=lambda *args: {"data": [{"id": "chat-1", "name": "Team"}]},
        uploadFile=lambda *args: {"object_id": "file-1", "name": "notes.pdf"},
    )
    space = Space._from_api(backend, {"id": "space-1", "name": "Work"})

    chats = space.get_chats(filters={"name[contains]": "Team"})
    uploaded = space.upload_file(SimpleNamespace(read=lambda: b"pdf"))

    assert len(chats) == 1
    assert isinstance(chats[0], Object)
    assert chats[0].id == "chat-1"
    assert chats[0].space_id == "space-1"
    assert uploaded["object_id"] == "file-1"


def test_anytype_global_search_forwards_full_search_request():
    recorded = {}

    def global_search(*args, **kwargs):
        recorded["args"] = args
        recorded["kwargs"] = kwargs
        return {"data": [{"id": "object-1", "space_id": "space-1"}]}

    client = Anytype()
    client._apiEndpoints = SimpleNamespace(globalSearch=global_search)

    result = client.global_search(
        "roadmap",
        types=["page"],
        sort={"direction": "desc", "property_key": "last_modified_date"},
        filters={"operator": "and", "conditions": []},
    )

    assert result[0].id == "object-1"
    assert recorded["args"] == ("roadmap", 0, 100)
    assert recorded["kwargs"]["types"] == ["page"]
    assert recorded["kwargs"]["filters"]["operator"] == "and"


def test_non_success_response_raises_typed_api_error(api, monkeypatch):
    response = FakeResponse({"code": "bad_request", "message": "invalid filter"}, status_code=400)
    monkeypatch.setattr("anytype.api.requests.request", lambda *args, **kwargs: response)

    with pytest.raises(ResponseHasError, match="invalid filter") as error:
        api.getSpaces()

    assert error.value.status_code == 400
    assert error.value.code == "bad_request"


@pytest.mark.parametrize("version", [None, "2025-05-20", "not-a-date"])
def test_rejects_missing_old_or_invalid_response_version(api, monkeypatch, version):
    response = FakeResponse({"data": []}, version=version)
    monkeypatch.setattr("anytype.api.requests.request", lambda *args, **kwargs: response)

    with pytest.raises(ValueError):
        api.getSpaces()
