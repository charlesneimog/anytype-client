import sys
import os

path = os.path.dirname(__file__)

sys.path.append(path + "/..")

import anytype

any = anytype.Anytype()

any.auth()

space = any.get_spaces()[0]
objects = space.get_objects(limit=1000)

mytype = space.get_type_byname("Book")

for obj in objects:
    if obj.type is not None:
        if obj.type.name == "Note":
            obj.type = mytype
            space.update_object(obj)
