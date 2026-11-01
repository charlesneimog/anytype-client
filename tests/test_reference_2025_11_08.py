from types import SimpleNamespace

import pytest

from anytype import Anytype, Object, Space, Type, apiEndpoints
from anytype.api import ResponseHasError


class FakeResponse:
    def __init__(self, payload=None, status_code=200, version=None):
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


def test_uses_v2_without_date_version_header(api):
    assert api.api_url.endswith("/v2")
    assert "Anytype-Version" not in api.headers


def test_create_api_key_contract(api, request_spy):
    api.getToken("challenge-123", "1234")

    assert request_spy[-1]["method"] == "POST"
    assert request_spy[-1]["url"].endswith("/v2/auth/api_keys")
    assert request_spy[-1]["json"] == {
        "challenge_id": "challenge-123",
        "code": "1234",
    }


def test_boolean_query_parameters_are_lowercase(api, request_spy):
    api.createObject(
        "space-1",
        {"type": "page", "properties": {"done": True}},
        create_missing_options=True,
        dry_run=False,
    )

    assert request_spy[-1]["params"] == {
        "create_missing_options": "true",
        "dry_run": "false",
    }
    assert request_spy[-1]["json"]["properties"]["done"] is True


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
        types=["page"],
        sort=sort,
        filters=filters,
    )

    assert request_spy[-1]["method"] == "POST"
    assert request_spy[-1]["url"].endswith("/v2/search")
    assert request_spy[-1]["params"] == {"offset": 20, "limit": 50}
    assert request_spy[-1]["json"] == {
        "query": "roadmap",
        "type": "page",
        "sorts": [{"property": "name", "direction": "asc"}],
        "filters": filters,
    }


@pytest.mark.parametrize(
    ("case", "invoke", "path", "filters"),
    [
        (
            "spaces",
            lambda client, values: client.getSpaces(2, 25, values),
            "/v2/spaces",
            {"name[contains]": "project"},
        ),
        (
            "chats",
            lambda client, values: client.getChats("space-1", 2, 25, values),
            "/v2/spaces/space-1/chats",
            {"name[contains]": "team"},
        ),
        (
            "members",
            lambda client, values: client.getMembers("space-1", 2, 25, values),
            "/v2/spaces/space-1/members",
            {"name[ne]": "john"},
        ),
        (
            "objects",
            lambda client, values: client.getObjects("space-1", 2, 25, values),
            "/v2/spaces/space-1/objects",
            {"type": "page", "created_date[gte]": "2024-01-01"},
        ),
        (
            "properties",
            lambda client, values: client.getProperties("space-1", 2, 25, values),
            "/v2/spaces/space-1/properties",
            {"name[contains]": "date"},
        ),
        (
            "tags",
            lambda client, values: client.getTags("space-1", "property-1", 2, 25, values),
            "/v2/spaces/space-1/properties/property-1/options",
            {"name[contains]": "urgent"},
        ),
        (
            "types",
            lambda client, values: client.getTypes("space-1", 2, 25, values),
            "/v2/spaces/space-1/types",
            {"name[contains]": "task"},
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_list_endpoint_contracts(api, request_spy, case, invoke, path, filters):
    invoke(api, filters)

    assert request_spy[-1]["method"] == "GET", case
    assert request_spy[-1]["url"].endswith(path), case
    expected = {**filters, "offset": 2, "limit": 25}
    if case == "spaces":
        expected["ids"] = "full"
    assert request_spy[-1]["params"] == expected, case


def test_get_spaces_always_requests_full_ids(api, request_spy):
    api.getSpaces(filters={"ids": "short"})

    assert request_spy[-1]["params"]["ids"] == "full"


def test_get_space_requests_full_ids(api, request_spy):
    api.getSpace("space-short-id")

    assert request_spy[-1]["method"] == "GET"
    assert request_spy[-1]["url"].endswith("/v2/spaces/space-short-id")
    assert request_spy[-1]["params"] == {"ids": "full"}


def test_anytype_get_space_returns_the_full_id_from_the_api():
    client = Anytype()
    client._apiEndpoints = SimpleNamespace(
        getSpace=lambda space_id: {
            "space": {"id": "bafyreifull-space-id", "name": "Work"}
        }
    )

    space = client.get_space("short-id")

    assert space.id == "bafyreifull-space-id"


def test_list_templates_uses_v2_space_endpoint_and_type_key(api, request_spy):
    api.getTemplates(
        "space-1",
        "reading_list",
        offset=2,
        limit=25,
        filters={"name[contains]": "book"},
    )

    assert request_spy[-1]["method"] == "GET"
    assert request_spy[-1]["url"].endswith("/v2/spaces/space-1/templates")
    assert request_spy[-1]["params"] == {
        "name[contains]": "book",
        "offset": 2,
        "limit": 25,
        "type": "reading_list",
    }


def test_type_get_templates_uses_api_key_and_maps_template_rows():
    recorded = {}

    def get_templates(*args):
        recorded["args"] = args
        return {
            "data": [
                {
                    "id": "template-1",
                    "name": "Book notes",
                    "template_for": "reading_list",
                    "default": True,
                }
            ]
        }

    backend = SimpleNamespace(getTemplates=get_templates)
    object_type = Type._from_api(
        backend,
        {
            "formatVersion": "2.0",
            "id": "type-object-id",
            "space_id": "space-1",
            "properties": {"name": "Reading list"},
            "type_settings": {"api_key": "reading_list"},
        },
    )

    templates = object_type.get_templates(offset=3, limit=10)

    assert recorded["args"] == ("space-1", "reading_list", 3, 10, None)
    assert len(templates) == 1
    assert templates[0].id == "template-1"
    assert templates[0].name == "Book notes"
    assert templates[0].template_for == "reading_list"
    assert templates[0].default is True


def test_upload_file_contract_builds_multipart_without_json_content_type(
    api, request_spy, tmp_path
):
    path = tmp_path / "photo.png"
    path.write_bytes(b"png-data")

    api.uploadFile("space-1", path)

    call = request_spy[-1]
    assert call["method"] == "POST"
    assert call["url"].endswith("/v2/spaces/space-1/files")
    assert call["uploaded_name"] == "photo.png"
    assert call["uploaded_bytes"] == b"png-data"
    assert "Content-Type" not in call["headers"]
    assert call["headers"]["Authorization"] == "Bearer api-key"


def test_download_file_returns_raw_bytes_and_supports_image_width(api, monkeypatch):
    calls = []

    def request(method, url, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        response = FakeResponse()
        response.content = b"\x89PNG\r\n"
        return response

    monkeypatch.setattr("anytype.api.requests.request", request)

    result = api.downloadFile("space-1", "file-1", width=320)

    assert result == b"\x89PNG\r\n"
    assert calls[-1]["method"] == "GET"
    assert calls[-1]["url"].endswith("/v2/spaces/space-1/files/file-1/content")
    assert calls[-1]["params"] == {"width": 320}
    assert calls[-1]["headers"]["Authorization"] == "Bearer api-key"


def test_download_file_uses_standard_http_error_handling(api, monkeypatch):
    response = FakeResponse(
        {"code": "not_found", "message": "file not found"}, status_code=404
    )
    monkeypatch.setattr("anytype.api.requests.request", lambda *args, **kwargs: response)

    with pytest.raises(ResponseHasError, match="file not found") as error:
        api.downloadFile("space-1", "invalid-file")

    assert error.value.status_code == 404
    assert error.value.code == "not_found"


@pytest.mark.parametrize("file_id", [None, ""])
def test_download_file_rejects_missing_file_id(api, file_id):
    with pytest.raises(ValueError, match="non-empty"):
        api.downloadFile("space-1", file_id)


@pytest.mark.parametrize("width", [-1, True, 1.5, "320"])
def test_download_file_rejects_invalid_width(api, width):
    with pytest.raises(ValueError, match="non-negative integer"):
        api.downloadFile("space-1", "file-1", width=width)


def test_add_list_objects_contract_accepts_object_id_list(api, request_spy):
    api.addObjectsToList("space-1", "list-1", ["object-1", "object-2"])

    assert request_spy[-1]["method"] == "PATCH"
    assert request_spy[-1]["url"].endswith("/v2/spaces/space-1/objects/list-1")
    assert request_spy[-1]["json"] == {"ops": [{"op": "add_items", "items": ["object-1", "object-2"]}]}


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


def test_space_download_file_delegates_to_the_shared_api_client():
    calls = []
    backend = SimpleNamespace(
        downloadFile=lambda *args, **kwargs: calls.append((args, kwargs)) or b"image-bytes"
    )
    space = Space._from_api(backend, {"id": "space-1", "name": "Work"})

    assert space.download_file("file-1", width=0) == b"image-bytes"
    assert calls == [(('space-1', 'file-1'), {'width': 0})]


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
def test_v2_does_not_require_legacy_date_header(api, monkeypatch, version):
    response = FakeResponse({"data": []}, version=version)
    monkeypatch.setattr("anytype.api.requests.request", lambda *args, **kwargs: response)

    assert api.getSpaces() == {"data": []}
