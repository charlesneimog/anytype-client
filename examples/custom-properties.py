"""Create an object with a template, date, and object-relation property.

Example:
    python examples/custom-properties.py \
        --space "API" \
        --type "Quote" \
        --template "Quote Template" \
        --person "Ada Lovelace"

The selected type must contain a date property with the key ``date`` and an
objects property with the key ``people``. Use the corresponding command-line
options if your property keys are different.
"""

import argparse

from anytype import Anytype, Object


def item_by_name(items, name, kind):
    try:
        return next(item for item in items if item.name == name)
    except StopIteration as error:
        available = ", ".join(sorted(item.name for item in items))
        raise ValueError(f"{kind} {name!r} was not found. Available: {available}") from error


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", required=True, help="Name of the destination space")
    parser.add_argument("--type", required=True, dest="type_name", help="Object type name")
    parser.add_argument("--template", help="Optional template name for the selected type")
    parser.add_argument("--person", required=True, help="Exact name of an existing object")
    parser.add_argument("--name", default="API-created quote", help="Name of the new object")
    parser.add_argument("--date", default="02/06/2026", help="Date or RFC3339 value")
    parser.add_argument("--date-property", default="date", help="Date property API key")
    parser.add_argument("--people-property", default="people", help="Objects property API key")
    return parser.parse_args()


def main():
    args = parse_args()
    client = Anytype()
    client.auth()

    space = item_by_name(client.get_spaces(), args.space, "Space")
    object_type = item_by_name(space.get_types(), args.type_name, "Type")
    template = object_type.get_template_byname(args.template) if args.template is not None else None

    matches = space.search(args.person, limit=100)
    person = item_by_name(matches, args.person, "Object")

    properties = {prop.key: prop for prop in object_type.properties.values()}
    expected_formats = {
        args.date_property: "date",
        args.people_property: "objects",
    }
    for key, expected_format in expected_formats.items():
        prop = properties.get(key)
        if prop is None:
            raise ValueError(f"Type {object_type.name!r} has no property with key {key!r}")
        if prop.format != expected_format:
            raise ValueError(
                f"Property {key!r} must use format {expected_format!r}, not {prop.format!r}"
            )

    obj = Object(args.name, type=object_type, template=template)
    setattr(obj, args.date_property, args.date)
    setattr(obj, args.people_property, [person])

    created = space.create_object(obj)
    print(f"Created {created.name!r} ({created.id}) in {space.name!r}")


if __name__ == "__main__":
    main()
