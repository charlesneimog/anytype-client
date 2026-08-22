import sys
import os
from pprint import pprint

path = os.path.dirname(__file__)

sys.path.append(path + "/..")

import anytype

any = anytype.Anytype()

any.auth()

space = any.get_spaces()[1]
objects = space.get_objects(limit=100)


mytype = space.get_type_byname("Page")
page_icon = anytype.Icon("🗒️")
print(mytype.id)

pages = space.search("Peeters", type=mytype)


for obj in objects:
    if obj.type.id != mytype.id:
        print(obj.type)
        print(mytype)
        print("wrong")
        exit(-1)
