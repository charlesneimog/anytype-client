from copy import deepcopy

from .listview import ListView
from .type import Type
from .object import Object
from .member import Member
from .icon import Icon
from .api import apiEndpoints, APIWrapper
from .utils import requires_auth
from .property import PropertyFormat, Property


class Space(APIWrapper):
    """
    Used to interact with and manage objects, types, and other elements within a specific Space. It provides methods to retrieve objects, types, and perform search operations within the space. Additionally, it allows creating new objects associated with specific types.
    """

    def __init__(self):
        self._apiEndpoints: apiEndpoints | None = None
        self.name = ""
        self.id = ""
        self._all_types = []

    @requires_auth
    def _object_to_dict(self, obj: Object) -> dict:
        if obj.type is None:
            raise Exception(
                "You need to set one type for the object, use add_type method from the Object class"
            )
        if type(obj.type) is dict:
            obj.type = Type._from_api(self._apiEndpoints, obj.type)

        if obj.type.key == "":
            raise Exception(
                "Type has an invalid key, please retrieve it from the API to get a valid type"
            )

        type_key = obj.type_key if obj.type_key != "" else obj.type.key
        template_id = obj.template_id if obj.template_id != "" else obj.type.template_id
        icon_json = {}
        if isinstance(obj.icon, Icon):
            icon_json = obj.icon._get_json()
        else:
            raise ValueError("Invalid icon type")

        properties_json: list[dict] = [{}]
        if isinstance(obj.type.properties, list):
            properties_json = [prop._get_json() for prop in obj.type.properties]
        else:
            raise ValueError("Invalid properties type")

        object_data = {
            "icon": icon_json,
            "name": obj.name,
            "description": obj.description,
            "body": obj.body,
            "source": "",
            "template_id": template_id,
            "type_key": type_key,
            "properties": properties_json,
        }
        return object_data

    @requires_auth
    def get_objects(self, offset=0, limit=100) -> list[Object]:
        """
        Retrieves a list of objects associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).

        Returns:
            A list of Object instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response_data = self._apiEndpoints.getObjects(self.id, offset, limit)
        objects = [
            Object._from_api(self._apiEndpoints, data) for data in response_data.get("data", [])
        ]

        return objects

    @requires_auth
    def get_object(self, obj: str | Object) -> Object:
        """
        Retrieves a specific object by its ID.

        Parameters:
            object (Object | str): The object (or its ID) to retrieve.

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
        data = response.get("object", {})
        return Object._from_api(self._apiEndpoints, data)

    @requires_auth
    def create_object(self, obj: Object, type: Type | None = None) -> Object:
        """
        Creates a new object within the space, associated with a specified type.

        Parameters:
            obj (Object): The Object instance to create.
            type (Type): The Type instance to associate the object with.

        Returns:
            A new Object instance representing the created object.

        Raises:
            Raises an error if the request to the API fails.
        """
        if obj.type is None and type is not None:
            obj.type = type

        obj_clone = deepcopy(obj)
        obj_clone._apiEndpoints = self._apiEndpoints
        obj_clone.space_id = self.id
        object_data = self._object_to_dict(obj)

        response = self._apiEndpoints.createObject(self.id, object_data)

        for key, value in response.get("object", {}).items():
            setattr(obj_clone, key, value)
        return obj_clone

    @requires_auth
    def update_object(self, obj: Object) -> Object:
        """
        Updates an existing object within the space.

        Parameters:
            objectId (str): The ID of the object to update.
            data (dict): The data to update the object with.

        Returns:
            An Object instance representing the updated object.

        Raises:
            Raises an error if the request to the API fails.
        """
        data = self._object_to_dict(obj)
        response = self._apiEndpoints.updateObject(self.id, obj.id, data)
        data = response.get("object", {})
        return Object._from_api(self._apiEndpoints, data)

    @requires_auth
    def delete_object(self, obj: str | Object) -> None:
        """
        Attempt to delete an object by its unique identifier.

        Parameters:
            objectId (Object | str): The Object or object ID string to delete.

        Returns:
            None

        Raises:
            Exception: If the request to delete the object fails.

        """
        if isinstance(obj, Object):
            obj = obj.id
        self._apiEndpoints.deleteObject(self.id, obj)

    @requires_auth
    def create_type(self, type: Type) -> Type:
        """
        Create a new type within the current space.

        This function validates the `Type` instance, ensures all required fields are
        present (icon, layout, name, plural_name), and resolves all referenced
        properties—creating them if they don't already exist.

        Parameters:
            type (Type): The Type instance to be created, including its properties.

        Returns:
            Type: The created Type instance as returned by the API.

        Raises:
            Exception: If any of the required fields (icon, layout, name, plural_name)
                       are missing.
            ValueError: If a property has an invalid or unrecognized format.
        """

        if not type.icon or not type.layout or not type.name or not type.plural_name:
            raise Exception("Please define icon, layout, name and plural_name")

        defined_props = []
        all_props = self.get_properties(offset=0, limit=200)
        for prop in type.properties:
            prop_name = prop.name if isinstance(prop, Property) else prop["name"]
            prop_format = prop.format if isinstance(prop, Property) else prop["format"]
            exists = False
            for any_prop in all_props:
                if any_prop.name == prop_name:
                    exists = True
                    prop = any_prop

            if not exists:
                prop = self.create_property(prop_name, prop_format)

            if isinstance(prop, Property):
                defined_props.append(prop._json)
            elif isinstance(prop, dict):
                defined_props.append(prop)
            else:
                raise ValueError("Invalid prop type, this should not happen, please report!")

        icon = type.icon._get_json()
        data = {
            "name": type.name,
            "plural_name": type.plural_name,
            "icon": icon,
            "layout": type.layout,
            "properties": defined_props,
        }
        response = self._apiEndpoints.createType(self.id, data)
        type = Type._from_api(self._apiEndpoints, response.get("type", {}) | {"space_id": self.id})
        return type

    @requires_auth
    def update_type(self, type: Type) -> Type:
        """
        Update an existing type within the current space.

        This function updates the specified `Type` instance, including its metadata and properties.
        It ensures the type exists, validates the provided fields, and updates any referenced
        properties as needed.

        Parameters:
            type (Type): The Type instance to be updated. Must include a valid `id`.

        Returns:
            Type: The updated Type instance as returned by the API.

        Raises:
            Exception: If the type does not exist, the ID is missing, or an API error occurs.
            ValueError: If any updated fields or properties are invalid or unrecognized.
        """
        if not type.icon or not type.layout or not type.name or not type.plural_name:
            raise Exception("Please define icon, layout, name and plural_name")

        defined_props = []
        all_props = self.get_properties(offset=0, limit=200)
        for prop in type.properties:
            prop_name = prop.name if isinstance(prop, Property) else prop["name"]
            prop_format = prop.format if isinstance(prop, Property) else prop["format"]
            exists = False
            for any_prop in all_props:
                if any_prop.name == prop_name:
                    exists = True
                    prop = any_prop

            if not exists:
                prop = self.create_property(prop_name, prop_format)
                pass

            if isinstance(prop, Property):
                defined_props.append(prop._json)
            elif isinstance(prop, dict):
                defined_props.append(prop)
            else:
                raise ValueError("Invalid prop type, this should not happen, please report!")

        icon = type.icon._get_json()
        data = {
            "name": type.name,
            "plural_name": type.plural_name,
            "icon": icon,
            "layout": type.layout,
            "properties": defined_props,
        }
        response = self._apiEndpoints.updateType(self.id, type.id, data)
        type = Type._from_api(self._apiEndpoints, response.get("type", {}) | {"space_id": self.id})
        return type

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
            typeId = type.id
        else:
            typeId = type
        _ = self._apiEndpoints.deleteType(self.id, typeId)

    @requires_auth
    def get_type(self, type: str | Type) -> Type:
        """
        Retrieves a specific type by its ID.

        Parameters:
            type_name (str): The name of the type to retrieve.

        Returns:
            A Type instance representing the type.

        Raises:
            ValueError: If the type with the specified name is not found.
        """
        if isinstance(type, Type):
            typeId = type.id
        else:
            typeId = type

        response = self._apiEndpoints.getType(self.id, typeId)
        data = response.get("type", {})
        # TODO: Sometimes we need to add more attributes beyond the ones in the
        # API response. There might be a cleaner way to do this, but doing
        # a dict merge with | works for now.
        return Type._from_api(self._apiEndpoints, data | {"space_id": self.id})

    @requires_auth
    def get_types(self, offset=0, limit=100) -> list[Type]:
        """
        Retrieves a list of types associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).

        Returns:
            A list of Type instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getTypes(self.id, offset, limit)
        types = [
            Type._from_api(self._apiEndpoints, data | {"space_id": self.id})
            for data in response.get("data", [])
        ]
        return types

    def get_type_byname(self, name: str) -> Type:
        offset = 0
        limit = 5
        while True:
            types = self.get_types(offset=offset, limit=limit)
            type_len = len(types)
            for type in types:
                if type.name == name:
                    return type
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
        data = response.get("object", {})
        return Member._from_api(self._apiEndpoints, data)

    @requires_auth
    def get_members(self, offset: int = 0, limit: int = 100) -> list[Member]:
        """
        Retrieves a list of members associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).

        Returns:
            A list of Member instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getMembers(self.id, offset, limit)
        return [Member._from_api(self._apiEndpoints, data) for data in response.get("data", [])]

    @requires_auth
    def get_listviews(
        self, listId: str | Object | Type, offset: int = 0, limit: int = 100
    ) -> list[ListView]:
        if isinstance(listId, Object) or isinstance(listId, Type):
            listId = listId.id

        response = self._apiEndpoints.getListViews(self.id, listId, offset, limit)
        return [
            ListView._from_api(
                self._apiEndpoints,
                data
                | {
                    "space_id": self.id,
                    "list_id": listId,
                },
            )
            for data in response.get("data", [])
        ]

    @requires_auth
    def get_properties(self, offset=0, limit=100) -> list[Property]:
        """
        Retrieves a list of property associated with the space.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 100).

        Returns:
            A list of Property instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getProperties(self.id, offset, limit)
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
    def create_property(self, name: str, prop_format: PropertyFormat | str) -> Property:
        if isinstance(prop_format, PropertyFormat):
            prop_format = prop_format.value

        object_data = {
            "name": name,
            "format": prop_format,
        }

        response = self._apiEndpoints.createProperty(self.id, object_data)
        prop = Property._from_api(self._apiEndpoints, response.get("property", {}))
        return prop

    @requires_auth
    def get_property(self, propertyId: str) -> Property:
        response = self._apiEndpoints.getProperty(self.id, propertyId)
        data = response.get("property", {})
        prop = Property._from_api(self._apiEndpoints, data | {"space_id": self.id})
        return prop

    def get_property_bykey(self, key: str) -> Property:
        all_properties = self.get_properties(offset=0, limit=100)
        offset = 0
        limit = 50
        while True:
            for prop in all_properties:
                if prop.key == key:
                    return prop

            if len(all_properties) < 100:
                break
            else:
                all_properties = self.get_properties(offset=offset, limit=limit)
            offset += limit
            limit += 100

        # If we reach here, the property was not found
        raise ValueError("Property not found, create it using create_property method")

    @requires_auth
    def search(
        self, query, type: Type | None = None, offset: int = 0, limit: int = 10
    ) -> list[Object]:
        """
        Performs a search for objects in the space using a query string.

        Parameters:
            query (str): The search query string.
            type (Type, optional): The type to filter by.
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 10).

        Returns:
            A list of Object instances that match the search query.

        Raises:
            ValueError: If the space ID is not set.
        """
        if self.id == "":
            raise ValueError("Space ID is required")

        types = []
        if type is not None:
            types = [type.key]
        data = {
            "query": query,
            "sort": {"direction": "desc", "property_key": "last_modified_date"},
            "types": types,
        }
        response = self._apiEndpoints.search(self.id, data, offset, limit)
        return [Object._from_api(self._apiEndpoints, data) for data in response.get("data", [])]

    def __repr__(self):
        return f"<Space(name={self.name})>"
