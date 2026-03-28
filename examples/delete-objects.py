import sys
import os

path = os.path.dirname(__file__)

sys.path.append(path + "/..")

import anytype

any = anytype.Anytype()

any.auth()

space = any.get_spaces()[0]
objects = space.get_objects(limit=1000)

for obj in objects:
    if obj.type is not None:
        if obj.type.name == "Aerea":
            print(obj)
