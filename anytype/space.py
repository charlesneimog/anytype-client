from copy import deepcopy
from .listview import ListView
from .type import Type
from .object import Object
from .member import Member
from .icon import Icon
from .api import apiEndpoints, APIWrapper
from .utils import requires_auth
from .property import Property


class Space(APIWrapper):
    """
    Used to interact with and manage objects, types, and other elements within a specific Space. It provides methods to retrieve objects, types, and perform search operations within the space. Additionally, it allows creating new objects associated with specific types.
    """

    def __init__(self):
        self._apiEndpoints: apiEndpoints | None = None
        self.name = ""
        self.id = ""
        self._all_types = []

    def _object_to_dict(self, obj):
        if obj.template_id:
            raise NotImplementedError("v2 object creation does not accept template_id; use the type's default_template")
        if obj._markdown and obj.blocks:
            raise ValueError("Supply blocks or markdown, not both")
        if obj._markdown:
            return {"type": obj.type.key if isinstance(obj.type, Type) else obj.type or "page",
                    "name": obj.name, "properties": obj._property_values(), "markdown": obj._markdown}
        return obj.to_document(for_create=True)

    @requires_auth
    def get_objects(self, offset=0, limit=100, filters: dict | None = None) -> list[Object]:
        """
        Retrieves a list of objects associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).
            filters (dict, optional): Dynamic query filters keyed by property and
                condition.

        Returns:
            A list of Object instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response_data = self._apiEndpoints.getObjects(self.id, offset, limit, filters)
        objects = [
            Object._from_api(self._apiEndpoints, data | {"space_id": self.id})
            for data in response_data.get("data", [])
        ]

        return objects

    @requires_auth
    def get_chats(self, offset=0, limit=100, filters: dict | None = None) -> list[Object]:
        """Retrieve chat container objects in this space."""
        response_data = self._apiEndpoints.getChats(self.id, offset, limit, filters)
        return [
            Object._from_api(self._apiEndpoints, data | {"space_id": self.id})
            for data in response_data.get("data", [])
        ]

    @requires_auth
    def upload_file(self, file) -> dict:
        """Upload a path or binary file object to this space."""
        return self._apiEndpoints.uploadFile(self.id, file)

    @requires_auth
    def get_object(self, obj: str | Object) -> Object:
        """
        Retrieves a specific object by its ID.

        Parameters:
            obj (Object | str): The object (or its ID) to retrieve.

        Returns:
            An Object instance representing the retrieved object.

        Raises:
            Raises an error if the request to the API fails.
        """
        if isinstance(obj, Object):
            objectId = obj.id
        else:
            objectId = obj
        response = self._apiEndpoints.getObject(self.id, objectId)
        data = response.get("object", response)
        return Object._from_api(self._apiEndpoints, data | {"space_id": self.id})

    @requires_auth
    def create_object(self, obj, type=None, **options):
        """Create an AnyBlock document and fetch its complete server representation.

        ``dry_run=True`` returns the validation result without creating anything.
        ``create_missing_options=True`` allows new select option names.
        """
        if obj.type is None and type is not None:
            obj.add_type(type)
        result = self._apiEndpoints.createObject(self.id, self._object_to_dict(obj), **options)
        if options.get("dry_run"):
            return result
        return self.get_object(result["id"])

    @requires_auth
    def update_object(self, obj):
        """Persist changes to a fetched object using an atomic, conditional patch.

        Block field edits and appended blocks retain existing IDs. Structural
        changes use explicit ``obj.patch`` operations (move_block/delete_block).
        """
        if obj._snapshot is None:
            raise ValueError("Retrieve the object before updating it")
        if obj._markdown_dirty:
            raise ValueError("Use insert_blocks with markdown or edit typed blocks; exported markdown is read-only")
        old, new = obj._snapshot, obj.to_document()
        ops = []
        if old['type'] != new['type'] or old.get('icon') != new.get('icon') or any(
            old.get(k) != new.get(k) for k in ('cover', 'collection_items', 'query_source')):
            raise ValueError("Use v2 patch operations to change type, icon, cover or list membership")
        changed = {key: value for key, value in new['properties'].items()
                   if key not in old['properties'] or old['properties'][key] != value}
        unset = [key for key in old['properties'] if key not in new['properties']]
        if changed or unset:
            op = {"op": "set_properties"}
            if changed:
                op["set"] = changed
            if unset:
                op["unset"] = unset
            ops.append(op)
        previous = old['blocks']
        current = new['blocks']
        if len(current) < len(previous) or any(
            a.get('id') != b.get('id') or a.get('indent', 0) != b.get('indent', 0)
            for a, b in zip(previous, current)):
            raise ValueError("Use delete_block/move_block operations for structural block edits")
        for before, after in zip(previous, current):
            fields = {key: after.get(key) for key in before.keys() | after.keys()
                      if key != 'id' and before.get(key) != after.get(key)}
            if fields:
                ops.append({"op": "update_block", "id": before['id'], "set": fields})
        if len(current) > len(previous):
            from .block import Block
            ops.append({"op": "insert_blocks", "blocks": [Block.from_dict(b).to_dict(for_create=True)
                        for b in current[len(previous):]]})
        if ops:
            obj.patch(ops)
        return obj

    @requires_auth
    def create_collection(self, name, objects=None):
        items = [o.id if isinstance(o, Object) else o for o in objects or []]
        result = self._apiEndpoints.createCollection(self.id, {"name": name, "items": items})
        return self.get_object(result['id'])

    @requires_auth
    def create_query(self, name, type, **options):
        result = self._apiEndpoints.createQuery(self.id, {"name": name,
            "type": type.key if isinstance(type, Type) else type, **options})
        return self.get_object(result['id'])

    @requires_auth
    def get_list_objects(self, list, view=None, offset=0, limit=100, kind="collection", fields=None):
        result = self._apiEndpoints.getObjectsInList(self.id,
            list.id if isinstance(list, Object) else list, view, offset, limit, kind=kind, fields=fields)
        return [Object._from_api(self._apiEndpoints, row | {"space_id": self.id}) for row in result['data']]

    @requires_auth
    def upload_file_url(self, url, name=None):
        data = {"url": url}
        if name:
            data["name"] = name
        return self._apiEndpoints._request("POST", f"/spaces/{self.id}/files", json=data)

    @requires_auth
    def delete_object(self, obj: str | Object) -> None:
        """
        Attempt to delete an object by its unique identifier.

        Parameters:
            obj (Object | str): The Object or object ID string to delete.

        Returns:
            None

        Raises:
            Exception: If the request to delete the object fails.

        """
        if isinstance(obj, Object):
            obj = obj.id
        self._apiEndpoints.deleteObject(self.id, obj)

    def _type_to_dict(self, type):
        data = {"name": type.name, "plural_name": type.plural_name, "layout": type.layout,
                "icon": type.icon._get_json(), "property_definitions": [
                    {"property": p.key} if p.key else {"name": p.name, "format": p.format}
                    for p in type.properties.values()]}
        if type.template_id:
            data["default_template"] = type.template_id
        return data

    @requires_auth
    def create_type(self, type):
        data = self._type_to_dict(type)
        if type.key:
            data["api_key"] = type.key
        result = self._apiEndpoints.createType(self.id, data)
        return self.get_type(result['key'])

    @requires_auth
    def update_type(self, type):
        self._apiEndpoints.updateType(self.id, type.key, self._type_to_dict(type))
        return self.get_type(type.key)

    def delete_type(self, type: str | Type) -> None:
        """
        Delete an existing type from the current space.

        This function deletes a type from the current space using its ID or a `Type` instance.
        If a `Type` object is provided, its `id` is extracted. The deletion is performed via
        the underlying API.

        Parameters:
            type (str | Type): The ID of the type to delete or a `Type` instance.

        Returns:
            None

        Raises:
            Exception: If the deletion fails due to an API error or invalid ID.
        """
        if isinstance(type, Type):
            typeId = type.key or type.id
        else:
            typeId = type
        _ = self._apiEndpoints.deleteType(self.id, typeId)

    @requires_auth
    def get_type(self, type):
        key = type.key or type.id if isinstance(type, Type) else type
        response = self._apiEndpoints.getType(self.id, key)
        return Type._from_api(self._apiEndpoints, response | {"space_id": self.id})

    @requires_auth
    def get_types(self, offset=0, limit=100, filters: dict | None = None) -> list[Type]:
        """
        Retrieves a list of types associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).
            filters (dict, optional): Dynamic query filters keyed by property and
                condition.

        Returns:
            A list of Type instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getTypes(self.id, offset, limit, filters)
        types = [
            Type._from_api(self._apiEndpoints, data | {"space_id": self.id})
            for data in response.get("data", [])
        ]
        return types

    def get_type_byname(self, name: str) -> Type:
        """
        Retrieves a type by its name.

        This method paginates through all available types in the space
        until a type with the given name is found.

        Parameters:
            name (str): The name of the type to retrieve.

        Returns:
            Type: The matching Type instance.

        Raises:
            ValueError: If no type with the given name is found.
            Raises an error if the request to the API fails.
        """
        offset = 0
        limit = 5
        while True:
            types = self.get_types(offset=offset, limit=limit)
            type_len = len(types)
            for type in types:
                if type.name == name:
                    return self.get_type(type.key)
            if type_len < limit:
                break

            offset += limit

        raise ValueError("Type not found")

    @requires_auth
    def get_member(self, member: str | Member) -> Member:
        if isinstance(member, Member):
            memberId = member.id
        else:
            memberId = member

        response = self._apiEndpoints.getMember(self.id, memberId)
        data = response.get("object", response)
        return Member._from_api(self._apiEndpoints, data | {"space_id": self.id})

    @requires_auth
    def get_members(
        self, offset: int = 0, limit: int = 100, filters: dict | None = None
    ) -> list[Member]:
        """
        Retrieves a list of members associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).
            filters (dict, optional): Dynamic query filters keyed by property and
                condition.

        Returns:
            A list of Member instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getMembers(self.id, offset, limit, filters)
        return [
            Member._from_api(self._apiEndpoints, data | {"space_id": self.id})
            for data in response.get("data", [])
        ]

    @requires_auth
    def get_listviews(
        self, listId: str | Object | Type, offset: int = 0, limit: int = 100, kind="collection"
    ) -> list[ListView]:
        if isinstance(listId, Object) or isinstance(listId, Type):
            listId = listId.id

        response = self._apiEndpoints.getListViews(self.id, listId, offset, limit, kind=kind)
        return [
            ListView._from_api(
                self._apiEndpoints,
                data
                | {
                    "space_id": self.id,
                    "list_id": listId,
                    "kind": kind,
                },
            )
            for data in response.get("data", [])
        ]

    @requires_auth
    def get_properties(self, offset=0, limit=100, filters: dict | None = None) -> list[Property]:
        """
        Retrieves a list of property associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).
            filters (dict, optional): Dynamic query filters keyed by property and
                condition.

        Returns:
            A list of Property instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getProperties(self.id, offset, limit, filters)
        # types = [
        #     Property._from_api(self._apiEndpoints, data | {"space_id": self.id})
        #     for data in response.get("data", [])
        # ]

        types = []
        for data in response.get("data", []):
            prop = Property._from_api(self._apiEndpoints, data | {"space_id": self.id})
            types.append(prop)

        self._all_types = types
        return types

    @requires_auth
    def create_property(self, prop: Property) -> Property:
        object_data = {
            "name": prop.name,
            "format": prop.format,
        }
        if prop.key:
            object_data["key"] = prop.key
        if hasattr(prop, "options"):
            object_data["options"] = prop.options
        response = self._apiEndpoints.createProperty(self.id, object_data)
        return self.get_property(response["key"])

    @requires_auth
    def get_property(self, prop: str | Property) -> Property:
        if isinstance(prop, Property):
            propertyId = prop.key or prop.id
        else:
            propertyId = prop

        response = self._apiEndpoints.getProperty(self.id, propertyId)
        data = response.get("property", response)
        prop = Property._from_api(self._apiEndpoints, data | {"space_id": self.id})
        return prop

    def get_property_bykey(self, key):
        return self.get_property(key)

    @requires_auth
    def search(self, query="", type=None, offset=0, limit=100, *, filters=None, filter=None,
               sorts=None, fields=None):
        data = {"query": query}
        if type is not None:
            if isinstance(type, list):
                if len(type) != 1:
                    raise ValueError("Use the type filter for searches across multiple types")
                type = type[0]
            data["type"] = type.key if isinstance(type, Type) else type
        for key, value in (("filters", filters), ("filter", filter), ("sorts", sorts), ("fields", fields)):
            if value is not None:
                data[key] = value
        response = self._apiEndpoints.search(self.id, data, offset, limit)
        return [Object._from_api(self._apiEndpoints, row | {"space_id": self.id})
                for row in response.get("data", [])]

    def __repr__(self):
        return f"<Space(name={self.name})>"
