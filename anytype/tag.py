from .api import APIWrapper
from .utils import requires_auth


class Tag(APIWrapper):
    def __init__(self):
        self.space_id: str = ""
        self._property_id: str = ""
        self.color: str = ""
        self.name: str = ""
        self.id: str = ""
        self.key: str = ""

    @requires_auth
    def update_tag(self, name: str, color: str = "red"):
        """
        Updates the name of an existing tag.
        Parameters:
            tag_id (str): The ID of the tag to update.
            name (str): The new name for the tag.
        Returns:
            A Tag instance representing the updated tag.
        Raises:
            Raises an error if the request to the API fails.
        """
        data = {"name": name, "color": color}
        response = self._apiEndpoints.updateTag(self.space_id, self._property_id, self.id, data)
        tag = Tag._from_api(self._apiEndpoints, response.get("tag", []))
        return tag

    @requires_auth
    def delete_tag(self) -> None:
        """
        Deletes a tag by its ID.

        Parameters:
            tag_id (str): The ID of the tag to delete.

        Returns:
            bool: True if the tag was successfully deleted, False otherwise.

        Raises:
            Raises an error if the request to the API fails.
        """
        _ = self._apiEndpoints.deleteTag(self.space_id, self._property_id, self.id)

    def __repr__(self):
        return f"<Tag(name={self.name})>"
