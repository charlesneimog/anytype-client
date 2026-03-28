import sys
import os

# just for my dev, you can remove it
path = os.path.dirname(__file__)
sys.path.append(path + "/..")

import anytype

# Need Anytype-0.44.13-beta or higher
# Auth, on first type you need to type the 4 digit code that will popup on Anytype App
any = anytype.Anytype()
any.auth()

# Get Spaces
spaces = any.get_spaces()
my_space = spaces[0]

page_type = my_space.get_type_byname("Page")
task_type = my_space.get_type_byname("Task")

# return just Page type objects
objects = my_space.search("OpenScofo", type=anytype.Type("Page"))
print(objects)

# return Page and Task type objects
objects = my_space.search("OpenScofo", type=[page_type, task_type])
print(objects)
