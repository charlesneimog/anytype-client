from os import PathLike
from pathlib import Path
from typing import TypeVar, Type

import requests

from .utils import _ANYTYPE_SYSTEM_RELATIONS

API_VERSION = "v2"
API_CONFIG = {
    "apiUrl": "http://localhost:31009/v2",
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
            self.issues = payload.get("issues", [])
            message = payload.get("message") or payload.get("error") or f"Anytype API returned HTTP {self.status_code}"
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
        self.headers = headers

    @staticmethod
    def _pagination_params(offset=0, limit=100, filters=None):
        params = dict(filters or {})
        params.update({"offset": offset, "limit": limit})
        return params

    def _request(self, method, path, params=None, json=None, files=None, headers=None):
        url = f"{self.api_url}{path}"
        headers = dict(self.headers) | dict(headers or {})
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
            timeout=30,
        )
        if not 200 <= response.status_code < 300:
            raise ResponseHasError(response)

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

    # v2 collections and queries replace /lists.
    def getListViews(self, spaceId, listId, offset=0, limit=100, kind="collection"):
        return self._request("GET", f"/spaces/{spaceId}/{self._list_kind(kind)}/{listId}/views",
                             params=self._pagination_params(offset, limit))

    @staticmethod
    def _list_kind(kind):
        if kind not in ("collection", "query"):
            raise ValueError("List kind must be collection or query")
        return "collections" if kind == "collection" else "queries"

    def getObjectsInList(self, spaceId, listId, viewId=None, offset=0, limit=100,
                         kind="collection", fields=None):
        params = self._pagination_params(offset, limit)
        if viewId:
            params["view"] = viewId
        if fields:
            params["fields"] = ",".join(fields)
        return self._request("GET", f"/spaces/{spaceId}/{self._list_kind(kind)}/{listId}/objects",
                             params=params)

    def addObjectsToList(self, spaceId, listId, object_ids):
        items = object_ids["objects"] if isinstance(object_ids, dict) else object_ids
        return self.updateObject(spaceId, listId, {"ops": [{"op": "add_items", "items": items}]})

    def deleteObjectsFromList(self, spaceId, listId, objectId):
        return self.updateObject(spaceId, listId,
                                 {"ops": [{"op": "remove_items", "items": [objectId]}]})

    def createCollection(self, spaceId, data):
        return self._request("POST", f"/spaces/{spaceId}/collections", json=data)

    def createQuery(self, spaceId, data):
        return self._request("POST", f"/spaces/{spaceId}/queries", json=data)

    # --- objects ---
    def createObject(self, spaceId, data, **options):
        return self._request("POST", f"/spaces/{spaceId}/objects", json=data, params=options or None)

    def updateObject(self, spaceId, objectId, data, etag=None, **options):
        return self._request("PATCH", f"/spaces/{spaceId}/objects/{objectId}", json=data,
                             params=options or None, headers={"If-Match": etag} if etag else None)

    def deleteObject(self, spaceId, objectId):
        return self._request("DELETE", f"/spaces/{spaceId}/objects/{objectId}")

    def getObject(self, spaceId, objectId, **options):
        return self._request("GET", f"/spaces/{spaceId}/objects/{objectId}",
                             params={"ids": "full", **options})

    def getObjects(self, spaceId, offset=0, limit=100, filters=None):
        return self._request("GET", f"/spaces/{spaceId}/objects",
                             params=self._pagination_params(offset, limit, filters))

    def getSchema(self, kind):
        return self._request("GET", f"/schemas/{kind}")

    def validate(self, document):
        return self._request("POST", "/validate", json=document)

    # --- search ---
    def globalSearch(self, query="", offset=0, limit=100, types=None, sort=None,
                     filters=None, **options):
        payload = {"query": query, **options}
        if types:
            if len(types) != 1:
                raise ValueError("v2 takes one type; use a filter expression for multiple types")
            payload["type"] = types[0]
        if sort:
            payload["sorts"] = [{("property" if k == "property_key" else k): v
                                  for k, v in sort.items()}]
        if filters is not None:
            payload["filter" if isinstance(filters, str) else "filters"] = filters
        return self._request("POST", "/search", params=self._pagination_params(offset, limit), json=payload)

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
    def getMember(self, spaceId, objectId):
        if objectId == "me":
            return self._request("GET", f"/spaces/{spaceId}/members/me")
        offset = 0
        while True:
            page = self.getMembers(spaceId, offset, 100)
            for member in page["data"]:
                if member.get("id") == objectId:
                    return member
            if not page.get("has_more"):
                raise ValueError(f"Member not found: {objectId}")
            offset += 100

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
    def getTemplate(self, spaceId, typeId, templateId):
        return self.getObject(spaceId, templateId)

    def getTemplates(self, spaceId, typeId, offset=0, limit=100, filters=None):
        raise NotImplementedError("v2 has no template-list endpoint; retrieve a template by ID")

    def createTemplate(self, spaceId, data):
        return self._request("POST", f"/spaces/{spaceId}/templates", json=data)

    # --- Property ---
    def getProperties(
        self, spaceId: str, offset: int = 0, limit: int = 100, filters: dict | None = None
    ):
        options = self._pagination_params(offset, limit, filters)
        return self._request("GET", f"/spaces/{spaceId}/properties", params=options)

    def getProperty(self, spaceId, propertyId):
        offset = 0
        while True:
            page = self.getProperties(spaceId, offset, 100)
            for prop in page["data"]:
                if prop["key"] == propertyId:
                    return prop
            if not page.get("has_more"):
                raise ValueError(f"Property not found: {propertyId}")
            offset += 100

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
            "GET", f"/spaces/{spaceId}/properties/{propertyId}/options", params=options
        )

    def getTag(self, spaceId, propertyId, tagId):
        offset = 0
        while True:
            page = self.getTags(spaceId, propertyId, offset, 100)
            for tag in page["data"]:
                if tag["name"] == tagId:
                    return {"tag": tag}
            if not page.get("has_more"):
                raise ValueError(f"Option not found: {tagId}")
            offset += 100

    def createTag(self, spaceId, propertyId, data):
        raise NotImplementedError("v2 creates missing options through object writes with create_missing_options=True")

    def updateTag(self, spaceId, propertyId, tagId, data):
        raise NotImplementedError("v2 does not expose an option-update endpoint")

    def deleteTag(self, spaceId, propertyId, tagId):
        raise NotImplementedError("v2 does not expose an option-delete endpoint")


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

            if key == "type" and isinstance(value, dict):
                from anytype import type

                setattr(
                    self,
                    key,
                    type.Type()._from_api(self._apiEndpoints, value | {"space_id": self.space_id}),
                )
            elif key == "properties" and isinstance(value, list):
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
