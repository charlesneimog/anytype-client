from copy import deepcopy

from .type import Type
from .object import Object
from .member import Member
from .error import ResponseHasError
from .icon import Icon
from .api import apiEndpoints


class Space:
    def __init__(self):
        self._headers = {}
        self._apiEndpoints: apiEndpoints | None = None
        self.name = ""
        self.id = ""
        self._all_types = []

    def get_object(self, objectId: str) -> Object:
        if self._apiEndpoints is None:
            raise Exception("You need to auth first")
        response_data = self._apiEndpoints.getObject(self.id, objectId)
        obj = Object()
        obj._apiEndpoints = self._apiEndpoints
        for key, value in response_data.get("object", {}).items():
            obj.__dict__[key] = value
        return obj

    def get_objects(self, offset=0, limit=100) -> list[Object]:
        if self._apiEndpoints is None:
            raise Exception("You need to auth first")
        response_data = self._apiEndpoints.getObjects(self.id, offset, limit)
        results = []
        for data in response_data.get("data", []):
            new_item = Object()
            new_item._apiEndpoints = self._apiEndpoints
            for key, value in data.items():
                new_item.__dict__[key] = value
            results.append(new_item)
        self._all_types = results
        return results

    def get_types(self, offset=0, limit=100) -> list[Type]:
        if self._apiEndpoints is None:
            raise Exception("You need to auth first")

        response_data = self._apiEndpoints.getTypes(self.id, offset, limit)
        results = []
        for data in response_data.get("data", []):
            new_item = Type()
            new_item._headers = self._headers
            new_item.space_id = self.id
            for key, value in data.items():
                new_item.__dict__[key] = value
            results.append(new_item)
        self._all_types = results
        return results

    def get_members(self, offset: int = 0, limit: int = 100) -> list[Member]:
        if self._apiEndpoints is None:
            raise Exception("You need to auth first")
        response_data = self._apiEndpoints.getMembers(self.id, offset, limit)
        results = []
        for data in response_data.get("data", []):
            new_item = Member()
            new_item._headers = self._headers
            for key, value in data.items():
                new_item.__dict__[key] = value
            results.append(new_item)
        return results

    def get_type(self, type_name: str) -> Type:
        if len(self._all_types) == 0:
            self._all_types = self.get_types()
        for type in self._all_types:
            if type.name == type_name:
                return type
        raise ValueError("Type not found")

    def search(self, query, offset=0, limit=10) -> list[Object]:
        if self._apiEndpoints is None:
            raise Exception("You need to auth first")

        if self.id == "":
            raise ValueError("Space ID is required")

        response = self._apiEndpoints.search(self.id, query, offset, limit)
        results = []
        for data in response.get("data", []):
            new_item = Object()
            new_item._apiEndpoints = self._apiEndpoints
            for key, value in data.items():
                new_item.__dict__[key] = value
            results.append(new_item)

        return results

    def create_object(self, obj: Object, type: Type) -> Object:
        if self._apiEndpoints is None:
            raise Exception("You need to auth first")
        icon = {}
        if isinstance(obj.icon, Icon):
            icon = obj.icon._get_json()
        else:
            raise ValueError("Invalid icon type")

        object_data = {
            "icon": icon,
            "name": obj.name,
            "description": obj.description,
            "body": obj.body,
            "source": "",
            "template_id": type.template_id,
            "type_key": type.key,
        }

        obj_clone = deepcopy(obj)
        obj_clone._apiEndpoints = self._apiEndpoints
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

    def __repr__(self):
        return f"<Space(name={self.name})>"
