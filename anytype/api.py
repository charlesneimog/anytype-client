import requests
from datetime import datetime
from typing import TypeVar, Type

MIN_API_VERSION = "2025-05-20"
MIN_REQUIRED_VERSION = datetime(2025, 4, 22).date()
API_CONFIG = {
    "apiUrl": "http://localhost:31009/v1",
    "apiAppName": "PythonClient",
}


class ResponseHasError(Exception):
    """Custom exception for API errors."""

    def __init__(self, response):
        self.status_code = response.status_code
        if self.status_code != 200 and self.status_code != 201:
            raise ValueError(response.json()["message"])


class apiEndpoints:
    def __init__(self, headers: dict = {}):
        self.api_url = API_CONFIG["apiUrl"].rstrip("/")
        self.app_name = API_CONFIG["apiAppName"]
        if "Anytype-Version" not in headers:
            headers["Anytype-Version"] = MIN_API_VERSION
        self.headers = headers

    def _request(self, method, path, params=None, json=None):
        url = f"{self.api_url}{path}"
        response = requests.request(method, url, headers=self.headers, json=json, params=params)
        version_str = response.headers.get("Anytype-Version")
        if version_str:
            version_date = datetime.strptime(version_str, "%Y-%m-%d").date()
            if version_date < MIN_REQUIRED_VERSION:
                raise Exception("❌ Version is too old:", version_date)
        else:
            raise ValueError("Anytype-Version header not found, probably anytype is too old")

        ResponseHasError(response)
        return response.json()

    # --- auth ---
    def displayCode(self):
        return self._request("POST", "/auth/challenges", json={"app_name": self.app_name})

    def getToken(self, challengeId: str, code: str):
        return self._request(
            "POST",
            "/auth/api_keys",
            json={"challenge_id": challengeId, "code": code},
        )

    # --- lists ---
    def getListViews(self, spaceId: str, listId: str, offset: int, limit: int):
        options = {"offset": offset, "limit": limit}
        return self._request("GET", f"/spaces/{spaceId}/lists/{listId}/views", params=options)

    def getObjectsInList(self, spaceId: str, listId: str, viewId: str, offset: int, limit: int):
        options = {"offset": offset, "limit": limit}
        return self._request(
            "GET",
            f"/spaces/{spaceId}/lists/{listId}/views/{viewId}/objects",
            params=options,
        )

    def addObjectsToList(self, spaceId: str, listId: str, object_ids: dict):
        return self._request("POST", f"/spaces/{spaceId}/lists/{listId}/objects", json=object_ids)

    def deleteObjectsFromList(self, spaceId: str, listId: str, objectId: str):
        return self._request("DELETE", f"/spaces/{spaceId}/lists/{listId}/objects/{objectId}")

    # --- objects ---
    def createObject(self, spaceId: str, data: dict):
        return self._request("POST", f"/spaces/{spaceId}/objects", json=data)

    def updateObject(self, spaceId: str, objectId: str, data: dict):
        return self._request("PATCH", f"/spaces/{spaceId}/objects/{objectId}", json=data)

    def deleteObject(self, spaceId: str, objectId: str):
        return self._request("DELETE", f"/spaces/{spaceId}/objects/{objectId}")

    def getObject(self, spaceId: str, objectId: str):
        return self._request("GET", f"/spaces/{spaceId}/objects/{objectId}")

    def getObjects(self, spaceId: str, offset=0, limit=10):
        options = {"offset": offset, "limit": limit}
        return self._request("GET", f"/spaces/{spaceId}/objects", params=options)

    # --- search ---
    def globalSearch(self, query: str = "", offset=0, limit=10):
        options = {"offset": offset, "limit": limit}
        payload = {"query": query}
        return self._request("POST", "/search", params=options, json=payload)

    def search(self, spaceId: str, data: dict, offset: int = 0, limit: int = 10):
        options = {"offset": offset, "limit": limit}
        return self._request("POST", f"/spaces/{spaceId}/search", params=options, json=data)

    # TODO: PATCH("/spaces/:space_id")
    def updateSpace(self, spaceId: str, data: dict):
        return self._request("PATCH", f"/spaces/{spaceId}", json=data)

    # --- spaces ---
    def createSpace(self, name):
        data = {"name": name}
        return self._request("POST", "/spaces", json=data)

    def getSpace(self, spaceId: str):
        return self._request("GET", f"/spaces/{spaceId}")

    def getSpaces(self, offset=0, limit=10):
        options = {"offset": offset, "limit": limit}
        return self._request("GET", "/spaces", params=options)

    # --- members ---
    def getMember(self, spaceId: str, objectId: str):
        return self._request("GET", f"/spaces/{spaceId}/members/{objectId}")

    def getMembers(self, spaceId: str, offset: int, limit: int):
        options = {"offset": offset, "limit": limit}
        return self._request("GET", f"/spaces/{spaceId}/members", params=options)

    # --- types ---
    def getType(self, spaceId: str, typeId: str):
        return self._request("GET", f"/spaces/{spaceId}/types/{typeId}")

    def getTypes(self, spaceId: str, offset: int, limit: int):
        options = {"offset": offset, "limit": limit}
        return self._request("GET", f"/spaces/{spaceId}/types", params=options)

    def createType(self, spaceId: str, data: dict):
        return self._request("POST", f"/spaces/{spaceId}/types", json=data)

    def updateType(self, spaceId: str, typeId: str, data: dict):
        return self._request("PATCH", f"/spaces/{spaceId}/types/{typeId}", json=data)

    def deleteType(self, spaceId: str, typeId: str):
        return self._request("DELETE", f"/spaces/{spaceId}/types/{typeId}")

    # --- templates ---
    def getTemplate(self, spaceId: str, typeId: str, templateId: str):
        return self._request("GET", f"/spaces/{spaceId}/types/{typeId}/templates/{templateId}")

    def getTemplates(self, spaceId: str, typeId: str, offset: int, limit: int):
        options = {"offset": offset, "limit": limit}
        return self._request("GET", f"/spaces/{spaceId}/types/{typeId}/templates", params=options)

    # --- Property ---
    def getProperties(self, spaceId: str, offset: int = 0, limit: int = 10):
        options = {"offset": offset, "limit": limit}
        return self._request("GET", f"/spaces/{spaceId}/properties", params=options)

    def getProperty(self, spaceId: str, propertyId: str):
        return self._request("GET", f"/spaces/{spaceId}/properties/{propertyId}")

    def createProperty(self, spaceId: str, data: dict):
        return self._request("POST", f"/spaces/{spaceId}/properties", json=data)

    def updateProperty(self, spaceId: str, propertyId: str, data: dict):
        return self._request("PATCH", f"/spaces/{spaceId}/properties/{propertyId}", json=data)

    def deleteProperty(self, spaceId: str, propertyId: str):
        return self._request("DELETE", f"/spaces/{spaceId}/properties/{propertyId}")

    # --- tag ---
    def getTags(self, spaceId: str, propertyId: str, offset: int = 0, limit: int = 10):
        options = {"offset": offset, "limit": limit}
        return self._request(
            "GET", f"/spaces/{spaceId}/properties/{propertyId}/tags", params=options
        )

    def getTag(self, spaceId: str, propertyId: str, tagId: str):
        return self._request("GET", f"/spaces/{spaceId}/properties/{propertyId}/tags/{tagId}")

    def createTag(self, spaceId: str, propertyId: str, data: dict):
        return self._request("POST", f"/spaces/{spaceId}/properties/{propertyId}/tags", json=data)

    def updateTag(self, spaceId: str, propertyId: str, tagId: str, data: dict):
        return self._request(
            "PATCH", f"/spaces/{spaceId}/properties/{propertyId}/tags/{tagId}", json=data
        )

    def deleteTag(self, spaceId: str, propertyId: str, tagId: str):
        return self._request("DELETE", f"/spaces/{spaceId}/properties/{propertyId}/tags/{tagId}")


T = TypeVar("T", bound="APIWrapper")


class APIWrapper:
    __slots__ = ()
    _apiEndpoints: apiEndpoints | None = None
    _json: dict | None = None

    @classmethod
    def _from_api(cls: Type[T], api: apiEndpoints, data: dict) -> T:
        instance = cls()
        instance._apiEndpoints = api
        instance._json = data
        instance._add_attrs_from_dict(data)
        return instance

    def _add_attrs_from_dict(self, data: dict) -> None:
        for key, value in data.items():
            setattr(self, key, value)
