# `anytype.Object`

## Templates and custom properties

Pass the selected type and template when constructing the object. Properties linked
to that type are available by their API key or by their normalized display name:

```python
obj = Object("Test", type=quote_type, template=template)
obj.date = "02/06/2026"
obj.people = [person]

created = space.create_object(obj)
```

Object creation sends the selected template ID as the v2 request's `template`
field. With no selected template, the field is omitted and the server applies
the type's default template. Set `obj.template_id = "none"` to start blank.
Additional blocks or Markdown follow the template's content in the same create
request; supply one body format at a time.

`date` must be the key of a date property. `people` must be the key of an objects
property; it accepts object instances or object IDs. A multi-select property instead
accepts tag names or `Tag` instances.

Properties selected from the space can also be assigned explicitly:

```python
properties = {prop.key: prop for prop in space.get_properties()}
properties["date"].value = "02/06/2026"
properties["people"].value = [person]

obj.properties["date"] = properties["date"]
obj.properties["people"] = properties["people"]
```

::: anytype.Object
