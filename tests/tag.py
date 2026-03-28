import anytype


any = anytype.Anytype()
any.auth()

space = any.get_spaces()[0]

obj = space.get_objects()[1]
if isinstance(obj, anytype.Object):
    prop = obj.properties["Creation date"]
    id = prop.id
