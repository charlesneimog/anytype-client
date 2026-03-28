import sys
import os
from pprint import pprint

path = os.path.dirname(__file__)

sys.path.append(path + "/..")

from anytype import Anytype
from anytype import Object

# Need Anytype-0.44.13-beta or higher
# Auth, on first type you need to type the 4 digit code that will popup on Anytype App
any = Anytype()
any.auth()

# Get Spaces
spaces = any.get_spaces()
my_space = spaces[0]

objects = my_space.search("Leçon 3")[0]
pprint(objects.markdown)
