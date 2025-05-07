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
    def get_object(self, objectId: str) -> Object:
        """
        Retrieves a specific object by its ID.

        Parameters:
            objectId (str): The ID of the object to retrieve.

        Returns:
            An Object instance representing the retrieved object.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getObject(self.id, objectId)
        data = response.get("object", {})
        return Object._from_api(self._apiEndpoints, data)

    @requires_auth
    def delete_object(self, objectId: str) -> None:
        # BUG: not working yet
        self._apiEndpoints.deleteObject(self.id, objectId)

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
        response = self._apiEndpoints.updateObject(self.id, obj.id, data)
        data = response.get("object", {})
        return Object._from_api(self._apiEndpoints, data)

    @requires_auth
    def create_object(self, obj: Object, type: Type = Type()) -> Object:
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
            type = obj.type

        if type.key == "" and obj.type_key == "":
            raise Exception(
                "You need to set one type for the object, use add_type method from the Object class"
            )

        type_key = obj.type_key if obj.type_key != "" else type.key
        template_id = obj.template_id if obj.template_id != "" else type.template_id

        icon = {}
        if isinstance(obj.icon, Icon):
            icon = obj.icon._get_json()
        else:
            raise ValueError("Invalid icon type")

        properties = []
        if isinstance(obj.properties, list):
            properties = [prop._get_json() for prop in obj.properties]
        else:
            raise ValueError("Invalid properties type")

        object_data = {
            "icon": icon,
            "name": obj.name,
            "description": obj.description,
            "body": obj.body,
            "source": "",
            "template_id": template_id,
            "type_key": type_key,
            "properties": properties,
        }

        obj_clone = deepcopy(obj)
        obj_clone._apiEndpoints = self._apiEndpoints
        obj_clone.space_id = self.id

        response = self._apiEndpoints.createObject(self.id, object_data)

        for key, value in response.get("object", {}).items():
            if key == "icon":
                icon = Icon()
                icon._update_with_json(value)
            else:
                obj_clone.__dict__[key] = value
        return obj_clone

    @requires_auth
    def get_type(self, typeId: str) -> Type:
        """
        Retrieves a specific type by its ID.

        Parameters:
            type_name (str): The name of the type to retrieve.

        Returns:
            A Type instance representing the type.

        Raises:
            ValueError: If the type with the specified name is not found.
        """
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
        all_types = self.get_types(limit=200)
        for type in all_types:
            if type.name == name:
                return type

        raise ValueError("Type not found")

    @requires_auth
    def get_member(self, memberId: str) -> Member:
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

    def get_listviewfromobject(
        self, obj: Object, offset: int = 0, limit: int = 100
    ) -> list[ListView]:
        if obj.type != "Collection":
            raise ValueError("Object is not a collection")
        return self.get_listviews(obj.id, offset, limit)

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
        types = [
            Property._from_api(self._apiEndpoints, data | {"space_id": self.id})
            for data in response.get("data", [])
        ]

        self._all_types = types
        return types

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
    def search(self, query, offset=0, limit=10) -> list[Object]:
        """
        Performs a search for objects in the space using a query string.

        Parameters:
            query (str): The search query string.
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 10).

        Returns:
            A list of Object instances that match the search query.

        Raises:
            ValueError: If the space ID is not set.
        """
        if self.id == "":
            raise ValueError("Space ID is required")

        response = self._apiEndpoints.search(self.id, query, offset, limit)
        return [Object._from_api(self._apiEndpoints, data) for data in response.get("data", [])]

    def __repr__(self):
        return f"<Space(name={self.name})>"
