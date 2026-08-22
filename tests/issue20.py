import sys

sys.path.append("/home/neimog/Documents/Git/anytype-client")

from anytype import Anytype, Space, Object, Property
from anytype.property import Date

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


if __name__ == "__main__":

    space = get_apispace()
    issue_type = space.get_type_byname("issue")

    print(issue_type)
    obj = Object("Issue2")

    obj.properties["date"] = Date("02/03/2026")

    created = space.create_object(obj, issue_type)
