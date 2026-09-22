"""Typed blocks for AnyBlock 2.0's flat, indentation-based document format."""
from copy import deepcopy


class Block:
    """Superclass of every block kind.

    Fields use the v2 wire names (``indent``, ``background_color``, etc.).
    ``from_dict`` dispatches by type and preserves unknown fields and future kinds.
    Nested table cell blocks may also be supplied as Block instances.
    """

    type = None
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.type:
            Block._registry[cls.type] = cls

    def __init__(self, *, id=None, indent=None, **fields):
        if id is not None:
            self.id = id
        if indent is not None:
            if isinstance(indent, bool) or not isinstance(indent, int) or not 0 <= indent <= 32:
                raise ValueError("Block indent must be an integer between 0 and 32")
            self.indent = indent
        if "type" in fields and self.type and fields["type"] != self.type:
            raise ValueError("Block type does not match its subclass")
        self.__dict__.update(deepcopy(fields))
        if not self.type:
            raise ValueError("Block requires a type")

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not isinstance(data.get("type"), str):
            raise ValueError("A block must be a mapping with a string type")
        fields = deepcopy(data)
        block_type = fields.pop("type")
        subclass = cls._registry.get(block_type, Block)
        if subclass is Block:
            fields["type"] = block_type
        instance = subclass.__new__(subclass)
        Block.__init__(instance, **fields)
        return instance

    def to_dict(self, *, for_create=False):
        """Serialize without sharing mutable data; omit server IDs on insertion."""
        def encode(value):
            if isinstance(value, Block):
                return value.to_dict(for_create=for_create)
            if isinstance(value, list):
                return [encode(item) for item in value]
            if isinstance(value, dict):
                return {key: encode(item) for key, item in value.items()
                        if not (for_create and key in ("id", "fields"))}
            if hasattr(value, "_get_json"):
                return value._get_json()
            return deepcopy(value)
        return {"type": self.type, **encode(self.__dict__)}

    def __repr__(self):
        return f"{self.__class__.__name__}({self.to_dict()!r})"


class Text(Block):
    """A paragraph. Inline formatting uses AnyBlock's text syntax."""
    type = "paragraph"

    def __init__(self, text="", **fields):
        super().__init__(text=text, **fields)


Paragraph = Text


class Heading1(Text):
    """AnyBlock ``heading_1`` block."""
    type = "heading_1"


class Heading2(Text):
    """AnyBlock ``heading_2`` block."""
    type = "heading_2"


class Heading3(Text):
    """AnyBlock ``heading_3`` block."""
    type = "heading_3"


class Heading4(Text):
    """AnyBlock ``heading_4`` block."""
    type = "heading_4"


class Header4(Text):
    """AnyBlock ``header_4`` block."""
    type = "header_4"


class Quote(Text):
    """AnyBlock ``quote`` block."""
    type = "quote"


class Code(Text):
    """AnyBlock ``code`` block."""
    type = "code"


class Title(Text):
    """AnyBlock ``title`` block."""
    type = "title"


class Description(Text):
    """AnyBlock ``description`` block."""
    type = "description"


class Checkbox(Text):
    """AnyBlock ``checkbox`` block."""
    type = "checkbox"


class BulletedListItem(Text):
    """AnyBlock ``bulleted_list_item`` block."""
    type = "bulleted_list_item"


class NumberedListItem(Text):
    """AnyBlock ``numbered_list_item`` block."""
    type = "numbered_list_item"


class Toggle(Text):
    """AnyBlock ``toggle`` block."""
    type = "toggle"


class Callout(Text):
    """AnyBlock ``callout`` block."""
    type = "callout"


class ToggleHeading1(Text):
    """AnyBlock ``toggle_heading_1`` block."""
    type = "toggle_heading_1"


class ToggleHeading2(Text):
    """AnyBlock ``toggle_heading_2`` block."""
    type = "toggle_heading_2"


class ToggleHeading3(Text):
    """AnyBlock ``toggle_heading_3`` block."""
    type = "toggle_heading_3"


class File(Block):
    """AnyBlock ``file`` block."""
    type = "file"


class Image(Block):
    """AnyBlock ``image`` block."""
    type = "image"


class Video(Block):
    """AnyBlock ``video`` block."""
    type = "video"


class Audio(Block):
    """AnyBlock ``audio`` block."""
    type = "audio"


class PDF(Block):
    """AnyBlock ``pdf`` block."""
    type = "pdf"


class Bookmark(Block):
    """AnyBlock ``bookmark`` block."""
    type = "bookmark"


class Link(Block):
    """AnyBlock ``link`` block."""
    type = "link"


class Divider(Block):
    """AnyBlock ``divider`` block."""
    type = "divider"


class Row(Block):
    """AnyBlock ``row`` block."""
    type = "row"


class Column(Block):
    """AnyBlock ``column`` block."""
    type = "column"


class Group(Block):
    """AnyBlock ``group`` block."""
    type = "group"


class Table(Block):
    """AnyBlock ``table`` block."""
    type = "table"


class Embed(Text):
    """AnyBlock ``embed`` block."""
    type = "embed"


class Equation(Text):
    """AnyBlock ``equation`` block."""
    type = "equation"


class TableOfContents(Block):
    """AnyBlock ``table_of_contents`` block."""
    type = "table_of_contents"


class PropertyBlock(Block):
    """AnyBlock ``property`` block."""
    type = "property"


class DataView(Block):
    """AnyBlock ``dataview`` block."""
    type = "dataview"


class Widget(Block):
    """AnyBlock ``widget`` block."""
    type = "widget"


class Chat(Block):
    """AnyBlock ``chat`` block."""
    type = "chat"


class FeaturedProperties(Block):
    """AnyBlock ``featured_properties`` block."""
    type = "featured_properties"


class IconBlock(Block):
    """AnyBlock ``icon`` block."""
    type = "icon"


class Math(Equation):
    """A LaTeX equation (wire type ``equation``)."""

    def __init__(self, text="", **fields):
        fields.setdefault("processor", "latex")
        super().__init__(text, **fields)


# Keep equation dispatch independent of the convenience Math constructor.
Block._registry["equation"] = Equation

__all__ = ['Block', 'Text', 'Paragraph', 'Heading1', 'Heading2', 'Heading3', 'Heading4', 'Header4', 'Quote', 'Code', 'Title', 'Description', 'Checkbox', 'BulletedListItem', 'NumberedListItem', 'Toggle', 'Callout', 'ToggleHeading1', 'ToggleHeading2', 'ToggleHeading3', 'File', 'Image', 'Video', 'Audio', 'PDF', 'Bookmark', 'Link', 'Divider', 'Row', 'Column', 'Group', 'Table', 'Embed', 'Equation', 'TableOfContents', 'PropertyBlock', 'DataView', 'Widget', 'Chat', 'FeaturedProperties', 'IconBlock', 'Math']
