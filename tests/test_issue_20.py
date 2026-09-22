from datetime import date, datetime, timezone

import pytest

from anytype import Object, Space, Template, Type
from anytype.property import Date, MultiSelect, Objects, Property, Select
from anytype.tag import Tag


class Issue20Backend:
    def __init__(self):
        self.created = []
        self.properties = {
            "property-date": {
                "id": "property-date",
                "key": "date",
                "name": "Quote Date",
                "format": "date",
                "object": "property",
            },
            "property-people": {
                "id": "property-people",
                "key": "people",
                "name": "People",
                "format": "objects",
                "object": "property",
            },
            "property-status": {
                "id": "property-status",
                "key": "status",
                "name": "Status",
                "format": "select",
                "object": "property",
            },
            "property-topics": {
                "id": "property-topics",
                "key": "topics",
                "name": "Topics",
                "format": "multi_select",
                "object": "property",
            },
        }

    def getProperty(self, space_id, property_id):
        assert space_id == "space-api"
        return {"property": dict(self.properties[property_id])}

    def getProperties(self, space_id, offset, limit, filters=None):
        assert space_id == "space-api"
        return {"data": [dict(value) for value in self.properties.values()]}

    def createObject(self, space_id, data):
        assert space_id == "space-api"
        self.created.append(data)
        return {"id": "created-object", "etag": "one"}

    def getObject(self, space_id, object_id):
        return {**self.created[-1], "id": object_id, "etag": "one"}


@pytest.fixture
def issue20_context():
    backend = Issue20Backend()
    space = Space()
    space.id = "space-api"
    space._apiEndpoints = backend

    quote_type = Type("Quote")
    quote_type.id = "type-quote"
    quote_type.key = "quote"
    quote_type.space_id = space.id
    quote_type._apiEndpoints = backend
    quote_type.properties = {
        "Quote Date": Property._from_api(
            backend,
            backend.properties["property-date"] | {"space_id": space.id},
        ),
        "People": Property._from_api(
            backend,
            backend.properties["property-people"] | {"space_id": space.id},
        ),
    }

    template = Template._from_api(
        backend,
        {"id": "template-quote", "name": "Quote Template", "space_id": space.id},
    )
    person = Object("Ada")
    person.id = "object-person"
    return backend, space, quote_type, template, person


def property_values(payload):
    return payload["properties"]


def test_get_properties_returns_format_specific_classes(issue20_context):
    _, space, _, _, person = issue20_context

    properties = {prop.key: prop for prop in space.get_properties()}

    assert isinstance(properties["date"], Date)
    assert isinstance(properties["people"], Objects)

    properties["date"].value = "02/06/2026"
    properties["people"].value = [person]
    assert properties["date"].value == "02/06/2026"
    assert properties["people"].value == [person]


def test_dynamic_property_assignment_and_template_constructor(issue20_context):
    backend, space, quote_type, template, person = issue20_context
    obj = Object()
    obj.add_type(quote_type)
    obj.name = "Test"

    obj.date = "02/06/2026"
    obj.people = [person]
    created = space.create_object(obj)

    payload = backend.created[-1]
    values = property_values(payload)
    assert created.id == "created-object"
    assert payload["type"] == "quote"
    assert values["date"] == "2026-06-02T00:00:00Z"
    assert values["people"] == ["object-person"]


def test_explicit_template_id_survives_type_argument(issue20_context):
    backend, space, quote_type, template, _ = issue20_context
    obj = Object("Test")
    obj.template_id = template.id

    with pytest.raises(NotImplementedError, match="template_id"):
        space.create_object(obj, quote_type)
    assert not backend.created


def test_manually_selected_properties_serialize(issue20_context):
    backend, space, quote_type, template, person = issue20_context
    properties = {prop.key: prop for prop in space.get_properties()}
    properties["date"].value = "2026-06-02"
    properties["people"].value = person

    obj = Object("Manual", quote_type)
    obj.properties = {
        "date": properties["date"],
        "people": properties["people"],
    }
    space.create_object(obj)

    values = property_values(backend.created[-1])
    assert values["date"] == "2026-06-02T00:00:00Z"
    assert values["people"] == ["object-person"]


def test_manual_properties_survive_type_argument(issue20_context):
    backend, space, quote_type, _, person = issue20_context
    properties = {prop.key: prop for prop in space.get_properties()}
    properties["date"].value = "02/06/2026"
    properties["people"].value = [person]

    obj = Object("Manual before type")
    obj.properties = {
        "date": properties["date"],
        "people": properties["people"],
    }
    space.create_object(obj, quote_type)

    values = property_values(backend.created[-1])
    assert values["date"] == "2026-06-02T00:00:00Z"
    assert values["people"] == ["object-person"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 6, 2, 13, 30), "2026-06-02T13:30:00Z"),
        (
            datetime(2026, 6, 2, 13, 30, tzinfo=timezone.utc),
            "2026-06-02T13:30:00Z",
        ),
        (date(2026, 6, 2), "2026-06-02T00:00:00Z"),
        ("2026-06-02T13:30:00Z", "2026-06-02T13:30:00Z"),
    ],
)
def test_supported_date_inputs_serialize(issue20_context, value, expected):
    _, _, quote_type, _, _ = issue20_context
    prop = quote_type.properties["Quote Date"]
    prop.value = value

    assert prop._get_json() == {"date": expected}


def test_objects_created_from_one_type_do_not_share_property_values(issue20_context):
    _, _, quote_type, _, _ = issue20_context
    first = Object("First", quote_type)
    second = Object("Second", quote_type)

    first.quote_date = "02/06/2026"

    assert first.quote_date == "02/06/2026"
    assert second.quote_date != first.quote_date


def test_object_response_preserves_typed_property_values(issue20_context):
    backend, space, _, _, _ = issue20_context

    obj = Object._from_api(
        backend,
        {
            "id": "existing-object",
            "properties": [
                {
                    "id": "property-date",
                    "date": "2026-06-02T00:00:00Z",
                }
            ],
            "space_id": space.id,
        },
    )

    assert isinstance(obj.properties["Quote Date"], Date)
    assert obj.date == "2026-06-02T00:00:00Z"


def test_object_response_tags_can_be_serialized_again(issue20_context):
    backend, space, _, _, _ = issue20_context

    obj = Object._from_api(
        backend,
        {
            "id": "existing-object",
            "properties": [
                {
                    "id": "property-status",
                    "select": {"id": "tag-draft", "key": "draft", "name": "Draft"},
                },
                {
                    "id": "property-topics",
                    "multi_select": [
                        {"id": "tag-python", "key": "python", "name": "Python"},
                        {"id": "tag-api", "key": "api", "name": "API"},
                    ],
                },
            ],
            "space_id": space.id,
        },
    )

    status = obj.properties["Status"]
    topics = obj.properties["Topics"]
    assert isinstance(status, Select)
    assert isinstance(status.value, Tag)
    assert isinstance(topics, MultiSelect)
    assert all(isinstance(tag, Tag) for tag in topics.value)
    assert status._get_json() == {"status": ["Draft"]}
    assert topics._get_json() == {
        "topics": ["Python", "API"],
    }


def test_invalid_property_value_is_not_silently_dropped(issue20_context):
    backend, space, quote_type, _, _ = issue20_context
    obj = Object("Invalid", quote_type)
    obj.date = "not-a-date"

    with pytest.raises(ValueError, match="Date values must use"):
        space.create_object(obj)

    assert backend.created == []
