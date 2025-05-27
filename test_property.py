from anytype import Anytype, Space, Object, Type, Icon

from anytype.property import (
    Text,
    Number,
    Checkbox,
    Select,
    MultiSelect,
    Date,
    Files,
    Email,
    Phone,
    Objects,
    Url,
)


import random
import string

any = Anytype()
any.auth()


def get_apispace() -> Space:
    spaces = any.get_spaces()
    for space in spaces:
        if space.name == "API":
            return space
    raise Exception("Space not found")


def test_testproperties():
    api_space = get_apispace()
    prop_test_type = Type("TestProperty")
    prop_test_type.icon = Icon()
    prop_test_type.layout = "basic"
    prop_test_type.plural_name = "TestProperties"

    prop_test_type.add_property(Text("prop_text"))
    prop_test_type.add_property(Number("prop_number"))
    prop_test_type.add_property(Select("prop_select"))
    prop_test_type.add_property(MultiSelect("prop_multi"))
    prop_test_type.add_property(Date("prop_date"))
    # article_type.add_property(Files("prop_files"))
    prop_test_type.add_property(Checkbox("prop_checkbox"))
    prop_test_type.add_property(Url("prop_url"))
    prop_test_type.add_property(Email("prop_email"))
    prop_test_type.add_property(Phone("prop_phone"))
    prop_test_type.add_property(Objects("prop_objects"))

    prop_test_type = api_space.create_type(prop_test_type)

    # Test
    obj = Object("My Property Object", prop_test_type)
    obj.icon = "🐍"
    obj.body = "`print('Hello World!')`"
    obj.description = "This is an object created from Python Api"

    obj.properties["prop_text"].value = "My Text"
    obj.properties["prop_number"].value = 12389
    obj.properties["prop_select"].value = "Test"
    obj.properties["prop_multi"].value = ["Test1", "Test2"]
    obj.properties["prop_date"].value = "27/03/2025"
    obj.properties["prop_checkbox"].value = True
    obj.properties["prop_url"].value = "https://charlesneimog.github.io"
    obj.properties["prop_email"].value = "myemail@email.com"
    obj.properties["prop_phone"].value = "+55112233445566"

    created_obj = api_space.create_object(obj)

    id = created_obj.properties["prop_text"].value
    print(api_space.get_property(id)._json)

    assert created_obj.properties["prop_text"].value == "My Text2"
    assert created_obj.properties["prop_number"].value == 12389
    assert created_obj.properties["prop_select"].value == "Test"
    assert created_obj.properties["prop_multi"].value == ["Test1", "Test2"]
    assert created_obj.properties["prop_date"].value == "27/03/2025"
    assert created_obj.properties["prop_checkbox"].value == True


test_testproperties()
