import copy
import re

from . import block as blocks
from .type import Type
from .template import Template
from .icon import Icon
from .property import Property
from .api import apiEndpoints, APIWrapper
from .utils import requires_auth, _ANYTYPE_SYSTEM_RELATIONS


class Object(APIWrapper):
    """
    Represents an object within a specific space, allowing creation and manipulation of its properties. The object can be customized with various attributes such as `name`, `icon`, `body`, `description`, and more. This class provides methods to export objects and add different content types to the object body, such as titles, text, code blocks, checkboxes, and bullet points.

    ### IMPORTANT

    Certain properties of an object, such as:

    - `DOI` in a collection of articles;
    - `Release Year` in albums;
    - `Genre` in music collections;
    - `Author` in book collections;
    - `Publication Date` in documents;
    - `Rating` in review-based objects;
    - `Tags` in categorized objects;

    are accessible through the class properties. For example, if an object is created with a `Type` (e.g., `anytype.Type`) that includes a `DOI` property, the DOI URL can be set during the object creation using `Object.doi`.

    You can also provide a Template for this object.

    Note that these property names are derived from the corresponding name in the Anytype GUI. They are all lowercase with spaces replaced by underscores. For instance, a property called `Release Year` in the Anytype GUI will be accessed as `release_year` in the object, and a property called `Publication Date` will be accessed as `publication_date`.

    """

    def __init__(self, name: str = "", type: Type | str | None = None, template: Template | None = None,
                 blocks=None):
        self._apiEndpoints: apiEndpoints | None = None
        self._icon: Icon = Icon()
        self._values: dict = {}
        self.type: None | Type = None
        self.type_key: str = ""
        self.id: str = ""
        self.source: str = ""
        self.name: str = name
        self._markdown: str = ""
        self._markdown_dirty = False
        self.blocks = list(blocks or [])
        self.etag = ""
        self._snapshot = None
        self.archived: bool = False
        self.description: str = ""
        self.layout: str = "basic"
        self.root_id: str = ""
        self.space_id: str = ""
        self.template_id: str = template.id if template is not None else ""

        self.properties: dict = {}
        if type is not None:
            self.add_type(type)

    @staticmethod
    def _normalize_property_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

    def _property_for_attribute(self, name: str) -> Property | None:
        properties = self.__dict__.get("properties")
        if not isinstance(properties, dict):
            return None

        for prop in properties.values():
            if isinstance(prop, Property) and prop.key == name:
                return prop
        for prop in properties.values():
            if isinstance(prop, Property) and self._normalize_property_name(prop.name) == name:
                return prop
        return None

    def __getattr__(self, name):
        prop = self._property_for_attribute(name)
        if prop is not None:
            return prop.value
        properties = self.__dict__.get("properties", {})
        for key, value in properties.items():
            if key == name or self._normalize_property_name(key) == name:
                return value
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if not name.startswith("_"):
            prop = self._property_for_attribute(name)
            if prop is not None:
                prop.value = value
                return
            if name not in self.__dict__ and not hasattr(type(self), name):
                for key in self.__dict__.get("properties", {}):
                    if key == name or self._normalize_property_name(key) == name:
                        self.properties[key] = value
                        return
        object.__setattr__(self, name, value)

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, value):
        if isinstance(value, dict):
            new_icon = Icon()
            new_icon._update_with_json(value)
            self._icon = new_icon
        elif isinstance(value, str):
            # This is from chatgpt, please report is you know about emoji encode
            emoji_pattern = re.compile(
                "[\U0001f600-\U0001f64f"  # Emoticons
                "\U0001f300-\U0001f5ff"  # Misc Symbols and Pictographs
                "\U0001f680-\U0001f6ff"  # Transport & Map Symbols
                "\U0001f1e0-\U0001f1ff"  # Regional Indicator Symbols
                "\U00002702-\U000027b0"  # Dingbats
                "\U000024c2-\U0001f251"  # Enclosed characters and others
                "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs (includes 🤯)
                "]+",
                flags=re.UNICODE,
            )

            if bool(emoji_pattern.fullmatch(value)):
                self._icon.emoji = value
            else:
                raise Exception(f"Invalid icon format {value}")
        elif isinstance(value, Icon):
            self._icon = value
        elif value is None:
            self._icon = Icon("")
        else:
            raise Exception("Invalid icon format")

    @icon.getter
    def icon(self):
        return self._icon

    @property
    def markdown(self):
        """Read-only server export, or locally supplied creation markdown."""
        if not self._markdown and self.id and self._apiEndpoints is not None:
            data = self._apiEndpoints.getObject(self.space_id, self.id, format="md")
            self._markdown = data.get("markdown", "") if isinstance(data, dict) else data
        return self._markdown

    @markdown.setter
    def markdown(self, text):
        self._markdown = text
        self._markdown_dirty = True

    @classmethod
    def _from_api(cls, api, data):
        if isinstance(data.get("properties"), list):
            return super()._from_api(api, data)
        obj = cls()
        obj._apiEndpoints = api
        obj._json = copy.deepcopy(data)
        for key, value in data.items():
            if key == "blocks":
                obj.blocks = [blocks.Block.from_dict(item) for item in value]
            elif key == "properties":
                obj.properties = copy.deepcopy(value)
            elif key == "type":
                obj.type = value
                obj.type_key = value if isinstance(value, str) else value.get("key", "")
            elif key != "$schema":
                setattr(obj, key, value)
        obj.name = data.get("name", obj.properties.get("name", ""))
        obj.description = obj.properties.get("description", "")
        obj._snapshot = obj.to_document() if "blocks" in data else None
        obj._markdown_dirty = False
        return obj

    def _property_values(self):
        values = {}
        for key, prop in self.properties.items():
            if isinstance(prop, Property):
                if prop.is_set:
                    values[prop._property_key()] = prop.to_value()
            else:
                values[key] = copy.deepcopy(prop)
        values["name"] = self.name
        if self.description or "description" in values:
            values["description"] = self.description
        return values

    def to_document(self, *, for_create=False):
        """Serialize an AnyBlock 2.0 document, preserving typed block content."""
        type_key = self.type.key if isinstance(self.type, Type) else self.type
        doc = {"formatVersion": "2.0", "type": type_key or self.type_key or "page",
               "properties": self._property_values(),
               "blocks": [(item if isinstance(item, blocks.Block) else blocks.Block.from_dict(item))
                          .to_dict(for_create=for_create) for item in self.blocks]}
        if self.icon is not None:
            doc["icon"] = self.icon._get_json()
        for key in ("cover", "collection_items", "query_source"):
            if key in self.__dict__:
                doc[key] = copy.deepcopy(self.__dict__[key])
        return doc

    def add_block(self, block):
        """Append a Block (or wire mapping) locally and return it."""
        if not isinstance(block, blocks.Block):
            block = blocks.Block.from_dict(block)
        self.blocks.append(block)
        return block

    @requires_auth
    def patch(self, ops, **options):
        """Apply v2 operations atomically and reload this object."""
        result = self._apiEndpoints.updateObject(self.space_id, self.id, {"ops": ops},
                                                etag=self.etag or None, **options)
        if not options.get("dry_run"):
            refreshed = self._from_api(self._apiEndpoints,
                self._apiEndpoints.getObject(self.space_id, self.id) | {"space_id": self.space_id})
            self.__dict__.update(refreshed.__dict__)
        return result

    def insert_blocks(self, new_blocks, **position):
        return self.patch([{"op": "insert_blocks", "blocks": [
            (b if isinstance(b, blocks.Block) else blocks.Block.from_dict(b)).to_dict(for_create=True)
            for b in new_blocks], **position}])

    def update_block(self, block, **fields):
        return self.patch([{"op": "update_block", "id": block.id if isinstance(block, blocks.Block) else block,
                            "set": fields}])

    def delete_block(self, block, recursive=False):
        return self.patch([{"op": "delete_block", "id": block.id if isinstance(block, blocks.Block) else block,
                            "recursive": recursive}])

    def add_type(self, type: Type):
        """
        Adds a type for an Object.

        Parameters:
            type (anytype.Type): Type from the space retrieved using `space.get_types()[0]`, `space.get_type(type)`, `space.get_type_byname("Articles")`

        """
        if isinstance(type, str):
            self.type = type
            self.type_key = type
            return
        if not isinstance(type, Type) or not (type.key or type.id):
            raise ValueError("Type must be retrieved from or created in the Anytype API")

        existing_properties = self.__dict__.get("properties", {})
        properties = {}
        for prop in type.properties.values():
            if isinstance(prop, Property) and prop.key not in _ANYTYPE_SYSTEM_RELATIONS:
                cloned = copy.copy(prop)
                for value_attribute in ("multi_select", "files", "objects"):
                    value = getattr(cloned, value_attribute, None)
                    if isinstance(value, list):
                        setattr(cloned, value_attribute, list(value))
                cloned._is_set = False
                properties[prop.name] = cloned

        for existing_name, existing in existing_properties.items():
            if not isinstance(existing, Property) or not existing.is_set:
                continue
            matching_name = next(
                (
                    name
                    for name, prop in properties.items()
                    if prop.key and prop.key == existing.key
                ),
                existing_name,
            )
            properties[matching_name] = existing

        self.type = type
        self.type_key = type.key
        self.properties = properties
        if not self.template_id and type.template_id:
            self.template_id = type.template_id

    def add_title1(self, text):
        return self.add_block(blocks.Heading1(text))

    def add_title2(self, text):
        return self.add_block(blocks.Heading2(text))

    def add_title3(self, text):
        return self.add_block(blocks.Heading3(text))

    def add_text(self, text):
        return self.add_block(blocks.Text(text))

    def add_codeblock(self, code, language=""):
        return self.add_block(blocks.Code(code, language=language))

    def add_math(self, text):
        return self.add_block(blocks.Math(text))

    def add_bullet(self, text):
        return self.add_block(blocks.BulletedListItem(text))

    def add_checkbox(self, text, checked=False):
        return self.add_block(blocks.Checkbox(text, checked=checked))

    def add_quote(self, text):
        return self.add_block(blocks.Quote(text))

    def add_image(self, image_url, alt="", title=""):
        """Add an uploaded image ID; remote URLs are uploaded when creating the object."""
        if image_url.startswith(("http://", "https://")):
            raise ValueError("Upload the URL with space.upload_file_url first, then pass its id")
        return self.add_block(blocks.Image(object_id=image_url, name=title or alt))

    def __repr__(self):
        return f"<Object(name={self.name})>"
