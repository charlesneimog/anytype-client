from .api import APIWrapper, apiEndpoints, T
from .tag import Tag
from .utils import requires_auth, _ANYTYPE_PROPERTIES_COLORS
import warnings
import random
from enum import Enum
import datetime
from typing import Type


class PropertyFormat(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    FILES = "files"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    OBJECTS = "objects"


class Property(APIWrapper):
    __slots__ = (
        "name",
        "id",
        "key",
        "_apiEndpoints",
        "_json",
        "object",
        "format",
        "space_id",
    )

    def __init__(self, name: str = ""):
        self.id: str = ""
        self.name: str = name

    @requires_auth
    def _get_json(self) -> dict:
        """
        Retrieves all properties associated with the property.

        Returns:
            A list of Property instances representing the properties associated with the property.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getProperty(self.space_id, self.id)
        json_dict = response.get("property", {})
        if isinstance(self, Checkbox):
            json_dict["checkbox"] = self.value
        elif isinstance(self, Text):
            json_dict["text"] = self.value
        elif isinstance(self, Number):
            json_dict["number"] = self.value
        elif isinstance(self, Select):
            all_tags = None  # self.get_tags()
            if isinstance(self.select, Tag):
                json_dict["select"] = self.select.id
            else:
                if all_tags is None:
                    all_tags = self.get_tags()
                notfound = True
                for found_tag in all_tags:
                    if found_tag.name == self.select:
                        json_dict["select"] = found_tag.id
                        notfound = False
                        break
                if notfound:
                    random_color = random.choice(_ANYTYPE_PROPERTIES_COLORS)
                    tag_obj = self.create_tag(self.select, random_color)
                    warnings.warn(f"Tag '{tag_obj.name}' not exist, creating it")
                    json_dict["select"] = tag_obj.id

            print(json_dict)
        elif isinstance(self, MultiSelect):
            tag_ids = []
            all_tags = None  # self.get_tags()
            for tag in self.multi_select:
                if isinstance(tag, Tag):
                    tag_ids.append(tag.id)
                else:
                    if all_tags is None:
                        all_tags = self.get_tags()
                    notfound = True
                    for found_tag in all_tags:
                        if found_tag.name == tag:
                            tag_ids.append(found_tag.id)
                            notfound = False
                            break
                    if notfound:
                        random_color = random.choice(_ANYTYPE_PROPERTIES_COLORS)
                        tag_obj = self.create_tag(tag, random_color)
                        tag_ids.append(tag_obj.id)
                        warnings.warn(f"Tag '{tag_obj.name}' not exist, creating it")

            json_dict["multi_select"] = tag_ids
        elif isinstance(self, Date):
            if self.value is None:
                json_dict["date"] = None
            elif isinstance(self.value, str):
                dt = datetime.datetime.strptime(self.date, "%d/%m/%Y")
                json_dict["date"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            elif isinstance(self.value, datetime.datetime):
                json_dict["date"] = self.date.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif isinstance(self, Files):
            json_dict["files"] = self.value
        elif isinstance(self, Url):
            json_dict["url"] = self.value
        elif isinstance(self, Email):
            json_dict["email"] = self.value
        elif isinstance(self, Phone):
            json_dict["phone"] = self.value
        elif isinstance(self, Objects):
            json_dict["objects"] = self.value
        else:
            raise ValueError("Format not supported")
        return json_dict

    @property
    def value(self):
        if isinstance(self, Checkbox):
            return self.checkbox
        elif isinstance(self, Text):
            return self.text
        elif isinstance(self, Number):
            return self.number
        elif isinstance(self, Select):
            return self.select
        elif isinstance(self, MultiSelect):
            return self.multi_select
        elif isinstance(self, Date):
            return self.date
        elif isinstance(self, Files):
            return self.files
        elif isinstance(self, Url):
            return self.url
        elif isinstance(self, Email):
            return self.email
        elif isinstance(self, Phone):
            return self.phone
        elif isinstance(self, Objects):
            return self.objects
        else:
            raise ValueError("Format not supported")

    @value.setter
    def value(self, value):
        if isinstance(self, Checkbox):
            if type(value) is bool:
                self.checkbox = value
            else:
                raise ValueError("Value for Checkbox property must be boolean")
        elif isinstance(self, Text):
            if type(value) is str:
                self.text = value
            else:
                raise ValueError("Value for Text property must be string")
        elif isinstance(self, Number):
            if type(value) is int or type(value) is float:
                self.number = value
            else:
                raise ValueError("Value for Number property must be number")
        elif isinstance(self, Select):
            if type(value) is str:
                self.select = value
            else:
                raise ValueError("Value for Select property must be string")
        elif isinstance(self, MultiSelect):
            if type(value) is list:
                self.multi_select = value
            else:
                raise ValueError("Value for MultiSelect property must be list of strings")
        elif isinstance(self, Date):
            if type(value) is str or type(value) is datetime.datetime:
                self.date = value
            else:
                raise ValueError("Value for Date property must be string or datetime.datetime")
        elif isinstance(self, Files):
            raise ValueError("Files are not implemented yet")
        elif isinstance(self, Url):
            if type(value) is str:
                self.url = value
            else:
                raise ValueError("Value for Url property must be string")
        elif isinstance(self, Email):
            if isinstance(value, str):
                self.email = value
            else:
                raise ValueError("Value for Email property must be string")
        elif isinstance(self, Phone):
            if isinstance(value, str):
                self.phone = value
            else:
                raise ValueError("Value for Phone property must be string")
        elif isinstance(self, Objects):
            raise ValueError("Files are not implemented yet")
        else:
            raise ValueError("Format not supported")


class Text(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "text"
        self.text = ""

    def __repr__(self):
        return f"<Text({self.name})>"


class Number(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "number"
        self.number = 0

    def __repr__(self):
        return f"<Number({self.name})>"


class Select(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "select"
        self.select = None

    @requires_auth
    def create_tag(self, name: str, color: str = "red", create_if_exists: bool = False):
        """
        Creates a new tag with the specified name for a `anytype.PropertyFormat.SELECT` or `anytype.PropertyFormat.MULTI_SELECT` property.

        Parameters:
            name (str): The name of the tag to create.

        Returns:
            A Tag instance representing the created tag.

        Raises:
            Raises an error if the request to the API fails.
        """
        data = {"name": name, "color": color}
        if not create_if_exists:
            for tag in self.get_tags():
                if tag.name == name:
                    warnings.warn(f"Tag '{name}' already exists, returning existing tag")
                    return tag

        response = self._apiEndpoints.createTag(self.space_id, self.id, data)
        tag = Tag._from_api(self._apiEndpoints, response.get("tag", []))
        return tag

    @requires_auth
    def get_tags(self) -> list[Tag]:
        """
        Retrieves all tags associated with the property.

        Returns:
            A list of Tag instances representing the tags associated with the property.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getTags(self.space_id, self.id)
        types = [
            Tag._from_api(
                self._apiEndpoints, data | {"space_id": self.space_id, "property_id": self.id}
            )
            for data in response.get("data", [])
        ]
        return types

    @requires_auth
    def get_tag(self, tag_id: str):
        """
        Retrieves a specific tag by its ID.

        Parameters:
            tag_id (str): The ID of the tag to retrieve.

        Returns:
            A Tag instance representing the retrieved tag.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getTag(self.space_id, self.id, tag_id)
        tag = Tag._from_api(self._apiEndpoints, response.get("tag", []))
        return tag

    def __repr__(self):
        return f"<Select({self.name})>"


class MultiSelect(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "multi_select"
        self.multi_select: list = []

    @requires_auth
    def create_tag(self, name: str, color: str = "red", create_if_exists: bool = False):
        """
        Creates a new tag with the specified name for a `anytype.PropertyFormat.SELECT` or `anytype.PropertyFormat.MULTI_SELECT` property.

        Parameters:
            name (str): The name of the tag to create.

        Returns:
            A Tag instance representing the created tag.

        Raises:
            Raises an error if the request to the API fails.
        """
        data = {"name": name, "color": color}
        if not create_if_exists:
            for tag in self.get_tags():
                if tag.name == name:
                    warnings.warn(f"Tag '{name}' already exists, returning existing tag")
                    return tag

        response = self._apiEndpoints.createTag(self.space_id, self.id, data)
        tag = Tag._from_api(self._apiEndpoints, response.get("tag", []))
        return tag

    @requires_auth
    def get_tags(self) -> list[Tag]:
        """
        Retrieves all tags associated with the property.

        Returns:
            A list of Tag instances representing the tags associated with the property.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getTags(self.space_id, self.id)
        types = [
            Tag._from_api(
                self._apiEndpoints, data | {"space_id": self.space_id, "property_id": self.id}
            )
            for data in response.get("data", [])
        ]
        return types

    @requires_auth
    def get_tag(self, tag_id: str):
        """
        Retrieves a specific tag by its ID.

        Parameters:
            tag_id (str): The ID of the tag to retrieve.

        Returns:
            A Tag instance representing the retrieved tag.

        Raises:
            Raises an error if the request to the API fails.
        """
        response = self._apiEndpoints.getTag(self.space_id, self.id, tag_id)
        tag = Tag._from_api(self._apiEndpoints, response.get("tag", []))
        return tag

    def __repr__(self):
        return f"<MultiSelect({self.name})>"


class Date(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "date"
        self.date = None

    def __repr__(self):
        return f"<Date({self.name})>"


class Files(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "files"
        self.files = None

    def __repr__(self):
        return f"<Files({self.name})>"


class Checkbox(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "checkbox"
        self.checkbox = False

    def __repr__(self):
        return f"<Checkbox({self.name})>"


class Url(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "url"
        self.url = ""

    def __repr__(self):
        return f"<Url({self.name})>"


class Email(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "email"
        self.email = ""

    def __repr__(self):
        return f"<Email({self.name})>"


class Phone(Property):
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "phone"
        self.phone = ""

    def __repr__(self):
        return f"<Phone({self.name})>"


class Objects(Property):
    def __init__(self, name: str = ""):
        self.format = "objects"
        super().__init__(name)
        self.objects = []

    def __repr__(self):
        return f"<Objects({self.name})>"
