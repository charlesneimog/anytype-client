import sys
import os

path = os.path.dirname(__file__)

sys.path.append(path + "/..")

import anytype

any = anytype.Anytype()

any.auth()

space = any.get_spaces()[0]
objects = space.get_objects(limit=1000)

mytype = space.get_type_byname("Page")
page_icon = anytype.Icon("🗒️")

for obj in objects:
    if obj.type is not None:
        if obj.type.name == "Page":
            obj.icon = page_icon
            space.update_object(obj)
            print("Icon updated to " + obj.name)
