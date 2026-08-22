from pprint import pprint

from anytype import Anytype

client = Anytype()
client.auth()

spaces = client.get_spaces()
my_space = spaces[0]

objects = my_space.search("Leçon 3")
if objects:
    pprint(objects[0].markdown)
else:
    print("No matching object found")
