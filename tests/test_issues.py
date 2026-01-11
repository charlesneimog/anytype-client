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

    any.create_space("API")

    spaces = any.get_spaces()
    for space in spaces:
        if space.name == "API":
            return space

    raise Exception("Space not found")


def test_issue16():
    space = get_apispace()
    tester = space.get_objects()[0]
    print(tester)
    space.update_object(tester)
