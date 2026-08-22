"""Explore the Anytype 2025-11-08 API from a real local space.

Listing and search are read-only. Passing --upload creates a file object, and
passing both --list-id and --add-object-id adds an existing object to a list.
"""

import argparse
from pathlib import Path

from anytype import Anytype


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", help="Space name; defaults to the first available space")
    parser.add_argument("--query", default="", help="Global search query")
    parser.add_argument("--type", dest="type_name", help="Type name used for search/templates")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--upload", type=Path, help="Optional file to upload")
    parser.add_argument("--list-id", help="Optional list object ID")
    parser.add_argument("--add-object-id", help="Existing object ID to add to --list-id")
    return parser.parse_args()


def show(label, items):
    names = [getattr(item, "name", getattr(item, "id", repr(item))) for item in items]
    print(f"{label} ({len(items)}): {names}")


def main():
    args = parse_args()
    client = Anytype()
    client.auth()

    spaces = client.get_spaces(limit=args.limit)
    show("Spaces", spaces)
    if not spaces:
        raise RuntimeError("No Anytype spaces are available")

    if args.space:
        space = next((item for item in spaces if item.name == args.space), None)
        if space is None:
            raise ValueError(f"Space {args.space!r} was not found in the first {args.limit} spaces")
    else:
        space = spaces[0]

    types = space.get_types(limit=args.limit)
    properties = space.get_properties(limit=args.limit)
    objects = space.get_objects(limit=args.limit)
    members = space.get_members(limit=args.limit)
    chats = space.get_chats(limit=args.limit)
    show("Types", types)
    show("Properties", properties)
    show("Objects", objects)
    show("Members", members)
    show("Chats", chats)

    selected_type = None
    if args.type_name:
        selected_type = next((item for item in types if item.name == args.type_name), None)
        if selected_type is None:
            raise ValueError(f"Type {args.type_name!r} was not found")
        show("Templates", selected_type.get_templates(limit=args.limit))

    tag_property = next(
        (prop for prop in properties if prop.format in {"select", "multi_select"}),
        None,
    )
    if tag_property is not None:
        show(f"Tags for {tag_property.name}", tag_property.get_tags(limit=args.limit))

    results = client.global_search(
        args.query,
        limit=args.limit,
        types=[selected_type.key] if selected_type is not None else None,
        sort={"direction": "desc", "property_key": "last_modified_date"},
    )
    show("Global search", results)

    if args.upload is not None:
        uploaded = space.upload_file(args.upload)
        print(f"Uploaded: {uploaded}")

    if bool(args.list_id) != bool(args.add_object_id):
        raise ValueError("--list-id and --add-object-id must be provided together")
    if args.list_id:
        views = space.get_listviews(args.list_id, limit=args.limit)
        if not views:
            raise ValueError(f"List {args.list_id!r} has no views")
        obj = space.get_object(args.add_object_id)
        views[0].add_objectinlistview(obj)
        print(f"Added object {obj.id!r} to list {args.list_id!r}")


if __name__ == "__main__":
    main()
