import pytest

from anytype import Anytype, Space, Template, Object, Property, apiEndpoints
import tempfile
import os

any = Anytype()
any.auth()


def get_apispace() -> Space:
    spaces = any.get_spaces()
    for space in spaces:
        if space.name == "API":
            return space
    raise Exception("Space not found")


def test_create_space():
    spaces = any.get_spaces()
    for space in spaces:
        if space.name == "API":
            return

    any.create_space("API")
    assert get_apispace()


def test_get_spaces():
    spaces = any.get_spaces()
    assert len(spaces) > 0
    found_space = False
    for space in spaces:
        if space.name == "API":
            found_space = True
            break
    assert found_space


def test_missspaceid():
    space = get_apispace()
    print(space)
    space.id = ""
    with pytest.raises(ValueError):
        space.search("bla bla bla")


def test_template():
    # this is unsued yet, but just to keep testing
    template = Template()
    print(template)


def test_search():
    space = get_apispace()
    values = space.search("Math")
    print(values)


def test_globalsearch():
    query = any.global_search("Isso não deve existir")
    print(query)

    query = any.global_search("Math")
    print(query)


def test_get_types():
    space = get_apispace()
    space._all_types = []

    with pytest.raises(ValueError):
        space.get_type("ExistingType")


def test_relation():
    # this is unsued yet, but just to keep testing
    relation = Property()
    print(relation)


def test_spacemethods():
    space = any.get_spaces()[0]
    objects = space.get_objects()
    obj = objects[0]
    obj = space.get_object(obj.id)


def test_templates():
    space = get_apispace()
    objtype = space.get_type_byname("Project")

    templates = objtype.get_templates()
    if templates is None:
        raise Exception("No templates found for Project")

    objtype.set_template(templates[0].name)
    objtype._all_templates = []
    objtype.set_template(templates[0].name)

    # template that does not exist
    with pytest.raises(ValueError):
        objtype.set_template("NoExists")

def test_createobj():
    space = get_apispace()
    if not space:
        raise Exception("Space not found")

    obj = Object()
    obj.name = "Hello World!"
    obj.icon = "🐍"
    obj.body = "`print('Hello World!')`"
    obj.description = "This is an object created from Python Api"

    objtype = space.get_type_byname("Page")
    obj.add_title1("Test!")
    obj.add_title2("Test!")
    obj.add_title3("Test!")
    obj.add_text("normal text")
    obj.add_codeblock("print('Hello World!')")
    obj.add_bullet("Hello World!")
    obj.add_checkbox("Hello World!")
    obj.add_image(
        "https://raw.githubusercontent.com/charlesneimog/"
        + "anytype-client/refs/heads/main/resources/pdf.png"
    )
    obj.add_image(
        "https://raw.githubusercontent.com/charlesneimog/"
        + "anytype-client/refs/heads/main/resources/pdf.png",
        alt="PDF",
        title="PDF",
    )

    created_obj = space.create_object(obj, objtype)
    # Add assertions to verify the object was created
    assert created_obj.name == "Hello World!"
    assert created_obj.icon.emoji == "🐍"
    assert created_obj.description == "This is an object created from Python Api"

    space.search("Hello World")


def test_getmembers():
    space = get_apispace()
    if not space:
        raise Exception("Space not found")
    members = space.get_members()
    assert len(members) > 0

def test_auth_force(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr("os.path.expanduser", lambda _: tmpdir)
    client = Anytype()

    def fake_callback():
        return "0000"  # Use um código inválido deliberadamente

    with pytest.raises(Exception):  # Ou controle o erro específico
        client.auth(force=True, callback=fake_callback)

def test_get_userdata_folder_creates(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr("os.path.expanduser", lambda _: tmpdir)
    client = Anytype()
    userdata = client._get_userdata_folder()
    assert os.path.exists(userdata)

def test_get_space_by_id():
    space = get_apispace()
    retrieved = any.get_space(space.id)
    assert retrieved.id == space.id

def test_invalid_token(monkeypatch):
    client = Anytype()
    client.token = "fake"
    client.app_key = "fake"
    client._apiEndpoints = apiEndpoints({
        "Content-Type": "application/json",
        "Authorization": "Bearer fake"
    })

    assert not client._validate_token()

