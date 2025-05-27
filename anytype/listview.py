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
        """
        Retrieve a list of objects displayed in the current list view.

        Sends a request to the API to fetch objects from a specific list view within a space,
        using pagination parameters.

        Parameters:
            offset (int, optional): The starting index for pagination. Defaults to 0.
            limit (int, optional): The maximum number of objects to retrieve. Defaults to 100.

        Returns:
            list[Object]: A list of Object instances parsed from the API response.
        """
        response = self._apiEndpoints.getObjectsInList(
            self.space_id, self.list_id, self.id, offset, limit
        )

        return [Object._from_api(self._apiEndpoints, data) for data in response.get("data", [])]

    def add_objectinlistview(self, obj: Object) -> None:
        """
        Add a one object to the current list view.

        This method assumes the object are already created and adds them to the
        current list view context in the space.

        Parameters:
            obj Object: One Object instances to be added to the list view.

        Returns:
            None

        Raises:
            Exception: If the API call to add objects to the list view fails.
        """
        self.add_objectsinlistview([obj])

    @requires_auth
    def add_objectsinlistview(self, objs: list[Object]) -> None:
        """
        Add a list of objects to the current list view.

        This method assumes the objects are already created and adds them to the
        current list view context in the space.

        Parameters:
            objs (list[Object]): A list of Object instances to be added to the list view.

        Returns:
            None

        Raises:
            Exception: If the API call to add objects to the list view fails.
        """
        id_lists = [obj.id for obj in objs]
        payload = {"objects": id_lists}
        response = self._apiEndpoints.addObjectsToList(self.space_id, self.list_id, payload)
        # TODO: implement

    @requires_auth
    def delete_objectinlistview(self, obj: Object | str) -> None:
        """
        Remove an object from the current list view.

        This does not delete the object from the space, only removes its association
        with the specific list view.

        Parameters:
            obj (Object): The Object instance to be removed from the list view.

        Returns:
            None

        Raises:
            Exception: If the API call to remove the object from the list view fails.
        """
        if isinstance(obj, Object):
            objId = obj.id
        else:
            objId = obj
        assert objId != ""
        self._apiEndpoints.deleteObjectsFromList(self.space_id, self.list_id, objId)

    def __repr__(self):
        return f"<ListView(name={self.name})>"
