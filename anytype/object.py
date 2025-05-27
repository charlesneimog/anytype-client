import re

from .type import Type
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

    Note that these property names are derived from the corresponding name in the Anytype GUI. They are all lowercase with spaces replaced by underscores. For instance, a property called `Release Year` in the Anytype GUI will be accessed as `release_year` in the object, and a property called `Publication Date` will be accessed as `publication_date`.

    """

    def __init__(self, name: str = "", type: Type | None = None):
        self._apiEndpoints: apiEndpoints | None = None
        self._icon: Icon = Icon()
        self._values: dict = {}
        self.type: None | Type = None
        self.type_key: str = ""

        self.id: str = ""
        self.source: str = ""
        self.name: str = name
        self.body: str = ""
        self.description: str = ""
        self.details = []
        self.layout: str = "basic"

        self.properties: dict = {}
        if type is not None:
            for prop in type.properties:
                if prop.key not in _ANYTYPE_SYSTEM_RELATIONS:
                    self.properties[prop.name] = prop
            self.type = type

        self.root_id: str = ""
        self.space_id: str = ""
        self.template_id: str = ""

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

    def add_type(self, type: Type):
        """
        Adds a type for an Object.

        Parameters:
            type (anytype.Type): Type from the space retrieved using `space.get_types()[0]`, `space.get_type(type)`, `space.get_type_byname("Articles")`

        """
        self.template_id = type.template_id
        self.type_key = type.key

    def add_title1(self, text) -> None:
        """
        Adds a level 1 title to the object's body.

        Parameters:
            text (str): The text to be added as a level 1 title.

        """
        self.body += f"# {text}\n"

    def add_title2(self, text) -> None:
        """
        Adds a level 2 title to the object's body.

        Parameters:
            text (str): The text to be added as a level 2 title.

        """
        self.body += f"## {text}\n"

    def add_title3(self, text) -> None:
        """
        Adds a level 3 title to the object's body.

        Parameters:
            text (str): The text to be added as a level 3 title.

        """
        self.body += f"### {text}\n"

    def add_text(self, text) -> None:
        """
        Adds plain text to the object's body.

        Parameters:
            text (str): The text to be added.

        """
        self.body += f"{text}\n"

    def add_codeblock(self, code, language="") -> None:
        """
        Adds a code block to the object's body.

        Parameters:
            code (str): The code to be added.
            language (str, optional): The programming language of the code block. Default is an empty string.

        """
        self.body += f"``` {language}\n{code}\n```\n"

    def add_bullet(self, text) -> None:
        """
        Adds a bullet point to the object's body.

        Parameters:
            text (str): The text to be added as a bullet point.

        """
        self.body += f"- {text}\n"

    def add_checkbox(self, text, checked=False) -> None:
        """
        Adds a checkbox to the object's body.

        Parameters:
            text (str): The text to be added next to the checkbox.
            checked (bool, optional): Whether the checkbox is checked. Default is False.

        """
        self.body += f"- [x] {text}\n" if checked else f"- [ ] {text}\n"

    def add_image(self, image_url: str, alt: str = "", title: str = "") -> None:
        """
        Adds an image to the object's body.

        Parameters:
            image_url (str): The URL of the image.
            alt (str, optional): The alternative text for the image. Default is an empty string.
            title (str, optional): The title of the image. Default is an empty string.

        """
        if title:
            self.body += f'![{alt}]({image_url} "{title}")\n'
        else:
            self.body += f"![{alt}]({image_url})\n"

    def __repr__(self):
        if self.type:
            if self.type.name != "":
                return f"<Object(name={self.name}, type={self.type.name})>"
            else:
                return f"<Object(name={self.name})>"
        else:
            return f"<Object(name={self.name})>"
