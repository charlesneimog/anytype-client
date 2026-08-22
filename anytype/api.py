from datetime import datetime
from os import PathLike
from pathlib import Path
from typing import TypeVar, Type

import requests

from .utils import _ANYTYPE_SYSTEM_RELATIONS

MIN_API_VERSION = "2025-11-08"
MIN_REQUIRED_VERSION = datetime(2025, 11, 8).date()
API_CONFIG = {
    "apiUrl": "http://localhost:31009/v1",
    "apiAppName": "PythonClient",
}


class ResponseHasError(Exception):
    """Custom exception for API errors."""

    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code
        try:
            payload = response.json()
        except (TypeError, ValueError):
            payload = None

        if isinstance(payload, dict):
            self.code = payload.get("code")
            message = payload.get("message") or f"Anytype API returned HTTP {self.status_code}"
        else:
            self.code = None
            message = str(payload) if payload else f"Anytype API returned HTTP {self.status_code}"

        super().__init__(message)


class apiEndpoints:
    def __init__(self, headers: dict | None = None):
        self.space_id = ""
        self.api_url = API_CONFIG["apiUrl"].rstrip("/")
        self.app_name = API_CONFIG["apiAppName"]
        headers = dict(headers or {})
        if "Anytype-Version" not in headers:
            headers["Anytype-Version"] = MIN_API_VERSION
        self.headers = headers

    @staticmethod
    def _pagination_params(offset=0, limit=100, filters=None):
        params = dict(filters or {})
        params.update({"offset": offset, "limit": limit})
        return params

    def _request(self, method, path, params=None, json=None, files=None):
        url = f"{self.api_url}{path}"
        headers = dict(self.headers)
        if files is not None:
            # requests must generate the multipart boundary itself.
            for key in list(headers):
                if key.lower() == "content-type":
                    headers.pop(key)

        response = requests.request(
            method,
            url,
            headers=headers,
            json=json,
            params=params,
            files=files,
        )
        if not 200 <= response.status_code < 300:
            raise ResponseHasError(response)

        version_str = response.headers.get("Anytype-Version")
        if version_str:
            try:
                version_date = datetime.strptime(version_str, "%Y-%m-%d").date()
            except ValueError as error:
                raise ValueError(
                    f"Invalid Anytype-Version response header: {version_str}"
                ) from error
            if version_date < MIN_REQUIRED_VERSION:
                raise ValueError(f"Anytype API version is too old: {version_str}")
        else:
            raise ValueError("Anytype-Version header not found, probably anytype is too old")

        if response.status_code == 204 or not response.content:
            return None
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
        options = self._pagination_params(offset, limit)
        return self._request("GET", f"/spaces/{spaceId}/lists/{listId}/views", params=options)

    def getObjectsInList(self, spaceId: str, listId: str, viewId: str, offset: int, limit: int):
        options = self._pagination_params(offset, limit)
        return self._request(
            "GET",
            f"/spaces/{spaceId}/lists/{listId}/views/{viewId}/objects",
            params=options,
        )

    def addObjectsToList(self, spaceId: str, listId: str, object_ids: list[str] | dict):
        payload = object_ids if isinstance(object_ids, dict) else {"objects": object_ids}
        return self._request("POST", f"/spaces/{spaceId}/lists/{listId}/objects", json=payload)

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

    def getObjects(self, spaceId: str, offset=0, limit=100, filters: dict | None = None):
        options = self._pagination_params(offset, limit, filters)
        return self._request("GET", f"/spaces/{spaceId}/objects", params=options)

    # --- search ---
    def globalSearch(
        self,
        query: str = "",
        offset=0,
        limit=100,
        types: list[str] | None = None,
        sort: dict | None = None,
        filters: dict | None = None,
    ):
        options = self._pagination_params(offset, limit)
        payload = {"query": query}
        if types is not None:
            payload["types"] = types
        if sort is not None:
            payload["sort"] = sort
        if filters is not None:
            payload["filters"] = filters
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

    def getSpaces(self, offset=0, limit=100, filters: dict | None = None):
        options = self._pagination_params(offset, limit, filters)
        return self._request("GET", "/spaces", params=options)

    # --- chats ---
    def getChats(self, spaceId: str, offset=0, limit=100, filters: dict | None = None):
        options = self._pagination_params(offset, limit, filters)
        return self._request("GET", f"/spaces/{spaceId}/chats", params=options)

    # --- files ---
    def uploadFile(self, spaceId: str, file):
        if isinstance(file, (str, PathLike)):
            path = Path(file)
            with path.open("rb") as handle:
                return self._request(
                    "POST",
                    f"/spaces/{spaceId}/files",
                    files={"file": (path.name, handle)},
                )
        return self._request("POST", f"/spaces/{spaceId}/files", files={"file": file})

    # --- members ---
    def getMember(self, spaceId: str, objectId: str):
        return self._request("GET", f"/spaces/{spaceId}/members/{objectId}")

    def getMembers(
        self, spaceId: str, offset: int = 0, limit: int = 100, filters: dict | None = None
    ):
        options = self._pagination_params(offset, limit, filters)
        return self._request("GET", f"/spaces/{spaceId}/members", params=options)

    # --- types ---
    def getType(self, spaceId: str, typeId: str):
        return self._request("GET", f"/spaces/{spaceId}/types/{typeId}")

    def getTypes(
        self, spaceId: str, offset: int = 0, limit: int = 100, filters: dict | None = None
    ):
        options = self._pagination_params(offset, limit, filters)
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

    def getTemplates(
        self,
        spaceId: str,
        typeId: str,
        offset: int = 0,
        limit: int = 100,
        filters: dict | None = None,
    ):
        options = self._pagination_params(offset, limit, filters)
        return self._request("GET", f"/spaces/{spaceId}/types/{typeId}/templates", params=options)

    # --- Property ---
    def getProperties(
        self, spaceId: str, offset: int = 0, limit: int = 100, filters: dict | None = None
    ):
        options = self._pagination_params(offset, limit, filters)
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
    def getTags(
        self,
        spaceId: str,
        propertyId: str,
        offset: int = 0,
        limit: int = 100,
        filters: dict | None = None,
    ):
        options = self._pagination_params(offset, limit, filters)
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
    space_id = ""

    @classmethod
    def _from_api(cls: Type[T], api: apiEndpoints, data: dict) -> T:
        instance = cls()
        instance._apiEndpoints = api
        instance._json = data
        if "space_id" in data:
            instance.space_id = data["space_id"]
        instance._add_attrs_from_dict(data)
        return instance

    def _add_attrs_from_dict(self, data: dict) -> None:
        for key, value in data.items():
            if value is None:
                continue

            if key == "type":
                from anytype import type

                setattr(
                    self,
                    key,
                    type.Type()._from_api(self._apiEndpoints, value | {"space_id": self.space_id}),
                )
            elif key == "properties":
                from anytype import property

                properties = {}
                for property_value in value:
                    property_id = property_value.get("id")
                    if property_id:
                        response = self._apiEndpoints.getProperty(self.space_id, property_id)
                        definition = response.get("property", {})
                    else:
                        definition = {}

                    prop = property.Property._from_api(
                        self._apiEndpoints,
                        definition | property_value | {"space_id": self.space_id},
                    )

                    if prop.key in _ANYTYPE_SYSTEM_RELATIONS:
                        continue

                    properties[prop.name] = prop

                setattr(self, key, properties)
            else:
                setattr(self, key, value)
