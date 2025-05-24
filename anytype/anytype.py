import os
import json

from .space import Space
from .object import Object
from .api import apiEndpoints
from .utils import requires_auth


class Anytype:
    """
    Used to interact with the Anytype API for authentication, retrieving spaces, creating spaces, and performing global searches. It provides methods to authenticate via a token, fetch spaces, create new spaces, and search for objects across spaces.
    """

    def __init__(self) -> None:
        self.app_name = ""
        self.space_id = ""
        self.api_key = ""
        self.app_key = ""
        self._apiEndpoints: apiEndpoints | None = None
        self._headers = {}

    def auth(self, force=False, callback=None) -> None:
        """
        Authenticates the user by retrieving or creating a session token. If the session token already exists, it validates the token. If not, the user will be prompted to enter a 4-digit code for authentication.

        Parameters:
            force (bool): If True, forces re-authentication even if a token already exists.
            callback (callable): A callback function to retrieve the 4-digit code. If None, the user will be prompted to enter the code.

        Raises:
            Raises an error if the authentication request or token validation fails.
        """
        userdata = self._get_userdata_folder()
        anytoken = os.path.join(userdata, "any_token.json")

        if force and os.path.exists(anytoken):
            os.remove(anytoken)

        if self.app_name == "":
            self.app_name = "python-anytype-client"

        if os.path.exists(anytoken):
            with open(anytoken) as f:
                auth_json = json.load(f)
            self.api_key = auth_json.get("api_key")
            if self._validate_token():
                return

        # Inicializa o client de API com o nome do app
        self._apiEndpoints = apiEndpoints()
        display_code_response = self._apiEndpoints.displayCode()
        challenge_id = display_code_response.get("challenge_id")

        if callback is None:
            api_four_digit_code = input("Enter the 4 digit code: ")
        else:
            api_four_digit_code = callback()

        token_response = self._apiEndpoints.getToken(challenge_id, api_four_digit_code)

        # Salva o token localmente
        with open(anytoken, "w") as file:
            json.dump(token_response, file, indent=4)

        self.api_key = token_response.get("api_key")
        self._validate_token()

    def _validate_token(self) -> bool:
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self._apiEndpoints = apiEndpoints(self._headers)
        try:
            self._apiEndpoints.getSpaces(0, 1)
            return True
        except Exception:
            return False

    def _get_userdata_folder(self) -> str:
        userdata = os.path.join(os.path.expanduser("~"), ".anytype")
        if not os.path.exists(userdata):
            os.makedirs(userdata)
        if os.name == "nt":
            os.system(f"attrib +h {userdata}")
        return userdata

    @requires_auth
    def get_space(self, space: str | Space) -> Space:
        """
        Retrieve a specific space by its unique identifier.

        Parameters:
            spaceId (str): The unique identifier of the space to retrieve.

        Returns:
            Space: A `Space` instance representing the requested space.

        Raises:
            Exception: If the request to the API fails or the space is not found.
        """
        if isinstance(space, Space):
            spaceId = space.id
        elif isinstance(space, str):
            spaceId = space
        else:
            # not reached
            raise Exception("Invalid space type")

        response = self._apiEndpoints.getSpace(spaceId)
        data = response.get("space", {})
        return Space._from_api(self._apiEndpoints, data)

    @requires_auth
    def get_spaces(self, offset=0, limit=10) -> list[Space]:
        """
        Retrieves a list of spaces associated with the authenticated user.

        Parameters:
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 10).

        Returns:
            A list of Space instances.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getSpaces(offset, limit)
        return [Space._from_api(self._apiEndpoints, data) for data in response.get("data", [])]

    @requires_auth
    def create_space(self, name: str) -> Space:
        """
        Creates a new space with a given name.

        Parameters:
            name (str): The name of the space to create.

        Returns:
            A Space instance representing the newly created space.

        Raises:
            Raises an error if the space creation request fails.
        """
        response = self._apiEndpoints.createSpace(name)
        data = response.get("space", {})
        return Space._from_api(self._apiEndpoints, data)

    @requires_auth
    def global_search(self, query, offset=0, limit=10) -> list[Object]:
        """
        Performs a global search for objects across all spaces using a query string.

        Parameters:
            query (str): The search query string.
            offset (int, optional): The offset for pagination (default: 0).
            limit (int, optional): The limit for the number of results (default: 10).

        Returns:
            A list of Object instances that match the search query.

        Raises:
            Raises an error if the search request fails.
        """
        response = self._apiEndpoints.globalSearch(query, offset, limit)
        return [Object._from_api(self._apiEndpoints, data) for data in response.get("data", [])]
