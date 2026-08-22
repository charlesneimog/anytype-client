import datetime
import random
import warnings

from .api import APIWrapper
from .tag import Tag
from .utils import requires_auth, _ANYTYPE_PROPERTIES_COLORS

_VALUE_FIELDS = {
    "checkbox",
    "text",
    "number",
    "select",
    "multi_select",
    "date",
    "files",
    "url",
    "email",
    "phone",
    "objects",
}


def _format_date(value) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        try:
            parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.datetime.strptime(value, "%d/%m/%Y")
            except ValueError as error:
                raise ValueError(
                    "Date values must use DD/MM/YYYY, YYYY-MM-DD, or RFC3339 format"
                ) from error
    elif isinstance(value, datetime.datetime):
        parsed = value
    elif isinstance(value, datetime.date):
        parsed = datetime.datetime.combine(value, datetime.time())
    else:
        raise ValueError("Date property must be a string, date, datetime, or None")

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


class Property(APIWrapper):
    """
    Base class for all property types in the system. Provides shared interface for accessing,
    setting, and serializing values to a JSON-compatible format for API communication.

    Attributes:
        name (str): The name of the property.
        id (str): The unique identifier of the property.
        key (str): Internal key reference for the property (if applicable).
        format (str): Format/type of the property (e.g., "text", "number").
        space_id (str): Identifier for the space/environment this property belongs to.

    Methods:
        value (property): Getter and setter for the property's value, dispatches by property type.
    """

    __slots__ = (
        "name",
        "id",
        "key",
        "_apiEndpoints",
        "_json",
        "object",
        "format",
        "space_id",
        "_is_set",
    )

    def __init__(self, name: str = ""):
        self.id: str = ""
        self.name: str = name
        self.key: str = ""
        self.space_id: str = ""
        self._is_set = False

    @classmethod
    def _from_api(cls, api, data: dict):
        property_class = cls
        if cls is Property:
            property_class = cls._FACTORY.get(data.get("format"))
            if property_class is None:
                raise ValueError(f"Unsupported property format: {data.get('format')}")

        instance = property_class()
        instance._apiEndpoints = api
        instance._json = data
        instance._add_attrs_from_dict(data)

        def tag_from_api(tag_data: dict) -> Tag:
            tag = Tag._from_api(
                api,
                tag_data
                | {
                    "space_id": instance.space_id,
                    "property_id": instance.id,
                },
            )
            tag._property_id = instance.id
            return tag

        # Object responses embed complete tags, while create/update requests expect
        # their IDs (or keys). Keep the rich response representation as Tag objects
        # so it can be serialized again without another lookup.
        if isinstance(instance, Select) and isinstance(instance.select, dict):
            instance.select = tag_from_api(instance.select)
        elif isinstance(instance, MultiSelect):
            instance.multi_select = [
                tag_from_api(tag) if isinstance(tag, dict) else tag for tag in instance.multi_select
            ]

        instance._is_set = any(field in data for field in _VALUE_FIELDS)
        return instance

    @property
    def is_set(self) -> bool:
        return self._is_set

    def _property_key(self) -> str:
        if self.key:
            return self.key
        if not self.id or self._apiEndpoints is None:
            raise ValueError(f"Property '{self.name}' has no API key")

        response = self._apiEndpoints.getProperty(self.space_id, self.id)
        definition = response.get("property", {})
        self.key = definition.get("key", "")
        if not self.key:
            raise ValueError(f"Property '{self.name}' has no API key")
        return self.key

    def _get_json(self) -> dict:
        """Serialize this property to an Anytype PropertyLinkWithValue."""
        json_dict = {"key": self._property_key()}
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
            json_dict["date"] = _format_date(self.value)
        elif isinstance(self, Files):
            json_dict["files"] = self.value
        elif isinstance(self, Url):
            json_dict["url"] = self.value
        elif isinstance(self, Email):
            json_dict["email"] = self.value
        elif isinstance(self, Phone):
            json_dict["phone"] = self.value
        elif isinstance(self, Objects):
            values = self.value if isinstance(self.value, list) else [self.value]
            object_ids = []
            for value in values:
                if isinstance(value, str):
                    object_id = value
                else:
                    object_id = getattr(value, "id", "")
                if not object_id:
                    raise ValueError("Objects properties require object IDs or Object instances")
                object_ids.append(object_id)
            json_dict["objects"] = object_ids
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
            if isinstance(value, (str, Tag)):
                self.select = value
            else:
                raise ValueError("Value for Select property must be a string or Tag")
        elif isinstance(self, MultiSelect):
            if isinstance(value, list) and all(isinstance(item, (str, Tag)) for item in value):
                self.multi_select = value
            else:
                raise ValueError("Value for MultiSelect property must be a list of strings or Tags")
        elif isinstance(self, Date):
            if value is None or isinstance(value, (str, datetime.date, datetime.datetime)):
                self.date = value
            else:
                raise ValueError(
                    "Value for Date property must be a string, date, datetime, or None"
                )
        elif isinstance(self, Files):
            if isinstance(value, list):
                self.files = value
            else:
                raise ValueError("Value for Files property must be a list of file IDs")
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
            if isinstance(value, (str, list)) or getattr(value, "id", ""):
                self.objects = value
            else:
                raise ValueError("Value for Objects property must contain object IDs or Objects")
        else:
            raise ValueError("Format not supported")
        self._is_set = True

    _FACTORY: dict[str, type["Property"]] = {}

    @classmethod
    def from_format(cls, name: str, fmt: str) -> "Property":
        try:
            return cls._FACTORY[fmt](name)
        except KeyError:
            raise ValueError(f"Unsupported property format: {fmt}")


class Text(Property):
    """
    Represents a text property.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "text"
        self.text = ""

    def __repr__(self):
        return f"<Text({self.name})>"


class Number(Property):
    """
    Represents a numeric property (integer or float).
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "number"
        self.number: int | float = 0

    def __repr__(self):
        return f"<Number({self.name})>"


class Select(Property):
    """
    Represents a select (single-choice) property using predefined tags.

    Methods:
        create_tag(name, color, create_if_exists): Creates a tag in the property.
        get_tags(): Fetches all tags associated with the property.
        get_tag(tag_id): Fetches a specific tag by ID.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "select"
        self.select = ""

    @requires_auth
    def create_tag(self, name: str, color: str = "red", create_if_exists: bool = False) -> Tag:
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

        if self._apiEndpoints is None:
            raise Exception("Internal error, please report")

        response = self._apiEndpoints.createTag(self.space_id, self.id, data)
        tag = Tag._from_api(
            self._apiEndpoints, response.get("tag", []) | {"space_id": self.space_id}
        )
        return tag

    @requires_auth
    def get_tags(self, offset: int = 0, limit: int = 100, filters: dict | None = None) -> list[Tag]:
        """
        Retrieves all tags associated with the property.

        Returns:
            A list of Tag instances representing the tags associated with the property.

        Raises:
            Raises an error if the request to the API fails.
        """
        if self._apiEndpoints is None:
            raise Exception("Internal error, please report")

        response = self._apiEndpoints.getTags(self.space_id, self.id, offset, limit, filters)
        types = [
            Tag._from_api(
                self._apiEndpoints, data | {"space_id": self.space_id, "property_id": self.id}
            )
            for data in response.get("data", [])
        ]
        return types

    @requires_auth
    def get_tag(self, tag_id: str) -> Tag:
        """
        Retrieves a specific tag by its ID.

        Parameters:
            tag_id (str): The ID of the tag to retrieve.

        Returns:
            A Tag instance representing the retrieved tag.

        Raises:
            Raises an error if the request to the API fails.
        """
        if self._apiEndpoints is None:
            raise Exception("Internal error, please report")

        response = self._apiEndpoints.getTag(self.space_id, self.id, tag_id)
        tag = Tag._from_api(
            self._apiEndpoints, response.get("tag", []) | {"space_id": self.space_id}
        )
        return tag

    def __repr__(self):
        return f"<Select({self.name})>"


class MultiSelect(Property):
    """
    Represents a multi-select (multiple-choice) property using predefined tags.

    Methods:
        create_tag(name, color, create_if_exists): Creates a tag in the property.
        get_tags(): Fetches all tags associated with the property.
        get_tag(tag_id): Fetches a specific tag by ID.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "multi_select"
        self.multi_select: list = []

    @requires_auth
    def create_tag(self, name: str, color: str = "red", create_if_exists: bool = False) -> Tag:
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

        if self._apiEndpoints is None:
            raise Exception("Internal error, please report")

        response = self._apiEndpoints.createTag(self.space_id, self.id, data)
        tag = Tag._from_api(
            self._apiEndpoints, response.get("tag", []) | {"space_id": self.space_id}
        )
        return tag

    @requires_auth
    def get_tags(self, offset: int = 0, limit: int = 100, filters: dict | None = None) -> list[Tag]:
        """
        Retrieves all tags associated with the property.

        Returns:
            A list of Tag instances representing the tags associated with the property.

        Raises:
            Raises an error if the request to the API fails.
        """
        if self._apiEndpoints is None:
            raise Exception("Internal error, please report")

        response = self._apiEndpoints.getTags(self.space_id, self.id, offset, limit, filters)
        types = [
            Tag._from_api(
                self._apiEndpoints, data | {"space_id": self.space_id, "property_id": self.id}
            )
            for data in response.get("data", [])
        ]
        return types

    @requires_auth
    def get_tag(self, tag_id: str) -> Tag:
        """
        Retrieves a specific tag by its ID.

        Parameters:
            tag_id (str): The ID of the tag to retrieve.

        Returns:
            A Tag instance representing the retrieved tag.

        Raises:
            Raises an error if the request to the API fails.
        """
        if self._apiEndpoints is None:
            raise Exception("Internal error, please report")

        response = self._apiEndpoints.getTag(self.space_id, self.id, tag_id)
        tag = Tag._from_api(
            self._apiEndpoints, response.get("tag", []) | {"space_id": self.space_id}
        )
        return tag

    def __repr__(self):
        return f"<MultiSelect({self.name})>"


class Date(Property):
    """
    Represents a date property (date, datetime, DD/MM/YYYY, or RFC3339 string).
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "date"
        self.date: str | datetime.date | datetime.datetime | None = ""

    def __repr__(self):
        return f"<Date({self.name})>"


class Files(Property):
    """
    Represents a files property as a list of file IDs.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "files"
        self.files = None

    def __repr__(self):
        return f"<Files({self.name})>"


class Checkbox(Property):
    """
    Represents a checkbox (boolean) property.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "checkbox"
        self.checkbox = False

    def __repr__(self):
        return f"<Checkbox({self.name})>"


class Url(Property):
    """
    Represents a URL property.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "url"
        self.url = ""

    def __repr__(self):
        return f"<Url({self.name})>"


class Email(Property):
    """
    Represents an email address property.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "email"
        self.email = ""

    def __repr__(self):
        return f"<Email({self.name})>"


class Phone(Property):
    """
    Represents a phone number property.
    """

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.format = "phone"
        self.phone = ""

    def __repr__(self):
        return f"<Phone({self.name})>"


class Objects(Property):
    """
    Represents links to other objects, supplied as object IDs or Object instances.
    """

    def __init__(self, name: str = ""):
        self.format = "objects"
        super().__init__(name)
        self.objects = []

    def __repr__(self):
        return f"<Objects({self.name})>"


Property._FACTORY = {
    "text": Text,
    "number": Number,
    "select": Select,
    "multi_select": MultiSelect,
    "date": Date,
    "files": Files,
    "checkbox": Checkbox,
    "url": Url,
    "email": Email,
    "phone": Phone,
    "objects": Objects,
}
