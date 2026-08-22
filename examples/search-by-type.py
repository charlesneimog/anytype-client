import anytype

client = anytype.Anytype()
client.auth()

spaces = client.get_spaces()
my_space = spaces[0]

page_type = my_space.get_type_byname("Page")
task_type = my_space.get_type_byname("Task")

# return just Page type objects
objects = my_space.search("OpenScofo", type=page_type)
print(objects)

# return Page and Task type objects
objects = my_space.search("OpenScofo", type=[page_type, task_type])
print(objects)
