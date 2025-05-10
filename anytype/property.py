from .api import APIWrapper
from .tag import Tag
from .utils import requires_auth, _ANYTYPE_PROPERTIES_COLORS
import warnings
import random


class Property(APIWrapper):
    # to avoid miss spelling errors
    __slots__ = (
        "name",
        "id",
        "key",
        "_format",
        "_checkbox",
        "_date",
        "_apiEndpoints",
        "_json",
        "object",
        "space_id",
        "_text",
        "_number",
        "_select",
        "_multi_select",
        "_files",
        "_url",
        "_email",
        "_phone",
        "_objects",
    )

    def __init__(self, key: str = ""):
        self.name: str = ""
        self.id: str = ""
        self.key: str = key
        self._format: str = ""

        # Initialize default properties
        self._checkbox = False
        self._date = None
        self._text = ""
        self._number = 0.0
        self._select = ""
        self._multi_select = []
        self._files = []
        self._url = ""
        self._email = ""
        self._phone = ""
        self._objects = []

    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, value):
        if not isinstance(value, str):
            raise ValueError("Format must be a string.")
        self._format = value

    @property
    def checkbox(self):
        if self._format != "checkbox":
            warnings.warn(
                f"Trying to access 'checkbox' for a property with format '{self._format}'"
            )
        return self._checkbox

    @checkbox.setter
    def checkbox(self, value):
        if self._format != "checkbox":
            warnings.warn(f"Trying to set 'checkbox' for a property with format '{self._format}'")
        if not isinstance(value, bool):
            raise TypeError("Expected a boolean value for 'checkbox'.")
        self._checkbox = value

    @property
    def date(self):
        if self._format != "date":
            warnings.warn(f"Trying to access 'date' for a property with format '{self._format}'")
        return self._date

    @date.setter
    def date(self, value):
        if self._format != "date":
            warnings.warn(f"Trying to set 'date' for a property with format '{self._format}'")
        self._date = value

    @property
    def text(self):
        if self._format != "text":
            warnings.warn(f"Trying to access 'text' for a property with format '{self._format}'")
        return self._text

    @text.setter
    def text(self, value):
        if self._format != "text":
            warnings.warn(f"Trying to set 'text' for a property with format '{self._format}'")
        if not isinstance(value, str):
            raise TypeError("Expected a string value for 'text'.")
        self._text = value

    @property
    def number(self):
        if self._format != "number":
            warnings.warn(f"Trying to access 'number' for a property with format '{self._format}'")
        return self._number

    @number.setter
    def number(self, value):
        if self._format != "number":
            warnings.warn(f"Trying to set 'number' for a property with format '{self._format}'")
        if not isinstance(value, (int, float)):
            raise TypeError("Expected an integer or float value for 'number'.")
        self._number = value

    @property
    def select(self):
        if self._format != "select":
            warnings.warn(f"Trying to access 'select' for a property with format '{self._format}'")
        return self._select

    @select.setter
    def select(self, value):
        if self._format != "select":
            warnings.warn(f"Trying to set 'select' for a property with format '{self._format}'")
        if not isinstance(value, str):
            raise TypeError("Expected a string value for 'select'.")
        self._select = value

    @property
    def multi_select(self):
        if self._format != "multi_select":
            warnings.warn(
                f"Trying to access 'multi_select' for a property with format '{self._format}'"
            )
        return self._multi_select

    @multi_select.setter
    def multi_select(self, value):
        if self._format != "multi_select":
            warnings.warn(
                f"Trying to set 'multi_select' for a property with format '{self._format}'"
            )

        if isinstance(value, str):
            value = [value]
            warnings.warn(
                "Multi-select properties must be a list, try to set value as list", UserWarning
            )

        if not isinstance(value, list):
            raise ValueError("Multi-select properties must be list of strings")
        self._multi_select = value

    @property
    def files(self):
        if self._format != "files":
            warnings.warn(f"Trying to access 'files' for a property with format '{self._format}'")
        return self._files

    @files.setter
    def files(self, value):
        if self._format != "files":
            warnings.warn(f"Trying to set 'files' for a property with format '{self._format}'")
        if not isinstance(value, list):
            raise TypeError("Expected a list value for 'files'.")
        self._files = value

    @property
    def url(self):
        if self._format != "url":
            warnings.warn(f"Trying to access 'url' for a property with format '{self._format}'")
        return self._url

    @url.setter
    def url(self, value):
        if self._format != "url":
            warnings.warn(f"Trying to set 'url' for a property with format '{self._format}'")
        if not isinstance(value, str):
            raise TypeError("Expected a string value for 'url'.")
        self._url = value

    @property
    def email(self):
        if self._format != "email":
            warnings.warn(f"Trying to access 'email' for a property with format '{self._format}'")
        return self._email

    @email.setter
    def email(self, value):
        if self._format != "email":
            warnings.warn(f"Trying to set 'email' for a property with format '{self._format}'")
        if not isinstance(value, str):
            raise TypeError("Expected a string value for 'email'.")
        self._email = value

    @property
    def phone(self):
        if self._format != "phone":
            warnings.warn(f"Trying to access 'phone' for a property with format '{self._format}'")
        return self._phone

    @phone.setter
    def phone(self, value):
        if self._format != "phone":
            warnings.warn(f"Trying to set 'phone' for a property with format '{self._format}'")
        if not isinstance(value, str):
            raise TypeError("Expected a string value for 'phone'.")
        self._phone = value

    @property
    def objects(self):
        if self._format != "objects":
            warnings.warn(f"Trying to access 'objects' for a property with format '{self._format}'")
        return self._objects

    @objects.setter
    def objects(self, value):
        if self._format != "objects":
            warnings.warn(f"Trying to set 'objects' for a property with format '{self._format}'")
        if not isinstance(value, list):
            raise TypeError("Expected a list value for 'objects'.")
        self._objects = value

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
        format = self._format
        if format == "checkbox":
            json_dict["checkbox"] = self.checkbox
        elif format == "text":
            json_dict["text"] = self.text
        elif format == "number":
            json_dict["number"] = self.number
        elif format == "select":
            json_dict["select"] = self.select
        elif format == "multi_select":
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
                        tag = self.create_tag(tag, random_color)
                        tag_ids.append(tag.id)
                        warnings.warn("Tag '{tag}' not exist, creating it")

            json_dict["multi_select"] = tag_ids
        elif format == "date":
            json_dict["date"] = self.date.isoformat() if self.date else None
        elif format == "files":
            json_dict["files"] = self.files
        elif format == "url":
            json_dict["url"] = self.url
        elif format == "email":
            json_dict["email"] = self.email
        elif format == "phone":
            json_dict["phone"] = self.phone
        elif format == "objects":
            json_dict["objects"] = self.objects
        else:
            raise ValueError("Formato não reconhecido")
        return json_dict

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

    @requires_auth
    def create_tag(self, name: str, color: str = "red", create_if_exists: bool = False):
        """
        Creates a new tag with the specified name.

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

    def __repr__(self):
        return f"<Property(name={self.name} | key={self.key})>"
