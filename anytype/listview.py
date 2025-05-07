from .api import apiEndpoints, APIWrapper
from .object import Object
from .utils import requires_auth


class ListView(APIWrapper):
    def __init__(self):
        self._apiEndpoints: apiEndpoints | None = None
        self.space_id = ""
        self.list_id = ""
        self.id = ""
        self.name = ""

    @requires_auth
    def get_objectsinlistview(self, offset=0, limit=100):
        response = self._apiEndpoints.getObjectsInList(
            self.space_id, self.list_id, self.id, offset, limit
        )

        return [Object._from_api(self._apiEndpoints, data) for data in response.get("data", [])]

    @requires_auth
    def add_objectsinlistview(self, objs: list[Object]) -> None:
        id_lists = [obj.id for obj in objs]
        self._apiEndpoints.addObjectsToList(self.space_id, self.list_id, id_lists)

    @requires_auth
    def delete_objectinlistview(self, obj: Object) -> None:
        self._apiEndpoints.deleteObjectsFromList(self.space_id, self.list_id, obj.id)

    def __repr__(self):
        return f"<ListView(name={self.name})>"
