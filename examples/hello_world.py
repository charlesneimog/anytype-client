from anytype import Anytype, Object

# Keep Anytype Desktop running. On first use, enter the four-digit code shown
# by Anytype to create a local API key.
client = Anytype()
client.auth()

# Get the first available space and its Page type.
spaces = client.get_spaces()
my_space = spaces[0]
note_type = my_space.get_type_byname("Page")

# Passing the type during construction attaches all of its custom properties.
new_object = Object("Hello World", type=note_type)
new_object.icon = "🐍"
new_object.description = "This object was created with the Anytype Python API"
new_object.add_title1("Hello")
new_object.add_title2("From")
new_object.add_title3("Python")
new_object.add_codeblock("print('Hello World!')", language="python")
new_object.add_bullet("1")
new_object.add_bullet("2")
new_object.add_bullet("3")
new_object.add_text("$x(n) = x + n$")

# The object already has a type, so it does not need to be passed again.
created_object = my_space.create_object(new_object)
print(f"Created {created_object.name!r} ({created_object.id})")
